export * as TrpWorkflow from "./workflow"

import { Context, Effect, Layer } from "effect"
import { ChildProcess } from "effect/unstable/process"
import { AppProcess } from "@helix/core/process"
import { LayerNode } from "@helix/core/effect/layer-node"
import fs from "node:fs/promises"
import path from "node:path"
import { randomUUID } from "node:crypto"
import { Question } from "../question"
import { InstanceState } from "../effect/instance-state"
import type { Tool } from "../tool/tool"
import { TrpSpecification as S } from "./specification"
import { TrpNextflow as N } from "./nextflow"
import { TrpResources as R } from "./resources"
import { TrpEvidence as E } from "./evidence"
import { Protocol } from "../nfcore/protocol"
import { HandCount } from "../nfcore/handcount"
import { TrpInterventions } from "./interventions"
import { TrpEnforcement } from "./enforcement"
import { TrpRemoteEnforcement } from "./remote-enforcement"
import { TrpRemote } from "./remote"

interface Draft {
  id: string
  bundle: N.Bundle
  evidenceRoot: string
  directory: string
  validationBytes: number
  demand: R.Demand
  budget: R.Budget
  event: ReturnType<typeof E.ledger>
  evidence?: Awaited<ReturnType<typeof E.pack>>
  abort: AbortController
  status: "prepared" | "reviewing" | "consumed"
  target?: TrpRemote.Target
}
export interface Preview {
  id: string
  digest: string
  specification: S.Specification
  validation: N.Bundle["report"]
  files: Record<string, string>
  command: readonly string[]
  limits: string
  admission: R.Decision
  inventory: R.Inventory
  budget: R.Budget
}
export interface RunResult {
  directory: string
  digest: string
  status: "succeeded"
  geometry: ReturnType<typeof N.validateGeometry>
  evidence: Awaited<ReturnType<typeof E.pack>>
}
export interface Interface {
  prepare: (raw: unknown, evidenceRoot: string, session: string, budget?: R.Budget) => Effect.Effect<Preview>
  run: (id: string, digest: string, ctx: Tool.Context) => Effect.Effect<RunResult>
}
export class Service extends Context.Service<Service, Interface>()("@helix/TrpWorkflow") {}

async function measureTasks(directory: string) {
  const counts = []
  for (const name of ["trace.tsv", "dry-run/trace.tsv"]) {
    const lines = (await fs.readFile(path.join(directory, name), "utf8"))
      .trim()
      .split(/\r?\n/)
      .map((s) => s.split("\t"))
    const status = lines[0].indexOf("status"),
      exit = lines[0].indexOf("exit")
    if (
      lines.length !== 3 ||
      status < 0 ||
      exit < 0 ||
      lines.slice(1).some((r) => r[status] !== "COMPLETED" || r[exit] !== "0")
    )
      throw new S.WorkflowError("trace-count", "Expected exactly two completed tasks per traversal")
    counts.push(lines.length - 1)
  }
  return { scientificTasks: counts[0], stubTasks: counts[1] }
}

const layer = Layer.effect(
  Service,
  Effect.gen(function* () {
    const process = yield* AppProcess.Service
    const question = yield* Question.Service
    const resources = yield* R.Service
    const protocol = yield* Protocol.Service
    const state = yield* InstanceState.make(() =>
      Effect.succeed({ drafts: new Map<string, Draft>(), generations: new Map<string, string>() }),
    )
    const prepare: Interface["prepare"] = (raw, evidenceRoot, session, budget) =>
      Effect.gen(function* () {
        const directory = yield* InstanceState.directory
        budget = budget ? structuredClone(budget) : undefined
        const { drafts, generations } = yield* InstanceState.get(state)
        // A new proposal invalidates the previous proposal immediately, even if validation fails.
        drafts.get(session)?.abort.abort(new Error("Proposal replaced"))
        drafts.delete(session)
        const generation = randomUUID()
        generations.set(session, generation)
        if (generations.size > 100) {
          const oldest = generations.keys().next().value!
          drafts.get(oldest)?.abort.abort(new Error("Proposal evicted"))
          drafts.delete(oldest)
          generations.delete(oldest)
        }
        const target = yield* Effect.promise(() => TrpRemote.configured())
        const bundle = yield* Effect.promise(() => N.prepare(raw, evidenceRoot, directory))
        if (target) TrpRemote.bind(bundle, target, generation)
        const demand = R.count(bundle.files)
        const parent = yield* Effect.promise(() => E.parent(directory))
        const observation = yield* (
          target ? TrpRemote.observe(target, process.run) : resources.observe(directory)
        ).pipe(Effect.exit)
        if (observation._tag === "Failure") {
          const admission = R.admit(demand, undefined, budget)
          yield* Effect.promise(() =>
            E.write(parent, `rejected-${generation}.json`, {
              session,
              inventory: null,
              budget: budget ?? null,
              admission,
              cause: String(observation.cause),
            }),
          )
          return yield* Effect.die(new S.WorkflowError("inventory-unavailable", S.canonical(admission)))
        }
        const inventory = observation.value
        const admission = R.admit(demand, inventory, budget)
        if (!admission.accepted || !budget) {
          yield* Effect.promise(() =>
            E.write(parent, `rejected-${generation}.json`, { session, inventory, budget: budget ?? null, admission }),
          )
          return yield* Effect.die(new S.WorkflowError("resource-rejected", S.canonical(admission)))
        }
        const allocation = inventory.enforcement
        if (allocation) yield* Effect.promise(() => TrpEnforcement.claim(allocation))
        if (inventory.remoteStrict) yield* Effect.promise(() => TrpRemoteEnforcement.claim(inventory.remoteStrict!))
        const action = {
          request: bundle.spec.intent.value,
          detail: S.canonical(bundle.spec) + " " + N.command.join(" "),
        }
        const guarded = yield* protocol.guard(action)
        const protocolSnapshot = {
          state: (yield* protocol.read()) ?? null,
          ledger: yield* protocol.ledger(),
          check: guarded.result,
        }
        if (guarded.result.refused || (guarded.result.enforced && guarded.result.unevaluated.length)) {
          yield* Effect.promise(() =>
            E.write(parent, `rejected-${generation}.json`, {
              session,
              inventory,
              budget,
              admission,
              protocol: protocolSnapshot,
            }),
          )
          return yield* Effect.die(
            new S.WorkflowError("protocol-rejected", "Binding protocol violated or contains unevaluated constraints"),
          )
        }
        const validationBytes = Buffer.byteLength(bundle.files["validation.json"])
        bundle.report.checks = bundle.report.checks.map((check) =>
          check.code === "resource-admission"
            ? {
                ...check,
                status: "passed" as const,
                detail: inventory.remoteStrict
                  ? "Root policy and kernel receipts verify one XFS project for co-located client and Slurm work, plus shared client/controller cgroup. See inventory.json and remote_strict_policy.json."
                  : inventory.enforcement
                    ? "Dated inventory, explicit budget, XFS quota and controller/task cgroups verified. See admission.json and enforcement.json."
                    : "Dated inventory and explicit budget checked; storage is an estimate, not a quota. See admission.json.",
              }
            : check,
        )
        Object.assign(bundle.files, {
          "validation.json": S.canonical(bundle.report) + "\n",
          "inventory.json": S.canonical(inventory) + "\n",
          "budget.json": S.canonical(budget) + "\n",
          "admission.json": S.canonical(admission) + "\n",
          "protocol.json": S.canonical(protocolSnapshot) + "\n",
        })
        bundle.digest = N.bundleDigest(bundle.files)
        if (generations.get(session) !== generation)
          return yield* Effect.die(
            new S.WorkflowError("proposal-superseded", "A newer proposal replaced this preparation"),
          )
        const destination = path.join(parent, `${bundle.digest.slice(0, 12)}-${generation}`)
        yield* Effect.promise(() => N.materialize(bundle, destination))
        const event = E.ledger(destination)
        yield* Effect.promise(async () => {
          await event("admission", "accepted-for-review", admission)
          await event("protocol", guarded.result.committed ? "checked" : "not-committed", protocolSnapshot)
          await E.write(destination, "run.json", { digest: bundle.digest, status: "prepared", outputs: [] })
        })
        const draft: Draft = {
          id: generation,
          bundle,
          evidenceRoot,
          directory: destination,
          validationBytes,
          demand,
          budget,
          event,
          abort: new AbortController(),
          status: "prepared",
          target,
        }
        drafts.set(session, draft)
        if (drafts.size > 100) {
          const oldest = drafts.keys().next().value!
          drafts.get(oldest)?.abort.abort(new Error("Proposal evicted"))
          drafts.delete(oldest)
          generations.delete(oldest)
        }
        return {
          id: draft.id,
          digest: bundle.digest,
          specification: structuredClone(bundle.spec),
          validation: structuredClone(bundle.report),
          files: Object.fromEntries(Object.entries(bundle.files).map(([name, text]) => [name, S.sha256(text)])),
          command: N.command,
          admission: structuredClone(admission),
          inventory: structuredClone(inventory),
          budget: structuredClone(budget),
          limits: inventory.remoteStrict
            ? "Verified co-located Slurm: real Helix client and Python/Nextflow share 1 CPU/2 GiB/swap-zero controller cgroup; declared client/work/temp/state/cache/export and worker-visible remote work inherit one global XFS project quota. Sequential worker Docker tasks have 2 CPU/2 GiB limits. Python transport is local to the verified head; no SSH transport is claimed. No automatic retries."
            : target
              ? "SSH/Slurm on the reviewed operator target. Controller: reservation 1 CPU/2 GiB on head; each sequential Docker task: 2 CPU/2 GiB with effective cgroup observations. Worker memory is not pooled. Storage is estimated; no hard disk quota or exclusive CPU allocation. Two stub tasks then two scientific tasks, no automatic retries."
              : inventory.enforcement
                ? "Local Docker in an operator allocation: XFS project quota; controller 1 CPU/2 GiB; sequential tasks 2 CPU/2 GiB; aggregate 3 CPU/4 GiB. No automatic retries."
                : "Local Docker; two stub tasks followed by two real tasks, each at most 2 CPUs, 2 GB RAM and 3 minutes. Host inventory and reviewed budget required; storage is an estimate with no aggregate quota. No automatic retries.",
        }
      }).pipe(Effect.orDie)

    const run: Interface["run"] = (id, digest, ctx) =>
      Effect.gen(function* () {
        const { drafts } = yield* InstanceState.get(state)
        const directory = yield* InstanceState.directory
        const draft = drafts.get(ctx.sessionID)
        if (!draft || draft.id !== id || draft.bundle.digest !== digest || draft.status !== "prepared") {
          return yield* Effect.die(
            new S.WorkflowError(
              "approval-mismatch",
              "Unknown, replaced, already submitted or changed proposal. Prepare and review the current specification.",
            ),
          )
        }
        draft.status = "reviewing"
        const signal = AbortSignal.any([ctx.abort, draft.abort.signal])
        const destination = draft.directory
        const log = (source: E.Event["source"], outcome: string, detail: unknown) =>
          Effect.promise(() => draft.event(source, outcome, detail))
        const runProcess: typeof process.run = (command, options) =>
          Effect.gen(function* () {
            const startedAt = new Date().toISOString(),
              start = Date.now()
            const argv =
              command._tag === "StandardCommand" ? [command.command, ...command.args] : ["unsupported-pipeline"]
            if (argv[0] === "ssh")
              argv[argv.length - 1] =
                `python3 -c <approved-runner-sha256:${S.sha256(draft.bundle.files["remote_runner.py"])}>`
            const result = yield* process.run(command, options).pipe(
              Effect.onExit((exit) =>
                Effect.promise(async () => {
                  const value =
                    exit._tag === "Success"
                      ? {
                          exitCode: exit.value.exitCode,
                          stdoutBytes: exit.value.stdout.length,
                          stderrBytes: exit.value.stderr.length,
                          stdoutTruncated: exit.value.stdoutTruncated,
                          stderrTruncated: exit.value.stderrTruncated,
                        }
                      : { failure: String(exit.cause) }
                  await fs.appendFile(
                    path.join(destination, "processes.jsonl"),
                    S.canonical({ argv, startedAt, durationMs: Date.now() - start, ...value }) + "\n",
                  )
                }),
              ),
            )
            return result
          })
        return yield* Effect.gen(function* () {
          // Permissions can be configured to auto-allow; they are distinct from the
          // scientific confirmation below, which is never supplied as an LLM argument.
          yield* log("permission", "requested", { digest, permission: "trp_run" })
          yield* ctx
            .ask({
              permission: "trp_run",
              patterns: [digest],
              always: [],
              metadata: { digest, command: N.command, specification: draft.bundle.spec },
            })
            .pipe(
              Effect.onExit((exit) =>
                exit._tag === "Failure"
                  ? log("permission", "denied-or-error", { cause: String(exit.cause) })
                  : Effect.void,
              ),
            )
          yield* log("permission", "returned-allowed", {
            digest,
            mode: "human-or-policy; ctx.ask does not expose which",
          })
          yield* log("approval", "requested", { digest, channel: "Question.Service" })
          const answers = yield* question
            .ask({
              sessionID: ctx.sessionID,
              tool: ctx.callID ? { messageID: ctx.messageID, callID: ctx.callID } : undefined,
              questions: [
                {
                  header: "Ejecutar análisis TRP",
                  question: `Aprobación de la especificación ${digest}.\nInfraestructura aprobada: ${draft.target ? S.canonical(draft.target.public) : "equipo local"}.\nSe comprobará la configuración y se ejecutarán dos tareas simuladas de recorrido en seco, seguidas de dos tareas reales con Docker y Nextflow (máximo por tarea: 2 CPU, 2 GB, 3 minutos), sin reintentos. Se guardarán entradas, código, aprobación, validación y resultados en .helix/trp/. Esta ruta calcula geometría de unidades suministradas; no detecta repeticiones.\n\nPresupuesto propuesto (su aprobación autoriza estos límites):\n${JSON.stringify(draft.budget, null, 2)}\nReserva calculada y supuestos:\n${JSON.stringify(draft.demand, null, 2)}\n${draft.bundle.files["remote_strict_policy.json"] ? "Perfil Slurm co-localizado verificado: cliente real y controlador/Nextflow comparten 1 CPU/2 GiB/swap cero; sus rutas de trabajo y las de los trabajadores heredan una única cuota XFS global. Transporte Python local en el head verificado; no es transporte SSH. Cada tarea del trabajador tiene límite independiente de 2 CPU/2 GiB." : draft.bundle.files["enforcement.json"] ? "Cuota XFS y límites agregados de CPU/memoria verificados; controlador y tareas comparten la asignación." : "El espacio de trabajo es una estimación sin cuota agregada."} El presupuesto global de API no está medido por esta ruta.\nProtocolo comprobado:\n${draft.bundle.files["protocol.json"]}\n\nEspecificación completa y fuentes declaradas:\n${JSON.stringify(draft.bundle.spec, null, 2)}\n\nComprobaciones omitidas:\n${draft.bundle.report.checks
                    .filter((c) => c.status === "omitted")
                    .map((c) => c.detail)
                    .join(
                      "\n",
                    )}\n\nLa aprobación se invalida si cambian la propuesta, las entradas, el catálogo o el código generado.`,
                  options: [
                    {
                      label: "Aprobar y ejecutar",
                      description: "Ejecutar esta especificación y conservar sus artefactos.",
                    },
                    { label: "Rechazar", description: "Volver a la especificación sin ejecutar." },
                  ],
                  multiple: false,
                  custom: false,
                },
              ],
            })
            .pipe(
              Effect.raceFirst(AppProcess.waitForAbort(signal)),
              Effect.onExit((exit) =>
                exit._tag === "Failure"
                  ? log("approval", "rejected-or-cancelled", { cause: String(exit.cause) })
                  : Effect.void,
              ),
            )
          yield* log("approval", "answered", { answers, channel: "Question.Service", digest })
          if (answers.length !== 1 || answers[0].length !== 1 || answers[0][0] !== "Aprobar y ejecutar") {
            return yield* Effect.die(new S.WorkflowError("approval-denied", "The proposal was not approved"))
          }
          if (signal.aborted || drafts.get(ctx.sessionID) !== draft)
            return yield* Effect.die(
              new S.WorkflowError("approval-invalidated", "Proposal replaced or cancelled during review"),
            )
          // Re-read source and catalogue reference evidence after the human response.
          const targetNow = yield* Effect.promise(() => TrpRemote.configured())
          if (targetNow?.fingerprint !== draft.target?.fingerprint)
            return yield* Effect.die(
              new S.WorkflowError(
                "remote-target-changed",
                "Operator target or SSH trust changed during review; prepare again",
              ),
            )
          const fresh = yield* Effect.promise(() => N.prepare(draft.bundle.spec, draft.evidenceRoot, directory))
          if (targetNow) TrpRemote.bind(fresh, targetNow, draft.id)
          const protocolNow = {
            state: (yield* protocol.read()) ?? null,
            ledger: yield* protocol.ledger(),
            check: yield* protocol.check({
              request: fresh.spec.intent.value,
              detail: S.canonical(fresh.spec) + " " + N.command.join(" "),
            }),
          }
          if (S.canonical(protocolNow) + "\n" !== draft.bundle.files["protocol.json"])
            return yield* Effect.die(
              new S.WorkflowError("protocol-changed", "Protocol changed during approval; prepare again"),
            )
          for (const name of ["inventory.json", "budget.json", "admission.json", "protocol.json", "validation.json"])
            fresh.files[name] = draft.bundle.files[name]
          fresh.report = draft.bundle.report
          fresh.digest = N.bundleDigest(fresh.files)
          if (fresh.digest !== digest || signal.aborted || drafts.get(ctx.sessionID) !== draft)
            return yield* Effect.die(new S.WorkflowError("approval-invalidated", "Bundle changed during review"))
          const observed = yield* draft.target
            ? TrpRemote.observe(draft.target, runProcess, signal)
            : resources.observe(directory)
          const decision = R.admit(draft.demand, observed, draft.budget)
          yield* Effect.promise(() => E.write(destination, "recheck.json", { inventory: observed, decision }))
          yield* log("admission", decision.accepted ? "recheck-accepted" : "recheck-rejected", decision)
          if (!decision.accepted)
            return yield* Effect.die(new S.WorkflowError("resource-rejected", S.canonical(decision)))
          yield* Effect.promise(() => N.verifyMaterialized(fresh, destination))
          yield* Effect.promise(() =>
            fs.writeFile(
              path.join(destination, "approval.json"),
              JSON.stringify(
                {
                  digest,
                  engine: S.ENGINE,
                  sessionID: ctx.sessionID,
                  messageID: ctx.messageID,
                  callID: ctx.callID ?? null,
                  channel: "Question.Service",
                  answer: answers[0][0],
                  recordedAt: new Date().toISOString(),
                },
                null,
                2,
              ),
            ),
          )
          const execute = Effect.gen(function* () {
            yield* Effect.promise(() => N.verifyMaterialized(fresh, destination))
            if (draft.target) {
              yield* TrpRemote.execute(
                draft.target,
                fresh,
                destination,
                draft.id,
                draft.budget,
                runProcess,
                signal,
                (outcome, detail) =>
                  draft.event(outcome.startsWith("analysis-") ? "admission" : "execution", outcome, detail),
              )
              yield* Effect.promise(() => N.verifyMaterialized(fresh, destination))
              const geometry = yield* Effect.promise(async () =>
                N.validateGeometry(
                  await fs.readFile(path.join(destination, "results", "geometry.csv"), "utf8"),
                  fresh.spec,
                ),
              )
              const measuredTasks = yield* Effect.promise(() => measureTasks(destination))
              yield* log("execution", "completed", { digest, geometry, measuredTasks, backend: TrpRemote.VERSION })
              const record = {
                digest,
                status: "succeeded" as const,
                geometry,
                measuredTasks,
                outputs: ["results/geometry.csv"],
                backend: TrpRemote.VERSION,
              }
              yield* Effect.promise(() => E.write(destination, "run.json", record))
              return { ...record, directory: destination }
            }
            const endpoint = yield* runProcess(
              ChildProcess.make("docker", ["context", "inspect", "--format", "{{.Endpoints.docker.Host}}"]),
              { signal, timeout: "15 seconds", maxOutputBytes: 4096, maxErrorBytes: 8192 },
            )
            const endpointText = globalThis.process.env.DOCKER_HOST || endpoint.stdout.toString().trim()
            yield* Effect.promise(() =>
              E.write(destination, "docker-endpoint.json", { endpoint: endpointText, exitCode: endpoint.exitCode }),
            )
            if (endpoint.exitCode !== 0 || !endpointText.startsWith("unix://"))
              return yield* Effect.die(
                new S.WorkflowError("docker-remote", "Inventory applies only to a local Unix-socket Docker daemon"),
              )
            const image = yield* runProcess(
              ChildProcess.make("docker", ["image", "inspect", "--format", "{{.Id}}", fresh.image]),
              { signal, timeout: "15 seconds", maxOutputBytes: 4096, maxErrorBytes: 8192 },
            )
            if (image.exitCode !== 0 || image.stdout.toString().trim() !== fresh.image)
              return yield* Effect.die(
                new S.WorkflowError(
                  "image-unavailable",
                  "Exact admitted image must already exist locally; no tag substitution or automatic pull",
                ),
              )
            const version = yield* runProcess(
              ChildProcess.make("nextflow", ["-version"], {
                cwd: destination,
                extendEnv: true,
                env: { NXF_OFFLINE: "true", NXF_DISABLE_CHECK_LATEST: "true" },
              }),
              { signal, timeout: "30 seconds", maxOutputBytes: 8192, maxErrorBytes: 8192 },
            )
            const versionText = version.stdout.toString() + version.stderr.toString()
            if (version.exitCode !== 0 || !/version 25\.10\.4\b/.test(versionText))
              return yield* Effect.die(
                new S.WorkflowError("nextflow-version", "This adapter requires the tested Nextflow 25.10.4 release"),
              )
            yield* Effect.promise(() => fs.writeFile(path.join(destination, "nextflow-version.txt"), versionText))
            yield* Effect.promise(() =>
              E.write(destination, "software.json", { nextflowVersionOutput: versionText, image: fresh.image }),
            )
            const config = yield* runProcess(
              ChildProcess.make(N.configCommand[0], N.configCommand.slice(1), {
                cwd: destination,
                extendEnv: true,
                env: { NXF_OFFLINE: "true", NXF_DISABLE_CHECK_LATEST: "true" },
              }),
              { signal, timeout: "30 seconds", maxOutputBytes: 1_000_000, maxErrorBytes: 1_000_000 },
            )
            yield* Effect.promise(async () => {
              await fs.writeFile(path.join(destination, "resolved.config.txt"), config.stdout)
              await fs.writeFile(path.join(destination, "config.stderr.log"), config.stderr)
              await fs.writeFile(
                path.join(destination, "preflight.json"),
                JSON.stringify({ config: { exitCode: config.exitCode }, dryRun: "not started" }, null, 2),
              )
            })
            if (config.exitCode !== 0)
              return yield* Effect.die(
                new S.WorkflowError("config-failed", `Nextflow configuration failed; see ${destination}`),
              )
            const dryDirectory = path.join(destination, "dry-run")
            yield* Effect.promise(() => N.materialize(fresh, dryDirectory))
            const dry = yield* runProcess(
              ChildProcess.make(N.dryCommand[0], N.dryCommand.slice(1), {
                cwd: dryDirectory,
                extendEnv: true,
                env: { NXF_OFFLINE: "true", NXF_DISABLE_CHECK_LATEST: "true" },
              }),
              { signal, timeout: "8 minutes", maxOutputBytes: 1_000_000, maxErrorBytes: 1_000_000 },
            )
            const marked = yield* Effect.promise(async () => {
              await fs.writeFile(path.join(dryDirectory, "stdout.log"), dry.stdout)
              await fs.writeFile(path.join(dryDirectory, "stderr.log"), dry.stderr)
              const marker = await fs
                .readFile(path.join(dryDirectory, "results", "geometry.csv"), "utf8")
                .catch(() => "")
              await fs.writeFile(
                path.join(destination, "preflight.json"),
                JSON.stringify(
                  {
                    config: { exitCode: config.exitCode },
                    dryRun: { exitCode: dry.exitCode, scientificResult: false, marker },
                  },
                  null,
                  2,
                ),
              )
              return marker.trim() === "STUB_ONLY_NO_SCIENTIFIC_RESULT"
            })
            if (dry.exitCode !== 0 || !marked)
              return yield* Effect.die(
                new S.WorkflowError("dry-run-failed", `Nextflow stub traversal failed; see ${destination}`),
              )
            yield* Effect.promise(() => N.verifyMaterialized(fresh, dryDirectory))
            yield* Effect.promise(() => N.verifyMaterialized(fresh, destination))
            const finalInventory = yield* resources.observe(directory)
            const finalDecision = R.admit(draft.demand, finalInventory, draft.budget)
            yield* Effect.promise(() =>
              E.write(destination, "analysis-admission.json", { inventory: finalInventory, decision: finalDecision }),
            )
            yield* log("admission", finalDecision.accepted ? "analysis-accepted" : "analysis-rejected", finalDecision)
            if (!finalDecision.accepted)
              return yield* Effect.die(new S.WorkflowError("resource-rejected", S.canonical(finalDecision)))
            const result = yield* runProcess(
              ChildProcess.make(N.command[0], N.command.slice(1), {
                cwd: destination,
                extendEnv: true,
                env: { NXF_OFFLINE: "true", NXF_DISABLE_CHECK_LATEST: "true" },
              }),
              { signal, timeout: "8 minutes", maxOutputBytes: 1_000_000, maxErrorBytes: 1_000_000 },
            )
            yield* Effect.promise(async () => {
              await fs.writeFile(path.join(destination, "stdout.log"), result.stdout)
              await fs.writeFile(path.join(destination, "stderr.log"), result.stderr)
            })
            if (result.exitCode !== 0)
              return yield* Effect.die(
                new S.WorkflowError("nextflow-failed", `Nextflow exit ${result.exitCode}; see ${destination}`),
              )
            yield* Effect.promise(() => N.verifyMaterialized(fresh, destination))
            const geometry = yield* Effect.promise(async () =>
              N.validateGeometry(
                await fs.readFile(path.join(destination, "results", "geometry.csv"), "utf8"),
                fresh.spec,
              ),
            )
            const measuredTasks = yield* Effect.promise(async () => {
              const counts = []
              for (const name of ["trace.tsv", "dry-run/trace.tsv"]) {
                const lines = (await fs.readFile(path.join(destination, name), "utf8"))
                  .trim()
                  .split(/\r?\n/)
                  .map((line) => line.split("\t"))
                const status = lines[0].indexOf("status"),
                  exit = lines[0].indexOf("exit")
                if (
                  lines.length !== 3 ||
                  status < 0 ||
                  exit < 0 ||
                  lines.slice(1).some((r) => r[status] !== "COMPLETED" || r[exit] !== "0")
                )
                  throw new S.WorkflowError("trace-count", "Expected exactly two completed tasks per traversal")
                counts.push(lines.length - 1)
              }
              return { scientificTasks: counts[0], stubTasks: counts[1] }
            })
            yield* log("execution", "completed", { digest, geometry, measuredTasks })
            const record = {
              digest,
              status: "succeeded" as const,
              geometry,
              measuredTasks,
              outputs: ["results/geometry.csv"],
            }
            yield* Effect.promise(() =>
              fs.writeFile(path.join(destination, "run.json"), JSON.stringify(record, null, 2)),
            )
            return { ...record, directory: destination }
          })
          return yield* execute
        }).pipe(
          Effect.onExit((exit) =>
            Effect.promise(async () => {
              if (exit._tag === "Failure") {
                await draft.event("execution", "failed-or-rejected", { error: String(exit.cause) })
                await E.write(destination, "run.json", {
                  status: "failed",
                  digest,
                  error: String(exit.cause),
                  outputs: [],
                })
              }
              await E.write(destination, "interventions.json", {
                source:
                  "Tool.Context.messages at run entry; Question.Service answers are separately recorded in events.jsonl",
                coverage: "provided transcript snapshot only; not a full-session coverage claim",
                taxonomy: HandCount.TAXONOMY_VERSION,
                classifier: TrpInterventions.VERSION,
                tally: TrpInterventions.tally(HandCount.turnsFromMessages(ctx.messages)),
                externalAgreement: null,
                limitation: "Spanish/English surface-cue heuristic; independent annotation and kappa remain pending.",
              })
              await E.methods(destination)
              draft.evidence = await E.pack(destination, draft.bundle, draft.validationBytes)
              await E.write(destination, "evidence-location.json", draft.evidence)
            }),
          ),
          Effect.map((result) => ({ ...result, evidence: draft.evidence! })),
          Effect.ensuring(
            Effect.sync(() => {
              draft.status = "consumed"
            }),
          ),
        )
      }).pipe(Effect.orDie)
    return Service.of({ prepare, run })
  }),
)

export const node = LayerNode.make({
  service: Service,
  layer,
  deps: [AppProcess.node, Question.node, R.node, Protocol.node],
})
