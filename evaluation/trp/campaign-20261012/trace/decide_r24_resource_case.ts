/** The production admisor, fed an actual fresh observer snapshot. No oracle. */
import fs from "node:fs/promises"
import path from "node:path"
import { TrpResources as R } from "../../../../packages/helix/src/trp/resources"
import { TrpSpecification as S } from "../../../../packages/helix/src/trp/specification"
import { TrpRemote as Remote } from "../../../../packages/helix/src/trp/remote"
const [planPath,id,inventoryPath] = process.argv.slice(2)
if (!planPath || !id || !inventoryPath) throw new Error("Usage: PLAN CASE_ID FRESH_INVENTORY")
const plan=JSON.parse(await fs.readFile(planPath,"utf8"))
const item=plan.cases.find((c:any)=>c.id===id)
if (!item) throw new Error("Unfrozen case")
const rawInventory=JSON.parse(await fs.readFile(inventoryPath,"utf8"))
const inventory=rawInventory.ok===true?Remote.inventory(rawInventory):rawInventory
const files:Record<string,string>={}
for(const [name,hash]of Object.entries(item.files)){
 const content=await fs.readFile(path.join(path.dirname(planPath),item.inputDirectory,name),"utf8")
 if(S.sha256(content)!==hash)throw new Error("Prepared input changed: "+name)
 files[name]=content
}
const demand=R.count(files)
if(S.canonical(demand)!==S.canonical(item.demand))throw new Error("Frozen production demand changed")
const decision=R.admit(demand,inventory,item.budget)
const resourceSource=path.resolve(import.meta.dir,"../../../../packages/helix/src/trp/resources.ts")
const actualResourceSourceSha256=S.sha256(await fs.readFile(resourceSource))
if(actualResourceSourceSha256!==plan.sources["packages/helix/src/trp/resources.ts"])
 throw new Error("Production admisor source changed after freeze")
console.log(JSON.stringify({case:id,planSha256:S.sha256(await fs.readFile(planPath)),
  observerSnapshotSha256:S.sha256(await fs.readFile(inventoryPath)),actualResourceSourceSha256,decision,
  source:"Actual production TrpResources.admit, not independent feasibility oracle",
  physicalFeasibilityLabel:null}))
