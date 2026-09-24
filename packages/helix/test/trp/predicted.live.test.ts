/** Engineering reference with synthetic Question.Service reply; no human evaluation claim. */
import { expect } from "bun:test"
import { Effect, Fiber, Queue } from "effect"
import { LayerNode } from "@helix/core/effect/layer-node"
import fs from "node:fs/promises"
import path from "node:path"
import { spawnSync } from "node:child_process"
import { TrpPredictedTool, APPROVE } from "../../src/tool/trp-predicted"
import { Question } from "../../src/question"
import { EventV2Bridge } from "../../src/event-v2-bridge"
import { Agent } from "../../src/agent/agent"
import { Truncate } from "../../src/tool/truncate"
import { InstanceState } from "../../src/effect/instance-state"
import { SessionID, MessageID } from "../../src/session/schema"
import { testEffect } from "../lib/effect"
import request from "../../../../evaluation/trp/reference/predicted-geometry-20260921-corrected/request.json"

const root = path.resolve(import.meta.dir, "../../../..")
const it = testEffect(
  LayerNode.compile(LayerNode.group([Question.node, EventV2Bridge.node, Agent.node, Truncate.node])),
)
const run = process.env.TRP_PREDICTED_TOOL_LIVE === "1" ? it.instance : it.instance.skip
run(
  "AFDB geometry through registered agent tool and authenticated question service",
  () =>
    Effect.gen(function* () {
      const directory = yield* InstanceState.directory
      yield* Effect.promise(async () => {
        await fs.writeFile(path.join(directory, "input.cif"), request.structure)
        await fs.writeFile(path.join(directory, "pae.json"), JSON.stringify(request.pae))
        await fs.writeFile(path.join(directory, "api.json"), JSON.stringify(request.api))
      })
      const ctx = {
        sessionID: SessionID.make("ses_predicted-engineering"),
        messageID: MessageID.make("msg_predicted-engineering"),
        callID: "predicted-reference",
        agent: "build",
        abort: new AbortController().signal,
        messages: [],
        metadata: () => Effect.void,
        ask: () => Effect.void,
      }
      const tool = yield* (yield* TrpPredictedTool).init()
      const questions = yield* Question.Service,
        events = yield* EventV2Bridge.Service,
        asked = yield* Queue.unbounded<void>()
      const off = yield* events.listen((event) => {
        if (event.type === Question.Event.Asked.type) Queue.offerUnsafe(asked, undefined)
        return Effect.void
      })
      yield* Effect.addFinalizer(() => off)
      const fiber = yield* tool
        .execute({ structure: "input.cif", pae: "pae.json", api: "api.json", options: request.options as any }, ctx)
        .pipe(Effect.forkScoped)
      for (;;) {
        const q = (yield* questions.list()).find((q) => q.sessionID === ctx.sessionID)
        if (!q) {
          yield* Queue.take(asked).pipe(
            Effect.raceFirst(
              Fiber.join(fiber).pipe(Effect.flatMap(() => Effect.die(new Error("Tool completed without approval")))),
            ),
            Effect.timeout("20 seconds"),
          )
          continue
        }
        expect(q.questions[0].question).toContain("pLDDT")
        expect(q.questions[0].question).toContain("SHA-256")
        yield* questions.reply({ requestID: q.id, answers: [[APPROVE]] })
        break
      }
      const result = JSON.parse((yield* Fiber.join(fiber)).output)
      expect(result.status).toBe("succeeded")
      const verification = spawnSync(
        "python3",
        [path.join(result.directory, "verify.py"), result.directory, "--sha256", result.manifestSha256],
        { encoding: "utf8" },
      )
      expect(verification.status).toBe(0)
      const original = yield* Effect.promise(() => fs.readFile(path.join(result.directory, "original-pae.txt")))
      yield* Effect.promise(() => fs.appendFile(path.join(result.directory, "original-pae.txt"), " "))
      expect(
        spawnSync("python3", [
          path.join(result.directory, "verify.py"),
          result.directory,
          "--sha256",
          result.manifestSha256,
        ]).status,
      ).not.toBe(0)
      yield* Effect.promise(() => fs.writeFile(path.join(result.directory, "original-pae.txt"), original))
      const csv = yield* Effect.promise(() => fs.readFile(result.geometry, "utf8"))
      expect(csv).toBe(
        yield* Effect.promise(() =>
          fs.readFile(
            path.join(root, "evaluation/trp/reference/predicted-geometry-20260921-corrected/geometry.csv"),
            "utf8",
          ),
        ),
      )
      if (process.env.TRP_PREDICTED_TOOL_OUTPUT)
        yield* Effect.promise(() =>
          fs.cp(result.directory, process.env.TRP_PREDICTED_TOOL_OUTPUT!, { recursive: true }),
        )
    }),
  180_000,
)
