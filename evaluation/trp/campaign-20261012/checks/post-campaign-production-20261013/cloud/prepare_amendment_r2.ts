/** Synthetic cancellation fixture, not a protein truth reference or rate case. */
import fs from "node:fs/promises"
import path from "node:path"
import os from "node:os"
import { randomUUID } from "node:crypto"
import { TrpNextflow as N } from "../../../../../../packages/helix/src/trp/nextflow"
import { TrpSpecification as S } from "../../../../../../packages/helix/src/trp/specification"

const root = path.resolve(import.meta.dir, "../../../../../..")
const [output, guestRoot] = process.argv.slice(2)
if (!output || !guestRoot) throw new Error("Supply fresh amendment output and guest runtime")
await fs.mkdir(output, { recursive: false })
const reference = path.join(root, "evaluation/trp/campaign-20261012/cloud/lab1/cancellation/next-ctx-abort/out/running-job/evidence/run")
const source = await fs.readFile(path.join(reference, "source.pdb"))
if (S.sha256(source) !== "e74115f68944ad5307202991cf9cf70de9d2774d0a104663ed77519f902d01ab")
  throw new Error("Previously validated synthetic source differs")
const spec = JSON.parse(await fs.readFile(path.join(reference, "specification.json"), "utf8"))
spec.catalogHash = S.catalogHash
spec.structure.value.path = "input.pdb"
const workspace = await fs.mkdtemp(path.join(os.tmpdir(), "helix-native-amendment-"))
await fs.writeFile(path.join(workspace, "input.pdb"), source)
const bundle = await N.prepare(spec, root, workspace)
await fs.rm(workspace, { recursive: true, force: true })
const graphId = "ENGINEERING-1000-CA"
const directory = path.join(output, graphId)
await fs.mkdir(directory)
await fs.writeFile(path.join(directory, "unbound-bundle.json"), JSON.stringify(bundle) + "\n")
await fs.writeFile(path.join(directory, "source.pdb"), source)
const item = {
  id: "POST-04-native-cancellation-1000", graphId, cohort: "controlled-native-failure-amendment",
  specification: spec,
  budget: { cpus: 3, memoryBytes: 4 * 1024 ** 3, workBytes: 128 * 1024 ** 2,
    wallSeconds: 1080, requireHardStorageLimit: true,
    origin: "Prospective post-repair native cancellation integration; ordinary real admission and enforced strict project/cgroups" },
  prospectiveDecisionUuid: randomUUID(), allowWorkOnlyOracle: false,
  unboundBundlePath: `${guestRoot}/campaign/post-integration-amendment-r2/${graphId}/unbound-bundle.json`,
  unboundFileHashes: Object.fromEntries(Object.entries(bundle.files).map(([name, text]) => [name, S.sha256(text)])),
  sourceInputPath: `${guestRoot}/campaign/post-integration-amendment-r2/${graphId}/source.pdb`, sourceInputSha256: S.sha256(source),
  goldCsvPath: null, goldCsvSha256: null, evidenceRoot: guestRoot,
  physicalFeasibilityLabel: null, helixDecision: null, biologicalValidity: "not_established",
  expectedIntegrationOutcome: "Own scientific GEOMETRY RUNNING, one scancel, actual native terminal retained, automatic failed package and complete owned cleanup",
  faultInjection: { kind: "native-scancel", afterApproval: true, afterAnalysisAdmission: true,
    jobName: "nf-GEOMETRY", requiredInitialNativeState: "RUNNING", exactOwnerCommentRequired: true,
    oneInjectionOnly: true, scientificResourceLabel: null },
  fixtureSource: { path: path.relative(root, path.join(reference, "source.pdb")), sha256: S.sha256(source),
    description: "Previously validated engineering fixture: 1000 transformed copies of six C-alpha coordinates, 6000 CA atoms; synthetic B-factor metadata. No experimental or biological validity claim, no geometry gold fabricated." },
}
await fs.writeFile(path.join(output, item.id + ".json"), JSON.stringify(item, null, 2) + "\n")
const sourceHashes: Record<string, string> = {}
for (const name of (await fs.readdir(path.join(root, "packages/helix/src/trp"))).filter(name => name.endsWith(".ts") || name.endsWith(".py.txt") || name === "catalog.json"))
  sourceHashes["packages/helix/src/trp/" + name] = S.sha256(await fs.readFile(path.join(root, "packages/helix/src/trp", name)))
for (const name of ["full_client_large.ts", "prepare_amendment_r2.ts", "fault_native.py", "drive_integration_r3.py"])
  sourceHashes[path.relative(root, path.join(import.meta.dir, name))] = S.sha256(await fs.readFile(path.join(import.meta.dir, name)))
sourceHashes["script/tesis/provision_remote_strict_profile.py"] = S.sha256(await fs.readFile(path.join(root, "script/tesis/provision_remote_strict_profile.py")))
const offline = JSON.parse(await fs.readFile(path.join(import.meta.dir, "offline-large-prepare.json"), "utf8"))
if (!offline.verified || offline.units !== 1000 || offline.runToolCalled !== false) throw new Error("Real offline preparation check not verified")
const producerCommit = Bun.spawnSync(["git", "rev-parse", "HEAD"], { cwd: root }).stdout.toString().trim()
await fs.writeFile(path.join(output, "freeze.json"), JSON.stringify({
  schema: "helix-post-repair-native-amendment/1.0", mode: "post-integration-amendment-r2", guestInputNamespace: "post-integration-amendment-r2",
  frozenAt: new Date().toISOString(), producerCommit, cases: [item], sourceHashes,
  amendmentCause: "POST-02 failed before client due observer/supervisor folder collision. POST-03 completed preparation but the harness parsed the truncated visual output; it never called Run. Both original attempts are preserved. New harness validates metadata and reads durable admission/budget/run artifacts; no truncation bypass, producer change or old-case resubmission.",
  original50Unmodified: true, originalIntegrationPositivePreserved: true,
  scientificMetrics: null, resourceClassificationMetrics: null, numericalGoldForInducedFailure: null,
  approvalActor: "synthetic operator through actual Question.Service and actual digest",
  offlineLargePreparationSha256: S.sha256(await fs.readFile(path.join(import.meta.dir, "offline-large-prepare.json"))),
}, null, 2) + "\n")
console.log(JSON.stringify({ output, cases: 1, units: 1000, cloudCalls: 0, numericalGoldInvented: false }))
