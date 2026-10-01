export * as TrpStructural from "./structural"

import { spawn } from "node:child_process"
import fs from "node:fs/promises"
import path from "node:path"
import { randomUUID } from "node:crypto"
import { Schema } from "effect"
import { TrpSpecification as S } from "./specification"
import { TrpEvidence as E } from "./evidence"
import SCRIPT from "./inspect_structure.py.txt"
import VERIFIER from "./verify_inspection.py.txt"
import catalog from "./structural_catalog.json"

export { SCRIPT, catalog }
export const VERSION = "trp-structural/1.1.0"
const Range = Schema.Struct({ start: Schema.Number, end: Schema.Number })
export const Options = Schema.Struct({
  format: Schema.Literals(["mmcif", "pdb"]),
  model: Schema.Number,
  chain: Schema.String.annotate({ description: "Author chain identifier, even when intervals use label_seq_id" }),
  frame: Schema.Literals(["auth_seq_id", "label_seq_id"]),
  units: Schema.Array(Range),
  plddtMin: Schema.optional(Schema.Number),
  paeMax: Schema.optional(Schema.Number),
  structureUrl: Schema.optional(Schema.String),
  paeUrl: Schema.optional(Schema.String),
  filter: Schema.optional(
    Schema.Struct({
      scale: Schema.String,
      operator: Schema.Literals([">=", "<="]),
      threshold: Schema.Number,
    }),
  ),
  reference: Schema.optional(
    Schema.Struct({
      structureSha256: Schema.String,
      chain: Schema.String,
      frame: Schema.String,
      model: Schema.Number,
      source: Schema.String,
      tolerance: Schema.Number,
      units: Schema.Array(Range),
    }),
  ),
})
export type Options = typeof Options.Type
const Check = Schema.Struct({
  id: Schema.String,
  status: Schema.Literals(["pass", "fail", "not_evaluable", "not_applicable"]),
  value: Schema.Unknown,
  threshold: Schema.Unknown,
  reason: Schema.String,
})
export const Report = Schema.Struct({
  version: Schema.String,
  provenance: Schema.Struct({
    structureSha256: Schema.String,
    parser: Schema.String,
    python: Schema.String,
    entry: Schema.NullOr(Schema.String),
    model: Schema.NullOr(Schema.String),
    authorChain: Schema.String,
    frame: Schema.String,
    confidenceScale: Schema.String,
    software: Schema.Array(Schema.Unknown),
    modelGroups: Schema.Array(Schema.String),
    confidenceBinding: Schema.Unknown,
  }),
  checks: Schema.Array(Check),
  mapping: Schema.Array(Schema.Unknown),
  summary: Schema.Struct({
    failed: Schema.Array(Schema.String),
    notEvaluable: Schema.Array(Schema.String),
    mechanicalAdmission: Schema.Boolean,
    blocking: Schema.Array(Schema.String),
    biologicalValidity: Schema.String,
  }),
  limitations: Schema.Array(Schema.String),
})
export type Report = typeof Report.Type

/** Trusted, bundled offline parser, isolated from cwd imports. Input is data on
 * stdin, never command text. Python path is an operator setting, not an LLM arg. */
export async function runParser(
  request: unknown,
  signal?: AbortSignal,
  python = process.env.HELIX_TRP_PYTHON ?? "python3",
  script = SCRIPT,
): Promise<unknown> {
  const stdin = S.canonical(request)
  if (Buffer.byteLength(stdin) > 40_000_000) throw new S.WorkflowError("inspection-size", "Inspection exceeds 40 MB")
  // Bun 1.3.14's node:child_process pipe loses stdin in this runtime; its native
  // Blob transport works. Keep the Node transport for packaged Node clients.
  const stdout =
    typeof Bun !== "undefined"
      ? await (async () => {
          signal?.throwIfAborted()
          const child = Bun.spawn([python, "-I", "-c", script], {
            stdin: new Blob([stdin]),
            stdout: "pipe",
            stderr: "pipe",
          })
          const kill = () => child.kill("SIGKILL")
          const timer = setTimeout(kill, 30_000)
          signal?.addEventListener("abort", kill, { once: true })
          let size = 0
          const collect = async (stream: ReadableStream<Uint8Array>) => {
            const reader = stream.getReader(),
              chunks: Uint8Array[] = []
            while (true) {
              const item = await reader.read()
              if (item.done) break
              size += item.value.length
              if (size > 5_000_000) {
                kill()
                throw new S.WorkflowError("inspection-output", "Parser output exceeds 5 MB")
              }
              chunks.push(item.value)
            }
            return Buffer.concat(chunks).toString("utf8")
          }
          try {
            const [out, err, code] = await Promise.all([collect(child.stdout), collect(child.stderr), child.exited])
            signal?.throwIfAborted()
            if (code !== 0) throw new S.WorkflowError("structural-inspection", err.trim() || "Parser interrupted")
            return out
          } finally {
            clearTimeout(timer)
            signal?.removeEventListener("abort", kill)
          }
        })()
      : await new Promise<string>((resolve, reject) => {
          const child = spawn(python, ["-I", "-c", script], {
            stdio: ["pipe", "pipe", "pipe"],
            timeout: 30_000,
            signal,
          })
          const chunks: Buffer[] = [],
            errors: Buffer[] = []
          let size = 0
          const collect = (target: Buffer[]) => (data: Buffer) => {
            size += data.length
            if (size > 5_000_000) {
              child.kill("SIGKILL")
              reject(new S.WorkflowError("inspection-output", "Parser output exceeds 5 MB"))
              return
            }
            target.push(data)
          }
          child.stdout.on("data", collect(chunks))
          child.stderr.on("data", collect(errors))
          child.on("error", reject)
          child.on("close", (code) =>
            code === 0
              ? resolve(Buffer.concat(chunks).toString("utf8"))
              : reject(
                  new S.WorkflowError(
                    "structural-inspection",
                    Buffer.concat(errors).toString("utf8") || "Parser interrupted",
                  ),
                ),
          )
          child.stdin.on("error", () => {
            /* close/error reports early parser exit. */
          })
          child.stdin.end(stdin)
        })
  return JSON.parse(stdout)
}

export async function inspect(
  request: {
    structure: string
    options: Options
    pae?: unknown
    api?: unknown
    colabfold?: { metadata: unknown; scores: string; pae: string }
  },
  signal?: AbortSignal,
  python = process.env.HELIX_TRP_PYTHON ?? "python3",
): Promise<Report> {
  Schema.decodeUnknownSync(Options, { onExcessProperty: "error" })(request.options)
  const report = Schema.decodeUnknownSync(Report, { onExcessProperty: "error" })(
    await runParser(request, signal, python),
  )
  if (
    report.version !== VERSION ||
    report.provenance.structureSha256 !== S.sha256(request.structure) ||
    S.canonical(report.checks.map((c) => c.id).sort()) !== S.canonical(catalog.controls.map((c) => c.id).sort())
  )
    throw new S.WorkflowError("inspection-contract", "Unexpected report identity or control inventory")
  return report
}

export async function legacy(spec: S.Specification, bytes: Uint8Array) {
  return inspect({
    structure: new TextDecoder("utf-8", { fatal: true }).decode(bytes),
    options: {
      format: "pdb",
      model: spec.model.value,
      chain: spec.chain.value,
      frame: "auth_seq_id",
      units: spec.units.value.ranges,
    },
  })
}

export const Parameters = Schema.Struct({
  structure: Schema.String,
  options: Options,
  pae: Schema.optional(Schema.String.annotate({ description: "Path to AFDB JSON PAE; paired with API metadata" })),
  api: Schema.optional(
    Schema.String.annotate({
      description: "Path to archived AFDB API response; entry, chain, sequence and versioned URLs must match",
    }),
  ),
  colabfold: Schema.optional(
    Schema.Struct({
      metadata: Schema.String.annotate({
        description: "Path to colabfold-local/1.0.0 identity, sequence and SHA-256 manifest",
      }),
      scores: Schema.String.annotate({ description: "Path to original ColabFold scores JSON, paired with the PDB" }),
      pae: Schema.String.annotate({
        description: "Path to original local predicted_aligned_error JSON; not AFDB metadata",
      }),
    }),
  ),
})
export type Parameters = typeof Parameters.Type

export async function inspectFiles(args: Parameters, workspace: string, signal?: AbortSignal) {
  const root = await fs.realpath(workspace)
  const files: Record<string, string> = {}
  const read = async (file: string, name: string) => {
    const resolved = await fs.realpath(path.resolve(root, file))
    const rel = path.relative(root, resolved)
    if (rel === ".." || rel.startsWith(`..${path.sep}`) || path.isAbsolute(rel))
      throw new S.WorkflowError("input-escape", "Inspection inputs must be inside the workspace")
    const stat = await fs.stat(resolved)
    if (!stat.isFile() || stat.size > 20_000_000)
      throw new S.WorkflowError("input-size", "Input must be a regular file <=20 MB")
    const data = await fs.readFile(resolved)
    if (data.length > 20_000_000) throw new S.WorkflowError("input-size", "Input grew beyond 20 MB")
    const text = new TextDecoder("utf-8", { fatal: true }).decode(data)
    files[name] = text
    return text
  }
  const request = {
    structure: await read(args.structure, "structure.txt"),
    options: args.options,
    ...(args.pae ? { pae: JSON.parse(await read(args.pae, "pae.json")) } : {}),
    ...(args.api ? { api: JSON.parse(await read(args.api, "api.json")) } : {}),
    ...(args.colabfold
      ? {
          colabfold: {
            metadata: JSON.parse(await read(args.colabfold.metadata, "colabfold-metadata.json")),
            scores: await read(args.colabfold.scores, "colabfold-scores.json"),
            pae: await read(args.colabfold.pae, "colabfold-pae.json"),
          },
        }
      : {}),
  }
  const localPython = path.join(root, ".helix", "trp-python", "bin", "python")
  const python =
    process.env.HELIX_TRP_PYTHON ??
    (await fs.access(localPython).then(
      () => localPython,
      () => "python3",
    ))
  const report = await inspect(request, signal, python)
  files["options.json"] = S.canonical(args.options) + "\n"
  files["report.json"] = S.canonical(report) + "\n"
  files["catalogue.json"] = S.canonical(catalog) + "\n"
  files["trp_inspect.py"] = SCRIPT
  files["verify.py"] = VERIFIER
  const directory = path.join(await E.parent(root), "inspection-" + randomUUID())
  await fs.mkdir(directory, { mode: 0o700 })
  for (const [name, text] of Object.entries(files))
    await fs.writeFile(path.join(directory, name), text, { flag: "wx", mode: 0o600 })
  const manifest =
    S.canonical({
      version: "trp-inspection-evidence/1.0.0",
      files: Object.entries(files).map(([name, text]) => ({
        path: name,
        bytes: Buffer.byteLength(text),
        sha256: S.sha256(text),
      })),
      limitations: "Integrity and declared provenance do not prove scientific validity or authorship.",
    }) + "\n"
  await fs.writeFile(path.join(directory, "manifest.json"), manifest, { flag: "wx", mode: 0o600 })
  return { directory, manifestSha256: S.sha256(manifest), report }
}
