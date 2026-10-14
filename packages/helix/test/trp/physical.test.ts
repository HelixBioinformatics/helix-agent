import { expect, test } from "bun:test"
import fs from "node:fs/promises"
import os from "node:os"
import path from "node:path"
import { createHash } from "node:crypto"
import { TrpStructural as C } from "../../src/trp/structural"

const python = process.env.HELIX_TRP_PHYSICAL_TEST_PYTHON
const fixtureScript = path.join(import.meta.dir, "physical_diagnostic_test.py")

async function fixture(kind: string) {
  const process = Bun.spawn([python!, fixtureScript, "--fixture", kind], { stdout: "pipe", stderr: "pipe" })
  const [out, err, code] = await Promise.all([
    new Response(process.stdout).text(),
    new Response(process.stderr).text(),
    process.exited,
  ])
  if (code) throw new Error(err)
  return JSON.parse(out)
}

async function configured(run: () => Promise<void>) {
  const keys = ["HELIX_TRP_PYTHON", "HELIX_TRP_PHYSICAL_PYTHON", "HELIX_TRP_SURFACE_PYTHON", "HELIX_TRP_STERIC_PYTHON"]
  const old = Object.fromEntries(keys.map((key) => [key, process.env[key]]))
  process.env.HELIX_TRP_PYTHON = python
  process.env.HELIX_TRP_PHYSICAL_PYTHON = python
  delete process.env.HELIX_TRP_SURFACE_PYTHON
  delete process.env.HELIX_TRP_STERIC_PYTHON
  try {
    await run()
  } finally {
    for (const key of keys) {
      if (old[key] === undefined) delete process.env[key]
      else process.env[key] = old[key]
    }
  }
}

test.skipIf(!python)(
  "physical column warning changes C9 and blocks admission while global validity remains unknown",
  async () =>
    configured(async () => {
      const request = await fixture("charge")
      const report = await C.inspect(request)
      const control = report.checks.find((c) => c.id === "fold-plausibility")!
      expect(control.status).toBe("fail")
      expect((control.value as any).physicalDiagnostic.measurement.chargeAlert).toBe(true)
      expect((control.value as any).physicalDiagnostic.version).toBe("helix-physical-diagnostic/1.1.0")
      expect(report.summary.failed).toContain("fold-plausibility")
      expect(report.summary.blocking).toContain("fold-plausibility")
      expect(report.summary.mechanicalAdmission).toBe(false)
      expect(report.summary.biologicalValidity).toBe("not_established")
      expect(await C.inspect(request)).toEqual(report)
    }),
)

test.skipIf(!python)("cofactor context can remove the warning without certifying a complete physical fold", async () =>
  configured(async () => {
    const request = await fixture("calcium")
    const report = await C.inspect(request)
    const control = report.checks.find((c) => c.id === "fold-plausibility")!
    expect(control.status).toBe("pass")
    expect((control.value as any).physicalDiagnostic.decision).toBe("no_targeted_failure_detected")
    expect(control.reason).toContain("limited to those mechanisms")
    expect(report.summary.biologicalValidity).toBe("not_established")
  }),
)

test.skipIf(!python)("missing runtime and ambiguous metal chemistry preserve C9 uncertainty", async () =>
  configured(async () => {
    const ambiguous = await C.inspect(await fixture("iron-unknown"))
    expect(ambiguous.checks.find((c) => c.id === "fold-plausibility")!.status).toBe("not_evaluable")
    process.env.HELIX_TRP_PHYSICAL_PYTHON = "/missing/helix-physical-python"
    const missing = await C.inspect(await fixture("charge"))
    const control = missing.checks.find((c) => c.id === "fold-plausibility")!
    expect(control.status).toBe("not_evaluable")
    expect((control.value as any).physicalDiagnostic.failureCode).toBe("validator-failed-or-interrupted")
  }),
)

test.skipIf(!python)(
  "inspection evidence carries the exact physical wrapper and rejects forged complete-fold claims",
  async () =>
    configured(async () => {
      const request = await fixture("calcium")
      const workspace = await fs.mkdtemp(path.join(os.tmpdir(), "helix-physical-evidence-"))
      try {
        process.env.HELIX_TRP_SURFACE_PYTHON = python
        await fs.writeFile(path.join(workspace, "synthetic.pdb"), request.structure)
        const evidence = await C.inspectFiles({ structure: "synthetic.pdb", options: request.options }, workspace)
        expect(JSON.parse(await fs.readFile(path.join(evidence.directory, "catalogue.json"), "utf8")).version).toBe(
          "trp-structural-catalog/1.2.0",
        )
        expect(await fs.readFile(path.join(evidence.directory, "physical_diagnostic.py"), "utf8")).toBe(
          C.PHYSICAL_SCRIPT,
        )
        const verify = async (anchor?: string) => {
          const child = Bun.spawn(
            [
              "python3",
              path.join(evidence.directory, "verify.py"),
              evidence.directory,
              ...(anchor ? ["--sha256", anchor] : []),
            ],
            { stdout: "pipe", stderr: "pipe" },
          )
          const [out, err, code] = await Promise.all([
            new Response(child.stdout).text(),
            new Response(child.stderr).text(),
            child.exited,
          ])
          return { out, err, code }
        }
        const valid = await verify(evidence.manifestSha256)
        expect(valid.code).toBe(0)
        expect(JSON.parse(valid.out).scope).toContain("no FreeSASA/physical scientific re-execution")
        const reportPath = path.join(evidence.directory, "report.json")
        const manifestPath = path.join(evidence.directory, "manifest.json")
        const originalReport = await fs.readFile(reportPath, "utf8")
        const originalManifest = await fs.readFile(manifestPath, "utf8")
        const badRatio = JSON.parse(originalReport)
        badRatio.checks.find(
          (c: any) => c.id === "fold-plausibility",
        ).value.physicalDiagnostic.chargedResidueObservations[0].relativePolarMoietyArea1p4 += 0.25
        const badRatioBytes = JSON.stringify(badRatio)
        const badRatioManifest = JSON.parse(originalManifest)
        const badRatioEntry = badRatioManifest.files.find((file: any) => file.path === "report.json")
        badRatioEntry.bytes = Buffer.byteLength(badRatioBytes)
        badRatioEntry.sha256 = createHash("sha256").update(badRatioBytes).digest("hex")
        await fs.writeFile(reportPath, badRatioBytes)
        await fs.writeFile(manifestPath, JSON.stringify(badRatioManifest))
        const ratioRejected = await verify()
        expect(ratioRejected.code).not.toBe(0)
        expect(ratioRejected.err).toContain("polar-moiety ratio differs")
        await fs.writeFile(reportPath, originalReport)
        await fs.writeFile(manifestPath, originalManifest)
        const forged = JSON.parse(originalReport)
        forged.checks.find((c: any) => c.id === "fold-plausibility").value.physicalDiagnostic.globalFoldValidity =
          "valid"
        const bytes = JSON.stringify(forged)
        const manifest = JSON.parse(originalManifest)
        const entry = manifest.files.find((file: any) => file.path === "report.json")
        entry.bytes = Buffer.byteLength(bytes)
        entry.sha256 = createHash("sha256").update(bytes).digest("hex")
        await fs.writeFile(reportPath, bytes)
        await fs.writeFile(manifestPath, JSON.stringify(manifest))
        const invalid = await verify()
        expect(invalid.code).not.toBe(0)
        expect(invalid.err).toContain("unsupported complete fold claim")
        await fs.writeFile(reportPath, originalReport)
        await fs.writeFile(manifestPath, originalManifest)
        await fs.appendFile(path.join(evidence.directory, "physical_diagnostic.py"), "\nchanged\n")
        expect((await verify(evidence.manifestSha256)).code).not.toBe(0)
      } finally {
        await fs.rm(workspace, { force: true, recursive: true })
      }
    }),
)

const legacySourcePath = process.env.HELIX_TRP_PHYSICAL_LEGACY_SOURCE
test.skipIf(!python || !legacySourcePath)(
  "new portable verifier accepts an actual legacy1.0 producer and a current1.1 inspection",
  async () =>
    configured(async () => {
      const request = await fixture("calcium")
      const workspace = await fs.mkdtemp(path.join(os.tmpdir(), "helix-physical-legacy-"))
      try {
        await fs.writeFile(path.join(workspace, "synthetic.pdb"), request.structure)
        const evidence = await C.inspectFiles({ structure: "synthetic.pdb", options: request.options }, workspace)
        expect(JSON.parse(await fs.readFile(path.join(evidence.directory, "catalogue.json"), "utf8")).version).toBe(
          "trp-structural-catalog/1.2.0",
        )
        const verify = async () => {
          const proc = Bun.spawn(["python3", path.join(evidence.directory, "verify.py"), evidence.directory], {
            stdout: "pipe",
            stderr: "pipe",
          })
          const [out, err, code] = await Promise.all([
            new Response(proc.stdout).text(),
            new Response(proc.stderr).text(),
            proc.exited,
          ])
          return { out, err, code }
        }
        expect((await verify()).code).toBe(0)
        const legacySource = await fs.readFile(legacySourcePath!, "utf8")
        const legacy = Bun.spawn([python!, "-I", "-c", legacySource], { stdin: "pipe", stdout: "pipe", stderr: "pipe" })
        legacy.stdin.write(JSON.stringify(request))
        legacy.stdin.end()
        const [out, err, code] = await Promise.all([
          new Response(legacy.stdout).text(),
          new Response(legacy.stderr).text(),
          legacy.exited,
        ])
        if (code) throw new Error(err)
        const oldDiagnostic = JSON.parse(out)
        expect(oldDiagnostic.version).toBe("helix-physical-diagnostic/1.0.0")
        const reportPath = path.join(evidence.directory, "report.json")
        const manifestPath = path.join(evidence.directory, "manifest.json")
        const report = JSON.parse(await fs.readFile(reportPath, "utf8"))
        const control = report.checks.find((c: any) => c.id === "fold-plausibility")
        control.value.physicalDiagnostic = oldDiagnostic
        control.value.physicalWrapperSha256 = createHash("sha256").update(legacySource).digest("hex")
        control.threshold = { rule: oldDiagnostic.version, rulesSha256: oldDiagnostic.rulesSha256 }
        await fs.writeFile(reportPath, JSON.stringify(report))
        await fs.writeFile(path.join(evidence.directory, "physical_diagnostic.py"), legacySource)
        const manifest = JSON.parse(await fs.readFile(manifestPath, "utf8"))
        for (const entry of manifest.files) {
          if (!["report.json", "physical_diagnostic.py"].includes(entry.path)) continue
          const bytes = await fs.readFile(path.join(evidence.directory, entry.path))
          entry.bytes = bytes.length
          entry.sha256 = createHash("sha256").update(bytes).digest("hex")
        }
        await fs.writeFile(manifestPath, JSON.stringify(manifest))
        const validLegacy = await verify()
        expect(validLegacy.code).toBe(0)
        expect(JSON.parse(validLegacy.out).ok).toBe(true)
      } finally {
        await fs.rm(workspace, { force: true, recursive: true })
      }
    }),
)
