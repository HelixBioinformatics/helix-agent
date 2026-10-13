/** Real workflow and tool adapter; simulated remote OS/process boundary only.
 * No Docker, SSH, cloud, model or scientific computation is performed.
 */
import { expect, spyOn, afterAll } from "bun:test"
import { Effect, Fiber, Layer, Queue } from "effect"
import { LayerNode } from "@helix/core/effect/layer-node"
import { AppProcess } from "@helix/core/process"
import fs from "node:fs/promises"
import path from "node:path"
import { TrpWorkflow } from "../../src/trp/workflow"
import { TrpRemote as Remote } from "../../src/trp/remote"
import { TrpRemoteEnforcement as H } from "../../src/trp/remote-enforcement"
import { TrpSpecification as S } from "../../src/trp/specification"
import { TrpResources as R } from "../../src/trp/resources"
import { Question } from "../../src/question"
import { EventV2Bridge } from "../../src/event-v2-bridge"
import { Agent } from "../../src/agent/agent"
import { Truncate } from "../../src/tool/truncate"
import { TrpRunTool } from "../../src/tool/trp"
import { InstanceState } from "../../src/effect/instance-state"
import { SessionID, MessageID } from "../../src/session/schema"
import { testEffect } from "../lib/effect"
import { inventory } from "../trp/resource-fixture"
import source from "../../../../evaluation/trp/development/f3-reference-spec.json"
import budget from "../../../../evaluation/trp/development/f4-budget.json"
const root = path.resolve(import.meta.dir, "../../../..")
let target: Remote.Target, receipt: any, workspace = "", actions: string[] = [], submitted: any
const configured = spyOn(Remote, "configured").mockImplementation(async () => target)
const rootObserver = spyOn(H, "observe").mockImplementation(async () => receipt)
afterAll(() => {configured.mockRestore();rootObserver.mockRestore()})
const ctx = { sessionID:SessionID.make("ses_backend-test"), messageID:MessageID.make("msg_backend-test"), callID:"backend-test",agent:"build",abort:new AbortController().signal,messages:[],metadata:()=>Effect.void,ask:()=>Effect.void }
function response(value: any) { return {command:"simulated remote process boundary",exitCode:0,stdout:Buffer.from(JSON.stringify(value)),stderr:Buffer.alloc(0),stdoutTruncated:false,stderrTruncated:false} }
function observed() {
 const remote={version:Remote.VERSION,fingerprint:target.fingerprint,partition:"helix",controllerCpus:target.strict?1:2,controllerMemoryBytes:target.strict?2*(1024 ** 3):3*(1024 ** 3),secondsRemaining:3600,requiredNodes:[],nodes:[{name:"worker",cpus:2,memoryBytes:8*(1024 ** 3),eligible:true,state:"IDLE",source:"simulated boundary"}]}
 return {...inventory(workspace),remote,...(target.strict?{cpus:target.strict.policy.entitlement.cpus,memoryBytes:target.strict.policy.entitlement.memoryBytes,freeBytes:target.strict.policy.entitlement.workBytes,remoteStrict:target.strict,remoteStrictObservation:receipt}:{}),ok:true}
}
const processLayer=Layer.mock(AppProcess.Service,{run:(_command, options)=>Effect.gen(function*(){
 const req=JSON.parse(String(options?.stdin));actions.push(req.action)
 if(req.action==="observe")return response(observed())
 if(req.action==="start"){submitted=req;return response({ok:true,directory:"/simulated/run",controller:{id:req.id,digest:req.digest}})}
 if(req.action==="status")return response({ok:true,status:"succeeded",controllerAlive:false,id:req.id,digest:req.digest,analysisInventory:observed(),analysisAdmitted:false})
 if(req.action==="admit-analysis")return response({ok:true})
 if(req.action==="export"){
  const csv=yield* Effect.promise(()=>fs.readFile(path.join(root,"evaluation/trp/reference/geometre/geometry.csv"),"utf8"))
  const trace="task_id\tname\tstatus\texit\n1\tSELECT\tCOMPLETED\t0\n2\tGEOMETRY\tCOMPLETED\t0\n"
  const files={...submitted.files,"results/geometry.csv":csv,"trace.tsv":trace,"dry-run/trace.tsv":trace}
  return response({ok:true,files:Object.entries(files).map(([p,v])=>({path:p,bytes:Buffer.byteLength(v as string),sha256:S.sha256(v as string),base64:Buffer.from(v as string).toString("base64")}))})
 }
 return yield* Effect.die(new Error("Unexpected fake remote action:"+req.action))
})})
const it=testEffect(LayerNode.compile(LayerNode.group([TrpWorkflow.node,Question.node,EventV2Bridge.node,Agent.node,Truncate.node]),[[AppProcess.node,processLayer],[R.node,Layer.mock(R.Service,{observe:()=>Effect.die(new Error("Remote route cannot admit the local resource fixture"))})]]))
const pending=Effect.fn(function*(){
 const question=yield* Question.Service,events=yield* EventV2Bridge.Service,asked=yield* Queue.unbounded<void>()
 const off=yield* events.listen(ev=>{if(ev.type===Question.Event.Asked.type)Queue.offerUnsafe(asked,undefined);return Effect.void})
 yield* Effect.addFinalizer(()=>off)
 for(;;){const q=(yield* question.list()).find(q=>q.sessionID===ctx.sessionID);if(q)return q;yield* Queue.take(asked).pipe(Effect.timeout("5 seconds"))}
})
for(const strict of [false,true]) it.instance(`actual workflow/tool writes ${strict?"co-located strict":"SSH"} backend from verified execution`,()=>Effect.gen(function*(){
 workspace=yield* InstanceState.directory;actions=[]
 const policy:any={version:H.VERSION,id:"hrs0123456789abcdef",uid:1000,hostname:"simulated-head",bootId:"simulated-boot",target:{host:"127.0.0.1",port:22,user:"ubuntu",hostKeyAlias:"simulated",root:path.join(workspace,"remote"),partition:"helix",numericalProfile:"haswell-single-thread"},filesystem:{mountPoint:workspace,uuid:"simulated-xfs",device:1,projectId:142,hardBytes:budget.workBytes},paths:{allocationRoot:path.join(workspace,"allocation"),clientWorkspace:workspace,remoteRoot:path.join(workspace,"remote"),temporaryRoot:path.join(workspace,"tmp"),exportRoot:path.join(workspace,"export"),clientStateRoot:path.join(workspace,"state"),clientCacheRoot:path.join(workspace,"cache")},controller:{cgroup:"helix-strict-hrs0123456789abcdef.service",cpus:1,memoryBytes:2*(1024 ** 3),swapBytes:0},entitlement:{cpus:3,memoryBytes:4*(1024 ** 3),workBytes:budget.workBytes,wallSeconds:budget.wallSeconds},checker:{path:H.checkerPath,sha256:H.checkerSha256},samplePath:"/run/helix-remote-strict/hrs0123456789abcdef.sample.json"}
 const policyRaw=S.canonical(policy),checkedAt=Date.now()/1000,quota={projectId:142,usedBytes:4096,hardBytes:budget.workBytes,reportSource:`#142 4 0 ${budget.workBytes/1024} 0 [------]\n`,stateSource:"Accounting: ON\nEnforcement: ON\n",treeCheckExitCode:0,treeCheckStdout:"",treeCheckStderr:""}
 const allocation:any={version:H.VERSION,policyPath:"/run/helix-remote-strict/hrs0123456789abcdef.json",policySha256:S.sha256(policyRaw),policy,targetFingerprint:"f".repeat(64)}
 const sampleRaw=S.canonical({version:"trp-remote-strict-sample/1.0.0",policySha256:allocation.policySha256,bootId:policy.bootId,observedAt:checkedAt,quota})
 receipt={version:H.VERSION,policy,policySha256:allocation.policySha256,policyRaw,sampleRaw,sampleSha256:S.sha256(sampleRaw),checkedAt,role:"client",host:policy.hostname,cwd:workspace,membership:"0::/"+policy.controller.cgroup,parentMembership:"0::/"+policy.controller.cgroup,transport:"co-located-python",currentUsageIsSubtractedFromEntitlement:false,entitlement:policy.entitlement,cgroup:{"cpu.max":"100000 100000","memory.max":String(2*(1024 ** 3)),"memory.swap.max":"0"},paths:Object.entries(policy.paths).map(([name,path])=>({name,path,device:1,projectId:142,inherit:true})),quota}
 target={config:{version:Remote.VERSION,...policy.target,identityFile:"/simulated/not-read",knownHostsFile:"/simulated/not-read",...(strict?{strictPolicy:allocation.policyPath}:{})},fingerprint:allocation.targetFingerprint,public:{version:Remote.VERSION,...policy.target,fingerprint:allocation.targetFingerprint,...(strict?{strict:allocation,transport:"co-located-python"}:{})},...(strict?{strict:allocation}:{})} as any
 yield* Effect.promise(async()=>{await fs.mkdir(policy.paths.allocationRoot);await fs.copyFile(path.join(root,source.structure.value.path),path.join(workspace,"input.pdb"))})
 const workflow=yield* TrpWorkflow.Service,raw=structuredClone(source);raw.structure.value.path="input.pdb"
 const preview=yield* workflow.prepare(raw,root,ctx.sessionID,budget)
 const tool=yield* (yield* TrpRunTool).init(),question=yield* Question.Service
 const fiber=yield* tool.execute({id:preview.id,digest:preview.digest},ctx).pipe(Effect.forkScoped)
 const request=yield* pending();expect(request.questions[0].question).toContain(preview.digest)
 yield* question.reply({requestID:request.id,answers:[["Aprobar y ejecutar"]]})
 const result=yield* Fiber.join(fiber);const payload=JSON.parse(result.output)
 const run=yield* Effect.promise(async()=>JSON.parse(await fs.readFile(path.join(payload.directory,"run.json"),"utf8")))
 const events=yield* Effect.promise(async()=>(await fs.readFile(path.join(payload.directory,"events.jsonl"),"utf8")).trim().split("\n").map(l=>JSON.parse(l)))
 const execution=JSON.parse(submitted.files["execution.json"]),expected=strict?H.BACKEND:Remote.VERSION
 expect(execution.backend).toBe(expected);expect(payload.backend).toBe(expected);expect(run.backend).toBe(expected)
 expect(events.find(e=>e.outcome==="completed").detail.backend).toBe(expected)
 expect(payload.evidence.manifestSha256).toMatch(/^[0-9a-f]{64}$/)
 expect(actions).toEqual(["observe","observe","start","status","admit-analysis","export"])
 const out={kind:"functional workflow metadata regression with simulated OS/process boundary",strict,actualBackend:execution.backend,resultBackend:payload.backend,runBackend:run.backend,completionBackend:events.find(e=>e.outcome==="completed").detail.backend,actions,sourcePreparedDigest:preview.digest,evidencePacked:true,humanApproval:false,scientificExecution:false,rootEnforcementObserved:false}
 if (process.env.TRP_BACKEND_TEST_OUTPUT) yield* Effect.promise(()=>fs.writeFile(path.join(process.env.TRP_BACKEND_TEST_OUTPUT!, `functional-${strict?"strict":"ssh"}.json`),JSON.stringify(out,null,2)+"\n"))
}),30000)
