import { expect, test } from "bun:test"
import { Effect, Schema } from "effect"
import { LayerNode } from "@helix/core/effect/layer-node"
import fs from "node:fs/promises"
import os from "node:os"
import path from "node:path"
import { rejects } from "node:assert/strict"
import { TrpStructural as C } from "../../src/trp/structural"
import { TrpNextflow as N } from "../../src/trp/nextflow"
import { TrpInspectTool } from "../../src/tool/trp"
import { Agent } from "../../src/agent/agent"
import { Truncate } from "../../src/tool/truncate"
import { InstanceState } from "../../src/effect/instance-state"
import { SessionID, MessageID } from "../../src/session/schema"
import { testEffect } from "../lib/effect"
import source from "../../../../evaluation/trp/development/f3-reference-spec.json"

const root = path.resolve(import.meta.dir, "../../../..")
const structure = await fs.readFile(path.join(root, source.structure.value.path), "utf8")
const options: C.Options = {
  format: "pdb",
  model: 1,
  chain: "A",
  frame: "auth_seq_id",
  units: source.units.value.ranges,
}

test("preparation binds structural report, catalogue and exact parser to approval", async () => {
  const bundle = await N.prepare(source, root, root)
  const report = JSON.parse(bundle.files["structural_report.json"])
  expect(report.summary.mechanicalAdmission).toBe(true)
  expect(report.summary.biologicalValidity).toBe("not_established")
  expect(report.checks).toHaveLength(9)
  const changed = { ...bundle.files, "structural_report.json": "{}\n" }
  expect(N.bundleDigest(changed)).not.toBe(bundle.digest)
})

test("unestablished experimental method cannot be admitted by legacy preparation", async () => {
  const altered = structure.replace(/^EXPDTA.*\n/gm, "")
  const report = await C.inspect({ structure: altered, options })
  expect(report.summary.mechanicalAdmission).toBe(false)
  expect(report.summary.blocking).toContain("confidence-scale")
})

test("model ordinal selects second model without flattening it", async () => {
  const atoms = structure
    .split("\n")
    .filter((line) => line.startsWith("ATOM  "))
    .join("\n")
  const text = `EXPDTA    X-RAY DIFFRACTION\nMODEL        7\n${atoms}\nENDMDL\nMODEL        9\n${atoms}\nENDMDL\n`
  const report = await C.inspect({ structure: text, options: { ...options, model: 2 } })
  expect(report.summary.mechanicalAdmission).toBe(true)
  expect(report.mapping.length).toBe(258)
})

test("aborted inspection cannot return a report", async () => {
  const abort = new AbortController()
  abort.abort()
  await rejects(() => C.inspect({ structure, options }, abort.signal))
})

test("input symlinks cannot escape workspace", async () => {
  const directory = await fs.mkdtemp(path.join(os.tmpdir(), "trp-inspect-"))
  try {
    await fs.symlink(path.join(root, source.structure.value.path), path.join(directory, "external.pdb"))
    await rejects(() => C.inspectFiles({ structure: "external.pdb", options }, directory), /inside the workspace/)
  } finally {
    await fs.rm(directory, { recursive: true, force: true })
  }
})

test("local ColabFold inspection archives original sidecars and verifies their hashes", async () => {
  const python = process.env.HELIX_TRP_PYTHON ?? "python3"
  const fixture = Bun.spawn(
    [
      python,
      "-I",
      "-c",
      "import json,runpy,sys;print(json.dumps(runpy.run_path(sys.argv[1])['fixture']()))",
      path.join(root, "script/tesis/test_colabfold_binding.py"),
    ],
    { stdout: "pipe", stderr: "pipe" },
  )
  const request = JSON.parse(await new Response(fixture.stdout).text())
  expect(await fixture.exited).toBe(0)
  const workspace = await fs.mkdtemp(path.join(os.tmpdir(), "helix-colabfold-"))
  try {
    const meta = request.colabfold.metadata
    await fs.writeFile(path.join(workspace, meta.structureFile), request.structure)
    await fs.writeFile(path.join(workspace, meta.scoresFile), request.colabfold.scores)
    await fs.writeFile(path.join(workspace, meta.paeFile), request.colabfold.pae)
    await fs.writeFile(path.join(workspace, "metadata.json"), JSON.stringify(meta))
    const evidence = await C.inspectFiles(
      {
        structure: meta.structureFile,
        options: request.options,
        colabfold: { metadata: "metadata.json", scores: meta.scoresFile, pae: meta.paeFile },
      },
      workspace,
    )
    expect(evidence.report.provenance.confidenceScale).toBe("pLDDT_0_100")
    expect(evidence.report.summary.mechanicalAdmission).toBe(true)
    expect(evidence.report.summary.biologicalValidity).toBe("not_established")
    const verify = () =>
      Bun.spawn(
        [
          python,
          path.join(root, "packages/helix/src/trp/verify_inspection.py.txt"),
          evidence.directory,
          "--sha256",
          evidence.manifestSha256,
        ],
        { stdout: "ignore", stderr: "ignore" },
      ).exited
    expect(await verify()).toBe(0)
    await fs.appendFile(path.join(evidence.directory, "colabfold-scores.json"), "\n")
    expect(await verify()).not.toBe(0)
    await rejects(() => C.inspect({ ...request, api: [{}] }), /mixed-confidence-producers/)
  } finally {
    await fs.rm(workspace, { recursive: true, force: true })
  }
})

const it = testEffect(LayerNode.compile(LayerNode.group([Agent.node, Truncate.node])))
it.instance("agent inspection writes portable evidence that detects every changed or missing artifact", () =>
  Effect.gen(function* () {
    const directory = yield* InstanceState.directory
    yield* Effect.promise(() => fs.writeFile(path.join(directory, "input.pdb"), structure))
    const tool = yield* (yield* TrpInspectTool).init()
    const result = yield* tool.execute(
      { structure: "input.pdb", options },
      {
        sessionID: SessionID.make("ses_structural"),
        messageID: MessageID.make("msg_structural"),
        callID: "structural-test",
        agent: "build",
        abort: new AbortController().signal,
        messages: [],
        metadata: () => Effect.void,
        ask: () => Effect.void,
      },
    )
    const evidence = result.metadata.directory
    const verify = async (anchor = result.metadata.manifestSha256) => {
      const p = Bun.spawn(["python3", path.join(evidence, "verify.py"), evidence, "--sha256", anchor], {
        stdout: "ignore",
        stderr: "ignore",
      })
      return p.exited
    }
    expect(yield* Effect.promise(() => verify())).toBe(0)
    const manifest = Schema.decodeUnknownSync(
      Schema.Struct({ files: Schema.Array(Schema.Struct({ path: Schema.String })) }),
    )(JSON.parse(yield* Effect.promise(() => fs.readFile(path.join(evidence, "manifest.json"), "utf8"))))
    // Use the trusted source verifier while testing removal of the embedded one.
    const verifier = path.join(root, "packages/helix/src/trp/verify_inspection.py.txt")
    const trustedVerify = () =>
      Bun.spawn(["python3", verifier, evidence, "--sha256", result.metadata.manifestSha256], {
        stdout: "ignore",
        stderr: "ignore",
      }).exited
    for (const item of manifest.files) {
      const file = path.join(evidence, item.path)
      const bytes = yield* Effect.promise(() => fs.readFile(file))
      yield* Effect.promise(() => fs.appendFile(file, "\nchanged"))
      expect(yield* Effect.promise(trustedVerify)).not.toBe(0)
      yield* Effect.promise(() => fs.rename(file, path.join(directory, "held-artifact")))
      expect(yield* Effect.promise(trustedVerify)).not.toBe(0)
      yield* Effect.promise(() => fs.writeFile(file, bytes))
    }
    expect(yield* Effect.promise(() => verify("0".repeat(64)))).not.toBe(0)
    expect(yield* Effect.promise(() => verify())).toBe(0)
  }),
)
