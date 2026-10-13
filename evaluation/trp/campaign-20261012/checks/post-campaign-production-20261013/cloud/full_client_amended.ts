/** Actual Helix prepare/run/bootstrap/export under the operator's strict policy.
 * Only the independently marked oracle may bypass a work-reservation rejection.
 * All other decisions and every Linux/root-policy verifier remain unchanged.
 */
import fs from "node:fs/promises"
import path from "node:path"
import { mock } from "bun:test"
import { Cause, Effect, Fiber, Queue } from "../../../../../../packages/core/node_modules/effect/dist/index.js"
import { LayerNode } from "../../../../../../packages/core/src/effect/layer-node"
import { AppProcess } from "../../../../../../packages/core/src/process"
import { TrpResources as R } from "../../../../../../packages/helix/src/trp/resources"
import { TrpRemote as Remote } from "../../../../../../packages/helix/src/trp/remote"
import { TrpSpecification as S } from "../../../../../../packages/helix/src/trp/specification"
import { TrpNextflow as N } from "../../../../../../packages/helix/src/trp/nextflow"

async function main(){
const [casePath]=process.argv.slice(2)
if(!casePath)throw new Error("Supply a prospectively frozen owner case")
const item=JSON.parse(await fs.readFile(casePath,"utf8"))
const root=path.resolve(import.meta.dir,"../../../../../..")
const target=await Remote.configured()
if(!target?.strict)throw new Error("Actual strict co-located allocation is required")
const policy=target.strict.policy
if(process.cwd()!==policy.paths.clientWorkspace)throw new Error("Full client cwd differs")
if(item.budget.workBytes!==policy.entitlement.workBytes)throw new Error("Frozen budget differs from kernel policy")
const emit=(kind:string,value:unknown)=>console.log(kind+":"+JSON.stringify(value))
const rawBundle=JSON.parse(await fs.readFile(item.unboundBundlePath,"utf8"))
for(const [name,hash]of Object.entries(item.unboundFileHashes))
 if(S.sha256(rawBundle.files[name])!==hash)throw new Error("Unbound reference bytes changed")
const bound=structuredClone(rawBundle)
Remote.bind(bound,target,item.prospectiveDecisionUuid)
const demand=R.count(bound.files)
const processLayer=LayerNode.compile(AppProcess.node)
const inventory=await Effect.runPromise(Effect.gen(function*(){
 const process=yield* AppProcess.Service
 return yield* Remote.observe(target,process.run)
}).pipe(Effect.provide(processLayer),Effect.scoped))
const originalAdmit=R.admit
const realDecision=originalAdmit(demand,inventory,item.budget)
emit("HELIX_REAL_ADMISSION",{case:item.id,demand,inventory,decision:realDecision,
 sourceSha256:S.sha256(await fs.readFile(path.join(root,"packages/helix/src/trp/resources.ts"))),
 policySha256:target.strict.policySha256,target:target.public,preparedReferenceOnly:true,
 oracleLabel:null,source:"Unmodified production R.count/admit on same strictly bound bundle before independent execution"})
const workOnly = !realDecision.accepted && realDecision.rejections.length>0 && realDecision.rejections.every((r:any)=>
 ["budget-insufficient","capacity-insufficient"].includes(r.code) && r.resource==="workBytes")
const allowOverride=item.allowWorkOnlyOracle===true && workOnly
if(allowOverride && (!realDecision.rejections.length || realDecision.rejections.some((r:any)=>
 !["budget-insufficient","capacity-insufficient"].includes(r.code) || r.resource!=="workBytes")))
 throw new Error("Counterfactual override requires only exact work-reservation rejection")
if(!allowOverride&&!realDecision.accepted)throw new Error("Ordinary full client must respect the actual decision")
const gateRecords:any[]=[]
if(allowOverride){
 const originalModule=await import("../../../../../../packages/helix/src/trp/resources")
 const override=(d:any,i:any,b:any,now?:Date)=>{
  const actual=originalAdmit(d,i,b,now)
  const eligible=!actual.accepted && actual.rejections.length>0 && actual.rejections.every((r:any)=>["budget-insufficient","capacity-insufficient"].includes(r.code)&&r.resource==="workBytes")
  const record={actual,overrideUsed:eligible,scope:"Independent executor only; actual decision retained; no policy/capacity/runtime override"}
  gateRecords.push(record);emit("HELIX_ORACLE_GATE",record)
  return eligible?{...actual,accepted:true,rejections:[]}:actual
 }
 mock.module(path.join(root,"packages/helix/src/trp/resources.ts"),()=>({
  ...originalModule,admit:override,TrpResources:{...R,admit:override},
 }))
}
emit("HELIX_ORACLE_MODE",{case:item.id,executionOracleForcedOnly:allowOverride,realAccepted:realDecision.accepted,scope:"Unmodified real decision retained before counterfactual filesystem/bootstrap/execution"})
// Every byte from initial input copy, persistent SQLite/bootstrap and prepared
// tool artifacts to the actual requested portable export is now in the quota.
await fs.copyFile(item.sourceInputPath,path.join(policy.paths.clientWorkspace,"input.pdb"))
if(S.sha256(await fs.readFile(path.join(policy.paths.clientWorkspace,"input.pdb")))!==item.sourceInputSha256)
 throw new Error("Real staged source differs")
await fs.writeFile(path.join(policy.paths.clientWorkspace,"helix.json"),JSON.stringify({
 $schema:"https://helixbiolab.github.io/helix-agent/config.json",plugin:[],share:"disabled",
}))
// Respect production bootstrap dependency order; concurrent entry imports can
// expose ESM cycles before FSUtil.node exists. No service is mocked here.
await import("../../../../../../packages/core/src/global")
await import("../../../../../../packages/core/src/fs-util")
await import("../../../../../../packages/helix/src/project/bootstrap")
const [{TrpWorkflow},{TrpPrepareTool,TrpRunTool},{Question},{EventV2Bridge},{Agent},{Truncate},
 {InstanceStore},{InstanceBootstrap},{SessionID,MessageID}]=await Promise.all([
 import("../../../../../../packages/helix/src/trp/workflow"),import("../../../../../../packages/helix/src/tool/trp"),
 import("../../../../../../packages/helix/src/question"),import("../../../../../../packages/helix/src/event-v2-bridge"),
 import("../../../../../../packages/helix/src/agent/agent"),import("../../../../../../packages/helix/src/tool/truncate"),
 import("../../../../../../packages/helix/src/project/instance-store"),import("../../../../../../packages/helix/src/project/bootstrap"),
 import("../../../../../../packages/helix/src/session/schema"),
])
const layer=LayerNode.compile(LayerNode.group([TrpWorkflow.node,Question.node,EventV2Bridge.node,Agent.node,Truncate.node,InstanceStore.node]),[
 [InstanceStore.bootstrapNode,InstanceBootstrap.node],
])
let terminal:any
try{
 terminal=await Effect.runPromise(Effect.gen(function*(){
  const store=yield* InstanceStore.Service
  return yield* store.provide({directory:policy.paths.clientWorkspace},Effect.gen(function*(){
   const raw=structuredClone(item.specification);raw.structure.value.path="input.pdb"
   const ctx={sessionID:SessionID.make("ses_postrepair_"+item.id),messageID:MessageID.make("msg_postrepair_"+item.id),
    callID:"post-repair-integration-driver",agent:"build",abort:new AbortController().signal,messages:[],metadata:()=>Effect.void,ask:()=>Effect.void}
   const prepare=yield* (yield* TrpPrepareTool).init(),run=yield* (yield* TrpRunTool).init()
   const prepared=yield* prepare.execute({specification:S.parse(raw),evidence_root:item.evidenceRoot,budget:item.budget},ctx)
   const preview=JSON.parse(prepared.output)
   if(S.canonical(preview.admission.demand)!==S.canonical(demand))throw new Error("Actual prepared demand differs from prospective strict-bound producer demand")
   if(S.canonical(preview.budget)!==S.canonical(item.budget))throw new Error("Actual budget differs from prospective budget")
   emit("HELIX_DEMAND_REPRODUCED",{case:item.id,prospective:demand,actual:preview.admission.demand,equal:true,files:preview.files})
   console.log("HELIX_OWNED_UUID:"+prepared.metadata.id)
   emit("HELIX_FULL_PREPARED",{...prepared.metadata,executionOracleForcedOnly:allowOverride})
   const question=yield* Question.Service,events=yield* EventV2Bridge.Service,asked=yield* Queue.unbounded<void>()
   const off=yield* events.listen(event=>{if(event.type===Question.Event.Asked.type)Queue.offerUnsafe(asked,undefined);return Effect.void})
   yield* Effect.addFinalizer(()=>off)
   const fiber=yield* run.execute(prepared.metadata,ctx).pipe(Effect.forkScoped)
   for(;;){
    const q=(yield* question.list()).find(q=>q.sessionID===ctx.sessionID)
    if(!q){yield* Queue.take(asked).pipe(Effect.timeout("15 seconds"));continue}
    if(!q.questions[0].question.includes(prepared.metadata.digest))throw new Error("Actual approval digest differs")
    yield* question.reply({requestID:q.id,answers:[["Aprobar y ejecutar"]]});break
   }
   const executed=yield* Fiber.join(fiber)
   return {prepared:prepared.metadata,executed:executed.metadata}
  }))
 }).pipe(Effect.provide(layer),Effect.scoped))
 const result=terminal.executed.directory
 const actual=await fs.readFile(path.join(result,"results/geometry.csv"))
 const gold=item.goldCsvPath===null?null:await fs.readFile(item.goldCsvPath)
 if(gold!==null && (S.sha256(actual)!==item.goldCsvSha256||!actual.equals(gold)))throw new Error("Actual full-client result differs from its fixed input gold")
 const destination=path.join(policy.paths.exportRoot,"portable-evidence")
 await fs.cp(path.join(result,"evidence"),destination,{recursive:true,dereference:true,errorOnExist:true,force:false})
 const verify=Bun.spawn(["python3",path.join(destination,"verify.py"),destination],{stdout:"pipe",stderr:"pipe"})
 const [exitCode,out,err]=await Promise.all([verify.exited,new Response(verify.stdout).text(),new Response(verify.stderr).text()])
 const portableVerification=JSON.parse(out)
 if((exitCode||err.trim()||!portableVerification.ok)&&!allowOverride)throw new Error("Actual ordinary portable export did not verify: "+out+err)
 const outcome={case:item.id,status:"succeeded",executionOracleForcedOnly:allowOverride,realDecision,
  gateRecords,terminal,actualCsvSha256:S.sha256(actual),goldCsvSha256:item.goldCsvSha256,numericalEqual:gold!==null?true:null,
  portableExportDirectory:destination,portableVerification,portableVerifierExitCode:exitCode,portableVerifierStderr:err,
  ordinaryExportRequired:!allowOverride,independentCounterfactualAuditRequired:allowOverride,syntheticApproval:true,humanEvaluation:false,
  persistentSqliteExpected:true,fullSourceSha256:S.sha256(await fs.readFile(import.meta.filename))}
 await fs.writeFile(path.join(policy.paths.clientWorkspace,"full-client-result.json"),JSON.stringify(outcome,null,2)+"\n")
 emit("HELIX_FULL_TERMINAL",outcome)
}catch(error){
 emit("HELIX_FULL_FAILURE",{case:item.id,cause:String(error),executionOracleForcedOnly:allowOverride,
  gateRecords,realDecision,terminal:terminal??null,humanEvaluation:false})
 throw error
}

}
try{await main()}catch(error:any){
 console.log("HELIX_CLIENT_THROW:"+JSON.stringify({pid:process.pid,failedAtEpochSeconds:Date.now()/1000,name:error?.name,code:error?.code,errno:error?.errno,syscall:error?.syscall,path:error?.path,dest:error?.dest,message:error?.message,cause:String(error),stack:error?.stack}));throw error
}
