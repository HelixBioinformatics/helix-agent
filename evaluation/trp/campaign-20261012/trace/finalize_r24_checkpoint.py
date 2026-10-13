#!/usr/bin/env python3
"""Finalize an observed clean checkpoint, preserving producer failures/unknowns."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path


def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument("--campaign",type=Path,required=True);a=p.parse_args()
 base=a.campaign.resolve();plan=read(base/"inputs/freeze.json");progress=read(base/"progress.json");cleanup=read(base/"checkpoint-cleanup.json")
 if not cleanup["verified"] or cleanup["progressSha256"]!=sha(base/"progress.json"):
  raise RuntimeError("Clean checkpoint does not bind this exact progress snapshot")
 before=sha(base/"progress.json")
 existing={r["id"]:r for r in progress["cases"]}
 for c in plan["cases"]:
  if c["id"] not in existing:
   progress["cases"].append({"id":c["id"],"status":"not-started-global-checkpoint","physicalFeasibilityLabel":None})
 progress["checkpointFinalization"]={"originalProgressSha256":before,"cleanupSha256":sha(base/"checkpoint-cleanup.json"),
  "atUtc":datetime.now(timezone.utc).isoformat(),"noConclusiveOutcomeRewritten":True,"remainingCasesRegisteredWithoutLabels":True}
 (base/"checkpoint-progress-before.json").write_bytes((base/"progress.json").read_bytes())
 (base/"progress.json").write_text(json.dumps(progress,indent=2)+"\n")
 known=[r for r in progress["cases"] if r["physicalFeasibilityLabel"] is not None]
 feasible=[r for r in known if r["physicalFeasibilityLabel"]];infeasible=[r for r in known if not r["physicalFeasibilityLabel"]]
 summary={"schema":"helix-r24-checkpoint-results/1.0","freezeSha256":sha(base/"inputs/freeze.json"),
  "originalDriverTerminal":read(base/"driver-terminal.json"),"checkpointCleanupSha256":sha(base/"checkpoint-cleanup.json"),
  "scope":plan["scope"],"storageUnit":plan["storageUnit"],"planned":len(plan["cases"]),"recorded":len(progress["cases"]),
  "empiricallyFeasible":len(feasible),"empiricallyInfeasible":len(infeasible),"unknownOrNotStarted":len(progress["cases"])-len(known),
  "falseRejections":sum(not r["helixAccepted"]for r in feasible),"falseRejectionRate":sum(not r["helixAccepted"]for r in feasible)/len(feasible)if feasible else None,
  "scientificR24Complete":False,"actualGroupMinimaSatisfied":len(feasible)>=20 and len(infeasible)>=20,"cases":progress["cases"]}
 if (base/"summary.json").exists():(base/"producer-summary.json").write_bytes((base/"summary.json").read_bytes())
 (base/"summary.json").write_text(json.dumps(summary,indent=2)+"\n")
 print(json.dumps({k:v for k,v in summary.items()if k not in {"cases","originalDriverTerminal"}}))


if __name__=="__main__":main()
