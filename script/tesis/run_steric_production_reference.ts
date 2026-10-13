import fs from "node:fs/promises"
import os from "node:os"
import path from "node:path"
import { TrpStructural as C } from "../../packages/helix/src/trp/structural"

if (!process.env.HELIX_TRP_STERIC_PYTHON) throw new Error("Configure HELIX_TRP_STERIC_PYTHON first")
const root = path.resolve(import.meta.dir, "../..")
const source = "evaluation/trp/reference/pratt-author-20261001"
const meta = JSON.parse(await fs.readFile(path.join(root, source, "metadata/8b.json"), "utf8"))
const cases = JSON.parse(await fs.readFile(path.join(root, source, "cases.json"), "utf8"))
const item = cases.find((row: { identifier: string }) => row.identifier === "8b")
const width = item.repeatSequence.length
const evidence = await C.inspectFiles(
  {
    structure: path.join(source, "originals", meta.structureFile),
    options: {
      format: "pdb",
      model: 1,
      chain: "A",
      frame: "auth_seq_id",
      units: Array.from({ length: 10 }, (_, i) => ({ start: i * width + 1, end: (i + 1) * width })),
      plddtMin: 70,
      paeMax: 5,
    },
    colabfold: {
      metadata: path.join(source, "metadata/8b.json"),
      scores: path.join(source, "originals", meta.scoresFile),
      pae: path.join(source, "originals", meta.paeFile),
    },
  },
  root,
)
const physical = evidence.report.checks.find((check) => check.id === "fold-plausibility")!
const value = physical.value as {
  stericDiagnostic: { status: string; measurement: { severeClashes: number; clashscore: number } }
}
if (physical.status !== "not_evaluable" || value.stericDiagnostic.status !== "measured")
  throw new Error("Physical diagnostic unavailable or unsupported classification")
const offline = JSON.parse(
  await fs.readFile(
    path.join(root, "evaluation/trp/campaign-20261012/structural/reports/pratt-original/8b.json"),
    "utf8",
  ),
)
if (
  value.stericDiagnostic.measurement.severeClashes !== offline.numClashes ||
  value.stericDiagnostic.measurement.clashscore !== offline.clashscore
)
  throw new Error("Production/offline steric outcome differs")
const privateRoot = path.join(os.homedir(), ".local/state/helix/structural-20261012")
await fs.chmod(privateRoot, 0o700)
const copy = path.join(privateRoot, "agent-reference-8b")
await fs.cp(evidence.directory, copy, { recursive: true, force: true })
const child = Bun.spawn(["python3", path.join(copy, "verify.py"), copy, "--sha256", evidence.manifestSha256], {
  stdout: "pipe",
  stderr: "pipe",
})
const verification = JSON.parse(await new Response(child.stdout).text())
if ((await child.exited) !== 0 || !verification.ok) throw new Error("Portable inspection evidence failed verification")
await fs.writeFile(
  path.join(root, "evaluation/trp/campaign-20261012/structural/agent-reference.json"),
  JSON.stringify(
    {
      case: "8b",
      scope: "Actual Helix file inspection adapter with optional maintained steric diagnostic; no LLM inference",
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
console.log(JSON.stringify({ case: "8b", matchesExternalFrozenRun: true, portableVerified: true, modelCalls: 0 }))
