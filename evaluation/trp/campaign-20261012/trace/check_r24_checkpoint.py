#!/usr/bin/env python3
"""Read-only ownership cleanup observation before a legitimate guest restart."""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import shlex
import subprocess

ROOT = Path(__file__).resolve().parents[4]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--campaign", required=True, type=Path)
    a = p.parse_args()
    campaign = a.campaign.resolve()
    plan = json.loads((campaign / "inputs/freeze.json").read_text())
    progress = json.loads((campaign / "progress.json").read_text())
    if not (campaign / "driver-terminal.json").is_file():
        raise RuntimeError("A recorded actual terminal orchestration is required")
    if any(r.get("dispatched") and r["status"] not in {"recovered", "unknown-supervisor-stopped-without-result"} for r in progress["cases"]):
        raise RuntimeError("A dispatched attempt is still live or its observation is unresolved")
    spec = importlib.util.spec_from_file_location("academy", ROOT / "script/tesis/aws_academy_cluster.py")
    academy = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(academy)
    academy.configure_lab("185395")
    state = academy.refresh(academy.ec2_client(), academy.load())
    head = next(n for n in state["nodes"] if n["role"] == "head")
    def probe(node, command):
        options = ["StrictHostKeyChecking=yes" if x == "StrictHostKeyChecking=accept-new" else x for x in academy.ssh_options(node)]
        value = subprocess.run(["ssh", *options, "ubuntu@"+node["public_ip"], command], text=True, capture_output=True, timeout=45)
        return {"node":node["name"],"instanceId":node["id"],"command":command,
                "exitCode":value.returncode,"stdout":value.stdout,"stderr":value.stderr,
                "observedAtUtc":datetime.now(timezone.utc).isoformat()}
    queue = probe(head, "squeue --noheader --format='%i|%k'")
    if queue["exitCode"]: raise RuntimeError("Scheduler query failed; cleanup cannot be inferred")
    comments = {c["runComment"] for c in plan["cases"]}
    jobs = [line for line in queue["stdout"].splitlines() if "|" in line and line.split("|",1)[1] in comments]
    units = ["helix-r24-"+row["id"].lower()+".service" for row in progress["cases"] if row.get("dispatched")]
    code = """import json,subprocess
units=json.loads(UNITS)
print(json.dumps([{'unit':u,'active':subprocess.run(['systemctl','is-active','--quiet',u]).returncode==0} for u in units]))
""".replace("UNITS",repr(json.dumps(units)))
    controller = probe(head, "python3 -c "+shlex.quote(code))
    if controller["exitCode"]: raise RuntimeError("Controller service query failed")
    controller_states = json.loads(controller["stdout"])
    remote = json.loads((campaign / "transfer.json").read_text())["remote"]
    pids = [remote+"/"+row["id"]+".pid" for row in progress["cases"] if row.get("dispatched")]
    supervisor_code = """import json,pathlib
paths=json.loads(PATHS)
rows=[]
for name in paths:
 p=pathlib.Path(name)
 if not p.is_file():rows.append({'pidFile':name,'known':False,'ownedRunning':None});continue
 pid=int(p.read_text().strip())
 proc=pathlib.Path('/proc')/str(pid)
 cmd=(proc/'cmdline').read_bytes().decode(errors='replace') if (proc/'cmdline').exists() else ''
 state=(proc/'stat').read_text().split(') ',1)[1].split()[0] if (proc/'stat').exists() else None
 rows.append({'pidFile':name,'pid':pid,'state':state,'known':True,'ownedRunning':'run_r24_independent.py' in cmd and state!='Z','cmdline':cmd})
print(json.dumps(rows))
""".replace("PATHS",repr(json.dumps(pids)))
    supervisor = probe(head, "sudo python3 -c "+shlex.quote(supervisor_code))
    if supervisor["exitCode"]:raise RuntimeError("Original supervisor query failed")
    supervisor_states=json.loads(supervisor["stdout"])
    containers = [probe(node,"docker ps --no-trunc --format '{{.ID}}|{{.Image}}|{{.Status}}'") for node in state["nodes"] if node["role"] != "head"]
    verified = not jobs and not any(r["active"] for r in controller_states) and all(r["known"] and not r["ownedRunning"] for r in supervisor_states) and all(c["exitCode"]==0 and not c["stdout"].strip() for c in containers)
    report = {"schema":"helix-r24-checkpoint-cleanup/1.0","verified":verified,
              "checkedAtUtc":datetime.now(timezone.utc).isoformat(),"freezeSha256":sha(campaign/"inputs/freeze.json"),
              "progressSha256":sha(campaign/"progress.json"),"driverTerminalSha256":sha(campaign/"driver-terminal.json"),
              "ownedJobs":jobs,"scheduler":queue,"controllerServices":controller,
              "controllerStates":controller_states,"supervisorProbe":supervisor,"supervisorStates":supervisor_states,"workerContainers":containers,
              "probeSourceSha256":sha(Path(__file__)),"cloudMutation":False,
              "scope":"All original unique comments, all dispatched controller services, and both exclusive campaign workers."}
    (campaign/"checkpoint-cleanup.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({"verified":verified,"ownedJobs":len(jobs),"activeControllers":sum(r["active"] for r in controller_states),"containers":sum(bool(c["stdout"].strip()) for c in containers)}))
    if not verified: raise RuntimeError("Owned campaign workload is not conclusively clean")


if __name__ == "__main__": main()
