/** A separate prospectively labeled engineering extension selected after
 * observing the original resource grid. Its denominator never replaces40.
 */
import fs from "node:fs/promises"
import path from "node:path"
import {randomUUID} from "node:crypto"
import {TrpNextflow as N} from "../../../../packages/helix/src/trp/nextflow"
import {TrpRemote as Remote} from "../../../../packages/helix/src/trp/remote"
import {TrpResources as R} from "../../../../packages/helix/src/trp/resources"
import {TrpSpecification as S} from "../../../../packages/helix/src/trp/specification"

const [outArg,originalArg,deadline,namespace]=process.argv.slice(2)
if(!outArg||!originalArg||!deadline||!namespace||!/^[a-z0-9-]+$/.test(namespace))
 throw new Error("NEW_INPUTS ORIGINAL_CAMPAIGN UTC_CHECKPOINT NEW_NAMESPACE required")
const root=path.resolve(import.meta.dir,"../../../.."),output=path.resolve(outArg),original=path.resolve(originalArg)
const oldBytes=await fs.readFile(path.join(original,"inputs/freeze.json")),old=JSON.parse(oldBytes.toString())
const allPath=path.join(original,"all-original-attempts.json")
const allBytes=await fs.readFile(allPath),all=JSON.parse(allBytes.toString())
if(!all.verified||!all.allOriginalCasesEmpiricallyObserved||all.originalFreezeSha256!==S.sha256(oldBytes))
 throw new Error("All original40 must first be conclusively and independently audited")
const missing=Math.max(0,20-all.empiricallyInfeasible)
if(!missing || missing>10 || all.empiricallyFeasible<20)throw new Error("Unsupported extension requirement; retain missing counts")
const target=await Remote.configured()
if(!target||target.config.numericalProfile!=="haswell-single-thread")throw new Error("Verified fixed-profile target required")
const checkpoint=Date.parse(deadline)
if(!Number.isFinite(checkpoint)||checkpoint<Date.now()+600000||checkpoint>Date.parse(target.config.sessionExpiresAt!)-600000)
 throw new Error("Verified checkpoint margin required")
for(const [name,expected]of Object.entries(old.sources).filter(([name])=>name.startsWith("packages/helix/src/trp/")))
 if(S.sha256(await fs.readFile(path.join(root,name)))!==expected)throw new Error("Production revision changed")
const graphPath=path.join(root,"evaluation/trp/campaign-20261012/contract-corpus/graphs.json")
const graphBytes=await fs.readFile(graphPath)
if(S.sha256(graphBytes)!==old.graphCorpusSha256)throw new Error("Original graph corpus changed")
const corpus=JSON.parse(graphBytes.toString())
const used=new Set(old.cases.map((c:any)=>c.graphId))
const selected=corpus.valid.filter((c:any)=>!used.has(c.id)).slice(0,missing)
if(selected.length!==missing)throw new Error("Insufficient unseen engineering graph variants")
await fs.mkdir(output,{recursive:false})
const cases:any[]=[]
for(const [index,source]of selected.entries()){
 const bundle=await N.prepare(source.specification,root,root),uid=randomUUID()
 Remote.bind(bundle,target,uid)
 const gold=path.join(output,"gold",source.id);await fs.mkdir(gold,{recursive:true})
 await fs.writeFile(path.join(gold,"2xqh.pdb"),bundle.files["selection.pdb"])
 const ranges=(values:any[])=>values.map(v=>`${v.start}_${v.end}`).join(",")
 const argv=["docker","run","--rm","--network","none","--read-only","--cpus","2","--memory","2g","--memory-swap","2g","--tmpfs","/tmp:rw,nosuid,size=256m",
  "-e","OPENBLAS_CORETYPE=Haswell","-e","OPENBLAS_NUM_THREADS=1","-e","OMP_NUM_THREADS=1","-e","MKL_NUM_THREADS=1","-v",`${gold}:/work`,bundle.image,"single","/work/2xqh.pdb",bundle.spec.chain.value,"/work/geometry.csv",ranges(bundle.spec.units.value.ranges)]
 if(bundle.spec.insertions.value.length)argv.push("-ins_def",ranges(bundle.spec.insertions.value))
 const proc=Bun.spawn(argv,{stdout:"pipe",stderr:"pipe"})
 const [exitCode,stdout,stderr]=await Promise.all([proc.exited,new Response(proc.stdout).text(),new Response(proc.stderr).text()])
 await fs.writeFile(path.join(gold,"execution.json"),JSON.stringify({argv,exitCode,stdout,stderr},null,2)+"\n")
 if(exitCode)throw new Error("Same-input comparator failed")
 const id=`R24-E${index+1}-small`;await fs.mkdir(path.join(output,id))
 const files:Record<string,string>={}
 for(const [name,content]of Object.entries(bundle.files)){
  await fs.writeFile(path.join(output,id,name),content,{flag:"wx"});files[name]=S.sha256(content)
 }
 cases.push({id,graphId:source.id,cohort:"small",inputDirectory:id,runComment:`helix:${uid}`,files,
  goldCsvPath:`gold/${source.id}/geometry.csv`,goldCsvSha256:S.sha256(await fs.readFile(path.join(gold,"geometry.csv"))),demand:R.count(bundle.files),
  budget:{cpus:3,memoryBytes:4*1024**3,workBytes:64*1024,wallSeconds:1080,requireHardStorageLimit:false,
   origin:"Separate prospective engineering extension after observed original grid group shortfall"},
  physicalFeasibilityLabel:null,helixDecision:null,oracleResult:null})
}
const sources={...old.sources}
for(const name of ["prepare_r24_extension.ts","drive_r24_extension.py","run_r24_extension.py"])
 sources[`evaluation/trp/campaign-20261012/trace/${name}`]=S.sha256(await fs.readFile(path.join(import.meta.dir,name)))
for (const name of ["script/tesis/aws_academy_cluster.py", "script/tesis/aws_academy_prepare_remote.py", "script/tesis/resume_r24_workspace.py"])
 sources[name]=S.sha256(await fs.readFile(path.join(root,name)))
const plan={...old,schema:"helix-r24-prospective-resource-extension/1.0",frozenAt:new Date().toISOString(),
 originalFreezeSha256:S.sha256(oldBytes),originalAllAttemptsSha256:S.sha256(allBytes),originalCountsBeforeExtension:{
  planned:40,empiricallyFeasible:all.empiricallyFeasible,empiricallyInfeasible:all.empiricallyInfeasible,scopedFalseRejections:all.scopedFalseRejections},
 cases,sources,target:target.public,executionOrder:cases.map(c=>c.id),globalDeadlineUtc:deadline,
 actualFeasibleMinimum:20,actualInfeasibleMinimum:20,prospectiveCohorts:{small:missing},
 originalMatrixPreservedSeparately:true,adaptedCombinedDenominator:40+missing,
 extensionChosenAfterObservingOriginalGrid:true,extensionPhysicalLabelsObservedBeforeFreeze:false,
 selectionRule:"First graph variants in the original frozen contract corpus not used by the original20 graphs; 64KiB quota for each. Number chosen to address observed infeasible group shortfall; causal failure must still be observed, never assumed.",
 operationalAmendment:{workspaceNamespace:namespace,projectIdBase:30000,unitPrefix:`helix-${namespace}-`,
  reason:"Separate prospective development extension; original40 and every attempt preserved; no scientific held-out metric claimed."}}
await fs.writeFile(path.join(output,"freeze.json"),JSON.stringify(plan,null,2)+"\n",{flag:"wx"})
console.log(JSON.stringify({prepared:true,extensionCases:missing,cloudJobsSubmitted:0,originalCases:40}))
