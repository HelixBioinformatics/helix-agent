/** Explicit engineering integration run. Replies are synthetic test-driver input,
 * not evidence of human agreement or thesis language/annotation performance. */
import { expect } from "bun:test"
import { Effect, Fiber, Queue } from "effect"
import { LayerNode } from "@helix/core/effect/layer-node"
import fs from "node:fs/promises"
import path from "node:path"
import { TrpWorkflow } from "../../src/trp/workflow"
import { TrpSpecification } from "../../src/trp/specification"
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
const it = testEffect(
  LayerNode.compile(LayerNode.group([TrpWorkflow.node, Question.node, EventV2Bridge.node, Agent.node, Truncate.node])),
)
const run = process.env.TRP_LIVE_REFERENCE === "1" ? it.instance : it.instance.skip

run(
  "real Nextflow geometry through the agent tools (synthetic approval driver)",
  () =>
    Effect.gen(function* () {
      const directory = yield* InstanceState.directory
      yield* Effect.promise(() =>
        fs.copyFile(path.join(root, source.structure.value.path), path.join(directory, "input.pdb")),
      )
      const raw = { ...structuredClone(source), catalogHash: TrpSpecification.catalogHash }
      raw.structure.value.path = "input.pdb"
      if (process.env.TRP_REFERENCE_MAPPING === "1") {
        yield* Effect.promise(async () => {
          const cif = "evaluation/trp/reference/structural-f5/experimental/2xqh.cif"
          const xml = "evaluation/trp/reference/coordinate-integrated-20260921/2xqh-sifts.xml"
          await fs.copyFile(path.join(root, cif), path.join(directory, "mapping.cif"))
          await fs.copyFile(path.join(root, xml), path.join(directory, "sifts.xml"))
          ;(raw as any).coordinateMapping = {
            value: {
              path: "mapping.cif",
              sha256: TrpSpecification.sha256(await fs.readFile(path.join(root, cif))),
              frame: "uniprot",
              units: source.units.value.ranges,
              sifts: {
                path: "sifts.xml",
                sha256: TrpSpecification.sha256(await fs.readFile(path.join(root, xml))),
                accession: "Q9MCI8",
              },
            },
            origin: {
              kind: "reference",
              reference: "https://ftp.ebi.ac.uk/pub/databases/msd/sifts/xml/2xqh.xml.gz",
              detail: "Archived 2026-09-21 residue-level SIFTS mapping; development reference",
            },
          }
        })
      }
      const pad = Number(process.env.TRP_REFERENCE_REMARK_BYTES ?? 0)
      if (pad) {
        // Development size contrast: ignored PDB REMARK records; coordinates and
        // expected geometry are unchanged. These are never held-out proteins.
        yield* Effect.promise(async () => {
          const file = path.join(directory, "input.pdb")
          const comment = "REMARK 999 RESOURCE DEVELOPMENT SIZE CONTRAST " + "x".repeat(30) + "\n"
          const data = comment.repeat(Math.ceil(pad / Buffer.byteLength(comment))) + (await fs.readFile(file, "utf8"))
          await fs.writeFile(file, data)
          raw.structure.value.sha256 = TrpSpecification.sha256(data)
        })
      }
      const ctx = {
        sessionID: SessionID.make("ses_trp-engineering-reference"),
        messageID: MessageID.make("msg_trp-engineering-reference"),
        callID: "reference-driver",
        agent: "build",
        abort: new AbortController().signal,
        messages: [],
        metadata: () => Effect.void,
        ask: () => Effect.void,
      }
      const prepare = yield* (yield* TrpPrepareTool).init()
      const runTool = yield* (yield* TrpRunTool).init()
      const prepared = yield* prepare.execute(
        {
          specification: TrpSpecification.parse(raw),
          evidence_root: root,
          budget: process.env.HELIX_TRP_SANDBOX
            ? {
                ...budget,
                workBytes: Number(process.env.TRP_RESOURCE_WORK_MIB ?? 128) * 1024 ** 2,
                requireHardStorageLimit: true,
                origin: "operator-authorized isolated resource engineering reference; synthetic approval",
              }
            : budget,
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
      const fiber = yield* runTool.execute({ id: preview.id, digest: preview.digest }, ctx).pipe(Effect.forkScoped)
      for (;;) {
        const item = (yield* question.list()).find((q) => q.sessionID === ctx.sessionID)
        if (!item) {
          yield* Queue.take(asked).pipe(Effect.timeout("5 seconds"))
          continue
        }
        expect(item.questions[0].question).toContain(preview.digest)
        yield* question.reply({ requestID: item.id, answers: [["Aprobar y ejecutar"]] })
        break
      }
      const execution = yield* Fiber.join(fiber).pipe(
        Effect.onExit((exit) =>
          exit._tag === "Failure" && process.env.TRP_REFERENCE_OUTPUT
            ? Effect.promise(async () => {
                const from = path.join(directory, ".helix", "trp")
                if (await fs.stat(from).catch(() => undefined))
                  await fs.cp(from, `${process.env.TRP_REFERENCE_OUTPUT}-failure-${Date.now()}`, { recursive: true })
              })
            : Effect.void,
        ),
      )
      const result = execution.metadata
      expect(result.digest).toBe(preview.digest)
      const actual = yield* Effect.promise(() =>
        fs.readFile(path.join(result.directory, "results", "geometry.csv"), "utf8"),
      )
      const reference = yield* Effect.promise(() =>
        fs.readFile(path.join(root, "evaluation/trp/reference/geometre/geometry.csv"), "utf8"),
      )
      expect(actual).toBe(reference)
      const target = process.env.TRP_REFERENCE_OUTPUT
      if (target)
        yield* Effect.promise(async () => {
          if (process.env.HELIX_TRP_SANDBOX) {
            // Same-filesystem move: the bounded run already contains the portable
            // copy. A test-only second duplication would bias peak calibration.
            await fs.rename(result.directory, target)
          } else {
            await fs.mkdir(target, { recursive: false })
            for (const entry of await fs.readdir(result.directory, { withFileTypes: true })) {
              if (entry.isFile())
                await fs.copyFile(path.join(result.directory, entry.name), path.join(target, entry.name))
            }
            await fs.cp(path.join(result.directory, "evidence"), path.join(target, "evidence"), { recursive: true })
            await fs.cp(path.join(result.directory, "results"), path.join(target, "results"), { recursive: true })
            await fs.mkdir(path.join(target, "dry-run"))
            const execution = JSON.parse(await fs.readFile(path.join(result.directory, "execution.json"), "utf8"))
            const logs =
              execution.backend === "trp-slurm-ssh/1.0.0"
                ? ["remote-stdout.log", "remote-stderr.stderr"]
                : ["stdout.log", "stderr.log"]
            for (const name of [...logs, "trace.tsv", "results/geometry.csv"]) {
              const destination = path.join(target, "dry-run", name)
              await fs.mkdir(path.dirname(destination), { recursive: true })
              await fs.copyFile(path.join(result.directory, "dry-run", name), destination)
            }
          }
          await fs.writeFile(
            path.join(target, "engineering-reference.json"),
            JSON.stringify(
              {
                kind: "development-reference",
                approvalDriver: "synthetic Question.Service.reply in reference.live.test.ts",
                humanEvaluation: false,
                expectedCsvSha256: TrpSpecification.sha256(reference),
                actualCsvSha256: TrpSpecification.sha256(actual),
                equal: actual === reference,
                toolPath: ["trp_prepare", "trp_run"],
                digest: preview.digest,
              },
              null,
              2,
            ),
          )
        })
    }),
  600_000,
)
