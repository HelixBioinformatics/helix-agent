/** Prospective operational amendment after a legitimate guest stop/start.
 * Original forty scenarios, labels and historical first attempts stay intact.
 * Only unresolved IDs are copied with a fresh target, namespace and comment.
 */
import fs from "node:fs/promises"
import path from "node:path"
import { randomUUID } from "node:crypto"
import { TrpRemote as Remote } from "../../../../packages/helix/src/trp/remote"
import { TrpResources as R } from "../../../../packages/helix/src/trp/resources"
import { TrpSpecification as S } from "../../../../packages/helix/src/trp/specification"

const [outArg, originalArg, deadline, namespace] = process.argv.slice(2)
if (!outArg || !originalArg || !deadline || !namespace || !/^[a-z0-9-]+$/.test(namespace))
  throw new Error("Usage: NEW_INPUTS ORIGINAL_CAMPAIGN UTC_CHECKPOINT NEW_NAMESPACE")
const root = path.resolve(import.meta.dir, "../../../..")
const output = path.resolve(outArg)
const original = path.resolve(originalArg)
const oldBytes = await fs.readFile(path.join(original, "inputs/freeze.json"))
const old = JSON.parse(oldBytes.toString())
const progressBytes = await fs.readFile(path.join(original, "progress.json"))
const progress = JSON.parse(progressBytes.toString())
if (progress.freezeSha256 !== S.sha256(oldBytes)) throw new Error("Original freeze differs")
if (!await fs.stat(path.join(original, "summary.json")).then(s => s.isFile()).catch(() => false))
  throw new Error("Original orchestration must reach its final checkpoint before continuation")
if (progress.cases.some((c:any) => c.dispatched && !["recovered","unknown-supervisor-stopped-without-result"].includes(c.status)))
  throw new Error("An original dispatched attempt is not recovered; inspect without resubmission")
if (progress.cases.find((c:any)=>c.id === old.cases[0].id)?.physicalFeasibilityLabel !== true)
  throw new Error("Original generous smoke was not established")
const cleanupPath = path.join(original, "checkpoint-cleanup.json")
const cleanupBytes = await fs.readFile(cleanupPath)
const cleanup = JSON.parse(cleanupBytes.toString())
if (!cleanup.verified || cleanup.ownedJobs.length || cleanup.workerContainers.some((c:any)=>c.stdout.trim()))
  throw new Error("Independent original controller/jobs/containers cleanup not established")
const target = await Remote.configured()
if (!target || target.config.numericalProfile !== "haswell-single-thread") throw new Error("Renewed actual target absent")
const checkpoint = Date.parse(deadline)
if (!Number.isFinite(checkpoint) || checkpoint < Date.now()+1200000 ||
    checkpoint > Date.parse(target.config.sessionExpiresAt!)-600000)
  throw new Error("Continuation checkpoint requires verified guest/Academy window and copy margin")
if (target.fingerprint === old.target.fingerprint) throw new Error("Target was not prospectively rebound after restart")
for (const [name, expected] of Object.entries(old.sources).filter(([name])=>name.startsWith("packages/helix/src/trp/")))
  if (S.sha256(await fs.readFile(path.join(root,name))) !== expected)
    throw new Error("Production source changed beyond operational rebinding: "+name)
const pending = old.cases.filter((c:any)=>progress.cases.find((r:any)=>r.id===c.id)?.physicalFeasibilityLabel == null)
if (!pending.length) throw new Error("No unresolved original case needs continuation")
await fs.mkdir(output, {recursive:false})
await fs.cp(path.join(original,"inputs/gold"),path.join(output,"gold"),{recursive:true})
const cases:any[]=[]
for (const previous of pending) {
  const cid=previous.id
  const ownId=randomUUID()
  const oldDirectory=path.join(original,"inputs",previous.inputDirectory)
  const newDirectory=path.join(output,cid)
  await fs.mkdir(newDirectory)
  const files:Record<string,string>={}
  for (const [name, expected] of Object.entries(previous.files)) {
    const bytes=await fs.readFile(path.join(oldDirectory,name))
    if(S.sha256(bytes)!==expected)throw new Error("Original immutable input changed: "+cid+"/"+name)
    files[name]=bytes.toString()
  }
  const permitted=new Set(["remote_target.json","execution.json","nextflow.config"])
  files["remote_target.json"]=S.canonical(target.public)+"\n"
  const execution=JSON.parse(files["execution.json"])
  execution.target=target.public
  files["execution.json"]=S.canonical(execution)+"\n"
  files["nextflow.config"]=files["nextflow.config"].replaceAll(previous.runComment,`helix:${ownId}`)
  const hashes:Record<string,string>={}
  for(const [name,value]of Object.entries(files)){
    hashes[name]=S.sha256(value)
    if(!permitted.has(name) && hashes[name]!==previous.files[name])throw new Error("Scientific input altered")
    await fs.writeFile(path.join(newDirectory,name),value,{flag:"wx"})
  }
  if(S.sha256(await fs.readFile(path.join(output,previous.goldCsvPath)))!==previous.goldCsvSha256)
    throw new Error("Same-input gold changed")
  cases.push({...previous,inputDirectory:cid,runComment:`helix:${ownId}`,files:hashes,demand:R.count(files),
    previousInputHashes:previous.files, previousDemand:previous.demand, physicalFeasibilityLabel:null,
    helixDecision:null,oracleResult:null,originalAttempt:progress.cases.find((r:any)=>r.id===cid)??null})
}
const sources={...old.sources}
for(const name of ["prepare_r24_continuation.ts","drive_r24_continuation.py","run_r24_continuation.py"])
  sources[`evaluation/trp/campaign-20261012/trace/${name}`]=S.sha256(await fs.readFile(path.join(import.meta.dir,name)))
for (const name of ["script/tesis/aws_academy_cluster.py", "script/tesis/aws_academy_prepare_remote.py", "script/tesis/resume_r24_workspace.py"])
 sources[name]=S.sha256(await fs.readFile(path.join(root,name)))
const plan={...old,schema:"helix-r24-operational-continuation/1.0",frozenAt:new Date().toISOString(),
  originalFreezeSha256:S.sha256(oldBytes),originalProgressSha256:S.sha256(progressBytes),
  originalCleanupSha256:S.sha256(cleanupBytes),originalCaseCount:old.cases.length,
  cases,sources,target:target.public,executionOrder:cases.map(c=>c.id),globalDeadlineUtc:deadline,
  operationalAmendment:{reason:"Checkpoint preserved and owned jobs cleaned before legitimate guest restart; unchanged original scientific scenarios rebound to observed renewed target.",
    workspaceNamespace:namespace,projectIdBase:20000,unitPrefix:`helix-${namespace}-`,
    changedScientificInputs:false,changedBudgetOrGold:false,originalLabelsRewritten:false,
    automaticResubmissionOnTimeout:false,permittedInputChanges:["target binding","unique run comment"],
    scopePreserved:true,pendingOriginalIds:cases.map(c=>c.id)}}
await fs.writeFile(path.join(output,"freeze.json"),JSON.stringify(plan,null,2)+"\n",{flag:"wx"})
console.log(JSON.stringify({prepared:true,cases:cases.length,cloudJobsSubmitted:0,originalCaseCount:old.cases.length}))
