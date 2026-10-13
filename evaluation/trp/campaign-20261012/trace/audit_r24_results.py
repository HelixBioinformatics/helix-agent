#!/usr/bin/env python3
"""Read-only second calculation of the frozen head-workspace resource matrix."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import tarfile


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def audit(base):
    plan=read(base/"inputs/freeze.json")
    progress=read(base/"progress.json")
    if progress["freezeSha256"]!=sha(base/"inputs/freeze.json"):
        raise ValueError("Progress belongs to a different freeze")
    planned={row["id"]:row for row in plan["cases"]}
    if len(planned)!=40 or any(c["physicalFeasibilityLabel"] is not None for c in planned.values()):
        raise ValueError("Prospective forty-case plan changed its unknown physical labels")
    if len({r["id"]for r in progress["cases"]})!=len(progress["cases"]):
        raise ValueError("Repeated original case must not inflate the denominator")
    rows=[]
    for recorded in progress["cases"]:
        cid=recorded["id"]
        expected=planned[cid]
        row={"id":cid,"state":recorded["status"],"physicalFeasibilityLabel":None,
             "helixAccepted":recorded.get("helixAccepted"),"oracleScope":"head-workspace-development"}
        if recorded["status"]!="recovered":
            rows.append(row)
            continue
        case=base/cid
        if sha(case/"retained-result.tar.gz")!=recorded["resultArchiveSha256"]:
            raise ValueError("Transported result archive changed: "+cid)
        path=case/cid/"oracle-result.json"
        if sha(path)!=recorded["oracleResultSha256"]:
            raise ValueError("Oracle result changed: "+cid)
        result=read(path)
        if result["planSha256"]!=sha(base/"inputs/freeze.json") or result["budget"]!=expected["budget"]:
            raise ValueError("Oracle altered frozen case or budget")
        decision=read(case/"decision.json")
        if decision!=result["helixDecision"] or decision["decision"]["accepted"] is not recorded.get("helixAccepted"):
            raise ValueError("Recorded Helix admission differs from externally anchored actual decision")
        if decision["planSha256"]!=sha(base/"inputs/freeze.json") or decision["observerSnapshotSha256"]!=sha(case/"inventory.json"):
            raise ValueError("Admission belongs to another frozen case or observer snapshot")
        if decision["actualResourceSourceSha256"]!=plan["sources"]["packages/helix/src/trp/resources.ts"]:
            raise ValueError("Admission source is not the frozen production admisor")
        if result["nativeCleanup"].get("remaining")!=[]:
            raise ValueError("Owned job cleanup not independently recorded")
        quota=result["finalQuota"]
        if quota["hardBytes"]!=expected["budget"]["workBytes"] or quota["usedBytes"]>quota["hardBytes"]:
            raise ValueError("Quota differs or declared workspace exceeded approved blocks")
        if "Accounting: ON" not in quota["state"] or "Enforcement: ON" not in quota["state"]:
            raise ValueError("Kernel quota is not observed as enforced")
        label=None
        if result["oracleStatus"]=="exact-output-under-observed-limits":
            controller=[sample["controllerCgroup"]for sample in result["samples"]if sample.get("controllerCgroup")]
            if not controller or any(c.get("cpu.max")!="100000 100000" or c.get("memory.max")!="2147483648" or c.get("memory.swap.max")!="0" for c in controller):
                raise ValueError("Controller actual caps differ")
            if len(result["runtime"])!=2 or any(r["cpuMax"]!="200000 100000" or r["memoryMax"]!="2147483648" or r["swapMax"]!="0" or r["numericalProfile"]!="Haswell" or r["threads"]!="1" for r in result["runtime"]):
                raise ValueError("Scientific actual caps/profile differ")
            if len(result["traces"])!=4 or len({r["native_id"]for r in result["traces"]})!=4 or any(r["status"]!="COMPLETED" or r["exit"]!="0" for r in result["traces"]):
                raise ValueError("Expected four distinct completed native jobs absent")
            if len(result["native"])!=4 or {re.search(r"JobId=(\d+)",raw).group(1) for raw in result["native"]}!={r["native_id"] for r in result["traces"]}:
                raise ValueError("Native scheduler IDs do not bind all four trace records")
            spec_path=base/"inputs"/expected["inputDirectory"]/"specification.json"
            if sha(spec_path)!=expected["files"]["specification.json"]:
                raise ValueError("Frozen workflow graph changed")
            specification=read(spec_path)
            placement={node["id"].upper():plan["target"]["selectNode" if node["operation"]=="pdb.select" else "geometryNode"]
                for node in specification["graph"]["nodes"] if node["operation"] in {"pdb.select","geometre.geometry"}}
            for raw in result["native"]:
                if "JobState=COMPLETED" not in raw or "ExitCode=0:0" not in raw or "Comment="+expected["runComment"] not in raw:
                    raise ValueError("Native scheduler evidence belongs to another run/outcome")
                fields=dict(field.split("=",1) for field in raw.split() if "=" in field)
                process_name=fields["JobName"].removeprefix("nf-")
                if process_name not in placement or fields.get("NodeList")!=placement[process_name] or fields.get("NumCPUs")!="2" or fields.get("MinMemoryNode")!="2G":
                    raise ValueError("Native worker placement or task allocation differs from frozen graph")
            for runtime in result["runtime"]:
                blas=runtime.get("blas",[])
                if not any(b.get("internal_api")=="openblas" and b.get("architecture")=="Haswell" and b.get("num_threads")==1 for b in blas):
                    raise ValueError("Actual OpenBLAS architecture/thread profile not observed")
            actual=case/cid/"retained-workspace/results/geometry.csv"
            gold=base/"inputs"/expected["goldCsvPath"]
            if sha(actual)!=expected["goldCsvSha256"] or actual.read_bytes()!=gold.read_bytes():
                raise ValueError("Correct per-input numerical reference differs")
            label=True
        elif result["oracleStatus"]=="infeasible-observed-staging-quota":
            if result.get("errno")not in [28,122]:
                raise ValueError("Insufficient staging lacks causal errno")
            label=False
        elif result["oracleStatus"]=="infeasible-observed-workspace-quota":
            evidence=result.get("oracleError","")
            causal_files=[]
            # The producer keeps only the last12KiB of aggregated logs. A later
            # normal Nextflow debug tail can hide an earlier causal errno. Read
            # the unmodified externally anchored archive, not an invented label.
            with tarfile.open(case/"retained-result.tar.gz") as archive:
                for member in archive.getmembers():
                    if member.isfile() and "/retained-workspace/" in member.name and (
                        member.name.endswith((".stderr", ".stdout")) or member.name.endswith("/.nextflow.log")):
                        stream=archive.extractfile(member)
                        text=stream.read().decode(errors="replace")
                        if re.search("Disk quota exceeded|No space left on device",text):
                            causal_files.append(member.name)
                            evidence+="\n"+text
            if not re.search("Disk quota exceeded|No space left on device",evidence):
                raise ValueError("Insufficient workspace lacks observed quota failure in complete anchored logs")
            row["causalArchivedLogs"]=causal_files
            label=False
        if label is not result["physicalFeasibilityLabel"] or label is not recorded["physicalFeasibilityLabel"]:
            raise ValueError("Recorded label differs from external engineering oracle")
        row.update(physicalFeasibilityLabel=label,oracleResultSha256=sha(path),
                   usedProjectBytes=quota["usedBytes"],budgetProjectBytes=quota["hardBytes"],
                   elapsedSeconds=result["elapsedSeconds"])
        rows.append(row)
    feasible=[r for r in rows if r["physicalFeasibilityLabel"]is True]
    infeasible=[r for r in rows if r["physicalFeasibilityLabel"]is False]
    known=feasible+infeasible
    return {"schema":"helix-r24-independent-offline-audit/1.0","verified":True,
            "auditedAtUtc":datetime.now(timezone.utc).isoformat(),"freezeSha256":sha(base/"inputs/freeze.json"),
            "progressSnapshotSha256":sha(base/"progress.json"),"planned":40,"recorded":len(rows),
            "empiricallyFeasible":len(feasible),"empiricallyInfeasible":len(infeasible),
            "unknownOrNotYetObserved":40-len(known),"falseRejections":sum(not r["helixAccepted"]for r in feasible),
            "scopedFalseRejectionRate":sum(not r["helixAccepted"]for r in feasible)/len(feasible)if feasible else None,
            "scopedAccuracy":sum(r["helixAccepted"]==r["physicalFeasibilityLabel"]for r in known)/len(known)if known else None,
            "actualGroupMinimaSatisfied":len(feasible)>=20 and len(infeasible)>=20,
            "scientificR24Complete":False,"aggregateRemotePlusRealClientR22Enforced":False,
            "scope":plan["scope"],"unit":plan["storageUnit"],"cases":rows,
            "interpretation":"Same-input execution supplies scoped empirical labels, not the admisor or cohort names. Actual local-client preparation/export is outside this oracle, so scoped false rejections do not establish estimator error on an identical end-to-end storage scope."}


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base",type=Path)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    result=audit(args.base.resolve())
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    print(json.dumps({k:v for k,v in result.items()if k!="cases"}))
