export * as TrpRemote from "./remote"

import fs from "node:fs/promises"
import path from "node:path"
import { Effect, Schema } from "effect"
import { ChildProcess } from "effect/unstable/process"
import { AppProcess } from "@helix/core/process"
import { TrpSpecification as S } from "./specification"
import type { TrpNextflow as N } from "./nextflow"
import { TrpResources as R } from "./resources"
import RUNNER from "./remote_runner.py.txt"

export const VERSION = "trp-slurm-ssh/1.0.0"
export const Config = Schema.Struct({
  version: Schema.Literal(VERSION),
  host: Schema.String,
  port: Schema.Number,
  user: Schema.String,
  identityFile: Schema.String,
  knownHostsFile: Schema.String,
  hostKeyAlias: Schema.String,
  root: Schema.String,
  partition: Schema.String,
  selectNode: Schema.optional(Schema.String),
  geometryNode: Schema.optional(Schema.String),
  numericalProfile: Schema.optional(Schema.Literal("haswell-single-thread")),
  sessionExpiresAt: Schema.optional(Schema.String),
})
export type Config = Schema.Schema.Type<typeof Config>
export interface Target {
  config: Config
  fingerprint: string
  public: Record<string, unknown>
}

/** The model cannot choose credentials, cluster capacity or a different target.
 * Only the operator's owner-controlled configuration selects this backend. */
export async function configured(): Promise<Target | undefined> {
  const pointer = process.env.HELIX_TRP_REMOTE
  if (!pointer) return undefined
  if (process.env.HELIX_TRP_SANDBOX)
    throw new S.WorkflowError("remote-sandbox-conflict", "A local sandbox cannot authorize remote resources")
  const privateFile = async (file: string, secret: boolean) => {
    if (!path.isAbsolute(file)) throw new S.WorkflowError("remote-config", "Operator paths must be absolute")
    const stat = await fs.lstat(file)
    if (
      !stat.isFile() ||
      stat.isSymbolicLink() ||
      stat.uid !== process.getuid?.() ||
      stat.mode & (secret ? 0o077 : 0o022)
    )
      throw new S.WorkflowError("remote-config", "Operator files must be owner-controlled ordinary files")
    return S.sha256(await fs.readFile(file))
  }
  const configHash = await privateFile(pointer, true)
  const config = Schema.decodeUnknownSync(Config)(JSON.parse(await fs.readFile(pointer, "utf8")), {
    onExcessProperty: "error",
  })
  for (const value of [
    config.host,
    config.user,
    config.hostKeyAlias,
    config.partition,
    config.selectNode,
    config.geometryNode,
  ])
    if (value !== undefined && !/^[a-zA-Z0-9][a-zA-Z0-9_.-]*$/.test(value))
      throw new S.WorkflowError("remote-config", "Invalid SSH or Slurm identifier")
  if (
    !Number.isSafeInteger(config.port) ||
    config.port < 1 ||
    config.port > 65535 ||
    !/^\/[a-zA-Z0-9_./-]+$/.test(config.root) ||
    config.root.includes("..") ||
    config.root === "/"
  )
    throw new S.WorkflowError("remote-config", "Invalid port or shared root")
  if (config.sessionExpiresAt !== undefined && !Number.isFinite(Date.parse(config.sessionExpiresAt)))
    throw new S.WorkflowError("remote-config", "Invalid session expiry")
  const credentialsHash = await privateFile(config.identityFile, true)
  const knownHostsHash = await privateFile(config.knownHostsFile, false)
  const fingerprint = S.sha256(S.canonical({ configHash, credentialsHash, knownHostsHash }))
  const { identityFile: _identity, knownHostsFile: _known, ...description } = config
  return {
    config,
    fingerprint,
    public: { ...description, fingerprint, hostKeyVerification: "strict", credentialBytes: "excluded" },
  }
}

const quote = (text: string) => "'" + text.replaceAll("'", "'\\''") + "'"
export function command(target: Target) {
  const c = target.config
  return ChildProcess.make("ssh", [
    "-T",
    "-o",
    "BatchMode=yes",
    "-o",
    "StrictHostKeyChecking=yes",
    "-o",
    `UserKnownHostsFile=${c.knownHostsFile}`,
    "-o",
    `HostKeyAlias=${c.hostKeyAlias}`,
    "-o",
    "ConnectTimeout=15",
    "-o",
    "ServerAliveInterval=15",
    "-o",
    "ServerAliveCountMax=2",
    "-i",
    c.identityFile,
    "-p",
    String(c.port),
    `${c.user}@${c.host}`,
    `python3 -c ${quote(RUNNER)}`,
  ])
}

export function request(
  target: Target,
  action: string,
  payload: Record<string, unknown>,
  runProcess: AppProcess.Interface["run"],
  signal?: AbortSignal,
) {
  return Effect.gen(function* () {
    const result = yield* runProcess(command(target), {
      stdin: S.canonical({ action, target: target.public, ...payload }),
      signal,
      timeout: "90 seconds",
      maxOutputBytes: action === "export" ? 256 * R.MiB : 2 * R.MiB,
      maxErrorBytes: 64 * 1024,
    })
    let response: any
    try {
      response = JSON.parse(result.stdout.toString())
    } catch {
      /* SSH failures need not emit controller JSON. */
    }
    if (response?.ok === false)
      return yield* Effect.die(new S.WorkflowError(response.code || "remote-failed", response.error || action))
    if (result.exitCode !== 0 || result.stdoutTruncated || result.stderrTruncated || !response?.ok)
      return yield* Effect.die(
        new S.WorkflowError(
          "remote-command-failed",
          `SSH action ${action}, exit ${result.exitCode}: ${result.stderr.toString().slice(-8192)}`,
        ),
      )
    return response as any
  })
}

export function observe(target: Target, runProcess: AppProcess.Interface["run"], signal?: AbortSignal) {
  return request(target, "observe", {}, runProcess, signal).pipe(Effect.map(inventory))
}
export function inventory(value: any): R.Inventory {
  return {
    version: R.VERSION,
    observedAt: value.observedAt,
    platform: value.platform,
    architecture: value.architecture,
    host: value.host,
    workspace: value.workspace,
    filesystem: value.filesystem,
    cpus: value.cpus,
    memoryBytes: value.memoryBytes,
    freeBytes: value.freeBytes,
    sources: value.sources,
    limitations: value.limitations,
    remote: value.remote,
  }
}

/** Target and exact runner/configuration bytes are immutable approved inputs. */
export function bind(bundle: N.Bundle, target: Target, id: string): void {
  const c = target.config
  const select = bundle.spec.graph.nodes.find((n) => n.operation === "pdb.select")!.id.toUpperCase()
  const geometry = bundle.spec.graph.nodes.find((n) => n.operation === "geometre.geometry")!.id.toUpperCase()
  bundle.files["remote_target.json"] = S.canonical(target.public) + "\n"
  bundle.files["remote_runner.py"] = RUNNER
  const execution = JSON.parse(bundle.files["execution.json"])
  execution.backend = VERSION
  execution.target = target.public
  execution.numericalProfile = c.numericalProfile ?? "native-single-thread"
  bundle.files["execution.json"] = S.canonical(execution) + "\n"
  bundle.files["nextflow.config"] = bundle.files["nextflow.config"]
    .replace("process.executor = 'local'", `process.executor = 'slurm'\nprocess.queue = '${c.partition}'`)
    .replace("--cpus 2 --tmpfs", "--cpus 2 --memory=2g --memory-swap=2g --tmpfs")
  bundle.files["nextflow.config"] += `process.clusterOptions = '--comment=helix:${id}'\n`
  if (c.selectNode)
    bundle.files["nextflow.config"] +=
      `process { withName: ${select} { clusterOptions = '--comment=helix:${id} --nodelist=${c.selectNode}' } }\n`
  if (c.geometryNode)
    bundle.files["nextflow.config"] +=
      `process { withName: ${geometry} { clusterOptions = '--comment=helix:${id} --nodelist=${c.geometryNode}' } }\n`
  if (c.numericalProfile) bundle.files["nextflow.config"] += "env.OPENBLAS_CORETYPE = 'Haswell'\n"
  // Container-side observations are evidence of effective limits, distinct from
  // the scheduler request. They cannot silently substitute for a disk quota.
  const runtime = `import os, json, pathlib, socket, numpy
from threadpoolctl import threadpool_info
def _limit(name):
    return pathlib.Path('/sys/fs/cgroup/' + name).read_text().strip()
print('HELIX_RUNTIME:' + json.dumps({'hostname': socket.gethostname(), 'cpuMax': _limit('cpu.max'), 'memoryMax': _limit('memory.max'), 'swapMax': _limit('memory.swap.max'), 'numericalProfile': os.environ.get('OPENBLAS_CORETYPE', 'native'), 'threads': os.environ.get('OPENBLAS_NUM_THREADS'), 'blas': threadpool_info()}), flush=True)
`
  for (const name of ["trp_select.py", "trp_geometry.py"]) bundle.files[name] = runtime + bundle.files[name]
}

export function execute(
  target: Target,
  bundle: N.Bundle,
  directory: string,
  id: string,
  budget: R.Budget,
  runProcess: AppProcess.Interface["run"],
  signal: AbortSignal,
  log: (outcome: string, detail: unknown) => Promise<unknown>,
) {
  let submitted = false,
    cleaned = false,
    finished = false
  return Effect.gen(function* () {
    const payload = { id, digest: bundle.digest, budget, files: bundle.files }
    submitted = true // A lost SSH response cannot prove that submission never happened.
    const start = yield* request(target, "start", payload, runProcess, signal).pipe(Effect.exit)
    if (start._tag === "Success")
      yield* Effect.promise(() =>
        log("remote-started", {
          directory: start.value.directory,
          controller: start.value.controller,
          digest: bundle.digest,
        }),
      )
    const deadline = Date.now() + budget.wallSeconds * 1000
    let terminal: any
    let failure: unknown = start._tag === "Failure" ? String(start.cause) : undefined
    try {
      while (!failure) {
        if (signal.aborted) throw AppProcess.abortError(signal)
        if (Date.now() > deadline) throw new S.WorkflowError("remote-timeout", "Reviewed wall time exceeded")
        const response = yield* request(target, "status", { id, digest: bundle.digest }, runProcess, signal).pipe(
          Effect.exit,
        )
        if (response._tag === "Failure") throw new S.WorkflowError("remote-monitor-failed", String(response.cause))
        const state = response.value
        yield* Effect.promise(() =>
          fs.writeFile(path.join(directory, "remote-observation.json"), S.canonical(state) + "\n"),
        )
        if (state.analysisInventory && !state.analysisAdmitted) {
          const observed = inventory(state.analysisInventory)
          const demand = JSON.parse(bundle.files["admission.json"]).demand
          const decision = R.admit(demand, observed, budget)
          yield* Effect.promise(async () => {
            await fs.writeFile(
              path.join(directory, "analysis-admission.json"),
              S.canonical({ inventory: observed, decision }) + "\n",
            )
          })
          yield* Effect.promise(() => log(decision.accepted ? "analysis-accepted" : "analysis-rejected", decision))
          if (!decision.accepted) throw new S.WorkflowError("remote-analysis-rejected", S.canonical(decision))
          const accepted = yield* request(
            target,
            "admit-analysis",
            { id, digest: bundle.digest, decision },
            runProcess,
            signal,
          ).pipe(Effect.exit)
          if (accepted._tag === "Failure")
            throw new S.WorkflowError("remote-analysis-admission-failed", String(accepted.cause))
        }
        if (["succeeded", "failed", "cancelled"].includes(state.status)) {
          terminal = state
          break
        }
        // A missing controller is a verified failure, never grounds for silently resubmitting.
        if (!state.controllerAlive)
          throw new S.WorkflowError(
            "remote-controller-lost",
            "Controller absent without a terminal record; no automatic resubmission",
          )
        yield* Effect.sleep("2 seconds")
      }
    } catch (error) {
      failure = error
    }
    if (failure || terminal?.status !== "succeeded") {
      const cancellation = yield* request(
        target,
        "cancel",
        { id, digest: bundle.digest, reason: String(failure ?? terminal?.error ?? terminal?.status) },
        runProcess,
      ).pipe(Effect.exit)
      yield* Effect.promise(async () => {
        await fs.writeFile(
          path.join(directory, "remote-cancellation.json"),
          S.canonical(
            cancellation._tag === "Success"
              ? cancellation.value
              : { confirmed: false, error: String(cancellation.cause) },
          ) + "\n",
        )
      })
      yield* Effect.promise(() =>
        log("remote-failed-or-cancelled", { terminal, error: String(failure ?? "Remote failure") }),
      )
      cleaned = true
    }
    // Even failure paths attempt to preserve remote logs; unreachable transport
    // is recorded explicitly rather than inventing a successful cancellation.
    const exported = yield* request(
      target,
      "export",
      { id, digest: bundle.digest, maxBytes: budget.workBytes },
      runProcess,
    ).pipe(Effect.exit)
    if (exported._tag === "Success") {
      yield* Effect.promise(() => importExport(bundle, directory, exported.value))
    } else {
      yield* Effect.promise(() =>
        fs.writeFile(
          path.join(directory, "remote-retrieval-error.json"),
          S.canonical({ error: String(exported.cause) }) + "\n",
        ),
      )
    }
    if (failure || terminal?.status !== "succeeded" || exported._tag === "Failure")
      return yield* Effect.die(
        new S.WorkflowError(
          signal.aborted ? "remote-cancelled" : "remote-execution-failed",
          String(failure ?? terminal?.error ?? "Evidence retrieval failed"),
        ),
      )
    finished = true
    return terminal
  }).pipe(
    Effect.onExit((exit) => {
      if (exit._tag === "Success" || !submitted || cleaned || finished) return Effect.void
      // Fiber interruption also runs this uninterruptible finalizer. It must not
      // leave native jobs running just because the local tool disappeared.
      return Effect.gen(function* () {
        const cancelled = yield* request(
          target,
          "cancel",
          { id, digest: bundle.digest, reason: "Local execution interrupted" },
          runProcess,
        ).pipe(Effect.exit)
        yield* Effect.promise(() =>
          fs.writeFile(
            path.join(directory, "remote-cancellation.json"),
            S.canonical(
              cancelled._tag === "Success" ? cancelled.value : { confirmed: false, error: String(cancelled.cause) },
            ) + "\n",
          ),
        )
        const exported = yield* request(
          target,
          "export",
          { id, digest: bundle.digest, maxBytes: budget.workBytes },
          runProcess,
        ).pipe(Effect.exit)
        if (exported._tag === "Success")
          yield* Effect.promise(() => importExport(bundle, directory, exported.value)).pipe(Effect.ignore)
        yield* Effect.promise(() =>
          log("remote-interruption-cleanup", { confirmed: cancelled._tag === "Success" && cancelled.value.confirmed }),
        ).pipe(Effect.ignore)
      })
    }),
  )
}

export async function importExport(bundle: N.Bundle, directory: string, response: any) {
  const seen = new Set<string>()
  for (const file of response.files) {
    if (
      !/^[a-zA-Z0-9_.-]+(?:\/[a-zA-Z0-9_.-]+)*$/.test(file.path) ||
      file.path.split("/").some((s: string) => s === "." || s === "..") ||
      seen.has(file.path)
    )
      throw new S.WorkflowError("remote-export-path", file.path)
    seen.add(file.path)
    const bytes = Buffer.from(file.base64, "base64")
    if (bytes.length !== file.bytes || S.sha256(bytes) !== file.sha256)
      throw new S.WorkflowError("remote-export-hash", file.path)
    const destination = path.join(directory, file.path)
    if (file.path in bundle.files) {
      if (S.sha256(bytes) !== S.sha256(bundle.files[file.path]))
        throw new S.WorkflowError("remote-bundle-changed", file.path)
      continue
    }
    await fs.mkdir(path.dirname(destination), { recursive: true, mode: 0o700 })
    await fs.writeFile(destination, bytes, { flag: "wx", mode: 0o600 })
  }
  for (const name of Object.keys(bundle.files))
    if (!seen.has(name)) throw new S.WorkflowError("remote-export-missing", name)
  await fs.writeFile(
    path.join(directory, "remote-transfer.json"),
    S.canonical({
      digest: bundle.digest,
      files: response.files.map(({ base64: _, ...file }: any) => file),
      verifiedAt: new Date().toISOString(),
    }) + "\n",
  )
}
