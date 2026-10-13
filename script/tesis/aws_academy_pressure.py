#!/usr/bin/env python3
"""Prospective kernel/scheduler contrasts, independent of Helix admission outputs."""
import argparse
import importlib.util
import json
import shlex
import subprocess
from datetime import datetime, timezone
from pathlib import Path

IMAGE = 'sha256:1dd91e70acb153a0bd9a51346fc001dd5025f851c9598697cdd37f07d9490b0a'
ROOT = Path(__file__).resolve().parents[2]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--lab', choices=['183928', '185395'], required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--freeze-only', action='store_true')
    a = p.parse_args()
    a.output.mkdir(parents=True, exist_ok=True)
    cases = []
    for node in ['helix-worker1', 'helix-worker2']:
        for cpu in [.25, .5, 1, 1.5, 2]:
            cases.append(dict(id=f'{node}-cpu-{cpu}', node=node, mode='cpu', cpus=cpu, memory_mib=256, expected='feasible'))
        for mem in [128, 256, 512, 1024, 2048]:
            cases.append(dict(id=f'{node}-memory-{mem}', node=node, mode='memory', cpus=1, memory_mib=mem, expected='feasible'))
        for cpu in [3, 4, 5, 6, 7]:
            cases.append(dict(id=f'{node}-unavailable-cpu-{cpu}', node=node, mode='scheduler', requested_cpus=cpu, memory_mib=512, expected='infeasible_node_capacity'))
        for mem in [7500, 8192, 9216, 10240, 11264]:
            cases.append(dict(id=f'{node}-unavailable-memory-{mem}', node=node, mode='scheduler', requested_cpus=1, memory_mib=mem, expected='infeasible_node_capacity'))
    plan = dict(version='academy-pressure/1.0.0', frozen_at=datetime.now(timezone.utc).isoformat(), lab=a.lab,
                kind='engineering_capacity_contrasts', scientific_cases=False, image=IMAGE, cases=cases,
                definitions={'feasible':'A permitted Slurm allocation with a real bounded container; not feasibility of any biological workflow',
                             'infeasible':'Requested per-node CPU or RAM exceeds independently observed configured capacity'},
                limits=['Does not validate per-workflow storage estimates or physical biology', 'CPU quota is not exclusive cores'])
    frozen = a.output/'plan.json'
    if not frozen.exists(): frozen.write_text(json.dumps(plan, indent=2)+'\n')
    else:
        old=json.loads(frozen.read_text())
        if old['cases']!=cases or old['image']!=IMAGE or old['lab']!=a.lab: raise RuntimeError('Frozen plan differs')
        plan=old
    if a.freeze_only:
        print(json.dumps({'frozen':str(frozen),'cases':len(cases)})); return
    spec=importlib.util.spec_from_file_location('academy',ROOT/'script/tesis/aws_academy_cluster.py')
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);mod.configure_lab(a.lab)
    state=mod.refresh(mod.ec2_client(),mod.load());head=next(n for n in state['nodes'] if n['role']=='head')
    if head['state']!='running': raise RuntimeError('Head not running')
    def ssh(command, timeout=90):
        return subprocess.run(['ssh',*mod.ssh_options(head),'ubuntu@'+head['public_ip'],'bash -lc '+shlex.quote(command)],capture_output=True,text=True,timeout=timeout)
    inventory=ssh('scontrol show nodes -o; scontrol show partition helix -o; sinfo -N -o "%N %c %m %t"')
    if inventory.returncode: raise RuntimeError(inventory.stderr)
    (a.output/'scheduler-inventory.txt').write_text(inventory.stdout)
    rows=[]
    for case in plan['cases']:
        target=a.output/(case['id']+'.json')
        if target.exists():
            rows.append(json.loads(target.read_text()));continue
        if case['mode']=='scheduler':
            command=f"sbatch --test-only --partition=helix --nodelist={case['node']} --cpus-per-task={case['requested_cpus']} --mem={case['memory_mib']}M --time=00:01:00 --wrap=true"
        else:
            if case['mode']=='cpu':
                code="""import json,multiprocessing,time,pathlib
p=pathlib.Path('/sys/fs/cgroup')
def values(): return {k:int(v) for k,v in (l.split() for l in (p/'cpu.stat').read_text().splitlines())}
def spin():
 end=time.monotonic()+4
 while time.monotonic()<end: sum(range(1000))
a=values();t=time.monotonic();xs=[multiprocessing.Process(target=spin) for _ in range(4)]
for x in xs:x.start()
for x in xs:x.join()
b=values();elapsed=time.monotonic()-t
print(json.dumps({'cpu_max':(p/'cpu.max').read_text().strip(),'memory_max':(p/'memory.max').read_text().strip(),'swap_max':(p/'memory.swap.max').read_text().strip(),'mean_cpus':(b['usage_usec']-a['usage_usec'])/1e6/elapsed,'elapsed_seconds':elapsed,'throttled_delta':b['nr_throttled']-a['nr_throttled'],'child_exit_codes':[x.exitcode for x in xs]}))
"""
            else:
                code="""import json,multiprocessing,pathlib,time
p=pathlib.Path('/sys/fs/cgroup')
def values():return {k:int(v) for k,v in (l.split() for l in (p/'memory.events').read_text().splitlines())}
def fill():
 xs=[]
 while True:xs.append(bytearray(8*1024**2))
a=values();x=multiprocessing.Process(target=fill);x.start();x.join(40)
if x.is_alive():x.kill();x.join();raise RuntimeError('Memory probe did not stop at hard limit')
b=values();print(json.dumps({'cpu_max':(p/'cpu.max').read_text().strip(),'memory_max':(p/'memory.max').read_text().strip(),'swap_max':(p/'memory.swap.max').read_text().strip(),'oom_kill_delta':b['oom_kill']-a['oom_kill'],'child_exit_code':x.exitcode,'peak_bytes':int((p/'memory.peak').read_text())}))
"""
            docker=['docker','run','--rm','--network','none','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','--pids-limit','128','--cpus',str(case['cpus']),'--memory',str(case['memory_mib'])+'m','--memory-swap',str(case['memory_mib'])+'m','--entrypoint','python',IMAGE,'-c',code]
            command='srun --partition=helix --nodelist='+case['node']+' --cpus-per-task=2 --mem=3000M --time=00:02:00 --kill-on-bad-exit=1 '+shlex.join(docker)
        r=ssh(command)
        row=dict(case=case,command=command,observed_at=datetime.now(timezone.utc).isoformat(),exit_code=r.returncode,stdout=r.stdout,stderr=r.stderr)
        if case['mode']=='scheduler':
            row['passed']=r.returncode!=0 and any(s in r.stderr.lower() for s in ['requested node configuration','memory specification','more processors','cpu count','memory limit'])
        else:
            try:
                observed=json.loads(r.stdout.strip().splitlines()[-1]);row['observed']=observed
                quota,period=map(int,observed['cpu_max'].split())
                common=r.returncode==0 and quota/period==case['cpus'] and int(observed['memory_max'])==case['memory_mib']*1024**2 and observed['swap_max']=='0'
                if case['mode']=='cpu': row['passed']=common and observed['throttled_delta']>0 and observed['mean_cpus']<=case['cpus']*1.15+.05 and all(x==0 for x in observed['child_exit_codes'])
                else: row['passed']=common and observed['oom_kill_delta']>0 and observed['child_exit_code']==-9
            except (ValueError,KeyError,IndexError): row['passed']=False
        target.write_text(json.dumps(row,indent=2)+'\n');rows.append(row)
        print(json.dumps({'lab':a.lab,'case':case['id'],'passed':row['passed']}),flush=True)
        if not row['passed']: raise RuntimeError('Capacity contrast failed; preserve evidence and inspect '+case['id'])
    summary=dict(kind=plan['kind'],lab=a.lab,cases=len(rows),feasible=sum(x['case']['expected']=='feasible' for x in rows),infeasible=sum(x['case']['expected']!='feasible' for x in rows),passed=sum(x['passed'] for x in rows),all_passed=all(x['passed'] for x in rows),scientific_evaluation=False)
    (a.output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary))


if __name__=='__main__':main()
