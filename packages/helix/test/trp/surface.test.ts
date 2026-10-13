import { expect, test } from "bun:test"
import fs from "node:fs/promises"
import os from "node:os"
import path from "node:path"
import { TrpStructural as C } from "../../src/trp/structural"
import { TrpNextflow as N } from "../../src/trp/nextflow"

const root = path.resolve(import.meta.dir, "../../../..")
const reference = JSON.parse(
  await fs.readFile(path.join(root, "evaluation/trp/development/f3-reference-spec.json"), "utf8"),
)
const baseline = await fs.readFile(path.join(root, reference.structure.value.path), "utf8")
const options: C.Options = {
  format: "pdb",
  model: 1,
  chain: "A",
  frame: "auth_seq_id",
  units: [
    { start: 1, end: 22 },
    { start: 23, end: 44 },
  ],
}
async function originalCase(id: string) {
  const directory = path.join(root, "evaluation/trp/reference/pratt-author-20261001")
  const metadata = JSON.parse(await fs.readFile(path.join(directory, "metadata", id + ".json"), "utf8"))
  return fs.readFile(path.join(directory, "originals", metadata.structureFile), "utf8")
}

async function configured(run: () => Promise<void>) {
  const surface = process.env.HELIX_TRP_SURFACE_PYTHON
  const steric = process.env.HELIX_TRP_STERIC_PYTHON
  process.env.HELIX_TRP_SURFACE_PYTHON = process.env.HELIX_TRP_SURFACE_TEST_PYTHON!
  delete process.env.HELIX_TRP_STERIC_PYTHON
  try {
    await run()
  } finally {
    if (surface === undefined) delete process.env.HELIX_TRP_SURFACE_PYTHON
    else process.env.HELIX_TRP_SURFACE_PYTHON = surface
    if (steric === undefined) delete process.env.HELIX_TRP_STERIC_PYTHON
    else process.env.HELIX_TRP_STERIC_PYTHON = steric
  }
}

test("missing operator-configured surface runtime preserves explicit uncertainty", async () => {
  const previous = process.env.HELIX_TRP_SURFACE_PYTHON
  process.env.HELIX_TRP_SURFACE_PYTHON = "/missing/helix-surface-python"
  try {
    const report = await C.inspect({
      structure: baseline,
      options: { ...options, units: reference.units.value.ranges },
    })
    const physical = report.checks.find((c) => c.id === "fold-plausibility")!
    expect(physical.status).toBe("not_evaluable")
    expect((physical.value as any).surfaceDiagnostic.status).toBe("not_evaluable")
    expect(report.summary.biologicalValidity).toBe("not_established")
  } finally {
    if (previous === undefined) delete process.env.HELIX_TRP_SURFACE_PYTHON
    else process.env.HELIX_TRP_SURFACE_PYTHON = previous
  }
})

test.skipIf(!process.env.HELIX_TRP_SURFACE_TEST_PYTHON)(
  "surface measurement is deterministic and portable without a fold verdict",
  async () =>
    configured(async () => {
      const original = await originalCase("22r")
      const first = await C.inspect({ structure: original, options })
      const second = await C.inspect({ structure: original, options })
      expect(second).toEqual(first)
      const physical = first.checks.find((c) => c.id === "fold-plausibility")!
      const value = physical.value as any
      const diagnostic = value.surfaceDiagnostic
      expect(physical.status).toBe("not_evaluable")
      expect(diagnostic.status).toBe("measured")
      expect(diagnostic.sourceSha256).toBe(first.provenance.structureSha256)
      expect(diagnostic.measurement.chargedResidues).toBe(40)
      expect(diagnostic.measurement.completeChargedSidechains).toBe(40)
      expect(diagnostic.measurement.chargedSidechainRelativeAreaMedian).toBeCloseTo(0.5077180802119905, 12)
      expect(diagnostic.measurement.chargedSidechainRelativeAreaMin).toBeCloseTo(0.00004633258019466424, 12)
      expect(diagnostic.foldVerdict).toBe("not_established")
      expect(diagnostic.burialThreshold).toBeNull()
      expect(diagnostic.engine.versions.freesasa).toBe("2.2.1")
      expect(Object.keys(diagnostic.engine.modulesSha256)).toHaveLength(3)
      const workspace = await fs.mkdtemp(path.join(os.tmpdir(), "helix-surface-integration-"))
      try {
        await fs.writeFile(path.join(workspace, "original.pdb"), original, { mode: 0o600 })
        const evidence = await C.inspectFiles({ structure: "original.pdb", options }, workspace)
        const verify = () =>
          Bun.spawn(
            [
              "python3",
              path.join(evidence.directory, "verify.py"),
              evidence.directory,
              "--sha256",
              evidence.manifestSha256,
            ],
            { stdout: "ignore", stderr: "ignore" },
          ).exited
        expect(await verify()).toBe(0)
        const names = await fs.readdir(evidence.directory)
        expect(names).toContain("surface_diagnostic.py")
        expect(names).not.toContain("steric_diagnostic.py")
        await fs.appendFile(path.join(evidence.directory, "surface_diagnostic.py"), "\nchanged\n")
        expect(await verify()).not.toBe(0)
      } finally {
        await fs.rm(workspace, { recursive: true, force: true })
      }
    }),
)

test.skipIf(!process.env.HELIX_TRP_SURFACE_TEST_PYTHON)(
  "prepared workflow binds the configured surface wrapper without claiming physical admission",
  async () =>
    configured(async () => {
      const bundle = await N.prepare(reference, root, root)
      const structural = JSON.parse(bundle.files["structural_report.json"])
      const physical = structural.checks.find((c: { id: string }) => c.id === "fold-plausibility")
      expect(physical.status).toBe("not_evaluable")
      expect(physical.value.surfaceDiagnostic.status).toBe("measured")
      expect(bundle.files["surface_diagnostic.py"]).toBe(C.SURFACE_SCRIPT)
      expect(bundle.files["steric_diagnostic.py"]).toBeUndefined()
      expect(structural.summary.biologicalValidity).toBe("not_established")
      expect(bundle.digest).toBe(N.bundleDigest(bundle.files))
    }),
)

test.skipIf(!process.env.HELIX_TRP_SURFACE_TEST_PYTHON)(
  "missing sidechain coordinates remain incomplete and absent charge identities remain non applicable",
  async () =>
    configured(async () => {
      const original = await originalCase("22r")
      const partial = original
        .split("\n")
        .filter(
          (line) =>
            !(line.startsWith("ATOM  ") && line.slice(22, 26).trim() === "28" && line.slice(12, 16).trim() === "OD1"),
        )
        .join("\n")
      const report = await C.inspect({ structure: partial, options })
      const diagnostic = (report.checks.find((c) => c.id === "fold-plausibility")!.value as any).surfaceDiagnostic
      expect(diagnostic.status).toBe("measured")
      expect(diagnostic.measurement.chargedResidues).toBe(40)
      expect(diagnostic.measurement.completeChargedSidechains).toBe(39)
      expect(diagnostic.measurement.incompleteChargedSidechains).toBe(1)
      const residue = diagnostic.chargedResidueObservations.find((r: { residue: string }) => r.residue === "28")
      expect(residue.missingSidechainAtoms).toEqual(["OD1"])
      expect(residue.interpretableRelativeSidechainArea).toBeNull()
      expect(report.summary.biologicalValidity).toBe("not_established")
      const eight = await originalCase("8b")
      const empty = await C.inspect({
        structure: eight,
        options: {
          ...options,
          units: [
            { start: 1, end: 8 },
            { start: 9, end: 16 },
          ],
        },
      })
      const absent = (empty.checks.find((c) => c.id === "fold-plausibility")!.value as any).surfaceDiagnostic
      expect(absent.status).toBe("measured")
      expect(absent.measurement.chargedResidues).toBe(0)
      expect(absent.measurement.chargedSidechainRelativeAreaMedian).toBeNull()
      expect(absent.chargedResidueObservations).toHaveLength(0)
    }),
)
