/** Real local preparation only, testing metadata instead of visual truncation. */
import fs from "node:fs/promises"
import path from "node:path"
import { Effect } from "../../../../../../packages/core/node_modules/effect/dist/index.js"
import { LayerNode } from "../../../../../../packages/core/src/effect/layer-node"

const root = path.resolve(import.meta.dir, "../../../../../..")
const [workspace, output] = process.argv.slice(2)
if (!workspace || !output) throw new Error("Supply isolated workspace and report")
process.chdir(workspace)
await fs.writeFile(path.join(workspace, "helix.json"), JSON.stringify({ plugin: [], share: "disabled" }))
const reference = path.join(root, "evaluation/trp/campaign-20261012/cloud/lab1/cancellation/next-ctx-abort/out/running-job/evidence/run")
await fs.copyFile(path.join(reference, "source.pdb"), path.join(workspace, "input.pdb"))
await import("../../../../../../packages/core/src/global")
await import("../../../../../../packages/core/src/fs-util")
await import("../../../../../../packages/helix/src/project/bootstrap")
const [{ TrpWorkflow }, { TrpPrepareTool }, { Question }, { EventV2Bridge }, { Agent }, { Truncate },
  { InstanceStore }, { InstanceBootstrap }, { SessionID, MessageID }, { TrpSpecification: S }] = await Promise.all([
  import("../../../../../../packages/helix/src/trp/workflow"), import("../../../../../../packages/helix/src/tool/trp"),
  import("../../../../../../packages/helix/src/question"), import("../../../../../../packages/helix/src/event-v2-bridge"),
  import("../../../../../../packages/helix/src/agent/agent"), import("../../../../../../packages/helix/src/tool/truncate"),
  import("../../../../../../packages/helix/src/project/instance-store"), import("../../../../../../packages/helix/src/project/bootstrap"),
  import("../../../../../../packages/helix/src/session/schema"), import("../../../../../../packages/helix/src/trp/specification"),
])
const layer = LayerNode.compile(LayerNode.group([TrpWorkflow.node, Question.node, EventV2Bridge.node, Agent.node, Truncate.node, InstanceStore.node]),
  [[InstanceStore.bootstrapNode, InstanceBootstrap.node]])
const report = await Effect.runPromise(Effect.gen(function* () {
  const store = yield* InstanceStore.Service
  return yield* store.provide({ directory: workspace }, Effect.gen(function* () {
    const spec = JSON.parse(await fs.readFile(path.join(reference, "specification.json"), "utf8"))
    spec.catalogHash = S.catalogHash
    spec.structure.value.path = "input.pdb"
    const budget = { cpus: 3, memoryBytes: 4 * 1024 ** 3, workBytes: 256 * 1024 ** 2, wallSeconds: 1080,
      requireHardStorageLimit: false, origin: "Offline preparation-only metadata check, actual local inventory, no execution or strict quota claim" }
    const ctx = { sessionID: SessionID.make("ses_offline_large_metadata"), messageID: MessageID.make("msg_offline_large_metadata"),
      callID: "offline-large-prepare", agent: "build", abort: new AbortController().signal,
      messages: [], metadata: () => Effect.void, ask: () => Effect.void }
    const tool = yield* (yield* TrpPrepareTool).init()
    const prepared = yield* tool.execute({ specification: S.parse(spec), evidence_root: root, budget }, ctx)
    const metadata = prepared.metadata
    if (!/^[a-f0-9-]{36}$/.test(metadata.id) || !/^[a-f0-9]{64}$/.test(metadata.digest)) throw new Error("Invalid real metadata")
    const directory = path.join(workspace, ".helix/trp", metadata.digest.slice(0, 12) + "-" + metadata.id)
    const admission = JSON.parse(await fs.readFile(path.join(directory, "admission.json"), "utf8"))
    const actualBudget = JSON.parse(await fs.readFile(path.join(directory, "budget.json"), "utf8"))
    const run = JSON.parse(await fs.readFile(path.join(directory, "run.json"), "utf8"))
    if (!admission.accepted || S.canonical(actualBudget) !== S.canonical(budget) || run.digest !== metadata.digest || run.status !== "prepared")
      throw new Error("Durable preparation does not match real metadata")
    let visualJson = true
    try { JSON.parse(prepared.output) } catch { visualJson = false }
    return { verified: true, metadata, directory, visualOutputParseableJson: visualJson,
      units: spec.units.value.ranges.length, actualBudget, admissionAccepted: admission.accepted,
      preparedDigestMatches: true, runStatus: run.status, runToolCalled: false,
      approvalRequested: false, nativeTasks: 0, cloudCalls: 0, modelCalls: 0,
      scope: "Real local Tool.prepare/bootstrap/SQLite and inventory; synthetic engineering fixture. Durable id/digest/contracts verified without parsing truncated presentation or invoking Run." }
  }))
}).pipe(Effect.provide(layer), Effect.scoped))
await fs.writeFile(output, JSON.stringify(report, null, 2) + "\n")
console.log(JSON.stringify({ verified: report.verified, units: report.units, visualOutputParseableJson: report.visualOutputParseableJson, runToolCalled: false }))
