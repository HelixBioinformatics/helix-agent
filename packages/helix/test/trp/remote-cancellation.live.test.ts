/** Opt-in actual Slurm cancellation/configuration fault injection.
 * Answers are authorized engineering driver inputs, never expert annotations.
 */
import { expect } from "bun:test"
import { Effect, Exit, Fiber, Queue } from "effect"
import { ChildProcess } from "effect/unstable/process"
import { AppProcess } from "@helix/core/process"
import { LayerNode } from "@helix/core/effect/layer-node"
import fs from "node:fs/promises"
import path from "node:path"
import { TrpWorkflow } from "../../src/trp/workflow"
import { TrpRemote } from "../../src/trp/remote"
import { TrpSpecification as S } from "../../src/trp/specification"
import { TrpPrepareTool, TrpRunTool } from "../../src/tool/trp"
import { Question } from "../../src/question"
import { EventV2Bridge } from "../../src/event-v2-bridge"
import { Agent } from "../../src/agent/agent"
import { Truncate } from "../../src/tool/truncate"
import { InstanceState } from "../../src/effect/instance-state"
import { SessionID, MessageID } from "../../src/session/schema"
import { testEffect } from "../lib/effect"
import budget from "../../../../evaluation/trp/development/f4-budget.json"
import source from "../../../../evaluation/trp/development/f3-reference-spec.json"

const root = path.resolve(import.meta.dir, "../../../..")
const output = path.resolve(
  process.env.TRP_CANCELLATION_OUTPUT ?? path.join(root, "evaluation/trp/campaign-20261012/cloud/lab1/cancellation"),
)
const it = testEffect(
  LayerNode.compile(
    LayerNode.group([TrpWorkflow.node, Question.node, EventV2Bridge.node, Agent.node, Truncate.node, AppProcess.node]),
  ),
)
const run = process.env.TRP_LIVE_REMOTE_FAILURES === "1" ? it.instance : it.instance.skip
const quote = (text: string) => "'" + text.replaceAll("'", "'\\''") + "'"
const WATCH = `import json, os, re, subprocess, sys, time
from datetime import datetime, timezone
req=json.load(sys.stdin)
until=time.monotonic()+240
found=None
while time.monotonic()<until:
    p=subprocess.run(['squeue','--noheader','--user',str(os.getuid()),'--format','%i|%k|%T|%N'],capture_output=True,text=True,check=True)
    for line in p.stdout.splitlines():
        row=line.strip().split('|')
        if len(row)==4 and row[1]=='helix:'+req['id'] and row[2]=='RUNNING' and re.fullmatch('[0-9]+',row[0]):
            s=subprocess.run(['scontrol','show','job',row[0],'--oneliner'],capture_output=True,text=True)
            if 'JobState=RUNNING' in s.stdout and 'Comment=helix:'+req['id'] in s.stdout and 'JobName=nf-GEOMETRY' in s.stdout and '/dry-run/' not in s.stdout:
                found={'id':row[0],'comment':row[1],'queueState':row[2],'nodes':row[3],'source':s.stdout,'observedAt':datetime.now(timezone.utc).isoformat(),'independentProbe':True}
                break
    if found:break
    time.sleep(0.1)
print(json.dumps({'found':found,'pollIntervalSeconds':0.1,'maximumSeconds':240}))
`

async function copyInput(directory: string) {
  await fs.copyFile(path.join(root, source.structure.value.path), path.join(directory, "input.pdb"))
  const raw = structuredClone(source)
  raw.structure.value.path = "input.pdb"
  return raw
}

run(
  "cancel an independently observed native RUNNING job through the production tool",
  () =>
    Effect.gen(function* () {
      const target = yield* Effect.promise(() => TrpRemote.configured())
      if (!target) throw new Error("Cancellation requires an operator SSH/Slurm target")
      const folder = path.join(output, "running-job")
      yield* Effect.promise(async () => {
        await fs.mkdir(folder, { recursive: false })
        await fs.writeFile(
          path.join(folder, "protocol.json"),
          JSON.stringify(
            {
              kind: "prospective engineering fault injection",
              humanEvaluation: false,
              approvalDriver: "synthetic Question.Service reply under user-authorized goal",
              operation: "abort the actual workflow after independent owner-scoped squeue/scontrol RUNNING observation",
              intervention: "Tool.Context.abort, no changes to scientific input, code, resources or job signal",
              success:
                "actual RUNNING observation, failed/interrupted portable run, confirmed no owned jobs remaining, native CANCELLED or verified absence",
              watcherSha256: S.sha256(WATCH),
              templateSha256: source.structure.value.sha256,
              frozenFixture: process.env.TRP_CANCELLATION_FIXTURE ?? null,
              frozenAt: new Date().toISOString(),
            },
            null,
            2,
          ),
        )
      })
      const directory = yield* InstanceState.directory
      const raw = yield* Effect.promise(async () => {
        if (process.env.TRP_CANCELLATION_FIXTURE) {
          const frozen = path.resolve(process.env.TRP_CANCELLATION_FIXTURE)
          const manifest = JSON.parse(await fs.readFile(path.join(frozen, "freeze.json"), "utf8"))
          for (const file of manifest.files)
            if (S.sha256(await fs.readFile(path.join(frozen, file.path))) !== file.sha256)
              throw new Error("Prospective cancellation fixture changed: " + file.path)
          const bytes = await fs.readFile(path.join(frozen, "source.pdb"))
          const value = JSON.parse(await fs.readFile(path.join(frozen, "specification.json"), "utf8"))
          if (S.sha256(bytes) !== value.structure.value.sha256)
            throw new Error("Frozen cancellation structure/specification differ")
          value.structure.value.path = "input.pdb"
          await fs.writeFile(path.join(directory, "input.pdb"), bytes)
          await fs.writeFile(path.join(folder, "synthetic-source.pdb"), bytes)
          await fs.copyFile(path.join(frozen, "freeze.json"), path.join(folder, "fixture-freeze.json"))
          return S.parse(value)
        }
        const original = await fs.readFile(path.join(root, source.structure.value.path), "utf8")
        const ca = original
          .split(/\r?\n/)
          .filter((line) => line.startsWith("ATOM  ") && line.slice(12, 16).trim() === "CA" && line[21] === "A")
          .slice(0, 6)
        const center = [0, 1, 2].map(
          (axis) => ca.reduce((sum, line) => sum + Number(line.slice(30 + 8 * axis, 38 + 8 * axis)), 0) / ca.length,
        )
        const header = "HEADER    SYNTHETIC CANCELLATION ENGINEERING FIXTURE".padEnd(62, " ") + "0SYN\n"
        let pdb =
          header +
          "EXPDTA    X-RAY DIFFRACTION\nREMARK 999 Synthetic transformed CA fixture, not an experimental structure.\nREMARK 999 EXPDTA emulates the admitted B-factor schema, not an X-ray claim.\n"
        for (let unit = 0; unit < 1000; unit++) {
          const theta = unit * 0.1
          for (let local = 0; local < 6; local++) {
            const line = ca[local]
            const x = Number(line.slice(30, 38)) - center[0],
              y = Number(line.slice(38, 46)) - center[1],
              z = Number(line.slice(46, 54)) - center[2]
            const xyz = [
              x * Math.cos(theta) - y * Math.sin(theta) + 40 * Math.cos(theta),
              x * Math.sin(theta) + y * Math.cos(theta) + 40 * Math.sin(theta),
              z + unit * 0.5,
            ]
            const residue = unit * 6 + local + 1
            pdb +=
              line.slice(0, 6) +
              String(residue).padStart(5) +
              line.slice(11, 22) +
              String(residue).padStart(4) +
              line.slice(26, 30) +
              xyz.map((v) => v.toFixed(3).padStart(8)).join("") +
              line.slice(54) +
              "\n"
          }
        }
        pdb += "END\n"
        await fs.writeFile(path.join(directory, "input.pdb"), pdb)
        await fs.writeFile(path.join(folder, "synthetic-source.pdb"), pdb)
        const value = structuredClone(source)
        value.structure.value = { path: "input.pdb", sha256: S.sha256(pdb), pdb: "0syn" }
        value.intent.value =
          "Synthetic engineering cancellation workload, not a known PDB entry or a biological accuracy case."
        value.units.value.ranges = Array.from({ length: 1000 }, (_, n) => ({ start: n * 6 + 1, end: n * 6 + 6 }))
        value.units.value.contract = S.contract(S.parse(value), "input.units")
        value.insertions.value = []
        for (const key of ["structure", "intent", "units", "insertions"] as const)
          value[key].origin = {
            kind: "reference",
            reference: "protocol.json",
            detail:
              "Deterministic engineering fixture: 1000 transformed copies of the first six 2XQH/A C-alpha coordinates; synthetic metadata emulates B-factor schema; no experimental or biological validity claim.",
          }
        const graph = S.geometryGraph(S.parse(value))
        value.graph = {
          nodes: Array.from(graph.nodes),
          edges: graph.edges.map((edge) => ({ ...edge, contract: { ...edge.contract } })),
        }
        await fs.writeFile(
          path.join(folder, "fixture.json"),
          JSON.stringify(
            {
              sourceSha256: S.sha256(pdb),
              templateSha256: source.structure.value.sha256,
              units: 1000,
              unitLength: 6,
              identifier: "0syn",
              headerIsSynthetic: true,
              scientificTruth: "not_established",
              generatedBeforeExecution: true,
            },
            null,
            2,
          ),
        )
        return value
      })
      const abort = new AbortController()
      const ctx = {
        sessionID: SessionID.make("ses_remote-cancellation"),
        messageID: MessageID.make("msg_remote-cancellation"),
        callID: "cancel-live",
        agent: "build",
        abort: abort.signal,
        messages: [],
        metadata: () => Effect.void,
        ask: () => Effect.void,
      }
      const prepare = yield* (yield* TrpPrepareTool).init()
      const runTool = yield* (yield* TrpRunTool).init()
      const prepared = yield* prepare.execute({ specification: S.parse(raw), evidence_root: root, budget }, ctx)
      const preview = prepared.metadata
      const original = TrpRemote.command(target)
      if (original._tag !== "StandardCommand") throw new Error("Unexpected SSH transport")
      const argv = [...original.args]
      argv[argv.length - 1] = `python3 -c ${quote(WATCH)}`
      const transport = yield* AppProcess.Service
      const watcher = yield* transport
        .run(ChildProcess.make("ssh", argv), {
          stdin: JSON.stringify({ id: preview.id }),
          timeout: "255 seconds",
          maxOutputBytes: 16384,
        })
        .pipe(Effect.forkScoped)
      const question = yield* Question.Service
      const events = yield* EventV2Bridge.Service
      const asked = yield* Queue.unbounded<void>()
      const off = yield* events.listen((event) => {
        if (event.type === Question.Event.Asked.type) Queue.offerUnsafe(asked, undefined)
        return Effect.void
      })
      yield* Effect.addFinalizer(() => off)
      const execution = yield* runTool
        .execute({ id: preview.id, digest: preview.digest }, ctx)
        .pipe(Effect.exit, Effect.forkScoped)
      for (;;) {
        const q = (yield* question.list()).find((q) => q.sessionID === ctx.sessionID)
        if (!q) {
          yield* Queue.take(asked).pipe(Effect.timeout("10 seconds"))
          continue
        }
        expect(q.questions[0].question).toContain(preview.digest)
        yield* question.reply({ requestID: q.id, answers: [["Aprobar y ejecutar"]] })
        break
      }
      const watchResult = yield* Fiber.join(watcher)
      const before = JSON.parse(watchResult.stdout.toString())
      yield* Effect.promise(() => fs.writeFile(path.join(folder, "before-abort.json"), JSON.stringify(before, null, 2)))
      if (!before.found) {
        const completed = yield* Fiber.join(execution)
        yield* Effect.promise(async () => {
          await fs.cp(path.join(directory, ".helix/trp"), path.join(folder, "uninterrupted-run"), { recursive: true })
          await fs.writeFile(
            path.join(folder, "inconclusive.json"),
            JSON.stringify({ reason: "No independently observed native RUNNING interval", exit: completed._tag }),
          )
        })
        throw new Error("Cancellation injection was not triggered; do not report this as a cancellation success")
      }
      const requestedAt = new Date().toISOString()
      abort.abort(new Error("Authorized native RUNNING-job cancellation fault injection"))
      yield* Effect.promise(() =>
        fs.writeFile(
          path.join(folder, "abort-request.json"),
          JSON.stringify(
            {
              requestedAt,
              id: preview.id,
              digest: preview.digest,
              nativeId: before.found.id,
              mechanism: "Tool.Context.abort",
              syntheticApproval: true,
              humanEvaluation: false,
            },
            null,
            2,
          ),
        ),
      )
      const result = yield* Fiber.join(execution)
      const destination = path.join(directory, ".helix/trp", `${preview.digest.slice(0, 12)}-${preview.id}`)
      yield* Effect.promise(() =>
        fs.cp(path.join(destination, "evidence"), path.join(folder, "evidence"), { recursive: true }),
      )
      const afterScript = `import json, subprocess, sys\nr=json.load(sys.stdin)\np=subprocess.run(['scontrol','show','job',r['id'],'--oneliner'],capture_output=True,text=True)\nprint(json.dumps({'exitCode':p.returncode,'source':p.stdout,'stderr':p.stderr}))\n`
      const afterArgs = [...original.args]
      afterArgs[afterArgs.length - 1] = `python3 -c ${quote(afterScript)}`
      const afterResult = yield* transport.run(ChildProcess.make("ssh", afterArgs), {
        stdin: JSON.stringify({ id: before.found.id }),
        timeout: "30 seconds",
        maxOutputBytes: 16384,
      })
      const after = JSON.parse(afterResult.stdout.toString())
      yield* Effect.promise(() => fs.writeFile(path.join(folder, "after-abort.json"), JSON.stringify(after, null, 2)))
      const cancellation = yield* Effect.promise(async () =>
        JSON.parse(await fs.readFile(path.join(destination, "remote-cancellation.json"), "utf8")),
      )
      const recorded = yield* Effect.promise(async () =>
        JSON.parse(await fs.readFile(path.join(destination, "run.json"), "utf8")),
      )
      yield* Effect.promise(() =>
        fs.writeFile(
          path.join(folder, "case.json"),
          JSON.stringify(
            {
              kind: "actual native cancellation engineering contrast",
              id: preview.id,
              digest: preview.digest,
              status: recorded.status,
              nativeId: before.found.id,
              before: before.found.queueState,
              after: after.source,
              cancellation,
              syntheticApproval: true,
              humanEvaluation: false,
            },
            null,
            2,
          ),
        ),
      )
      expect(Exit.isFailure(result)).toBe(true)
      expect(recorded.status).toBe("failed")
      expect(cancellation.confirmed).toBe(true)
      expect(cancellation.remaining).toEqual([])
      expect(after.source.includes("JobState=CANCELLED") || after.exitCode !== 0).toBe(true)
    }),
  600000,
)

run(
  "a nonexistent live Slurm partition is refused before approval/submission",
  () =>
    Effect.gen(function* () {
      const directory = yield* InstanceState.directory
      const raw = yield* Effect.promise(() => copyInput(directory))
      const pointer = process.env.HELIX_TRP_REMOTE!
      const folder = path.join(output, "invalid-partition")
      const temporary = path.join(directory, "invalid-operator.json")
      yield* Effect.promise(async () => {
        await fs.mkdir(folder, { recursive: false })
        const config = JSON.parse(await fs.readFile(pointer, "utf8"))
        await fs.writeFile(temporary, JSON.stringify({ ...config, partition: "helix_nonexistent_fault_injection" }), {
          mode: 0o600,
        })
        await fs.writeFile(
          path.join(folder, "protocol.json"),
          JSON.stringify(
            {
              kind: "prospective actual configuration refusal",
              fault: "nonexistent partition",
              expected: "read-only inventory fails before approval or job submission",
              humanEvaluation: false,
              frozenAt: new Date().toISOString(),
            },
            null,
            2,
          ),
        )
      })
      process.env.HELIX_TRP_REMOTE = temporary
      yield* Effect.addFinalizer(() =>
        Effect.sync(() => {
          process.env.HELIX_TRP_REMOTE = pointer
        }),
      )
      const workflow = yield* TrpWorkflow.Service
      const result = yield* workflow.prepare(raw, root, "ses_invalid-partition", budget).pipe(Effect.exit)
      yield* Effect.promise(async () => {
        await fs.cp(path.join(directory, ".helix/trp"), path.join(folder, "refusal"), { recursive: true })
        await fs.writeFile(
          path.join(folder, "case.json"),
          JSON.stringify(
            {
              status: result._tag === "Failure" ? "refused" : "unexpectedly-accepted",
              cause: result._tag === "Failure" ? String(result.cause) : null,
              scientificJobsSubmitted: 0,
              humanEvaluation: false,
            },
            null,
            2,
          ),
        )
      })
      expect(Exit.isFailure(result)).toBe(true)
    }),
  60000,
)
