#!/usr/bin/env python3
"""Read-only final cleanup proof across all preserved resource revisions."""
import argparse
from datetime import datetime,timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import shlex
import subprocess

ROOT=Path(__file__).resolve().parents[4]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument("--campaign",type=Path,action="append",required=True);p.add_argument("--output",type=Path,required=True);a=p.parse_args()
 spec=importlib.util.spec_from_file_location("academy",ROOT/"script/tesis/aws_academy_cluster.py");academy=importlib.util.module_from_spec(spec);spec.loader.exec_module(academy);academy.configure_lab("185395")
 state=academy.refresh(academy.ec2_client(),academy.load());head=next(n for n in state["nodes"]if n["role"]=="head")
 comments=set();units=[];supervisors=[];revisions=[]
 for directory in a.campaign:
  directory=directory.resolve();plan=read(directory/"inputs/freeze.json");progress=read(directory/"progress.json");terminal=read(directory/"driver-terminal.json")
  if any(r.get("dispatched")and r["status"] not in {"recovered","unknown-supervisor-stopped-without-result"}for r in progress["cases"]):raise RuntimeError("An attempt is still running/unrecovered")
  comments.update(c["runComment"]for c in plan["cases"])
  operational=plan.get("operationalAmendment",{});prefix=operational.get("unitPrefix","helix-r24-")
  remote=read(directory/"transfer.json")["remote"]
  runner="run_r24_extension.py"if "extension"in plan["schema"]else"run_r24_continuation.py"if "continuation"in plan["schema"]else"run_r24_independent.py"
  for r in progress["cases"]:
   if r.get("dispatched"):
    units.append(prefix+r["id"].lower()+".service")
    supervisors.append({"pidFile":remote+"/"+r["id"]+".pid","ownedScript":remote+"/"+runner})
  revisions.append({"directory":str(directory),"freezeSha256":sha(directory/"inputs/freeze.json"),"progressSha256":sha(directory/"progress.json"),"terminalSha256":sha(directory/"driver-terminal.json"),"exitCode":terminal["exitCode"]})
 def probe(node,command):
  options=["StrictHostKeyChecking=yes"if x=="StrictHostKeyChecking=accept-new"else x for x in academy.ssh_options(node)]
  r=subprocess.run(["ssh",*options,"ubuntu@"+node["public_ip"],command],text=True,capture_output=True,timeout=45)
  return {"node":node["name"],"instanceId":node["id"],"exitCode":r.returncode,"stdout":r.stdout,"stderr":r.stderr,"observedAtUtc":datetime.now(timezone.utc).isoformat(),"command":command}
 queue=probe(head,"squeue --noheader --format='%i|%k'")
 if queue["exitCode"]:raise RuntimeError("Scheduler cleanup unknown because query failed")
 owned=[line for line in queue["stdout"].splitlines()if "|"in line and line.split("|",1)[1]in comments]
 code="""import json,pathlib,subprocess
units=json.loads(UNITS);supervisors=json.loads(SUPERVISORS)
controllers=[{'unit':u,'active':subprocess.run(['systemctl','is-active','--quiet',u]).returncode==0}for u in units]
rows=[]
for item in supervisors:
 p=pathlib.Path(item['pidFile'])
 if not p.is_file():rows.append({**item,'known':False,'ownedRunning':None});continue
 pid=int(p.read_text().strip());proc=pathlib.Path('/proc')/str(pid)
 cmd=(proc/'cmdline').read_bytes().decode(errors='replace')if(proc/'cmdline').exists()else''
 state=(proc/'stat').read_text().split(') ',1)[1].split()[0]if(proc/'stat').exists()else None
 rows.append({**item,'pid':pid,'state':state,'known':True,'ownedRunning':item['ownedScript']in cmd and state!='Z'})
print(json.dumps({'controllers':controllers,'supervisors':rows}))
""".replace("UNITS",repr(json.dumps(units))).replace("SUPERVISORS",repr(json.dumps(supervisors)))
 services=probe(head,"sudo python3 -c "+shlex.quote(code))
 if services["exitCode"]:raise RuntimeError("Service/supervisor cleanup query failed")
 service_states=json.loads(services["stdout"])
 containers=[probe(n,"docker ps --no-trunc --format '{{.ID}}|{{.Image}}|{{.Status}}'")for n in state["nodes"]if n["role"]!="head"]
 verified=not owned and not any(r["active"]for r in service_states["controllers"])and all(r["known"]and not r["ownedRunning"]for r in service_states["supervisors"])and all(c["exitCode"]==0 and not c["stdout"].strip()for c in containers)
 value={"schema":"helix-r24-final-independent-quiescence/1.0","verified":verified,"observedAtUtc":datetime.now(timezone.utc).isoformat(),"ownedJobs":owned,"scheduler":queue,"controllerAndSupervisorObservation":services,"workerContainers":containers,"revisions":revisions,"uniqueCommentsChecked":len(comments),"supervisorsChecked":len(supervisors),"probeSourceSha256":sha(Path(__file__)),"cloudMutation":False}
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(value,indent=2)+"\n");print(json.dumps({"verified":verified,"ownedJobs":len(owned),"activeControllers":sum(r["active"]for r in service_states["controllers"]),"supervisorsChecked":len(supervisors),"containers":sum(bool(c["stdout"].strip())for c in containers)}))
 if not verified:raise RuntimeError("Final resource campaign is not conclusively clean")


if __name__=="__main__":main()
