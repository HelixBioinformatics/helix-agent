#!/usr/bin/env python3
"""Independent, read-only proof of owned process/cgroup/native/container cleanup."""
import importlib.util, json, subprocess, shlex, hashlib
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[6]
HERE=Path(__file__).resolve().parent
GUEST = r'''import json,os,subprocess
from pathlib import Path
from datetime import datetime,timezone
owned=[]
for proc in Path('/proc').iterdir():
 if not proc.name.isdigit():continue
 try:
  args=[x.decode(errors='replace') for x in (proc/'cmdline').read_bytes().split(b'\0') if x]
  if any(x.endswith('/fault_native.py') or x.endswith('/full_client.ts') or x.endswith('/full_client_amended.ts') or x.endswith('/full_client_large.ts') or x.endswith('/remote_runner.py') for x in args) or any(x=='guest-supervise' for x in args):owned.append({'pid':int(proc.name),'args':args})
 except (FileNotFoundError,PermissionError,ProcessLookupError):pass
cg=[]
for p in Path('/sys/fs/cgroup').glob('helix-strict-*.service'):
 cg.append({'path':str(p),'procs':(p/'cgroup.procs').read_text().strip(),'events':(p/'cgroup.events').read_text().strip()})
def command(args):
 r=subprocess.run(args,capture_output=True,text=True);return dict(exitCode=r.returncode,stdout=r.stdout,stderr=r.stderr)
print(json.dumps({'at':datetime.now(timezone.utc).isoformat(),'hostname':os.uname().nodename,'ownedProcesses':owned,'cgroups':cg,'containers':command(['docker','ps','--no-trunc','--format','{{json .}}'])}))'''
def main():
 sp=importlib.util.spec_from_file_location('academy',ROOT/'script/tesis/aws_academy_cluster.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);m.configure_lab('185395')
 state=m.refresh(m.ec2_client(),m.load());rows=[];queue=None
 for n in state['nodes']:
  opts=['StrictHostKeyChecking=yes'if x=='StrictHostKeyChecking=accept-new'else x for x in m.ssh_options(n)]
  args=['ssh',*opts,'ubuntu@'+n['public_ip']]
  r=subprocess.run([*args,'sudo python3 -c '+shlex.quote(GUEST)],capture_output=True,text=True,timeout=40)
  observed=json.loads(r.stdout) if r.returncode==0 else None
  rows.append(dict(role=n['role'],instanceId=n['id'],exitCode=r.returncode,stdout=r.stdout,stderr=r.stderr,observation=observed))
  if n['role']=='head':
   q=subprocess.run([*args,"sudo squeue -h -o '%i|%j|%T|%k'"],capture_output=True,text=True,timeout=30)
   queue=dict(exitCode=q.returncode,stdout=q.stdout,stderr=q.stderr)
 success=all(x['exitCode']==0 and x['observation']['containers']['exitCode']==0 and not x['observation']['containers']['stderr'] for x in rows)
 no_procs=success and all(not x['observation']['ownedProcesses']for x in rows)
 no_cg=success and all(not c['procs'] and 'populated 0'in c['events'] for x in rows for c in x['observation']['cgroups'])
 no_docker=success and all(not x['observation']['containers']['stdout'].strip() for x in rows)
 no_jobs=queue['exitCode']==0 and not queue['stderr'] and not queue['stdout'].strip()
 v=dict(schema='helix-post-repair-independent-quiescence/1.0',verified=bool(success and no_procs and no_cg and no_docker and no_jobs),at=datetime.now(timezone.utc).isoformat(),nodes=rows,queue=queue,allNativeJobsEmpty=no_jobs,allContainersEmpty=no_docker,ownedProcessesEmpty=no_procs,controllerCgroupsEmpty=no_cg,sourceSha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),readOnly=True)
 (HERE/'post-quiescence.json').write_text(json.dumps(v,indent=2)+'\n')
 print(json.dumps({k:v[k]for k in ['verified','at','allNativeJobsEmpty','allContainersEmpty','ownedProcessesEmpty','controllerCgroupsEmpty']}))
 if not v['verified']:raise SystemExit(1)
if __name__=='__main__':main()
