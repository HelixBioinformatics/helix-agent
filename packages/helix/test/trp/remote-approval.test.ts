import { expect } from "bun:test"
import { Effect, Exit, Layer } from "effect"
import { LayerNode } from "@helix/core/effect/layer-node"
import { AppProcess } from "@helix/core/process"
import fs from "node:fs/promises"
import path from "node:path"
import { TrpWorkflow } from "../../src/trp/workflow"
import { TrpRemote } from "../../src/trp/remote"
import { TrpResources as R } from "../../src/trp/resources"
import { Question } from "../../src/question"
import { InstanceState } from "../../src/effect/instance-state"
import { SessionID, MessageID } from "../../src/session/schema"
import { testEffect } from "../lib/effect"
import { inventory } from "./resource-fixture"
import budget from "../../../../evaluation/trp/development/f4-budget.json"
import source from "../../../../evaluation/trp/development/f3-reference-spec.json"

const root = path.resolve(import.meta.dir, "../../../..")
let mode = "reject",
  approvals = 0,
  actions: string[] = [],
  workspace = "",
  configPath = ""
const it = testEffect(
  LayerNode.compile(TrpWorkflow.node, [
    [
      AppProcess.node,
      Layer.mock(AppProcess.Service, {
        run: (_command, options) =>
          Effect.gen(function* () {
            const req = JSON.parse(String(options?.stdin))
            actions.push(req.action)
            if (req.action !== "observe")
              return yield* Effect.die(new Error("Gate refusal must not transfer or submit a run"))
            const remote = {
              version: TrpRemote.VERSION,
              fingerprint: req.target.fingerprint,
              partition: "helix",
              controllerCpus: 2,
              controllerMemoryBytes: 3 * 1024 ** 3,
              secondsRemaining: 3600,
              requiredNodes: [],
              nodes: [
                {
                  name: "worker",
                  cpus: 2,
                  memoryBytes: 8 * 1024 ** 3,
                  eligible: true,
                  state: "IDLE",
                  source: "synthetic gate fixture",
                },
              ],
            }
            return {
              command: "SSH read-only fixture",
              exitCode: 0,
              stdout: Buffer.from(JSON.stringify({ ok: true, ...inventory(workspace), remote })),
              stderr: Buffer.alloc(0),
              stdoutTruncated: false,
              stderrTruncated: false,
            }
          }),
      }),
    ],
    [
      R.node,
      Layer.mock(R.Service, {
        observe: () => Effect.die(new Error("Remote route must not admit local host resources")),
      }),
    ],
    [
      Question.node,
      Layer.mock(Question.Service, {
        ask: () =>
          Effect.gen(function* () {
            approvals++
            if (mode === "source-changed")
              yield* Effect.promise(() => fs.appendFile(path.join(workspace, "input.pdb"), "REMARK CHANGED\n"))
            if (mode === "target-changed")
              yield* Effect.promise(async () => {
                const config = JSON.parse(await fs.readFile(configPath, "utf8"))
                await fs.writeFile(configPath, JSON.stringify({ ...config, partition: "different" }))
              })
            return [[mode === "reject" ? "Rechazar" : "Aprobar y ejecutar"]]
          }),
      }),
    ],
  ]),
)
const ctx = {
  sessionID: SessionID.make("ses_remote-gate"),
  messageID: MessageID.make("msg_remote-gate"),
  agent: "build",
  abort: new AbortController().signal,
  messages: [],
  metadata: () => Effect.void,
  ask: () => Effect.void,
}

for (const behavior of ["reject", "source-changed", "target-changed", "hard-quota"])
  it.instance(`remote ${behavior} refuses execution through the production workflow gate`, () =>
    Effect.gen(function* () {
      const directory = yield* InstanceState.directory
      workspace = directory
      approvals = 0
      actions = []
      mode = behavior
      const previous = process.env.HELIX_TRP_REMOTE
      yield* Effect.addFinalizer(() =>
        Effect.sync(() => {
          if (previous === undefined) delete process.env.HELIX_TRP_REMOTE
          else process.env.HELIX_TRP_REMOTE = previous
        }),
      )
      configPath = path.join(directory, "operator.json")
      const identityFile = path.join(directory, "key"),
        knownHostsFile = path.join(directory, "hosts")
      yield* Effect.promise(async () => {
        await fs.writeFile(identityFile, "synthetic private fixture", { mode: 0o600 })
        await fs.writeFile(knownHostsFile, "synthetic pinned host fixture", { mode: 0o600 })
        await fs.writeFile(
          configPath,
          JSON.stringify({
            version: TrpRemote.VERSION,
            host: "192.0.2.1",
            port: 22,
            user: "ubuntu",
            identityFile,
            knownHostsFile,
            hostKeyAlias: "fixture-host",
            root: "/shared/helix",
            partition: "helix",
          }),
          { mode: 0o600 },
        )
        await fs.copyFile(path.join(root, source.structure.value.path), path.join(directory, "input.pdb"))
      })
      process.env.HELIX_TRP_REMOTE = configPath
      const raw = structuredClone(source)
      raw.structure.value.path = "input.pdb"
      const workflow = yield* TrpWorkflow.Service
      const prepare = yield* workflow
        .prepare(raw, root, ctx.sessionID, { ...budget, requireHardStorageLimit: behavior === "hard-quota" })
        .pipe(Effect.exit)
      if (behavior === "hard-quota") {
        expect(Exit.isFailure(prepare)).toBe(true)
        expect(approvals).toBe(0)
      } else {
        if (prepare._tag === "Failure") throw new Error(String(prepare.cause))
        expect(prepare.value.inventory.remote).toBeDefined()
        expect(prepare.value.limits).toContain("SSH/Slurm")
        const run = yield* workflow.run(prepare.value.id, prepare.value.digest, ctx).pipe(Effect.exit)
        expect(Exit.isFailure(run)).toBe(true)
        expect(approvals).toBe(1)
      }
      expect(actions).toEqual(["observe"])
    }),
  )
