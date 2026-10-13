/** Fresh engineering integration cases; no resource labels or reserved metrics. */
import fs from "node:fs/promises"
import path from "node:path"
import os from "node:os"
import { randomUUID } from "node:crypto"
import { TrpNextflow as N } from "../../../../../../packages/helix/src/trp/nextflow"
import { TrpSpecification as S } from "../../../../../../packages/helix/src/trp/specification"

const root = path.resolve(import.meta.dir, "../../../../../..")
const [output, guestRoot] = process.argv.slice(2)
if (!output || !guestRoot) throw new Error("Supply a fresh output and immutable guest runtime")
await fs.mkdir(output, { recursive: false })
const corpusPath = path.join(root, "evaluation/trp/campaign-20261012/contract-corpus/graphs.json")
const bytes = await fs.readFile(corpusPath)
const corpus = JSON.parse(bytes.toString())
const originalFreeze = JSON.parse(await fs.readFile(path.join(path.dirname(corpusPath), "freeze.json"), "utf8"))
if (S.sha256(bytes) !== originalFreeze.files.find((row: any) => row.path === "graphs.json").sha256)
  throw new Error("Development graph corpus changed")
const cases: any[] = []
for (const [index, graphId] of ["G-valid-048", "G-valid-049"].entries()) {
  const entry = corpus.valid.find((row: any) => row.id === graphId)
  if (!entry) throw new Error("Graph missing")
  const workspace = await fs.mkdtemp(path.join(os.tmpdir(), "helix-postrepair-reference-"))
  const source = await fs.readFile(path.join(root, entry.specification.structure.value.path))
  await fs.writeFile(path.join(workspace, "input.pdb"), source)
  const normalized = structuredClone(entry.specification)
  normalized.structure.value.path = "input.pdb"
  const bundle = await N.prepare(normalized, root, workspace)
  await fs.rm(workspace, { recursive: true, force: true })
  const directory = path.join(output, graphId)
  await fs.mkdir(directory)
  await fs.writeFile(path.join(directory, "unbound-bundle.json"), JSON.stringify(bundle) + "\n")
  await fs.writeFile(path.join(directory, "source.pdb"), source)
  const goldPath = path.join(root, "evaluation/trp/campaign-20261012/cloud/lab1/workflows", graphId, "standalone-reference/geometry.csv")
  const gold = await fs.readFile(goldPath)
  await fs.writeFile(path.join(directory, "geometry.csv"), gold)
  const id = index === 0 ? "POST-01-positive" : "POST-02-native-cancellation"
  const item = {
    id, graphId, cohort: index === 0 ? "ordinary-positive" : "controlled-native-failure",
    specification: entry.specification,
    budget: { cpus: 3, memoryBytes: 4 * 1024 ** 3, workBytes: 128 * 1024 ** 2,
      wallSeconds: 1080, requireHardStorageLimit: true,
      origin: "New post-repair integration only; no resource-label or scientific-rate inference" },
    prospectiveDecisionUuid: randomUUID(), allowWorkOnlyOracle: false,
    unboundBundlePath: `${guestRoot}/campaign/post-integration/${graphId}/unbound-bundle.json`,
    unboundFileHashes: Object.fromEntries(Object.entries(bundle.files).map(([name, text]) => [name, S.sha256(text)])),
    sourceInputPath: `${guestRoot}/campaign/post-integration/${graphId}/source.pdb`, sourceInputSha256: S.sha256(source),
    goldCsvPath: `${guestRoot}/campaign/post-integration/${graphId}/geometry.csv`, goldCsvSha256: S.sha256(gold),
    evidenceRoot: guestRoot, physicalFeasibilityLabel: null, helixDecision: null,
    expectedIntegrationOutcome: index === 0 ? "four native tasks and own-input gold plus cold verified export" : "own scientific GEOMETRY native task observed RUNNING then scancel; automatic failed package and complete owned cleanup",
    faultInjection: index === 0 ? null : { kind: "native-scancel", afterApproval: true, afterAnalysisAdmission: true,
      jobName: "nf-GEOMETRY", requiredInitialNativeState: "RUNNING", exactOwnerCommentRequired: true,
      oneInjectionOnly: true, scientificResourceLabel: null },
  }
  await fs.writeFile(path.join(output, id + ".json"), JSON.stringify(item, null, 2) + "\n")
  cases.push(item)
}
const sourceHashes: Record<string, string> = {}
for (const name of (await fs.readdir(path.join(root, "packages/helix/src/trp"))).filter(name => name.endsWith(".ts") || name.endsWith(".py.txt") || name === "catalog.json"))
  sourceHashes["packages/helix/src/trp/" + name] = S.sha256(await fs.readFile(path.join(root, "packages/helix/src/trp", name)))
for (const name of ["full_client.ts", "prepare_integration.ts", "fault_native.py", "prepare_runtime.py", "drive_integration.py"])
  sourceHashes[path.relative(root, path.join(import.meta.dir, name))] = S.sha256(await fs.readFile(path.join(import.meta.dir, name)))
sourceHashes["script/tesis/provision_remote_strict_profile.py"] = S.sha256(await fs.readFile(path.join(root, "script/tesis/provision_remote_strict_profile.py")))
const producerCommit = Bun.spawnSync(["git", "rev-parse", "HEAD"], { cwd: root }).stdout.toString().trim()
if (!/^[a-f0-9]{40}$/.test(producerCommit)) throw new Error("Producer commit unavailable")
await fs.writeFile(path.join(output, "freeze.json"), JSON.stringify({
  schema: "helix-post-repair-strict-integration/1.0", mode: "post-integration", guestInputNamespace: "post-integration",
  frozenAt: new Date().toISOString(), cases, sourceHashes, graphCorpusSha256: S.sha256(bytes),
  uniqueProteins: 1, resourceClassificationMetrics: null, scientificMetrics: null,
  original50Unmodified: true, approvalActor: "synthetic operator via real Question.Service",
  producerCommit, originalCampaignCommit: "ecfab67", localIntegrationHarnessBytesFrozen: true,
  runtimeRoot: guestRoot, nativeFaultSource: "fault_native.py", resubmissionForbiddenOnTransportUnknown: true,
}, null, 2) + "\n")
console.log(JSON.stringify({ cases: cases.length, cloudJobsSubmitted: 0, output }))
