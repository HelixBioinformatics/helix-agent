#!/usr/bin/env python3
"""Resumable transport/orchestration for the frozen independent Lab2 contrasts.

The parent explicitly signals --run after both positive batches and the source
revision are fixed. A poll/SSH timeout NEVER resubmits a case. Detached guest
supervisors enforce their own checkpoint and are inspected/recovered first.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shlex
import subprocess
import tarfile
import time

ROOT=Path(__file__).resolve().parents[4]
HERE=Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_text())


def save(path,value):
    temporary=path.with_suffix(path.suffix+".tmp")
    temporary.write_text(json.dumps(value,indent=2,allow_nan=False)+"\n")
    temporary.replace(path)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output",required=True,type=Path)
    p.add_argument("--run",action="store_true")
    p.add_argument("--original", required=True, type=Path)
    p.add_argument("--deadline", required=True)
    p.add_argument("--namespace", required=True)
    p.add_argument("--prepare-only",action="store_true")
    a=p.parse_args()
    if not a.run and not a.prepare_only:
        p.error("Explicit --run or --prepare-only required after parent's source-ready signal")
    output=a.output.resolve()
    output.mkdir(parents=True,exist_ok=True)
    spec=importlib.util.spec_from_file_location("academy",ROOT/"script/tesis/aws_academy_cluster.py")
    academy=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(academy)
    academy.configure_lab("185395")
    state=academy.refresh(academy.ec2_client(),academy.load())
    head=next(n for n in state["nodes"] if n["role"]=="head")
    if any(n["state"]!="running"for n in state["nodes"]):
        raise RuntimeError("Every required guest must be running")
    private_config=academy.PRIVATE/"remote.json"
    package=output/"inputs"
    if not (package/"freeze.json").exists():
        if package.exists():
            raise RuntimeError("Partial input preparation is retained; choose a new revision directory")
        command=["bun",str(HERE/"prepare_r24_extension.ts"),str(package),str(a.original.resolve()),a.deadline,a.namespace]
        run=subprocess.run(command,cwd=ROOT,env={**os.environ,"HELIX_TRP_REMOTE":str(private_config)},
                           capture_output=True,text=True,timeout=300)
        save(output/"prepare.json",{"argv":command,"exitCode":run.returncode,"stdout":run.stdout,"stderr":run.stderr})
        if run.returncode:
            raise RuntimeError("Prospective preparation failed; no AWS jobs submitted")
    plan=load(package/"freeze.json")
    runner_source=ROOT/"packages/helix/src/trp/remote_runner.py.txt"
    if sha(runner_source)!=plan["sources"]["packages/helix/src/trp/remote_runner.py.txt"]:
        raise RuntimeError("Production observer source changed after freeze")
    if sha(HERE/"run_r24_extension.py")!=plan["sources"]["evaluation/trp/campaign-20261012/trace/run_r24_extension.py"]:
        raise RuntimeError("Independent oracle source changed after freeze")
    if a.prepare_only:
        print(json.dumps({"prepared":True,"cases":len(plan["cases"]),"cloudJobsSubmitted":0}))
        return
    transport_options=["StrictHostKeyChecking=yes" if option=="StrictHostKeyChecking=accept-new" else option for option in academy.ssh_options(head)]
    ssh_args=["ssh",*transport_options,"ubuntu@"+head["public_ip"]]
    def ssh(command,input=None,timeout=60):
        return subprocess.run([*ssh_args,command],input=input,text=True,capture_output=True,timeout=timeout)
    def checked(command,input=None,timeout=60):
        value=ssh(command,input,timeout)
        if value.returncode:
            raise RuntimeError("SSH operation failed: "+value.stderr[-2000:])
        return value.stdout
    remote="/home/ubuntu/helix-r24-"+sha(package/"freeze.json")[:12]
    stage_marker=output/"transfer.json"
    if not stage_marker.exists():
        archive=output/"inputs.tar.gz"
        with tarfile.open(archive,"w:gz")as tar:
            tar.add(package,arcname="inputs")
            tar.add(HERE/"run_r24_extension.py",arcname="run_r24_extension.py")
        checked("mkdir -m 0711 "+shlex.quote(remote))
        subprocess.run(["scp",*transport_options,str(archive),"ubuntu@"+head["public_ip"]+":"+remote+"/inputs.tar.gz"],check=True,timeout=120)
        actual=checked("sha256sum "+shlex.quote(remote+"/inputs.tar.gz")).split()[0]
        if actual!=sha(archive):raise RuntimeError("Package transport hash differs")
        checked("tar -xzf "+shlex.quote(remote+"/inputs.tar.gz")+" -C "+shlex.quote(remote)+" && mkdir -m 0711 "+shlex.quote(remote+"/decisions")+" "+shlex.quote(remote+"/results"))
        save(stage_marker,{"remote":remote,"archiveSha256":actual,"freezeSha256":sha(package/"freeze.json"),"driverSha256":sha(Path(__file__)),"checkedAtUtc":datetime.now(timezone.utc).isoformat()})
    elif load(stage_marker)["freezeSha256"]!=sha(package/"freeze.json"):
        raise RuntimeError("Transferred package belongs to another freeze")
    deadline=datetime.fromisoformat(plan["globalDeadlineUtc"].replace("Z","+00:00"))
    ledger_path=output/"progress.json"
    ledger=load(ledger_path)if ledger_path.exists()else{"schema":"helix-r24-extension-orchestration/1.0","freezeSha256":sha(package/"freeze.json"),"cases":[],"resubmissionOnPollFailure":False}
    by_id={r["id"]:r for r in ledger["cases"]}
    def persist():
        ledger["updatedAtUtc"]=datetime.now(timezone.utc).isoformat()
        save(ledger_path,ledger)
    for index,item in enumerate(plan["cases"]):
        cid=item["id"]
        case=output/cid
        case.mkdir(exist_ok=True)
        row=by_id.get(cid)
        if row is None:
            row={"id":cid,"physicalFeasibilityLabel":None,"status":"not-started"}
            ledger["cases"].append(row)
            by_id[cid]=row
            persist()
        if row["status"]=="recovered":continue
        if datetime.now(timezone.utc)>=deadline and not row.get("dispatched"):
            row.update(status="not-started-global-checkpoint",physicalFeasibilityLabel=None)
            persist()
            continue
        if not row.get("dispatched"):
            req={"action":"observe","target":plan["target"]}
            probe=ssh("python3 -c "+shlex.quote(runner_source.read_text()),json.dumps(req),45)
            save(case/"observer-transport.json",{"exitCode":probe.returncode,"stdout":probe.stdout,"stderr":probe.stderr,"observedAtUtc":datetime.now(timezone.utc).isoformat()})
            if probe.returncode:
                row.update(status="unknown-observer-failure",cause=probe.stderr)
                persist()
                raise RuntimeError("Observer failed; no case submitted")
            observed=json.loads(probe.stdout)
            if observed.get("ok")is not True:
                row.update(status="unknown-observer-refusal",cause=observed)
                persist()
                raise RuntimeError("Observer refused; no case submitted")
            save(case/"inventory.json",observed)
            decision=subprocess.run(["bun",str(HERE/"decide_r24_resource_case.ts"),str(package/"freeze.json"),cid,str(case/"inventory.json")],cwd=ROOT,capture_output=True,text=True,timeout=45)
            save(case/"decision-transport.json",{"exitCode":decision.returncode,"stdout":decision.stdout,"stderr":decision.stderr})
            if decision.returncode:raise RuntimeError("Production decision could not be recorded")
            (case/"decision.json").write_text(decision.stdout)
            row["helixAccepted"]=load(case/"decision.json")["decision"]["accepted"]
            subprocess.run(["scp",*transport_options,str(case/"decision.json"),"ubuntu@"+head["public_ip"]+":"+remote+"/decisions/"+cid+".json"],check=True,timeout=45)
            cmd=["sudo","python3",remote+"/run_r24_extension.py","--package",remote+"/inputs","--case",cid,"--mount","/shared/helix-r24","--output",remote+"/results/"+cid,"--decision",remote+"/decisions/"+cid+".json"]
            row.update(dispatched=True,status="dispatch-intent-recorded",dispatchAtUtc=datetime.now(timezone.utc).isoformat())
            persist()
            launch="nohup "+shlex.join(cmd)+" > "+shlex.quote(remote+"/"+cid+".stdout")+" 2> "+shlex.quote(remote+"/"+cid+".stderr")+" < /dev/null & echo $! > "+shlex.quote(remote+"/"+cid+".pid")
            try:
                value=ssh("bash -lc "+shlex.quote(launch),timeout=30)
                save(case/"dispatch-transport.json",{"exitCode":value.returncode,"stdout":value.stdout,"stderr":value.stderr})
                row["status"]="dispatched"if value.returncode==0 else"dispatch-uncertain"
                persist()
            except subprocess.TimeoutExpired:
                row["status"]="dispatch-uncertain"
                persist()
                raise RuntimeError("Dispatch response lost; inspect existing supervisor, never resubmit")
        # A resumable watcher only observes this already dispatched invocation.
        local_watch_deadline=time.monotonic()+item["budget"]["wallSeconds"]+120
        while True:
            status=ssh("bash -lc "+shlex.quote("if sudo test -f "+shlex.quote(remote+"/results/"+cid+"/export-ready.json")+"; then echo RESULT; elif test -f "+shlex.quote(remote+"/"+cid+".pid")+" && kill -0 $(cat "+shlex.quote(remote+"/"+cid+".pid")+") 2>/dev/null; then echo RUNNING; else echo STOPPED; fi"),timeout=30)
            if status.returncode:
                row["status"]="watch-transport-interrupted"
                persist()
                if time.monotonic()>local_watch_deadline:raise RuntimeError("Watch interrupted; do not resubmit")
                time.sleep(3)
                continue
            if status.stdout.strip()=="RESULT":break
            if status.stdout.strip()=="STOPPED":
                logs=ssh("cat "+shlex.quote(remote+"/"+cid+".stdout")+" "+shlex.quote(remote+"/"+cid+".stderr"))
                save(case/"stopped-supervisor.json",{"stdout":logs.stdout,"stderr":logs.stderr,"source":"Same dispatched supervisor; no automatic retry"})
                row.update(status="unknown-supervisor-stopped-without-result",physicalFeasibilityLabel=None)
                persist()
                raise RuntimeError("Supervisor stopped without result; diagnose preserved first attempt")
            if time.monotonic()>local_watch_deadline:
                row["status"]="watch-timeout-no-resubmit"
                persist()
                raise RuntimeError("Local watcher expired; inspect the same guest supervisor")
            time.sleep(3)
        archive_name=remote+"/"+cid+"-result.tar.gz"
        checked("sudo tar --dereference -czf "+shlex.quote(archive_name)+" -C "+shlex.quote(remote+"/results")+" "+shlex.quote(cid),timeout=120)
        archive_hash=checked("sudo sha256sum "+shlex.quote(archive_name)).split()[0]
        archive=case/"retained-result.tar.gz"
        subprocess.run(["scp",*transport_options,"ubuntu@"+head["public_ip"]+":"+archive_name,str(archive)],check=True,timeout=120)
        if sha(archive)!=archive_hash:raise RuntimeError("Result transport hash differs")
        with tarfile.open(archive)as tar:tar.extractall(case,filter="data")
        actual=load(case/cid/"oracle-result.json")
        row.update(status="recovered",physicalFeasibilityLabel=actual["physicalFeasibilityLabel"],oracleStatus=actual.get("oracleStatus"),resultArchiveSha256=archive_hash,oracleResultSha256=sha(case/cid/"oracle-result.json"))
        persist()
        print(json.dumps({"case":cid,"helixAccepted":row.get("helixAccepted"),"physicalFeasibilityLabel":row["physicalFeasibilityLabel"],"oracleStatus":row.get("oracleStatus")}),flush=True)
        if index==0 and item["cohort"]=="generous" and actual["physicalFeasibilityLabel"]is not True:
            raise RuntimeError("First generous smoke not proven; suspend before later cases")
    known=[r for r in ledger["cases"]if r["physicalFeasibilityLabel"]is not None]
    feasible=[r for r in known if r["physicalFeasibilityLabel"]]
    infeasible=[r for r in known if not r["physicalFeasibilityLabel"]]
    summary={"schema":"helix-r24-extension-head-workspace-results/1.0","originalFreezeSha256":plan["originalFreezeSha256"],"freezeSha256":sha(package/"freeze.json"),"scope":plan["scope"],"storageUnit":plan["storageUnit"],"planned":len(plan["cases"]),"recorded":len(ledger["cases"]),"empiricallyFeasible":len(feasible),"empiricallyInfeasible":len(infeasible),"unknownOrNotStarted":len(ledger["cases"])-len(known),"falseRejections":sum(not r["helixAccepted"]for r in feasible),"falseRejectionRate":sum(not r["helixAccepted"]for r in feasible)/len(feasible)if feasible else None,"accuracy":sum(r["helixAccepted"]==r["physicalFeasibilityLabel"]for r in known)/len(known)if known else None,"scientificR24Complete":False,"actualGroupMinimaSatisfied":len(feasible)>=20 and len(infeasible)>=20,"cases":ledger["cases"]}
    save(output/"summary.json",summary)
    print(json.dumps({k:v for k,v in summary.items()if k!="cases"}),flush=True)


if __name__=="__main__":main()
