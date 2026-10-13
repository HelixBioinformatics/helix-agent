/** Real Helix tool execution of prospectively frozen development graph cases.
 * Automatic answers are engineering fixtures, not independent human annotation.
 */
import { expect } from "bun:test"
import { Effect, Fiber, Queue } from "effect"
import { LayerNode } from "@helix/core/effect/layer-node"
import fs from "node:fs/promises"
import path from "node:path"
import { TrpWorkflow } from "../../src/trp/workflow"
import { TrpSpecification as S } from "../../src/trp/specification"
import { TrpGraph } from "../../src/trp/graph"
import { TrpNextflow } from "../../src/trp/nextflow"
import { TrpPrepareTool, TrpRunTool } from "../../src/tool/trp"
import { Question } from "../../src/question"
import { EventV2Bridge } from "../../src/event-v2-bridge"
import { Agent } from "../../src/agent/agent"
import { Truncate } from "../../src/tool/truncate"
import { InstanceState } from "../../src/effect/instance-state"
import { SessionID, MessageID } from "../../src/session/schema"
import { testEffect } from "../lib/effect"
import budget from "../../../../evaluation/trp/development/f4-budget.json"

const root = path.resolve(import.meta.dir, "../../../..")
const base = path.join(root, "evaluation/trp/campaign-20261012")
const freeze = JSON.parse(await fs.readFile(path.join(base, "contract-corpus/freeze.json"), "utf8"))
for (const item of freeze.files) {
  const target = item.source_path ? path.join(root, item.source_path) : path.join(base, "contract-corpus", item.path)
  if (item.source_path?.startsWith("packages/helix/src/")) continue
  if (S.sha256(await fs.readFile(target)) !== item.sha256) throw new Error("Frozen contract corpus changed: " + target)
}
const corpus = JSON.parse(await fs.readFile(path.join(base, "contract-corpus/graphs.json"), "utf8"))
const start = Number(process.env.TRP_CAMPAIGN_START ?? 0)
const count = Number(process.env.TRP_CAMPAIGN_COUNT ?? 50)
if (!Number.isSafeInteger(start) || !Number.isSafeInteger(count) || start < 0 || count < 1 || start + count > 50)
  throw new Error("Invalid frozen campaign range")
const output = path.resolve(process.env.TRP_CAMPAIGN_OUTPUT ?? path.join(base, "cloud/development-workflows"))
if (process.env.TRP_REMOTE_CAMPAIGN === "1") {
  const subjectPaths = [
    "catalog.json",
    "graph.ts",
    "specification.ts",
    "nextflow.ts",
    "workflow.ts",
    "resources.ts",
    "remote.ts",
    "remote_runner.py.txt",
    "evidence.ts",
    "verify_bundle.py.txt",
    "structural.ts",
  ]
  const sources = Object.fromEntries(
    await Promise.all(
      subjectPaths.map(async (name) => {
        const source = "packages/helix/src/trp/" + name
        return [source, S.sha256(await fs.readFile(path.join(root, source)))]
      }),
    ),
  )
  for (const source of ["bun.lock", "packages/helix/test/trp/remote-campaign.live.test.ts", "packages/helix/src/tool/trp.ts", "packages/sdk/js/src/v2/client.ts"]) {
    sources[source] = S.sha256(await fs.readFile(path.join(root, source)))
  }
  await fs.mkdir(output, { recursive: true })
  const prospective = {
    kind: "engineering implementation revision",
    frozenAt: new Date().toISOString(),
    baseCorpusFreezeSha256: S.sha256(await fs.readFile(path.join(base, "contract-corpus/freeze.json"))),
    casesUnchanged: true,
    syntheticApproval: true,
    heldOutScientific: false,
    start,
    count,
    sources,
    reason:
      "Original contract cases are preserved; execution uses the new remote adapter and resource observer, not the baseline implementation frozen for static graphs.",
  }
  const snapshot = path.join(output, `source-snapshot-${start}-${count}.json`)
  try {
    await fs.writeFile(snapshot, JSON.stringify(prospective, null, 2) + "\n", { flag: "wx" })
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code !== "EEXIST") throw error
    const old = JSON.parse(await fs.readFile(snapshot, "utf8"))
    if (S.canonical(old.sources) !== S.canonical(sources))
      throw new Error("Execution source revision changed; choose a new output directory and preserve prior evidence")
  }
}
const it = testEffect(
  LayerNode.compile(LayerNode.group([TrpWorkflow.node, Question.node, EventV2Bridge.node, Agent.node, Truncate.node])),
)
const run = process.env.TRP_REMOTE_CAMPAIGN === "1" ? it.instance : it.instance.skip
let consecutiveFailures = 0
for (const item of corpus.valid.slice(start, start + count)) {
  run(
    "remote frozen development workflow " + item.id,
    () =>
      Effect.gen(function* () {
        const target = path.join(output, item.id)
        if (consecutiveFailures >= 3)
          throw new Error("Campaign suspended after three consecutive failures; inspect preserved evidence")
        if (yield* Effect.promise(() => fs.stat(path.join(target, "case.json")).catch(() => undefined))) {
          const old = yield* Effect.promise(async () =>
            JSON.parse(await fs.readFile(path.join(target, "case.json"), "utf8")),
          )
          if (old.status === "succeeded") return
          throw new Error("Existing failed case must be preserved; use a new output directory after repair")
        }
        yield* Effect.promise(() => fs.mkdir(target, { recursive: true }))
        const directory = yield* InstanceState.directory
        const raw = structuredClone(item.specification)
        const bytes = yield* Effect.promise(() => fs.readFile(path.join(root, raw.structure.value.path)))
        yield* Effect.promise(() => fs.writeFile(path.join(directory, "input.pdb"), bytes))
        raw.structure.value.path = "input.pdb"
        const graph = TrpGraph.validate(raw, bytes)
        if (!graph.valid || !graph.selected) throw new Error("Frozen positive graph is not valid")
        const goldDir = path.join(target, "standalone-reference")
        const image = "sha256:1dd91e70acb153a0bd9a51346fc001dd5025f851c9598697cdd37f07d9490b0a"
        const local = yield* Effect.promise(async () => {
          await fs.mkdir(goldDir, { recursive: true })
          await fs.writeFile(path.join(goldDir, "2xqh.pdb"), graph.selected!)
          const ranges = (values: { start: number; end: number }[]) =>
            values.map((r) => `${r.start}_${r.end}`).join(",")
          const argv = [
            "docker",
            "run",
            "--rm",
            "--network",
            "none",
            "--read-only",
            "--cpus",
            "2",
            "--memory",
            "2g",
            "--memory-swap",
            "2g",
            "--user",
            `${process.getuid?.()}:${process.getgid?.()}`,
            "--env",
            "OPENBLAS_CORETYPE=Haswell",
            "--env",
            "OPENBLAS_NUM_THREADS=1",
            "--env",
            "OMP_NUM_THREADS=1",
            "--env",
            "MKL_NUM_THREADS=1",
            "--tmpfs",
            "/tmp:rw,nosuid,size=256m",
            "--mount",
            `type=bind,src=${goldDir},dst=/work`,
            image,
            "single",
            "/work/2xqh.pdb",
            "A",
            "/work/geometry.csv",
            ranges(raw.units.value.ranges),
          ]
          if (raw.insertions.value.length) argv.push("-ins_def", ranges(raw.insertions.value))
          const child = Bun.spawn(argv, { stdout: "pipe", stderr: "pipe" })
          const [stdout, stderr, exitCode] = await Promise.all([
            new Response(child.stdout).text(),
            new Response(child.stderr).text(),
            child.exited,
          ])
          await fs.writeFile(
            path.join(goldDir, "execution.json"),
            JSON.stringify(
              {
                argv,
                exitCode,
                stdout,
                stderr,
                scientificTruth: "not_established",
                kind: "standalone same-tool execution comparator",
              },
              null,
              2,
            ) + "\n",
          )
          if (exitCode !== 0) throw new Error("Standalone frozen-image comparator failed: " + stderr)
          const csv = await fs.readFile(path.join(goldDir, "geometry.csv"), "utf8")
          TrpNextflow.validateGeometry(csv, raw)
          return csv
        })
        const actions: unknown[] = []
        const ctx = {
          sessionID: SessionID.make("ses_remote-" + item.id),
          messageID: MessageID.make("msg_remote-" + item.id),
          callID: item.id,
          agent: "build",
          abort: new AbortController().signal,
          messages: [],
          metadata: () => Effect.void,
          ask: () =>
            Effect.sync(() => {
              actions.push({ action: "permission", decision: "allowed_by_authorized_engineering_driver" })
            }),
        }
        const prepare = yield* (yield* TrpPrepareTool).init()
        const runTool = yield* (yield* TrpRunTool).init()
        const prepared = yield* prepare.execute(
          {
            specification: S.parse(raw),
            evidence_root: root,
            budget: {
              ...budget,
              origin: "Authorized remote engineering campaign; synthetic approval; not independent expert judgment",
            },
          },
          ctx,
        )
        const preview = prepared.metadata
        const question = yield* Question.Service
        const events = yield* EventV2Bridge.Service
        const asked = yield* Queue.unbounded<void>()
        const off = yield* events.listen((event) => {
          if (event.type === Question.Event.Asked.type) Queue.offerUnsafe(asked, undefined)
          return Effect.void
        })
        yield* Effect.addFinalizer(() => off)
        const result = yield* Effect.gen(function* () {
          const fiber = yield* runTool.execute({ id: preview.id, digest: preview.digest }, ctx).pipe(Effect.forkScoped)
          for (;;) {
            const q = (yield* question.list()).find((q) => q.sessionID === ctx.sessionID)
            if (!q) {
              yield* Queue.take(asked).pipe(Effect.timeout("10 seconds"))
              continue
            }
            expect(q.questions[0].question).toContain(preview.digest)
            actions.push({
              action: "approval",
              digest: preview.digest,
              answer: "Aprobar y ejecutar",
              driver: "synthetic engineering fixture",
            })
            yield* question.reply({ requestID: q.id, answers: [["Aprobar y ejecutar"]] })
            break
          }
          return yield* Fiber.join(fiber)
        }).pipe(Effect.exit)
        if (result._tag === "Failure") {
          consecutiveFailures++
          yield* Effect.promise(async () => {
            await fs
              .cp(path.join(directory, ".helix/trp"), path.join(target, "failure"), { recursive: true })
              .catch(() => undefined)
            await fs.writeFile(
              path.join(target, "case.json"),
              JSON.stringify(
                {
                  id: item.id,
                  status: "failed",
                  cause: String(result.cause),
                  syntheticApproval: true,
                  humanEvaluation: false,
                  actions,
                },
                null,
                2,
              ) + "\n",
            )
          })
          return yield* result
        }
        const completed = result.value.metadata
        const actual = yield* Effect.promise(() =>
          fs.readFile(path.join(completed.directory, "results/geometry.csv"), "utf8"),
        )
        const evidence = JSON.parse(result.value.output).evidence
        yield* Effect.promise(async () => {
          await fs.cp(evidence.directory, path.join(target, "evidence"), { recursive: true })
          await fs.writeFile(
            path.join(target, "case.json"),
            JSON.stringify(
              {
                id: item.id,
                status: "succeeded",
                digest: preview.digest,
                manifestSha256: evidence.manifestSha256,
                unitCount: raw.units.value.ranges.length,
                localCsvSha256: S.sha256(local),
                remoteCsvSha256: S.sha256(actual),
                equal: actual === local,
                syntheticApproval: true,
                humanEvaluation: false,
                uniqueDevelopmentProtein: "2XQH/A",
                actions,
              },
              null,
              2,
            ) + "\n",
          )
        })
        expect(actual).toBe(local)
        consecutiveFailures = 0
        console.log(
          JSON.stringify({ case: item.id, status: "succeeded", equal: true, manifestSha256: evidence.manifestSha256 }),
        )
      }),
    600000,
  )
}
