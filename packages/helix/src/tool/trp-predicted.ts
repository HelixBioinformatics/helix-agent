import { Effect, Schema } from "effect"
import fs from "node:fs/promises"
import path from "node:path"
import os from "node:os"
import { spawn } from "node:child_process"
import { Question } from "../question"
import { InstanceState } from "../effect/instance-state"
import { EffectBridge } from "../effect/bridge"
import { AppProcess } from "@helix/core/process"
import { TrpSpecification as S } from "../trp/specification"
import { TrpStructural as C } from "../trp/structural"
import SCRIPT from "../trp/predicted_geometry.py.txt"
import VERIFIER from "../trp/verify_predicted.py.txt"
import * as Tool from "./tool"

export const Parameters = Schema.Struct({
  structure: Schema.String,
  pae: Schema.String,
  api: Schema.String,
  options: C.Options,
})
type Args = typeof Parameters.Type
export const APPROVE = "Aprobar geometría predicha"
const LIMITS =
  "2 CPU, 2 GiB RAM sin swap adicional, tmpfs 256 MiB, 128 procesos, 120 segundos, Docker local sin red. Se requieren 2 GiB libres; almacenamiento persistente sin cuota dura. Sin llamadas API pagadas."
type Dependencies = {
  approve: (question: string) => Promise<ReadonlyArray<ReadonlyArray<string>>>
  launch?: typeof launch
}

export async function launch(script: string, args: string[], directory: string, signal: AbortSignal) {
  signal.throwIfAborted()
  const local = path.join(directory, ".helix/trp-python/bin/python")
  const python =
    process.env.HELIX_TRP_PYTHON ??
    (await fs.access(local).then(
      () => local,
      () => "python3",
    ))
  return new Promise<string>((resolve, reject) => {
    const child = spawn(python, ["-I", script, ...args], { cwd: directory, stdio: ["ignore", "pipe", "pipe"] })
    let stdout = "",
      stderr = "",
      size = 0,
      stopped = false
    const stop = () => {
      stopped = true
      child.kill("SIGTERM")
    }
    const timer = setTimeout(stop, 150_000)
    signal.addEventListener("abort", stop, { once: true })
    if (signal.aborted) stop()
    const collect = (err: boolean) => (data: Buffer) => {
      size += data.length
      if (size > 1_000_000) {
        stop()
        return
      }
      if (err) stderr += data
      else stdout += data
    }
    child.stdout.on("data", collect(false))
    child.stderr.on("data", collect(true))
    child.on("error", (error) => {
      clearTimeout(timer)
      signal.removeEventListener("abort", stop)
      reject(error)
    })
    child.on("close", (code) => {
      clearTimeout(timer)
      signal.removeEventListener("abort", stop)
      if (stopped || signal.aborted || code !== 0) reject(new Error(stderr || "Predicted geometry interrupted"))
      else resolve(stdout)
    })
  })
}

/** Preparation is offline. Only a session-bound Question response can start the container. */
export async function executePredicted(
  args: Args,
  directory: string,
  sessionID: string,
  signal: AbortSignal,
  deps: Dependencies,
) {
  Schema.decodeUnknownSync(Parameters, { onExcessProperty: "error" })(args)
  args = structuredClone(args)
  signal.throwIfAborted()
  const root = await fs.realpath(directory)
  const sources: Record<string, { path: string; requested: string; sha256: string }> = {}
  const originals: Record<string, Buffer> = {}
  const read = async (name: string, file: string) => {
    const requested = path.resolve(root, file),
      resolved = await fs.realpath(requested),
      relative = path.relative(root, resolved)
    if (relative === ".." || relative.startsWith(`..${path.sep}`) || path.isAbsolute(relative))
      throw new Error("Source escapes workspace")
    const stat = await fs.stat(resolved)
    if (!stat.isFile() || stat.size > 20_000_000) throw new Error("Source must be regular and <=20 MB")
    const bytes = await fs.readFile(resolved)
    if (bytes.length > 20_000_000) throw new Error("Source grew beyond limit")
    sources[name] = { path: resolved, requested, sha256: S.sha256(bytes) }
    originals[name] = bytes
    return new TextDecoder("utf-8", { fatal: true }).decode(bytes)
  }
  const request = {
    structure: await read("structure", args.structure),
    pae: JSON.parse(await read("pae", args.pae)),
    api: JSON.parse(await read("api", args.api)),
    options: args.options,
  }
  let base = root
  for (const part of [".helix", "trp", "predicted"]) {
    base = path.join(base, part)
    await fs.mkdir(base).catch((error: NodeJS.ErrnoException) => {
      if (error.code !== "EEXIST") throw error
    })
    if ((await fs.realpath(base)) !== base) throw new Error("Symlinked output directory")
  }
  const capacity = async () => {
    const disk = await fs.statfs(base)
    if (disk.bavail * disk.bsize < 2 * 1024 ** 3 || os.freemem() < 2 * 1024 ** 3 || os.availableParallelism() < 2)
      throw new Error("Insufficient observed resources for fixed predicted geometry budget")
    return {
      freeBytes: disk.bavail * disk.bsize,
      freeMemoryBytes: os.freemem(),
      availableCpus: os.availableParallelism(),
      hardPersistentQuota: false,
    }
  }
  const inventory = await capacity()
  const runRoot = await fs.mkdtemp(path.join(base, "run-")),
    work = path.join(runRoot, "work"),
    runner = path.join(runRoot, "predicted_geometry.py")
  const requestText = S.canonical(request) + "\n"
  for (const [name, bytes] of Object.entries(originals))
    await fs.writeFile(path.join(runRoot, `original-${name}.txt`), bytes, { flag: "wx", mode: 0o600 })
  await fs.writeFile(runner, SCRIPT, { flag: "wx", mode: 0o600 })
  await fs.writeFile(path.join(runRoot, "verify.py"), VERIFIER, { flag: "wx", mode: 0o600 })
  await fs.writeFile(path.join(runRoot, "inspect_structure.py"), C.SCRIPT, { flag: "wx", mode: 0o600 })
  await fs.writeFile(path.join(runRoot, "request.json"), requestText, { flag: "wx", mode: 0o600 })
  const events: object[] = []
  const save = () => fs.writeFile(path.join(runRoot, "approval-events.json"), JSON.stringify(events, null, 2))
  try {
    const run = deps.launch ?? launch
    const prepared = JSON.parse(await run(runner, ["prepare", path.join(runRoot, "request.json"), work], root, signal))
    const proposalBytes = await fs.readFile(path.join(work, "proposal.json")),
      proposal = JSON.parse(proposalBytes.toString()),
      digest = S.sha256(proposalBytes)
    if (
      prepared.directory !== work ||
      prepared.digest !== digest ||
      proposal.files["request.json"] !== S.sha256(requestText) ||
      proposal.files["predicted_geometry.py"] !== S.sha256(SCRIPT) ||
      proposal.files["inspect_structure.py"] !== S.sha256(C.SCRIPT) ||
      proposal.confidenceScale !== "pLDDT_0_100"
    )
      throw new Error("Proposal does not match request or trusted adapters")
    const approval = { sessionID, digest, sources, inventory, limits: LIMITS }
    const approvalDigest = S.sha256(S.canonical(approval))
    await fs.writeFile(path.join(runRoot, "admission.json"), S.canonical({ ...approval, approvalDigest }) + "\n")
    signal.throwIfAborted()
    const answers = await deps.approve(
      `Calcular geometría de unidades SUMINISTRADAS en ${proposal.entry}. No son detecciones ni anotaciones independientes. pLDDT y PAE no prueban plausibilidad física.\n${LIMITS}\nSesión: ${sessionID}\nSHA-256 admisión: ${approvalDigest}\nSHA-256 propuesta: ${digest}\n${proposalBytes.toString()}`,
    )
    signal.throwIfAborted()
    if (answers.length !== 1 || answers[0].length !== 1 || answers[0][0] !== APPROVE)
      throw new Error("Predicted geometry rejected or unapproved")
    for (const source of Object.values(sources))
      if (
        (await fs.realpath(source.requested)) !== source.path ||
        S.sha256(await fs.readFile(source.path)) !== source.sha256
      )
        throw new Error("Original source changed after approval")
    if (
      S.sha256(await fs.readFile(runner)) !== S.sha256(SCRIPT) ||
      S.sha256(await fs.readFile(path.join(runRoot, "inspect_structure.py"))) !== S.sha256(C.SCRIPT) ||
      S.sha256(await fs.readFile(path.join(work, "proposal.json"))) !== digest
    )
      throw new Error("Approved adapter or proposal changed")
    const recheck = await capacity()
    events.push({ channel: "Question.Service", sessionID, digest, approvalDigest, answer: APPROVE, recheck })
    await save()
    const result = JSON.parse(await run(runner, ["run", work, "--digest", digest], root, signal))
    if (
      result.status !== "succeeded" ||
      result.proposalDigest !== digest ||
      result.sourceEntry !== proposal.entry ||
      result.geometrySha256 !== S.sha256(await fs.readFile(path.join(work, "geometry.csv")))
    )
      throw new Error("Execution result binding mismatch")
    const artifacts: Record<string, { sha256: string; bytes: number }> = {}
    const collect = async (directory: string) => {
      for (const name of await fs.readdir(directory)) {
        const file = path.join(directory, name),
          stat = await fs.lstat(file)
        if (stat.isSymbolicLink()) throw new Error("Symlink in predicted evidence")
        if (stat.isDirectory()) await collect(file)
        else if (stat.isFile()) {
          const bytes = await fs.readFile(file)
          artifacts[path.relative(runRoot, file)] = { sha256: S.sha256(bytes), bytes: bytes.length }
        } else throw new Error("Special file in predicted evidence")
      }
    }
    await collect(runRoot)
    const evidence =
      S.canonical({
        version: "helix-predicted-evidence/1.0.0",
        digest,
        approvalDigest,
        sessionID,
        entry: proposal.entry,
        biologicalValidity: "not_established",
        files: artifacts,
      }) + "\n"
    await fs.writeFile(path.join(runRoot, "manifest.json"), evidence, { flag: "wx", mode: 0o600 })
    return {
      directory: runRoot,
      status: "succeeded",
      entry: proposal.entry,
      digest,
      manifestSha256: S.sha256(evidence),
      geometry: path.join(work, "geometry.csv"),
      biologicalValidity: "not_established",
      limits: LIMITS,
    }
  } catch (error) {
    events.push({ stage: "failure", sessionID, reason: String(error) })
    await save()
    throw error
  }
}

export const TrpPredictedTool = Tool.define(
  "trp_predicted_geometry",
  Effect.gen(function* () {
    const question = yield* Question.Service
    return {
      description:
        "Prepare, review and execute geometry for supplied AFDB units from local mmCIF, matching AFDB API metadata and PAE files. Preserves AFDB identity and pLDDT; requires >=3 units of >=6 residues. Offline preparation precedes authenticated human approval of hashes, sources and fixed budget. Docker local pinned image only: 2 CPU,2GiB,120s; no hard persistent quota. Units are hypotheses, not validated repeats. Never fabricates experimental metadata or biological accuracy.",
      parameters: Parameters,
      execute: (args: Args, ctx: Tool.Context) =>
        Effect.gen(function* () {
          const directory = yield* InstanceState.directory,
            bridge = yield* EffectBridge.make()
          yield* ctx.ask({
            permission: "trp_predicted_geometry",
            patterns: [args.structure, args.pae, args.api],
            always: [],
            metadata: { limits: LIMITS },
          })
          const result = yield* Effect.promise(() =>
            executePredicted(args, directory, ctx.sessionID, ctx.abort, {
              approve: (prompt) =>
                bridge.promise(
                  question
                    .ask({
                      sessionID: ctx.sessionID,
                      tool: ctx.callID ? { messageID: ctx.messageID, callID: ctx.callID } : undefined,
                      questions: [
                        {
                          header: "AFDB geometry",
                          question: prompt,
                          multiple: false,
                          custom: false,
                          options: [
                            { label: APPROVE, description: "Ejecutar esta propuesta y sus límites." },
                            { label: "Rechazar", description: "No ejecutar." },
                          ],
                        },
                      ],
                    })
                    .pipe(Effect.raceFirst(AppProcess.waitForAbort(ctx.abort))),
                ),
            }),
          )
          return {
            title: "TRP predicted geometry",
            metadata: { directory: result.directory, status: result.status },
            output: JSON.stringify(result, null, 2),
          }
        }),
    }
  }),
)
