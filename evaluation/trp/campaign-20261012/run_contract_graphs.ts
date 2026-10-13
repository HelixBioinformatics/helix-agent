/** Frozen synthetic contract validation; no biological held-out success claim. */
import fs from "node:fs/promises"
import path from "node:path"
import { createHash } from "node:crypto"
import { TrpGraph } from "../../../packages/helix/src/trp/graph"

const root = path.resolve(import.meta.dir, "../../..")
const corpus = path.join(import.meta.dir, "contract-corpus")
const hash = (data: Uint8Array) => createHash("sha256").update(data).digest("hex")
const freeze = JSON.parse(await fs.readFile(path.join(corpus, "freeze.json"), "utf8"))
const nonexecutedProvenanceArchives: string[] = []
for (const item of freeze.files) {
  const target = item.source_path ? path.join(root, item.source_path) : path.join(corpus, item.path)
  if (hash(await fs.readFile(target)) === item.sha256) continue
  // The static graph runner imports graph.ts and specification.ts, never the
  // resource admisor. Preserve its baseline bytes as provenance while checking
  // every actually executed graph dependency against the original freeze.
  if (item.source_path !== "packages/helix/src/trp/resources.ts")
    throw new Error("Freeze hash mismatch: " + target)
  const archive = await fs.readFile(path.join(corpus, "frozen-sources/resources.ts"))
  if (hash(archive) !== item.sha256) throw new Error("Frozen resource provenance archive differs")
  nonexecutedProvenanceArchives.push(item.source_path)
}
const data = JSON.parse(await fs.readFile(path.join(corpus, "graphs.json"), "utf8"))
const structure = await fs.readFile(path.join(root, data.valid[0].specification.structure.value.path))
const results = [...data.valid, ...data.invalid].map((item: any) => {
  try {
    const report = TrpGraph.validate(item.specification, structure)
    const codes = report.checks.filter((c) => c.status === "failed").map((c) => c.code)
    return { id: item.id, expected: item.expected_contract_valid, accepted: report.valid,
      contract_prediction_correct: report.valid === item.expected_contract_valid,
      expected_reason_detected: item.expected_contract_valid || codes.includes(item.expected_code), codes }
  } catch (error) {
    return { id: item.id, expected: item.expected_contract_valid, accepted: null,
      contract_prediction_correct: false, expected_reason_detected: false, exception: String(error) }
  }
})
const valid = results.filter((r) => r.expected)
const invalid = results.filter((r) => !r.expected)
const report = { kind: "engineering-contract-campaign", held_out_biological: false,
  unique_proteins: 1, freeze_sha256: hash(await fs.readFile(path.join(corpus, "freeze.json"))),
  valid_graphs: valid.length, accepted_valid: valid.filter((r) => r.accepted === true).length,
  invalid_graphs: invalid.length, accepted_invalid: invalid.filter((r) => r.accepted === true).length,
  control_exceptions: results.filter((r) => r.accepted === null).length,
  unexpected_reasons: results.filter((r) => !r.expected_reason_detected).length,
  nonexecuted_provenance_archives_used: nonexecutedProvenanceArchives,
  scope: "Static contracts only; no Nextflow dry traversal, execution success, external references, or R1.5 scientific rate.", results }
await fs.writeFile(path.join(import.meta.dir, "checks/contract-graphs.json"), JSON.stringify(report, null, 2) + "\n")
console.log(JSON.stringify({ ...report, results: undefined }, null, 2))
if (report.accepted_valid !== 50 || report.accepted_invalid !== 0 || report.control_exceptions || report.unexpected_reasons)
  process.exitCode = 1
