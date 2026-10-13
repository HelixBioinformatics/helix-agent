import { expect, test } from "bun:test"
import fs from "node:fs/promises"
import os from "node:os"
import path from "node:path"
import { TrpStructural as C } from "../../src/trp/structural"
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

test("missing operator-configured steric runtime preserves explicit uncertainty", async () => {
  const previous = process.env.HELIX_TRP_STERIC_PYTHON
  process.env.HELIX_TRP_STERIC_PYTHON = "/missing/helix-steric-python"
  try {
    const report = await C.inspect({ structure, options })
    const physical = report.checks.find((check) => check.id === "fold-plausibility")!
    expect(physical.status).toBe("not_evaluable")
    expect((physical.value as any).stericDiagnostic.status).toBe("not_evaluable")
    expect(report.summary.biologicalValidity).toBe("not_established")
    expect(report.summary.mechanicalAdmission).toBe(true)
  } finally {
    if (previous === undefined) delete process.env.HELIX_TRP_STERIC_PYTHON
    else process.env.HELIX_TRP_STERIC_PYTHON = previous
  }
})

test.skipIf(!process.env.HELIX_TRP_STERIC_TEST_PYTHON)(
  "maintained steric measurement is deterministic, source-bound and portable without asserting fold validity",
  async () => {
    const previous = process.env.HELIX_TRP_STERIC_PYTHON
    process.env.HELIX_TRP_STERIC_PYTHON = process.env.HELIX_TRP_STERIC_TEST_PYTHON!
    const metadata = JSON.parse(
      await fs.readFile(path.join(root, "evaluation/trp/reference/pratt-author-20261001/metadata/8b.json"), "utf8"),
    )
    const original = await fs.readFile(
      path.join(root, "evaluation/trp/reference/pratt-author-20261001/originals", metadata.structureFile),
      "utf8",
    )
    const request = {
      structure: original,
      options: {
        ...options,
        units: [
          { start: 1, end: 20 },
          { start: 21, end: 40 },
        ],
      },
    }
    const workspace = await fs.mkdtemp(path.join(os.tmpdir(), "helix-steric-integration-"))
    try {
      const first = await C.inspect(request)
      const second = await C.inspect(request)
      expect(second).toEqual(first)
      const physical = first.checks.find((check) => check.id === "fold-plausibility")!
      const diagnostic = (physical.value as any).stericDiagnostic
      expect(physical.status).toBe("not_evaluable")
      expect(diagnostic.status).toBe("measured")
      expect(diagnostic.measurement.severeClashes).toBe(77)
      expect(diagnostic.measurement.clashscore).toBeCloseTo(64.16666666666667, 10)
      expect(diagnostic.sourceSha256).toBe(first.provenance.structureSha256)
      expect(Object.keys(diagnostic.engine.resourcesSha256).length).toBeGreaterThan(40)
      expect(diagnostic.foldVerdict).toBe("not_established")
      expect(diagnostic.structureLevelThreshold).toBeNull()
      expect(first.summary.biologicalValidity).toBe("not_established")
      await fs.writeFile(path.join(workspace, "original.pdb"), original)
      const evidence = await C.inspectFiles({ structure: "original.pdb", options: request.options }, workspace)
      const verifier = path.join(root, "packages/helix/src/trp/verify_inspection.py.txt")
      const verify = () =>
        Bun.spawn(["python3", verifier, evidence.directory, "--sha256", evidence.manifestSha256], {
          stdout: "ignore",
          stderr: "ignore",
        }).exited
      expect(await verify()).toBe(0)
      await fs.appendFile(path.join(evidence.directory, "steric_diagnostic.py"), "\nchanged\n")
      expect(await verify()).not.toBe(0)
    } finally {
      if (previous === undefined) delete process.env.HELIX_TRP_STERIC_PYTHON
      else process.env.HELIX_TRP_STERIC_PYTHON = previous
      await fs.rm(workspace, { recursive: true, force: true })
    }
  },
  120_000,
)
