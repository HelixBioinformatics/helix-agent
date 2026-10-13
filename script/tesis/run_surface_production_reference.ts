import fs from "node:fs/promises"
import os from "node:os"
import path from "node:path"
import { TrpStructural as C } from "../../packages/helix/src/trp/structural"

if (!process.env.HELIX_TRP_SURFACE_PYTHON) throw new Error("Configure HELIX_TRP_SURFACE_PYTHON first")
if (process.env.HELIX_TRP_STERIC_PYTHON) throw new Error("Use a separate surface-only invocation for this reference")
const root = path.resolve(import.meta.dir, "../..")
const source = "evaluation/trp/reference/pratt-author-20261001"
const meta = JSON.parse(await fs.readFile(path.join(root, source, "metadata/22r.json"), "utf8"))
const evidence = await C.inspectFiles(
  {
    structure: path.join(source, "originals", meta.structureFile),
    options: {
      format: "pdb",
      model: 1,
      chain: "A",
      frame: "auth_seq_id",
      units: Array.from({ length: 10 }, (_, i) => ({ start: i * 22 + 1, end: (i + 1) * 22 })),
      plddtMin: 70,
      paeMax: 5,
    },
    colabfold: {
      metadata: path.join(source, "metadata/22r.json"),
      scores: path.join(source, "originals", meta.scoresFile),
      pae: path.join(source, "originals", meta.paeFile),
    },
  },
  root,
)
const physical = evidence.report.checks.find((check) => check.id === "fold-plausibility")!
const diagnostic = (physical.value as any).surfaceDiagnostic
const external = JSON.parse(
  await fs.readFile(
    path.join(root, "evaluation/trp/campaign-20261012/structural/freesasa/reports/pratt-original/22r.json"),
    "utf8",
  ),
)
if (
  physical.status !== "not_evaluable" ||
  diagnostic.status !== "measured" ||
  diagnostic.foldVerdict !== "not_established" ||
  diagnostic.burialThreshold !== null
)
  throw new Error("Unsupported surface diagnostic verdict")
for (const [left, right] of [
  [diagnostic.measurement.chargedResidues, external.chargedResidues],
  [diagnostic.measurement.completeChargedSidechains, external.completeChargedSidechains],
  [diagnostic.measurement.chargedSidechainRelativeAreaMedian, external.chargedSidechainRelativeAreaMedian],
  [diagnostic.measurement.chargedSidechainRelativeAreaMin, external.chargedSidechainRelativeAreaMin],
  [diagnostic.measurement.chargedSidechainRelativeAreaMax, external.chargedSidechainRelativeAreaMax],
])
  if (left !== right) throw new Error("Production/frozen external surface observable differs")
const privateRoot = path.join(os.homedir(), ".local/state/helix/surface-integration-20261012")
await fs.chmod(privateRoot, 0o700)
const copy = path.join(privateRoot, "agent-reference-22r")
await fs.cp(evidence.directory, copy, { recursive: true, force: true })
await fs.chmod(copy, 0o700)
const child = Bun.spawn(["python3", path.join(copy, "verify.py"), copy, "--sha256", evidence.manifestSha256], {
  stdout: "pipe",
  stderr: "pipe",
})
const verification = JSON.parse(await new Response(child.stdout).text())
if ((await child.exited) !== 0 || !verification.ok) throw new Error("Portable inspection failed verification")
const base = path.join(root, "evaluation/trp/campaign-20261012/structural/freesasa/integration")
await fs.mkdir(base, { recursive: true })
await fs.writeFile(
  path.join(base, "agent-reference.json"),
  JSON.stringify(
    {
      case: "22r",
      scope: "Actual Helix file inspection adapter with optional descriptive FreeSASA observable; no LLM inference",
      privateEvidenceDirectory: copy,
      manifestSha256: evidence.manifestSha256,
      verification,
      report: evidence.report,
      matchesExternalFrozenRun: true,
      modelCalls: 0,
      scientificClassification: "not established",
    },
    null,
    2,
  ) + "\n",
)
console.log(JSON.stringify({ case: "22r", matchesExternalFrozenRun: true, portableVerified: true, modelCalls: 0 }))
