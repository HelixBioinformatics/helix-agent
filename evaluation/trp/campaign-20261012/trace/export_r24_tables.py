#!/usr/bin/env python3
"""Export the independently checked original matrix and separate extension."""
import argparse
import csv
import json
from pathlib import Path


def read(p):return json.loads(p.read_text())


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument("--original",type=Path,required=True);p.add_argument("--continuation",type=Path,required=True);p.add_argument("--extension",type=Path);p.add_argument("--output",type=Path,required=True);a=p.parse_args()
 original=read(a.original/"all-original-attempts.json")
 if not original["verified"] or not original["allOriginalCasesEmpiricallyObserved"]:raise ValueError("Final original matrix is not verified")
 plans={str(folder.resolve()):read(folder/"inputs/freeze.json") for folder in [a.original,a.continuation]}
 a.output.mkdir(parents=True,exist_ok=True)
 fields=["case_id","cohort","graph_id","work_budget_bytes","helix_reserved_work_bytes","helix_accepted","head_workspace_feasible","final_project_allocated_bytes","max_observed_project_allocated_bytes","max_observed_controller_memory_bytes","elapsed_seconds","actual_attempt_count","preserved_unknown_attempt_count","conclusive_revision","oracle_result_sha256","scope"]
 rows=[]
 for item in original["cases"]:
  folder=Path(item["conclusiveRevision"]);plan=plans[str(folder.resolve())];case=next(c for c in plan["cases"]if c["id"]==item["id"])
  value=read(folder/item["id"]/item["id"]/"oracle-result.json")
  samples=value.get("samples",[])
  used=value["finalQuota"]["usedBytes"]
  memory=[int(c["controllerCgroup"]["memory.peak"])for c in samples if c.get("controllerCgroup",{}).get("memory.peak")]
  rows.append(dict(zip(fields,[item["id"],case["cohort"],case["graphId"],case["budget"]["workBytes"],case["demand"]["workBytes"],item["helixAccepted"],item["physicalFeasibilityLabel"],used,
   max([used]+[s["quota"]["usedBytes"]for s in samples]),max(memory)if memory else "",value["elapsedSeconds"],sum(r["attemptDispatched"]for r in item["attempts"]),
   sum(r["attemptDispatched"] and r["physicalFeasibilityLabel"] is None for r in item["attempts"]),str(folder),item["oracleResultSha256"],"head-workspace development; actual client preparation/export excluded"])))
 with (a.output/"original40.csv").open("w",newline="",encoding="utf-8")as file:
  w=csv.DictWriter(file,fieldnames=fields);w.writeheader();w.writerows(rows)
 if a.extension:
  plan=read(a.extension/"inputs/freeze.json");progress=read(a.extension/"progress.json")
  if not(a.extension/"summary.json").is_file():raise ValueError("Extension is not terminal")
  extra=[]
  for item in progress["cases"]:
   case=next(c for c in plan["cases"]if c["id"]==item["id"])
   value=read(a.extension/item["id"]/item["id"]/"oracle-result.json")
   extra.append({"case_id":item["id"],"graph_id":case["graphId"],"work_budget_bytes":case["budget"]["workBytes"],"helix_reserved_work_bytes":case["demand"]["workBytes"],"helix_accepted":item["helixAccepted"],"head_workspace_feasible":item["physicalFeasibilityLabel"],"causal_status":value["oracleStatus"],"extension_chosen_after_original_grid":True,"scope":"separate head-workspace development extension"})
  with(a.output/"extension.csv").open("w",newline="",encoding="utf-8")as file:
   w=csv.DictWriter(file,fieldnames=list(extra[0]));w.writeheader();w.writerows(extra)
 print(json.dumps({"originalRows":len(rows),"extensionRows":len(extra)if a.extension else 0,"output":str(a.output)}))


if __name__=="__main__":main()
