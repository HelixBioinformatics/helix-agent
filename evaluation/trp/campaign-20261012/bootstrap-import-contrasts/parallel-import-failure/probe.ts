import fs from "node:fs/promises";
import path from "node:path";
const repo=process.env.PROBE_REPO!;
let networkAttempts=0;
globalThis.fetch=async()=>{networkAttempts++;throw new Error("Network disabled in local bootstrap probe")};
const load=(file:string)=>import(path.join(repo,file));
const mode=process.argv[2];
const step=(name:string)=>console.log("STEP:"+name);
if(mode!=="parallel"){
 step("global");await load("packages/core/src/global.ts");
 step("fs-util");await load("packages/core/src/fs-util.ts");
 step("bootstrap");await load("packages/helix/src/project/bootstrap.ts");
}
step("application-imports");
const [{TrpWorkflow},{Agent},{InstanceStore},{InstanceBootstrap},{Question},{EventV2Bridge},{Truncate},{Database},{LayerNode},effects]=await Promise.all([
 load("packages/helix/src/trp/workflow.ts"),load("packages/helix/src/agent/agent.ts"),
 load("packages/helix/src/project/instance-store.ts"),load("packages/helix/src/project/bootstrap.ts"),
 load("packages/helix/src/question/index.ts"),load("packages/helix/src/event-v2-bridge.ts"),
 load("packages/helix/src/tool/truncate.ts"),load("packages/core/src/database/database.ts"),
 load("packages/core/src/effect/layer-node.ts"),load("packages/core/node_modules/effect/dist/index.js"),
]);
const {Effect}=effects;
step("layer-build");
const group=LayerNode.group([TrpWorkflow.node,Agent.node,InstanceStore.node,InstanceBootstrap.node,Question.node,EventV2Bridge.node,Truncate.node,Database.node]);
const layer=mode==="cli-builder"?(await load("packages/helix/src/effect/app-node-builder-v1.ts")).AppNodeBuilderV1.build(group):LayerNode.compile(group,[[InstanceStore.bootstrapNode,InstanceBootstrap.node]]);
step("instance-provide");
const result=await Effect.runPromise(Effect.gen(function*(){
 const store=yield* InstanceStore.Service;
 return yield* store.provide({directory:process.cwd()},Effect.gen(function*(){
  const workflow=yield* TrpWorkflow.Service,agent=yield* Agent.Service,question=yield* Question.Service;
  const {db}=yield* Database.Service;
  yield* db.run("CREATE TABLE IF NOT EXISTS bootstrap_local_probe (marker TEXT PRIMARY KEY)");
  yield* db.run("INSERT OR REPLACE INTO bootstrap_local_probe VALUES ('persistent-no-model-probe')");
  return {workflowPrepare:typeof workflow.prepare,agentService:!!agent,questionService:!!question,database:Database.path(),databaseInMemory:Database.path()===":memory:",networkAttempts};
 }));
}).pipe(Effect.provide(layer),Effect.scoped));
step("db-read-after-disposal");
const data=await fs.readFile(result.database);console.log("PROBE_RESULT:"+JSON.stringify({...result,sqliteHeader:data.subarray(0,16).toString(),databaseBytes:data.length}));
process.exit(0);
