/** Opt-in, real local Helix gates with independent callback/action observations.
 * Engineering fixture only: no model, human labels, cloud access or science jobs.
 */
import { expect } from "bun:test"
import { Cause, Effect, Exit, Fiber, Layer, Queue } from "effect"
import { LayerNode } from "@helix/core/effect/layer-node"
import { AppProcess } from "@helix/core/process"
import fs from "node:fs/promises"
import path from "node:path"
import { TrpWorkflow } from "../../src/trp/workflow"
import { TrpResources as R } from "../../src/trp/resources"
import { TrpSpecification as S } from "../../src/trp/specification"
import { Protocol } from "../../src/nfcore/protocol"
import { Question } from "../../src/question"
import { EventV2Bridge } from "../../src/event-v2-bridge"
import { Agent } from "../../src/agent/agent"
import { Truncate } from "../../src/tool/truncate"
import { TrpPrepareTool, TrpRunTool } from "../../src/tool/trp"
import { InstanceState } from "../../src/effect/instance-state"
import { SessionID, MessageID } from "../../src/session/schema"
import { testEffect } from "../lib/effect"
import budget from "../../../../evaluation/trp/development/f4-budget.json"
import source from "../../../../evaluation/trp/development/f3-reference-spec.json"

const root = path.resolve(import.meta.dir, "../../../..")
const enabled = process.env.TRP_NEGATIVE_CAMPAIGN === "1"
const output = path.resolve(process.env.TRP_NEGATIVE_OUTPUT ?? path.join(root, "evaluation/trp/campaign-20261012/event-negative-contrasts/primary"))
const protocolFile = path.join(path.dirname(output), "protocol.json")
type Action = { at: string; order: number; source: string; outcome: string; detail: unknown }
let externalLaunchAttempts = 0
const forbiddenProcess = Layer.mock(AppProcess.Service, {
  run: () => {
    externalLaunchAttempts++
    return Effect.die(new Error("Negative campaign must not launch Nextflow, Docker or SSH"))
  },
})
const it = testEffect(LayerNode.compile(
  LayerNode.group([TrpWorkflow.node, R.node, Protocol.node, Question.node, EventV2Bridge.node, Agent.node, Truncate.node]),
  [[AppProcess.node, forbiddenProcess]],
))
const run = enabled ? it.instance : it.instance.skip
const cases = ["permission-denied", "approval-rejected", "protocol-rejected", "admission-rejected"] as const

for (const id of cases) run(`independent negative action oracle: ${id}`, () => Effect.gen(function* () {
  const launchCountBefore = externalLaunchAttempts
  if (process.env.HELIX_TRP_REMOTE || process.env.HELIX_TRP_SANDBOX)
    throw new Error("Run this local campaign with remote/sandbox environment unset")
  const freeze = yield* Effect.promise(async () => {
    const value = JSON.parse(await fs.readFile(protocolFile, "utf8"))
    for (const item of value.sources)
      if (S.sha256(await fs.readFile(path.join(root, item.path))) !== item.sha256)
        throw new Error("Prospective source changed: " + item.path)
    return value
  })
  const planned = freeze.cases.find((c: { id: string }) => c.id === id)
  if (!planned) throw new Error("Case absent from prospective freeze")
  const caseOutput = path.join(output, id)
  yield* Effect.promise(() => fs.mkdir(caseOutput, { recursive: false }))
  const directory = yield* InstanceState.directory
  yield* Effect.promise(() => fs.copyFile(path.join(root, source.structure.value.path), path.join(directory, "input.pdb")))
  const raw = { ...structuredClone(source), catalogHash: S.catalogHash }
  raw.structure.value.path = "input.pdb"
  const actions: Action[] = []
  const observe = (kind: string, outcome: string, detail: unknown) => {
    actions.push({ at: new Date().toISOString(), order: actions.length, source: kind, outcome, detail })
  }
  const resources = yield* R.Service
  const realObserve = resources.observe
  // Instrument only this isolated service instance. The actual host observer runs.
  Reflect.set(resources, "observe", (workspace: string) => Effect.gen(function* () {
    observe("inventory", "requested", { workspace })
    const result = yield* realObserve(workspace)
    observe("inventory", "observed", result)
    return result
  }))
  const protocol = yield* Protocol.Service
  const realGuard = protocol.guard
  Reflect.set(protocol, "guard", (action: Protocol.Action) => Effect.gen(function* () {
    observe("protocol", "guard-requested", action)
    const result = yield* realGuard(action)
    observe("protocol", "guard-returned", result)
    return result
  }))
  if (id === "protocol-rejected") yield* protocol.commit({
    statement: "Independent negative engineering campaign: prohibit the supplied geometry request.",
    constraints: [{ id: "geometry-prohibited", text: "This campaign prohibits the supplied GeomeTRe request.", triggers: ["geometre"] }],
    posture: "binding", committedBy: "synthetic engineering fixture",
  })
  const question = yield* Question.Service
  const bridge = yield* EventV2Bridge.Service
  const asked = yield* Queue.unbounded<void>()
  const off = yield* bridge.listen((event) => {
    if (event.type === Question.Event.Asked.type) {
      observe("approval", "question-asked", event)
      Queue.offerUnsafe(asked, undefined)
    }
    if (event.type === Question.Event.Replied.type) observe("approval", "question-replied", event)
    if (event.type === Question.Event.Rejected.type) observe("approval", "question-rejected", event)
    return Effect.void
  })
  yield* Effect.addFinalizer(() => off)
  const ctx = {
    sessionID: SessionID.make("ses_negative-" + id),
    messageID: MessageID.make("msg_negative-" + id),
    callID: "negative-" + id, agent: "build", abort: new AbortController().signal,
    messages: [], metadata: () => Effect.void,
    ask: (request: unknown) => Effect.gen(function* () {
      observe("permission", "requested", request)
      if (id === "permission-denied") {
        observe("permission", "denied", { cause: "prospectively specified synthetic permission refusal" })
        return yield* Effect.die(new Error("Independent synthetic permission refusal"))
      }
      observe("permission", "allowed", { actor: "authorized synthetic engineering callback" })
    }),
  }
  const prepareTool = yield* (yield* TrpPrepareTool).init()
  const runTool = yield* (yield* TrpRunTool).init()
  observe("driver", "prepare-requested", { id, budget: id === "admission-rejected" ? { ...budget, cpus: 1 } : budget })
  const preparation = yield* prepareTool.execute({
    specification: S.parse(raw), evidence_root: root,
    budget: id === "admission-rejected" ? { ...budget, cpus: 1 } : budget,
  }, ctx).pipe(Effect.exit)
  let terminal: Exit.Exit<unknown, unknown> = preparation
  if (Exit.isSuccess(preparation)) {
    observe("driver", "prepare-returned", preparation.value.metadata)
    const preview = preparation.value.metadata
    const fiber = yield* runTool.execute({ id: preview.id, digest: preview.digest }, ctx).pipe(Effect.exit, Effect.forkScoped)
    if (id === "approval-rejected") {
      for (;;) {
        const pending = (yield* question.list()).find(q => q.sessionID === ctx.sessionID)
        if (!pending) { yield* Queue.take(asked).pipe(Effect.timeout("5 seconds")); continue }
        observe("driver", "question-reply-requested", { requestID: pending.id, answers: [["Rechazar"]] })
        yield* question.reply({ requestID: pending.id, answers: [["Rechazar"]] })
        break
      }
    }
    terminal = yield* Fiber.join(fiber)
  }
  observe("driver", "terminal-observed", { failed: Exit.isFailure(terminal), cause: Exit.isFailure(terminal) ? Cause.pretty(terminal.cause) : null })
  const producer = yield* Effect.promise(async () => {
    await fs.cp(path.join(directory, ".helix"), path.join(caseOutput, "producer"), { recursive: true })
    await fs.writeFile(path.join(caseOutput, "actions.json"), JSON.stringify(actions, null, 2) + "\n", { flag: "wx" })
    const files = await fs.readdir(path.join(directory, ".helix", "trp"), { withFileTypes: true })
    const runFolder = files.find(item => item.isDirectory() && !item.name.startsWith("rejected-"))
    return { preparationSucceeded: Exit.isSuccess(preparation), terminalFailed: Exit.isFailure(terminal),
      cause: Exit.isFailure(terminal) ? Cause.pretty(terminal.cause) : null,
      runDirectory: runFolder ? "producer/trp/" + runFolder.name : null,
      sourceFreezeSha256: S.sha256(await fs.readFile(protocolFile)),
      actionOracleBeforeProducerRead: true, expected: planned,
      actualHostInventory: true, syntheticCallbacks: true, modelCalls: 0, awsOperations: 0,
      forbiddenExternalLaunchAttempts: externalLaunchAttempts - launchCountBefore,
      scientificTasksLaunched: 0, humanLabels: 0, scientificMetrics: null }
  })
  yield* Effect.promise(() => fs.writeFile(path.join(caseOutput, "case.json"), JSON.stringify(producer, null, 2) + "\n", { flag: "wx" }))
  expect(producer.terminalFailed).toBe(true)
  expect(producer.forbiddenExternalLaunchAttempts).toBe(0)
  expect(producer.preparationSucceeded).toBe(id === "permission-denied" || id === "approval-rejected")
  expect(producer.cause).toContain(planned.causeContains)
}), { timeout: 30000 })
