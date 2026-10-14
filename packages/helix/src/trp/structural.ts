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
import STERIC_SCRIPT from "./steric_diagnostic.py.txt"
import SURFACE_SCRIPT from "./surface_diagnostic.py.txt"
import PHYSICAL_SCRIPT from "./physical_diagnostic.py.txt"
import catalog from "./structural_catalog.json"

export { SCRIPT, catalog }
export { STERIC_SCRIPT, SURFACE_SCRIPT, PHYSICAL_SCRIPT }
export const VERSION = "trp-structural/1.1.0"
const Range = Schema.Struct({ start: Schema.Number, end: Schema.Number })
export const Options = Schema.Struct({
  format: Schema.Literals(["mmcif", "pdb"]),
  model: Schema.Number,
  chain: Schema.String.annotate({
    description: "Author chain identifier, even when intervals use label_seq_id",
  }),
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
type InspectionRequest = {
  structure: string
  options: Options
  pae?: unknown
  api?: unknown
  colabfold?: { metadata: unknown; scores: string; pae: string }
}

/** Trusted, bundled offline parser, isolated from cwd imports. Input is data on
 * stdin, never command text. Python path is an operator setting, not an LLM arg. */
export async function runParser(
  request: unknown,
  signal?: AbortSignal,
  python = process.env.HELIX_TRP_PYTHON ?? "python3",
  script = SCRIPT,
  timeoutMs = 30_000,
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
          const timer = setTimeout(kill, timeoutMs)
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
            timeout: timeoutMs,
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
  request: InspectionRequest,
  signal?: AbortSignal,
  python = process.env.HELIX_TRP_PYTHON ?? "python3",
): Promise<Report> {
  Schema.decodeUnknownSync(Options, { onExcessProperty: "error" })(request.options)
  const report = Schema.decodeUnknownSync(Report, {
    onExcessProperty: "error",
  })(await runParser(request, signal, python))
  if (
    report.version !== VERSION ||
    report.provenance.structureSha256 !== S.sha256(request.structure) ||
    S.canonical(report.checks.map((c) => c.id).sort()) !== S.canonical(catalog.controls.map((c) => c.id).sort())
  )
    throw new S.WorkflowError("inspection-contract", "Unexpected report identity or control inventory")
  const stericPython = process.env.HELIX_TRP_STERIC_PYTHON
  let extended = report
  if (stericPython) {
    signal?.throwIfAborted()
    let diagnostic: unknown
    try {
      diagnostic = await runParser(request, signal, stericPython, STERIC_SCRIPT, 180_000)
      const value = Schema.decodeUnknownSync(
        Schema.Struct({
          version: Schema.Literal("helix-steric-diagnostic/1.0.0"),
          status: Schema.Literals(["measured", "not_evaluable"]),
        }),
      )(diagnostic)
      if (value.status === "measured") {
        const measured = diagnostic as {
          sourceSha256?: string
          scope?: { authorChain?: string; modelOrdinal?: number }
          measurement?: { clashscore?: number; severeClashes?: number }
          foldVerdict?: string
          structureLevelThreshold?: unknown
        }
        if (
          measured.sourceSha256 !== report.provenance.structureSha256 ||
          measured.scope?.authorChain !== request.options.chain ||
          measured.scope?.modelOrdinal !== request.options.model ||
          !Number.isFinite(measured.measurement?.clashscore) ||
          !Number.isInteger(measured.measurement?.severeClashes) ||
          Number(measured.measurement?.clashscore) < 0 ||
          Number(measured.measurement?.severeClashes) < 0 ||
          measured.foldVerdict !== "not_established" ||
          measured.structureLevelThreshold !== null
        )
          throw new S.WorkflowError("steric-contract", "Unexpected steric measurement identity or classification")
      }
    } catch {
      signal?.throwIfAborted()
      diagnostic = {
        version: "helix-steric-diagnostic/1.0.0",
        status: "not_evaluable",
        failureCode: "validator-failed-or-interrupted",
      }
    }
    extended = {
      ...report,
      checks: report.checks.map((check) =>
        check.id === "fold-plausibility"
          ? {
              ...check,
              value: {
                stericDiagnostic: diagnostic,
                wrapperSha256: S.sha256(STERIC_SCRIPT),
              },
              reason:
                check.reason +
                " An optional maintained all-atom steric diagnostic is recorded separately; its measurement does not establish overall fold plausibility.",
            }
          : check,
      ),
    }
  }
  const surfacePython = process.env.HELIX_TRP_SURFACE_PYTHON
  if (!surfacePython) return physicalReport(extended, request, signal)
  signal?.throwIfAborted()
  let surfaceDiagnostic: unknown
  try {
    surfaceDiagnostic = await runParser(request, signal, surfacePython, SURFACE_SCRIPT, 180_000)
    const value = Schema.decodeUnknownSync(
      Schema.Struct({
        version: Schema.Literal("helix-surface-diagnostic/1.0.0"),
        status: Schema.Literals(["measured", "not_evaluable"]),
      }),
    )(surfaceDiagnostic)
    if (value.status === "measured") {
      const measured = surfaceDiagnostic as {
        sourceSha256?: string
        scope?: { authorChain?: string; modelOrdinal?: number }
        measurement?: {
          areaAngstromSquared?: { total?: number }
          apolarAreaFraction?: number
          polarAreaFraction?: number
          chargedResidues?: number
          completeChargedSidechains?: number
          incompleteChargedSidechains?: number
          chargedSidechainRelativeAreaMedian?: number | null
        }
        foldVerdict?: string
        burialThreshold?: unknown
        confidenceScoresUsed?: boolean
      }
      const m = measured.measurement
      if (
        measured.sourceSha256 !== report.provenance.structureSha256 ||
        measured.scope?.authorChain !== request.options.chain ||
        measured.scope?.modelOrdinal !== request.options.model ||
        !Number.isFinite(m?.areaAngstromSquared?.total) ||
        Number(m?.areaAngstromSquared?.total) <= 0 ||
        !Number.isFinite(m?.apolarAreaFraction) ||
        Number(m?.apolarAreaFraction) < 0 ||
        Number(m?.apolarAreaFraction) > 1 ||
        !Number.isFinite(m?.polarAreaFraction) ||
        Number(m?.polarAreaFraction) < 0 ||
        Number(m?.polarAreaFraction) > 1 ||
        !Number.isInteger(m?.chargedResidues) ||
        Number(m?.chargedResidues) < 0 ||
        !Number.isInteger(m?.completeChargedSidechains) ||
        Number(m?.completeChargedSidechains) < 0 ||
        !Number.isInteger(m?.incompleteChargedSidechains) ||
        Number(m?.incompleteChargedSidechains) < 0 ||
        Number(m?.chargedResidues) !== Number(m?.completeChargedSidechains) + Number(m?.incompleteChargedSidechains) ||
        (m?.completeChargedSidechains === 0
          ? m.chargedSidechainRelativeAreaMedian !== null
          : !Number.isFinite(m?.chargedSidechainRelativeAreaMedian) ||
            Number(m?.chargedSidechainRelativeAreaMedian) < 0) ||
        measured.foldVerdict !== "not_established" ||
        measured.burialThreshold !== null ||
        measured.confidenceScoresUsed !== false
      )
        throw new S.WorkflowError("surface-contract", "Unexpected surface measurement identity or classification")
    }
  } catch {
    signal?.throwIfAborted()
    surfaceDiagnostic = {
      version: "helix-surface-diagnostic/1.0.0",
      status: "not_evaluable",
      failureCode: "validator-failed-or-interrupted",
    }
  }
  return physicalReport(
    {
      ...extended,
      checks: extended.checks.map((check) =>
        check.id === "fold-plausibility"
          ? {
              ...check,
              value: {
                ...(check.value as Record<string, unknown> | null),
                surfaceDiagnostic,
                surfaceWrapperSha256: S.sha256(SURFACE_SCRIPT),
              },
              reason:
                check.reason +
                " An optional solvent-exposure diagnostic records continuous areas and incomplete sidechains; it does not establish overall fold plausibility.",
            }
          : check,
      ),
    },
    request,
    signal,
  )
}

/** Operator-configured physical warning; no LLM-selected cutoffs or runtime. */
async function physicalReport(report: Report, request: InspectionRequest, signal?: AbortSignal): Promise<Report> {
  const python = process.env.HELIX_TRP_PHYSICAL_PYTHON
  if (!python) return report
  signal?.throwIfAborted()
  let diagnostic: any
  try {
    diagnostic = await runParser(request, signal, python, PHYSICAL_SCRIPT, 180_000)
    Schema.decodeUnknownSync(
      Schema.Struct({
        version: Schema.Literals(["helix-physical-diagnostic/1.0.0", "helix-physical-diagnostic/1.1.0"]),
        status: Schema.Literals(["evaluated", "not_evaluable"]),
        decision: Schema.Literals(["alert", "no_targeted_failure_detected", "inconclusive"]),
      }),
    )(diagnostic)
    if (diagnostic.status === "evaluated" || diagnostic.sourceSha256) {
      const m = diagnostic.measurement
      if (
        diagnostic.sourceSha256 !== report.provenance.structureSha256 ||
        diagnostic.scope?.authorChain !== request.options.chain ||
        diagnostic.scope?.modelOrdinal !== request.options.model ||
        diagnostic.globalFoldValidity !== "not_established" ||
        diagnostic.confidenceScoresUsed !== false ||
        !/^[a-f0-9]{64}$/.test(diagnostic.rulesSha256 ?? "") ||
        !Array.isArray(diagnostic.chargeColumns) ||
        !Array.isArray(diagnostic.mechanismsDetected) ||
        !Number.isInteger(m?.chargedGroups) ||
        m.chargedGroups < 0 ||
        !Number.isInteger(m?.qualifiedColumns) ||
        m.qualifiedColumns !== diagnostic.chargeColumns.length ||
        typeof m?.chargeAlert !== "boolean" ||
        typeof m?.packingAlert !== "boolean" ||
        m.chargeAlert !== diagnostic.chargeColumns.some((c: any) => c.alert === true) ||
        m.packingAlert !== diagnostic.packingConflicts?.alert ||
        (diagnostic.decision === "alert") !== (m.chargeAlert || m.packingAlert) ||
        (diagnostic.status === "evaluated") !== (diagnostic.decision !== "inconclusive")
      )
        throw new S.WorkflowError("physical-contract", "Unexpected physical warning identity or decision")
      if (diagnostic.version === "helix-physical-diagnostic/1.1.0") {
        const rules = diagnostic.rules
        const observations = diagnostic.chargedResidueObservations
        if (
          rules?.polarMoietyRelativeArea1p4Maximum !== 0.08 ||
          rules?.polarMoietyRelativeArea2p0Maximum !== 0.02 ||
          rules?.referenceAreaEvidenceSha256 !== "0ee1d4daa7d2899b2031228848e2faa73cee01ac6e1c7aca90c1ab42cad8d2bb" ||
          diagnostic.engine?.surfaceParameters?.["probe-radius"] !== 1.4 ||
          diagnostic.engine?.surfaceParameters2p0?.["probe-radius"] !== 2 ||
          !Array.isArray(observations) ||
          observations.length !== m.chargedGroups
        )
          throw new S.WorkflowError("physical-contract", "Unexpected polar-moiety profile or denominator")
        const buried = new Set<string>()
        for (const group of observations) {
          if (!group.complete) continue
          const reference = rules.referenceMoietyAreaAngstromSquared?.[group.key.split(":").at(-1)]
          for (const [probe, area, ratio] of [
            ["1.4", "chargedGroupArea", "relativePolarMoietyArea1p4"],
            ["2.0", "chargedGroupArea2p0", "relativePolarMoietyArea2p0"],
          ]) {
            if (
              !Number.isFinite(reference?.[probe]) ||
              reference[probe] <= 0 ||
              !Number.isFinite(group[area]) ||
              group[area] < 0 ||
              !Number.isFinite(group[ratio]) ||
              group[ratio] < 0 ||
              Math.abs(group[ratio] - group[area] / reference[probe]) > 1e-9
            )
              throw new S.WorkflowError("physical-contract", "Unexpected polar-moiety arithmetic")
          }
          if (group.relativePolarMoietyArea1p4 <= 0.08 && group.relativePolarMoietyArea2p0 <= 0.02)
            buried.add(group.key)
        }
        if (
          buried.size !== m.buriedChargedGroups ||
          diagnostic.chargeColumns.some(
            (column: any) =>
              column.groups !== column.residues.length || column.residues.some((key: string) => !buried.has(key)),
          )
        )
          throw new S.WorkflowError("physical-contract", "Unexpected polar-moiety membership")
      }
    } else if (diagnostic.status !== "not_evaluable" || diagnostic.decision !== "inconclusive") {
      throw new S.WorkflowError("physical-contract", "Physical decision lacks measurement provenance")
    }
  } catch {
    signal?.throwIfAborted()
    diagnostic = {
      version: "helix-physical-diagnostic/1.1.0",
      status: "not_evaluable",
      decision: "inconclusive",
      failureCode: "validator-failed-or-interrupted",
    }
  }
  const status =
    diagnostic.decision === "alert"
      ? "fail"
      : diagnostic.decision === "no_targeted_failure_detected"
        ? "pass"
        : "not_evaluable"
  const checks = report.checks.map((check) =>
    check.id === "fold-plausibility"
      ? {
          ...check,
          status,
          value: {
            ...(check.value as Record<string, unknown> | null),
            physicalDiagnostic: diagnostic,
            physicalWrapperSha256: S.sha256(PHYSICAL_SCRIPT),
          },
          threshold: { rule: diagnostic.version, rulesSha256: diagnostic.rulesSha256 ?? null },
          reason:
            status === "fail"
              ? "A physical warning was detected under the declared nominal charge and packing assumptions; see the mechanism and residue evidence. This is not experimental proof of global fold impossibility."
              : status === "pass"
                ? "No buried-charge-column or distributed severe packing warning met this development rule. This pass is limited to those mechanisms; global fold validity and stability remain not established."
                : "The configured physical warning could not be adjudicated; retain the missing-input or chemistry uncertainty and do not infer global fold validity.",
        }
      : check,
  )
  const failed = checks.filter((c) => c.status === "fail").map((c) => c.id)
  const notEvaluable = checks.filter((c) => c.status === "not_evaluable").map((c) => c.id)
  const blocking = failed.concat(
    notEvaluable.filter((id) => ["confidence-scale", "filter-direction", "interunit-pae"].includes(id)),
  )
  return {
    ...report,
    checks: checks as Report["checks"],
    summary: {
      ...report.summary,
      failed,
      notEvaluable,
      blocking,
      mechanicalAdmission: blocking.length === 0,
      biologicalValidity: "not_established",
    },
  }
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
  pae: Schema.optional(
    Schema.String.annotate({
      description: "Path to AFDB JSON PAE; paired with API metadata",
    }),
  ),
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
      scores: Schema.String.annotate({
        description: "Path to original ColabFold scores JSON, paired with the PDB",
      }),
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
  const physical = report.checks.find((check) => check.id === "fold-plausibility")?.value as Record<
    string,
    unknown
  > | null
  if (physical?.stericDiagnostic) files["steric_diagnostic.py"] = STERIC_SCRIPT
  if (physical?.surfaceDiagnostic) files["surface_diagnostic.py"] = SURFACE_SCRIPT
  if (physical?.physicalDiagnostic) files["physical_diagnostic.py"] = PHYSICAL_SCRIPT
  files["verify.py"] = VERIFIER
  const directory = path.join(await E.parent(root), "inspection-" + randomUUID())
  await fs.mkdir(directory, { mode: 0o700 })
  for (const [name, text] of Object.entries(files))
    await fs.writeFile(path.join(directory, name), text, {
      flag: "wx",
      mode: 0o600,
    })
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
  await fs.writeFile(path.join(directory, "manifest.json"), manifest, {
    flag: "wx",
    mode: 0o600,
  })
  return { directory, manifestSha256: S.sha256(manifest), report }
}
