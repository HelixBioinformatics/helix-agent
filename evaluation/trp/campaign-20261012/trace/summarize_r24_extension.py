#!/usr/bin/env python3
"""Keep the original40 matrix separate from the subsequently chosen extension."""
import argparse
from datetime import datetime,timezone
import hashlib
import importlib.util
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument("--original",type=Path,required=True);p.add_argument("--extension",type=Path,required=True);p.add_argument("--output",type=Path,required=True);a=p.parse_args()
 original=a.original.resolve();extension=a.extension.resolve();path=original/"all-original-attempts.json";old=read(path);plan=read(extension/"inputs/freeze.json")
 if sha(path)!=plan["originalAllAttemptsSha256"] or sha(original/"inputs/freeze.json")!=plan["originalFreezeSha256"]:
  raise ValueError("Original observed matrix changed after prospective extension")
 spec=importlib.util.spec_from_file_location("extension_audit",HERE/"audit_r24_extension.py");module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 extra=module.audit(extension)
 originals={r["id"] for r in old["cases"]}
 if any(r["id"] in originals for r in extra["cases"]):raise ValueError("Extension reused original resource case ID")
 feasible=old["empiricallyFeasible"]+extra["empiricallyFeasible"];infeasible=old["empiricallyInfeasible"]+extra["empiricallyInfeasible"]
 rejects=old["scopedFalseRejections"]+extra["falseRejections"]
 old_correct=round(old["scopedAccuracy"]*(old["empiricallyFeasible"]+old["empiricallyInfeasible"]))
 extra_correct=sum(r["helixAccepted"]==r["physicalFeasibilityLabel"]for r in extra["cases"]if r["physicalFeasibilityLabel"] is not None)
 value={"schema":"helix-r24-original-plus-separate-extension/1.0","verified":True,"summarizedAtUtc":datetime.now(timezone.utc).isoformat(),
  "original40SummaryPath":str(path),"original40SummarySha256":sha(path),"original40Counts":{
   "planned":40,"empiricallyFeasible":old["empiricallyFeasible"],"empiricallyInfeasible":old["empiricallyInfeasible"],
   "scopedFalseRejections":old["scopedFalseRejections"],"scopedFalseRejectionRate":old["scopedFalseRejectionRate"],"scopedAccuracy":old["scopedAccuracy"]},
  "extensionFreezeSha256":sha(extension/"inputs/freeze.json"),"extensionChosenAfterObservingOriginalGrid":True,
  "extensionCounts":{"planned":extra["planned"],"empiricallyFeasible":extra["empiricallyFeasible"],"empiricallyInfeasible":extra["empiricallyInfeasible"],
   "unknown":extra["unknownOrNotYetObserved"],"scopedFalseRejections":extra["falseRejections"]},
  "adaptedCombinedCounts":{"planned":40+extra["planned"],"empiricallyFeasible":feasible,"empiricallyInfeasible":infeasible,
   "scopedFalseRejections":rejects,"scopedFalseRejectionRate":rejects/feasible if feasible else None,
   "scopedAccuracy":(old_correct+extra_correct)/(feasible+infeasible)if feasible+infeasible else None,
   "actualGroupMinimaSatisfied":feasible>=20 and infeasible>=20},
  "scope":old["scope"],"storageUnit":old["storageUnit"],"scientificR24Complete":False,
  "scientificR24FalseRejectionRate":None,"aggregateRemotePlusRealClientR22Enforced":False,
  "originalDenominatorPreserved":True,"independentExtensionAudit":extra,
  "interpretation":"The extension was chosen after observing the original grid and remains reported separately. All scope-limited false rejections and unknowns are retained. No end-to-end scientific resource metric is substituted.","summarySourceSha256":sha(Path(__file__))}
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(value,indent=2,allow_nan=False)+"\n")
 print(json.dumps({k:v for k,v in value.items()if k!="independentExtensionAudit"}))


if __name__=="__main__":main()
