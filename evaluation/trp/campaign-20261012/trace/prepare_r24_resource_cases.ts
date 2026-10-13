/** Freeze resource contrasts without submitting a cloud job or guessing labels.
 * Run locally after the production revision is fixed, with the operator's
 * HELIX_TRP_REMOTE pointing to Lab2. Output must be a new directory.
 */
import fs from "node:fs/promises"
import path from "node:path"
import { randomUUID } from "node:crypto"
import { TrpNextflow as N } from "../../../../packages/helix/src/trp/nextflow"
import { TrpRemote as Remote } from "../../../../packages/helix/src/trp/remote"
import { TrpSpecification as S } from "../../../../packages/helix/src/trp/specification"
import { TrpResources as R } from "../../../../packages/helix/src/trp/resources"

const root = path.resolve(import.meta.dir, "../../../..")
const output = process.argv[2] && path.resolve(process.argv[2])
if (!output) throw new Error("Supply a new output directory; no cloud jobs are submitted")
await fs.mkdir(output, { recursive: false })
const target = await Remote.configured()
if (!target || target.config.numericalProfile !== "haswell-single-thread")
  throw new Error("An actual owner-controlled remote target with the fixed numerical profile is required")
const corpusPath = path.join(root, "evaluation/trp/campaign-20261012/contract-corpus/graphs.json")
const oldFreeze = JSON.parse(await fs.readFile(path.join(path.dirname(corpusPath), "freeze.json"), "utf8"))
const corpusBytes = await fs.readFile(corpusPath)
if (S.sha256(corpusBytes) !== oldFreeze.files.find((x: any) => x.path === "graphs.json").sha256)
  throw new Error("Frozen graph corpus changed")
const corpus = JSON.parse(corpusBytes.toString())
const MiB = 1024 ** 2
const small = [64*1024, 128*1024, 256*1024, 512*1024, MiB, 2*MiB, 4*MiB, 8*MiB, 12*MiB, 16*MiB]
const cases: any[] = []
for (const [index, source] of corpus.valid.slice(0, 20).entries()) {
  const base = await N.prepare(source.specification, root, root)
  const id = randomUUID()
  Remote.bind(base, target, id)
  const gold = path.join(output,"gold",source.id)
  await fs.mkdir(gold,{recursive:true})
  await fs.writeFile(path.join(gold,"2xqh.pdb"),base.files["selection.pdb"])
  const intervals=(values:any[])=>values.map(v=>`${v.start}_${v.end}`).join(",")
  const argv=["docker","run","--rm","--network","none","--read-only","--cpus","2","--memory","2g",
    "--memory-swap","2g","--tmpfs","/tmp:rw,nosuid,size=256m",
    "-e","OPENBLAS_CORETYPE=Haswell","-e","OPENBLAS_NUM_THREADS=1","-e","OMP_NUM_THREADS=1","-e","MKL_NUM_THREADS=1",
    "-v",`${gold}:/work`,base.image,"single","/work/2xqh.pdb",base.spec.chain.value,"/work/geometry.csv",
    intervals(base.spec.units.value.ranges)]
  if(base.spec.insertions.value.length)argv.push("-ins_def",intervals(base.spec.insertions.value))
  const process=Bun.spawn(argv,{stdout:"pipe",stderr:"pipe"})
  const [exitCode,stdout,stderr]=await Promise.all([process.exited,new Response(process.stdout).text(),new Response(process.stderr).text()])
  await fs.writeFile(path.join(gold,"execution.json"),JSON.stringify({argv,exitCode,stdout,stderr},null,2)+"\n")
  if(exitCode!==0)throw new Error("Manual same-input reference failed: "+source.id)
  const goldCsvSha256=S.sha256(await fs.readFile(path.join(gold,"geometry.csv")))
  for (const [cohort, workBytes] of [["generous", 64*MiB], ["small", small[index%small.length]]] as const) {
    const caseId=`R24-${index+1}-${cohort}`
    const ownId=randomUUID()
    const files={...base.files,"nextflow.config":base.files["nextflow.config"].replaceAll(`helix:${id}`,`helix:${ownId}`)}
    const inputDirectory=path.join(output,caseId)
    await fs.mkdir(inputDirectory)
    const hashes:Record<string,string>={}
    for(const [name,value]of Object.entries(files)){
      await fs.writeFile(path.join(inputDirectory,name),value,{flag:"wx"})
      hashes[name]=S.sha256(value)
    }
    cases.push({ id:caseId,graphId: source.id,cohort,inputDirectory:caseId,
      runComment:`helix:${ownId}`,files:hashes,goldCsvPath:`gold/${source.id}/geometry.csv`,goldCsvSha256,
      demand:R.count(files), budget: { cpus: 3, memoryBytes: 4*1024**3, workBytes, wallSeconds: 1080,
        requireHardStorageLimit: false, origin: "Prospective operator-controlled resource contrast" },
      physicalFeasibilityLabel: null, helixDecision: null, oracleResult: null })
  }
}
const sources: Record<string,string> = {}
for (const name of (await fs.readdir(path.join(root,"packages/helix/src/trp"))).filter(name=>name.endsWith(".ts")||name.endsWith(".py.txt")||name==="catalog.json"))
  sources[`packages/helix/src/trp/${name}`] = S.sha256(await fs.readFile(path.join(root, "packages/helix/src/trp", name)))
for (const name of ["prepare_r24_resource_cases.ts", "decide_r24_resource_case.ts", "run_r24_independent.py", "drive_r24_campaign.py"])
  sources[`evaluation/trp/campaign-20261012/trace/${name}`] = S.sha256(await fs.readFile(path.join(import.meta.dir, name)))
const plan = { schema: "helix-r24-independent-head-workspace/1.0", frozenAt: new Date().toISOString(),
  graphCorpusSha256: S.sha256(corpusBytes), uniqueProteins: 1, target: target.public,
  cases, sources, physicalLabelsObservedBeforeFreeze: false,
  scope: "Development admission contrast of the exact frozen Nextflow task graph in an independently limited head workspace; not held-out scientific R2.4 or aggregate client plus remote R2.2.",
  storageUnit: "XFS allocated project blocks including staged inputs, work/logs and materialized portable run copy. Operator supervisor evidence and pre-existing image/Nextflow caches are outside this scope.",
  oracle: "Execute under the quota even after Helix rejection; classify only from exact CSV, effective limits and quota/runtime outcomes. No label from estimator or cohort name.",
  protocolThresholdsRetained: { falseRejectionMax: 0.05, acceptedBudgetExceedanceMax: 0 },
  prospectiveCohorts: { generous: 20, small: 20 },
  actualFeasibleMinimum: 20, actualInfeasibleMinimum: 20,
  insufficientActualGroupRule: "Report missing minimum; any extension must be a new prospectively frozen batch, preserving every initial outcome.",
  executionOrder: cases.map(c => c.id), globalDeadlineUtc: "2026-10-13T02:59:00Z",
  biologicalCorrectness: "not_established", scientificR24Complete: false }
await fs.writeFile(path.join(output, "freeze.json"), JSON.stringify(plan,null,2)+"\n", {flag:"wx"})
console.log(JSON.stringify({output,cases:cases.length,cloudJobsSubmitted:0,physicalLabelsInferred:0}))
