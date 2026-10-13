/** Freeze unbound references; actual full client prepares again inside quota. */
import fs from 'node:fs/promises'
import path from 'node:path'
import os from 'node:os'
import {randomUUID} from 'node:crypto'
import {TrpNextflow as N} from '../../../../packages/helix/src/trp/nextflow'
import {TrpSpecification as S} from '../../../../packages/helix/src/trp/specification'
const root=path.resolve(import.meta.dir,'../../../..')
const [output,positiveArgument,negativeArgument,namespaceArgument]=process.argv.slice(2)
const mode='extension',positiveCount=Number(positiveArgument),negativeCount=Number(negativeArgument),count=positiveCount+negativeCount
if(!Number.isInteger(positiveCount)||!Number.isInteger(negativeCount)||positiveCount<0||negativeCount<0||count<1||count>27)throw new Error('Supply new positive and negative extension cohort sizes')
const namespace=namespaceArgument??mode
if(!output)throw new Error('Supply a fresh extension output directory')
await fs.mkdir(output,{recursive:false})
const corpusPath=path.join(root,'evaluation/trp/campaign-20261012/contract-corpus/graphs.json')
const bytes=await fs.readFile(corpusPath),corpus=JSON.parse(bytes.toString())
const old=JSON.parse(await fs.readFile(path.join(path.dirname(corpusPath),'freeze.json'),'utf8'))
if(S.sha256(bytes)!==old.files.find((f:any)=>f.path==='graphs.json').sha256)throw new Error('Contract corpus changed')
const MiB=1024**2,small=[64*1024,128*1024,256*1024,512*1024,MiB,2*MiB,4*MiB,8*MiB,12*MiB,16*MiB]
const sources=corpus.valid.slice(23,23+count)
const guestRoot='/opt/helix-strict-runtime'
const cases:any[]=[]
for(const [index,entry]of sources.entries()){
 const workspace=await fs.mkdtemp(path.join(os.tmpdir(),'helix-aggregate-reference-'))
 const sourceBytes=await fs.readFile(path.join(root,entry.specification.structure.value.path))
 await fs.writeFile(path.join(workspace,'input.pdb'),sourceBytes)
 const normalized=structuredClone(entry.specification);normalized.structure.value.path='input.pdb'
 const bundle=await N.prepare(normalized,root,workspace)
 await fs.rm(workspace,{recursive:true,force:true})
 const directory=path.join(output,entry.id);await fs.mkdir(directory)
 await fs.writeFile(path.join(directory,'unbound-bundle.json'),JSON.stringify(bundle)+'\n')
 const input=await fs.readFile(path.join(root,entry.specification.structure.value.path))
 await fs.writeFile(path.join(directory,'source.pdb'),input)
 const firstGold=path.join(root,'evaluation/trp/campaign-20261012/cloud/lab2/r24-extension/inputs/gold',entry.id,'geometry.csv')
 const secondGold=path.join(root,'evaluation/trp/campaign-20261012/cloud/lab1/workflows',entry.id,'standalone-reference/geometry.csv')
 const goldLocal=await fs.access(firstGold).then(()=>firstGold).catch(()=>secondGold)
 const gold=await fs.readFile(goldLocal);await fs.writeFile(path.join(directory,'geometry.csv'),gold)
 for(const [cohort,workBytes]of [[index<positiveCount?'generous-extension':'small-extension',index<positiveCount?128*MiB:((index-positiveCount)%2===0?64*1024:128*1024)]]as [string,number][]){
  const id=`EXT-${String(index+1).padStart(2,'0')}-${cohort}`
  const own={id,graphId:entry.id,cohort,specification:entry.specification,
   budget:{cpus:3,memoryBytes:4*1024**3,workBytes,wallSeconds:1080,requireHardStorageLimit:true,origin:'Prospectively bounded aggregate Helix client/controller and Slurm development contrast'},
   prospectiveDecisionUuid:randomUUID(),allowWorkOnlyOracle:true,
   unboundBundlePath:`${guestRoot}/campaign/${namespace}/${entry.id}/unbound-bundle.json`,
   unboundFileHashes:Object.fromEntries(Object.entries(bundle.files).map(([n,v])=>[n,S.sha256(v)])),
   sourceInputPath:`${guestRoot}/campaign/${namespace}/${entry.id}/source.pdb`,sourceInputSha256:S.sha256(input),
   goldCsvPath:`${guestRoot}/campaign/${namespace}/${entry.id}/geometry.csv`,goldCsvSha256:S.sha256(gold),
   evidenceRoot:guestRoot,physicalFeasibilityLabel:null,helixDecision:null,
   decisionScope:'Same strict-target-bound bundle; re-count actual policy/checker/runner before independent full client; actual preparation is repeated inside quota',
   oracleScope:'Real persistent SQLite/bootstrap and preparation, local Python controller, native Slurm tasks, portable export all in one XFS project; preinstalled immutable dependencies and image caches plus experiment-only root telemetry excluded'}
  await fs.writeFile(path.join(output,id+'.json'),JSON.stringify(own,null,2)+'\n');cases.push(own)
 }
}
const sourceHashes:Record<string,string>={}
for(const n of(await fs.readdir(path.join(root,'packages/helix/src/trp'))).filter(n=>n.endsWith('.ts')||n.endsWith('.py.txt')||n==='catalog.json'))sourceHashes['packages/helix/src/trp/'+n]=S.sha256(await fs.readFile(path.join(root,'packages/helix/src/trp',n)))
for(const n of ['full_client.ts','prepare_cases.ts','prepare_extension.ts','drive_campaign.py','audit_cases.py','quota_copy_control.ts','run_copy_controls.py'])sourceHashes['evaluation/trp/campaign-20261012/aggregate-resource-contrasts/'+n]=S.sha256(await fs.readFile(path.join(import.meta.dir,n)))
sourceHashes['script/tesis/provision_remote_strict_profile.py']=S.sha256(await fs.readFile(path.join(root,'script/tesis/provision_remote_strict_profile.py')))
const freeze={schema:'helix-aggregate-client-resource-contrasts/1.0',mode,guestInputNamespace:namespace,frozenAt:new Date().toISOString(),cases,sourceHashes,
 graphCorpusSha256:S.sha256(bytes),uniqueProteins:1,physicalLabelsObservedBeforeFreeze:false,
 prospectiveCohorts:{generousExtension:positiveCount,smallExtension:negativeCount},
 qualifiedEnospcMechanismReviewSha256:S.sha256(await fs.readFile(path.join(import.meta.dir,'copy-causal-controls/mechanism-review.json'))),
 extensionDesign:'Separate post-original-observation extension of unused strict-profile G024 onwards, 128MiB generous and alternating64KiB/128KiB small budgets, frozen before their outputs. Preserve original forty and boundary six, including original unknowns; do not replace or resend terminal cases.',
 actualFeasibleMinimum:null,actualInfeasibleMinimum:null,originalEngineeringMinimumTarget:20,
 retainedThresholds:{falseRejectionMax:.05,acceptedBudgetExceedanceMax:0,countDifferenceMax:0,medianStorageOverestimationMax:.25},
 failedSyscallObserver:'strace -f -Z -yy -ttt; observer executable and client share approved controller cgroup; syscall diagnostic stream is experiment-only root telemetry outside storage project',
 labelRule:'true only native four completed jobs, exact own-input gold, real portable export, actual persistent SQLite and verified quota/cgroup scope; false only terminal I/O failure causally linked by syscall/path/time to actual EDQUOT, or independently qualified quota-reservation ENOSPC with healthy global mount root, or actual kernel OOM; optional ignored cache failures never imply infeasible; otherwise unknown',
 originalHeadOnlyCampaignUnmodified:true,reservedBiologicalMetrics:null,globalCheckpointUtc:'2026-10-13T06:49:00Z'}
await fs.writeFile(path.join(output,'freeze.json'),JSON.stringify(freeze,null,2)+'\n')
console.log(JSON.stringify({mode,cases:cases.length,output,cloudJobsSubmitted:0}))
