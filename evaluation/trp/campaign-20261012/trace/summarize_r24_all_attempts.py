#!/usr/bin/env python3
"""Independently audit and combine original resource IDs without hiding attempts."""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def auditor(name):
    spec = importlib.util.spec_from_file_location(name, HERE/(name+".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.audit


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--original",type=Path,required=True)
    p.add_argument("--continuation",type=Path)
    p.add_argument("--output",type=Path,required=True)
    a = p.parse_args()
    base = a.original.resolve()
    original = read(base/"inputs/freeze.json")
    reports = [{"directory":str(base),"report":auditor("audit_r24_results")(base)}]
    if a.continuation:
        extra = a.continuation.resolve()
        plan = read(extra/"inputs/freeze.json")
        if plan["originalFreezeSha256"]!=sha(base/"inputs/freeze.json"):
            raise ValueError("Continuation belongs to another original prospective cohort")
        if plan["originalProgressSha256"]!=sha(base/"progress.json"):
            raise ValueError("Original progress changed after operational amendment")
        if plan["originalCleanupSha256"]!=sha(base/"checkpoint-cleanup.json"):
            raise ValueError("Original cleanup changed after operational amendment")
        old={c["id"]:c for c in original["cases"]}
        for c in plan["cases"]:
            initial=old[c["id"]]
            if c["budget"]!=initial["budget"] or c["goldCsvSha256"]!=initial["goldCsvSha256"]:
                raise ValueError("Operational amendment changed scenario budget or numerical truth")
            for name,expected in initial["files"].items():
                if name not in {"remote_target.json","execution.json","nextflow.config"} and c["files"][name]!=expected:
                    raise ValueError("Operational amendment changed a scientific input")
        reports.append({"directory":str(extra),"report":auditor("audit_r24_continuation")(extra)})
    selected = {c["id"]:{"id":c["id"],"physicalFeasibilityLabel":None,"helixAccepted":None,"attempts":[]} for c in original["cases"]}
    actual_attempts=0
    preserved_unknown=0
    for revision in reports:
        directory=Path(revision["directory"])
        progress={r["id"]:r for r in read(directory/"progress.json")["cases"]}
        for row in revision["report"]["cases"]:
            item=selected[row["id"]]
            observed=progress[row["id"]]
            row={**row,"revisionDirectory":str(directory),"attemptDispatched":bool(observed.get("dispatched"))}
            item["attempts"].append(row)
            if observed.get("dispatched"):
                actual_attempts+=1
                preserved_unknown+=row["physicalFeasibilityLabel"] is None and row["state"] in {"recovered","unknown-supervisor-stopped-without-result"}
            if row["physicalFeasibilityLabel"] is not None:
                if item["physicalFeasibilityLabel"] is not None:
                    raise ValueError("An already conclusive original case was rerun; do not replace or count twice")
                item.update(physicalFeasibilityLabel=row["physicalFeasibilityLabel"],helixAccepted=row["helixAccepted"],
                            conclusiveRevision=str(directory),oracleResultSha256=row["oracleResultSha256"])
    rows=list(selected.values())
    feasible=[r for r in rows if r["physicalFeasibilityLabel"] is True]
    infeasible=[r for r in rows if r["physicalFeasibilityLabel"] is False]
    known=feasible+infeasible
    false_rejections=sum(not r["helixAccepted"] for r in feasible)
    report={"schema":"helix-r24-all-original-attempts-summary/1.0","verified":True,
            "summarizedAtUtc":datetime.now(timezone.utc).isoformat(),"originalFreezeSha256":sha(base/"inputs/freeze.json"),
            "plannedOriginalCases":len(original["cases"]),"actualDispatchedAttempts":actual_attempts,
            "preservedUnknownAttempts":preserved_unknown,"empiricallyFeasible":len(feasible),
            "empiricallyInfeasible":len(infeasible),"originalCasesUnresolved":len(rows)-len(known),
            "scopedFalseRejections":false_rejections,"scopedFalseRejectionRate":false_rejections/len(feasible) if feasible else None,
            "scopedAccuracy":sum(r["helixAccepted"]==r["physicalFeasibilityLabel"] for r in known)/len(known) if known else None,
            "actualGroupMinimaSatisfied":len(feasible)>=20 and len(infeasible)>=20,
            "scope":original["scope"],"storageUnit":original["storageUnit"],"uniqueProteins":1,
            "scientificR24Complete":False,"aggregateRemotePlusRealClientR22Enforced":False,
            "scientificR24FalseRejectionRate":None,"allOriginalCasesEmpiricallyObserved":len(known)==len(rows),
            "threshold":original["protocolThresholdsRetained"]["falseRejectionMax"],
            "scopedThresholdMet":false_rejections/len(feasible)<=0.05 if feasible else None,
            "interpretation":"Independent head-workspace oracle includes portable duplication but excludes actual client preparation/export. Its counterfactual matrix diagnoses admission conservatism for this adapted scope; it does not establish a protocol end-to-end false-rejection metric. All original attempts and unknowns are retained.",
            "independentAudits":reports,"cases":rows,"summarySourceSha256":sha(Path(__file__))}
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
    print(json.dumps({k:v for k,v in report.items() if k not in {"cases","independentAudits"}}))


if __name__=="__main__":main()
