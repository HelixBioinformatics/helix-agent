#!/usr/bin/env python3
"""Stage the frozen scientific image and write private Helix remote configuration."""
import argparse
import hashlib
import importlib.util
import json
import re
import shlex
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
IMAGE='sha256:1dd91e70acb153a0bd9a51346fc001dd5025f851c9598697cdd37f07d9490b0a'


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--lab',choices=['183928','185395'],required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--image-archive',type=Path,default=Path('/tmp/helix-geometre-image.tar.gz'));a=p.parse_args()
 spec=importlib.util.spec_from_file_location('academy',ROOT/'script/tesis/aws_academy_cluster.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);m.configure_lab(a.lab)
 state=m.refresh(m.ec2_client(),m.load());a.output.mkdir(parents=True,exist_ok=True)
 report={'lab':a.lab,'observed_at_utc':datetime.now(timezone.utc).isoformat(),'image':IMAGE,'nodes':[]}
 def ssh(n,command,timeout=60):
  return subprocess.run(['ssh',*m.ssh_options(n),'ubuntu@'+n['public_ip'],'bash -lc '+shlex.quote(command)],capture_output=True,text=True,timeout=timeout)
 guest_deadlines=[]
 for n in state['nodes']:
  if n['state']!='running':raise RuntimeError('Node not running: '+n['name'])
  mount_check='mountpoint -q /shared/helix' if n['role']=='head' else 'test "$(findmnt -n -t nfs4 -T /shared/helix -o FSTYPE)" = nfs4'
  services=['munge','docker','slurmctld' if n['role']=='head' else 'slurmd']
  service_checks=' && '.join('systemctl is-active '+service for service in services)
  r=ssh(n,'test -f /var/lib/helix-bootstrap-ready && '+service_checks+' && '+mount_check+' && systemctl is-enabled helix-session-stop.timer')
  row={'node':n['name'],'instance_type':n['type'],'id':n['id'],'checks_exit':r.returncode,'checks_stdout':r.stdout,'checks_stderr':r.stderr};report['nodes'].append(row)
  if r.returncode:
   status=ssh(n,'sudo cloud-init status --format json; sudo tail -8 /var/log/helix-bootstrap.log');row['bootstrap_status']=status.stdout
   (a.output/'prepare-status.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'lab':a.lab,'ready':False,'node':n['name'],'status':status.stdout[-1200:]}));return 2
  # Academy renewal does not extend a guest's independent OnBoot shutdown.
  # Observe the guard on every required node and bind the earliest deadline.
  timer_code="""import json,pathlib,subprocess,time
unit='helix-session-stop.timer'
active=subprocess.run(['systemctl','is-active','--quiet',unit]).returncode==0
content=subprocess.check_output(['systemctl','cat',unit],text=True)
if not active or 'OnBootSec=180min' not in content:raise RuntimeError('Expected active180minute guest stop guard unavailable')
boot=int(next(line.split()[1] for line in pathlib.Path('/proc/stat').read_text().splitlines() if line.startswith('btime ')))
print(json.dumps({'active':active,'boot_epoch_seconds':boot,'stop_epoch_seconds':boot+180*60,'observed_epoch_seconds':time.time(),'guard_minutes_after_boot':180}))
"""
  timer=ssh(n,'python3 -c '+shlex.quote(timer_code))
  if timer.returncode:raise RuntimeError('Guest stop guard cannot be verified on '+n['name']+': '+timer.stderr)
  observed=json.loads(timer.stdout);row['guest_stop_guard']=observed
  guest_deadlines.append(observed['stop_epoch_seconds'])
 head=next(n for n in state['nodes'] if n['role']=='head')
 missing=[]
 for n in state['nodes']:
  r=ssh(n,'docker image inspect --format "{{.Id}}" '+shlex.quote(IMAGE));missing.append(n) if r.returncode else None
  if not r.returncode and r.stdout.strip()!=IMAGE:raise RuntimeError('Image identity mismatch')
 if missing:
  if not a.image_archive.is_file():raise RuntimeError('Frozen image archive unavailable')
  image_hash=hashlib.sha256(a.image_archive.read_bytes()).hexdigest();remote='/shared/helix/images/helix-geometre-image.tar.gz'
  r=ssh(head,'mkdir -p /shared/helix/images; sha256sum '+shlex.quote(remote))
  if r.returncode or not r.stdout.startswith(image_hash+' '):
   subprocess.run(['scp',*m.ssh_options(head),str(a.image_archive),'ubuntu@'+head['public_ip']+':'+remote],check=True,timeout=300)
  r=ssh(head,'sha256sum '+shlex.quote(remote))
  if r.returncode or not r.stdout.startswith(image_hash+' '):raise RuntimeError('Transferred image archive changed')
  for n in missing:
   r=ssh(n,'gzip -dc '+shlex.quote(remote)+' | docker load',timeout=180)
   if r.returncode:raise RuntimeError(r.stderr)
   r=ssh(n,'docker image inspect --format "{{.Id}}" '+shlex.quote(IMAGE))
   if r.returncode or r.stdout.strip()!=IMAGE:raise RuntimeError('Loaded image identity differs')
  report['transferred_archive_sha256']=image_hash
 config={'version':'trp-slurm-ssh/1.0.0','host':head['public_ip'],'port':22,'user':'ubuntu','identityFile':str(m.PRIVATE/'ssh-ed25519'),'knownHostsFile':str(m.PRIVATE/'known_hosts'),'hostKeyAlias':head['id'],'root':'/shared/helix','partition':'helix','selectNode':'helix-worker1','geometryNode':'helix-worker2','numericalProfile':'haswell-single-thread'}
 session=json.loads((Path.home()/f'.local/state/helix/aws-academy/session-{a.lab}.json').read_text())
 deadline=re.search(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{4}',session['after']['Session to end'])
 if not deadline:raise RuntimeError('Academy session deadline unavailable')
 academy_deadline=datetime.fromisoformat(deadline.group())
 effective_deadline=min(academy_deadline.timestamp(),*guest_deadlines)
 if effective_deadline-datetime.now(timezone.utc).timestamp()<1200:
  raise RuntimeError('Less than20minutes remain before Academy or a required guest stop guard; checkpoint and renew/restart before new runs')
 config['sessionExpiresAt']=datetime.fromtimestamp(effective_deadline,timezone.utc).isoformat()
 report['execution_window']={'academy_session_end':academy_deadline.isoformat(),'earliest_guest_stop':datetime.fromtimestamp(min(guest_deadlines),timezone.utc).isoformat(),'effective_admission_deadline':config['sessionExpiresAt'],'policy':'Minimum of Academy expiry and verified180minute boot guard on all required nodes'}
 m.private_write(m.PRIVATE/'remote.json',json.dumps(config,indent=2)+'\n')
 r=ssh(head,'sinfo -N -o "%N %c %m %t"; squeue -h; df -B1 /shared/helix; nextflow -version; sudo cloud-init status --format json')
 report['cluster_status_stdout']=r.stdout;report['cluster_status_stderr']=r.stderr;report['cluster_status_exit']=r.returncode
 report['ready']=True;report['private_config_written']=True
 (a.output/'prepare-status.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'lab':a.lab,'ready':True,'nodes':len(state['nodes']),'image':IMAGE,'private_config':str(m.PRIVATE/'remote.json')}));return 0


if __name__=='__main__':raise SystemExit(main())
