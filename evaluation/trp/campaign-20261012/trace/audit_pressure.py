#!/usr/bin/env python3
"""Recheck frozen Academy pressure contrasts from raw outputs, without AWS."""
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re

BASE = Path(__file__).resolve().parents[1]
SOURCE = BASE / "cloud/lab2-pressure"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    plan = json.loads((SOURCE / "plan.json").read_text())
    frozen = datetime.fromisoformat(plan["frozen_at"])
    capacities = {}
    for line in (SOURCE / "scheduler-inventory.txt").read_text().splitlines():
        fields = dict(re.findall(r"(\w+)=([^\s]+)", line))
        if "NodeName" in fields:
            capacities[fields["NodeName"]] = {"cpus": int(fields["CPUTot"]), "memory_mib": int(fields["RealMemory"])}
    rows = []
    ids = set()
    for case in plan["cases"]:
        if case["id"] in ids:
            raise ValueError("Duplicate prospective case")
        ids.add(case["id"])
        path = SOURCE / (case["id"] + ".json")
        row = json.loads(path.read_text())
        if row["case"] != case or datetime.fromisoformat(row["observed_at"]) < frozen:
            raise ValueError("Case or prospective order changed")
        if "--nodelist=" + case["node"] not in row["command"]:
            raise ValueError("Command targeted another node")
        if case["mode"] == "scheduler":
            capacity = capacities[case["node"]]
            contradicted = case["requested_cpus"] > capacity["cpus"] or case["memory_mib"] > capacity["memory_mib"]
            passed = contradicted and row["exit_code"] != 0 and "requested node configuration is not available" in row["stderr"].lower()
            if not all(x in row["command"] for x in ("sbatch --test-only", f"--cpus-per-task={case['requested_cpus']}", f"--mem={case['memory_mib']}M")):
                passed = False
            details = {"capacity": capacity, "request_exceeds_capacity": contradicted, "scheduler_exit_code": row["exit_code"]}
        else:
            observed = json.loads(row["stdout"].strip().splitlines()[-1])
            if observed != row["observed"]:
                raise ValueError("Parsed observation differs from raw output")
            quota, period = map(int, observed["cpu_max"].split())
            common = (row["exit_code"] == 0 and period > 0 and quota / period == case["cpus"]
                      and int(observed["memory_max"]) == case["memory_mib"] * 1024**2
                      and observed["swap_max"] == "0" and plan["image"] in row["command"])
            if case["mode"] == "cpu":
                passed = common and observed["throttled_delta"] > 0 and observed["mean_cpus"] <= case["cpus"] * 1.15 + .05 and all(x == 0 for x in observed["child_exit_codes"])
            else:
                passed = common and observed["oom_kill_delta"] > 0 and observed["child_exit_code"] == -9
            details = observed
        rows.append({"id": case["id"], "mode": case["mode"], "node": case["node"],
                     "independently_rechecked": bool(passed), "evidence_sha256": sha(path), "details": details})
    result = {"kind": "independent_raw_pressure_evidence_audit", "scientific_workflow_evaluation": False,
              "plan_sha256": sha(SOURCE / "plan.json"), "inventory_sha256": sha(SOURCE / "scheduler-inventory.txt"),
              "prospective_cases": len(rows), "rechecked": sum(row["independently_rechecked"] for row in rows),
              "permitted_container_contrasts": sum(row["mode"] != "scheduler" for row in rows),
              "infeasible_per_node_requests": sum(row["mode"] == "scheduler" for row in rows),
              "capacities": capacities, "rows": rows,
              "limitations": ["Memory OOM containment succeeds because the bound child is killed; this is not scientific task success.",
                              "No Helix admission predictions are present in these hardware contrasts, so workflow rejection accuracy and false-rejection rate are not derived.",
                              "CPU quota is bandwidth rather than exclusive cores; startup timing allowance follows the engineering probe criteria."]}
    result["verified"] = len(rows) == 40 and all(row["independently_rechecked"] for row in rows)
    (BASE / "trace/lab2-pressure-evidence.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k not in ("rows", "limitations")}))
    return 0 if result["verified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
