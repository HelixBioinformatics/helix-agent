#!/usr/bin/env python3
"""Read-only final observer; never dispatch, cancel, retry or mutate AWS."""
import hashlib, importlib.util, json, shlex, subprocess
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    groups = [("original40", "campaign-inputs", "campaign-outcomes"),
              ("boundary6", "boundary-inputs", "boundary-outcomes"),
              ("minimumSupplement", "extension-inputs", "extension-outcomes")]
    cases, comments, cgroups = [], [], []
    for group, inputs, outputs in groups:
        freeze = json.loads((HERE / inputs / "freeze.json").read_text())
        terminal = json.loads((HERE / outputs / "terminal.json").read_text())
        if not terminal["allFrozenCasesObserved"]:
            raise RuntimeError("Campaign not terminal: " + group)
        for item in freeze["cases"]:
            folder = HERE / outputs / item["id"]
            intent = json.loads((folder / "dispatch-intent.json").read_text())
            supervision_path = folder / "recovered" / Path(intent["guest"]).name / "supervision.json"
            supervision = json.loads(supervision_path.read_text())
            policy = json.loads((folder / "allocation.json").read_text())["policy"]
            cgroups.append(policy["controller"]["cgroup"])
            comments.extend(supervision["ownedComments"])
            reaped = (supervision["controllerAndTracerReaped"]
                      and not supervision["nativeCleanup"]["remaining"]
                      and not supervision["finalCgroup"]["cgroup.procs"].strip()
                      and "populated 0" in supervision["finalCgroup"]["cgroup.events"])
            cases.append({"id": item["id"], "group": group,
                          "supervisionPath": str(supervision_path.relative_to(ROOT)),
                          "supervisionSha256": sha(supervision_path),
                          "controllerAndTracerReaped": reaped,
                          "exactOwnedComments": supervision["ownedComments"]})
    spec = importlib.util.spec_from_file_location("academy", ROOT / "script/tesis/aws_academy_cluster.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    m.configure_lab("185395")
    state = m.refresh(m.ec2_client(), m.load())
    def observe(node):
        code = """import json,pathlib,subprocess,sys
def run(argv):
 r=subprocess.run(argv,capture_output=True,text=True)
 return {'exitCode':r.returncode,'stdout':r.stdout,'stderr':r.stderr}
out={'hostname':run(['hostname']), 'docker':run(['docker','ps','--format','{{.ID}}|{{.Names}}|{{.Status}}'])}
if sys.argv[1]=='head':
 out['scheduler']=run(['squeue','-h','-o','%i|%T|%j|%k'])
 out['supervisors']=run(['pgrep','-af','[p]rovision_remote_strict_profile.py guest-supervise'])
 out['cgroups']=[]
 for name in json.loads(sys.argv[2]):
  path=pathlib.Path('/sys/fs/cgroup')/name
  out['cgroups'].append({'name':name,'exists':path.exists(),'procs':(path/'cgroup.procs').read_text().strip() if path.exists() else None,'events':(path/'cgroup.events').read_text().strip() if path.exists() else None})
print(json.dumps(out))
"""
        command = "sudo python3 -c " + shlex.quote(code) + " " + shlex.quote(node["role"]) + " " + shlex.quote(json.dumps(cgroups))
        options = ["StrictHostKeyChecking=yes" if v == "StrictHostKeyChecking=accept-new" else v for v in m.ssh_options(node)]
        r = subprocess.run(["ssh", *options, "ubuntu@" + node["public_ip"], command], text=True, capture_output=True, timeout=60)
        return {"role":node["role"],"instanceId":node.get("id",node.get("instance_id")),
                "exitCode":r.returncode,"stdout":r.stdout,"stderr":r.stderr,
                "observations":json.loads(r.stdout) if r.returncode == 0 else None}
    with ThreadPoolExecutor(max_workers=3) as pool:
        nodes = list(pool.map(observe,state["nodes"]))
    head = next(n for n in nodes if n["role"] == "head")
    h = head["observations"]
    ready = (len(cases) == 50 and all(c["controllerAndTracerReaped"] for c in cases)
             and all(n["exitCode"] == 0 and n["observations"]["docker"]["exitCode"] == 0 and not n["observations"]["docker"]["stdout"].strip() for n in nodes)
             and h["scheduler"]["exitCode"] == 0 and not h["scheduler"]["stdout"].strip()
             and h["supervisors"]["exitCode"] == 1 and not h["supervisors"]["stdout"].strip()
             and all(not c["exists"] or (not c["procs"] and "populated 0" in c["events"]) for c in h["cgroups"]))
    output = {"schema":"helix-aggregate-resource-final-quiescence/1.0", "at":datetime.now(timezone.utc).isoformat(),
              "readyForParentSourceChangesAndLifecycle":ready,"observedCases":len(cases),"cases":cases,
              "nodes":nodes,"exactOwnedComments":sorted(set(comments)),"observerSha256":sha(Path(__file__)),
              "scope":"Read-only scheduler, all three Docker daemons, exact case cgroups and archived EOF; absent old cgroups after documented reboot do not replace archived EOF.",
              "submitted":False,"cancelled":False,"cloudLifecycleMutated":False}
    (HERE / "final-quiescence.json").write_text(json.dumps(output,indent=2)+"\n")
    print(json.dumps({"ready":ready,"observedCases":len(cases),"output":"final-quiescence.json"}))
    if not ready:
        raise RuntimeError("Quiescence incomplete")

if __name__ == "__main__":
    main()
