#!/usr/bin/env python3
"""Restore the existing strict volume and validate owned native NFS jobs.

No filesystem formatting, original quota resets, workload retries or AWS
lifecycle mutation. Explicit stable NFS fsid and normal hard mounts retain
root_squash. Preflight is infrastructure evidence, not a scientific case.
"""
import hashlib,importlib.util,json,shlex,subprocess,time,uuid
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];HERE=Path(__file__).resolve().parent
OUT=HERE/'continuation-1-preflight-r2';OUT.mkdir(exist_ok=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
def now():return datetime.now(timezone.utc).isoformat()
spec=importlib.util.spec_from_file_location('academy',ROOT/'script/tesis/aws_academy_cluster.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);m.configure_lab('185395')
state=m.refresh(m.ec2_client(),m.load());head=next(n for n in state['nodes']if n['role']=='head');workers=[n for n in state['nodes']if n['role']!='head'];steps=[]
def ssh(n,cmd,timeout=90,check=True):
 options=['StrictHostKeyChecking=yes'if v=='StrictHostKeyChecking=accept-new'else v for v in m.ssh_options(n)]
 r=subprocess.run(['ssh',*options,'ubuntu@'+n['public_ip'],cmd],capture_output=True,text=True,timeout=timeout)
 steps.append({'at':now(),'role':n['role'],'command':cmd,'exitCode':r.returncode,'stdout':r.stdout,'stderr':r.stderr});write(OUT/'steps.json',{'steps':steps,'sourceSha256':sha(Path(__file__))})
 if check and r.returncode:raise RuntimeError(r.stderr[-3000:])
 return r
identity='cd26a20b-f8e0-480a-9640-38e1b93e7fff'
restore=r'''import pathlib,subprocess,json,os
mount=pathlib.Path('/shared/helix-strict');image=pathlib.Path('/srv/helix-strict-store/disk.img')
assert image.is_file()and image.stat().st_size==2147483648
present=subprocess.run(['findmnt','--mountpoint',str(mount),'--noheadings','-o','FSTYPE'],text=True,capture_output=True)
if present.returncode!=0:subprocess.run(['mount','-o','loop,prjquota,allocsize=4k',str(image),str(mount)],check=True)
view=json.loads(subprocess.check_output(['findmnt','--json','--mountpoint',str(mount),'-o','TARGET,SOURCE,FSTYPE,OPTIONS,UUID'],text=True))['filesystems'][0]
assert view['fstype']=='xfs'and view['uuid']=='cd26a20b-f8e0-480a-9640-38e1b93e7fff'and'prjquota'in view['options'].split(',')
p=pathlib.Path('/etc/exports.d/helix-strict.exports');text='/shared/helix-strict 172.31.0.0/20(rw,sync,no_subtree_check,root_squash,fsid=43)\n'
if p.exists():assert p.read_text().strip().startswith('/shared/helix-strict ')
p.write_text(text);p.chmod(0o644);os.chown(p,0,0)
subprocess.run(['exportfs','-ra'],check=True)
print(json.dumps({'filesystem':view,'existingDataPreserved':True,'noFormat':True,'quotasNotReset':True,'export':text,'stableFsid':43}))'''
write(OUT/'prospective.json',{'at':now(),'sourceSha256':sha(Path(__file__)),'existingVolumeUuid':identity,'fsid':43,'reason':'Observed worker2 stale-file-handle prevented native stdout initialization. Restore unchanged XFS after legitimate guest stop/start and use explicit stable NFS export identity; validate actual native I/O before unseen campaign cases.','producerUnchanged':True,'preflightLabelsAreScientific':False})
ssh(head,'sudo python3 -c '+shlex.quote(restore))
for node in workers:
 cmd='sudo mkdir -p /shared/helix-strict; if mountpoint -q /shared/helix-strict; then sudo umount /shared/helix-strict; fi; sudo mount -t nfs4 -o vers=4.2,rw,hard,timeo=600,retrans=2 '+head['private_ip']+':/shared/helix-strict /shared/helix-strict; findmnt -T /shared/helix-strict -o TARGET,SOURCE,FSTYPE,OPTIONS'
 ssh(node,'bash -lc '+shlex.quote(cmd))
namespace='preflight-'+uuid.uuid4().hex[:12];directory='/shared/helix-strict/'+namespace
setup=r'''import pathlib,os,hashlib,json,sys
p=pathlib.Path(sys.argv[1]);p.mkdir(mode=0o755);os.chown(p,1000,1000)
source=p/'input.txt';source.write_text('HELIX_NATIVE_NFS_PREFLIGHT\n');source.chmod(0o644);os.chown(source,1000,1000)
for index in [1,2]:
 work=p/('worker'+str(index));work.mkdir(mode=0o755);os.chown(work,1000,1000)
 body='\n'.join(['#!/bin/bash','set -euo pipefail','cd '+str(work),'sha256sum ../input.txt > input.sha256','echo HELIX_NATIVE_NFS_OK > result.txt',"docker run --rm --cpus 2 --memory 2g --memory-swap 2g --user 1000:1000 -v \"$PWD:$PWD\" --workdir \"$PWD\" sha256:1dd91e70acb153a0bd9a51346fc001dd5025f851c9598697cdd37f07d9490b0a python -c \"from pathlib import Path; import hashlib,json; data=Path('../input.txt').read_bytes(); Path('docker-result.txt').write_text('HELIX_NATIVE_DOCKER_OK'); print(json.dumps({'cpuMax':Path('/sys/fs/cgroup/cpu.max').read_text().strip(),'memoryMax':Path('/sys/fs/cgroup/memory.max').read_text().strip(),'swapMax':Path('/sys/fs/cgroup/memory.swap.max').read_text().strip(),'inputHash':hashlib.sha256(data).hexdigest()}))\"",'echo 0 > .exitcode','hostname','cat result.txt'])+'\n'
 f=work/'job.sh';f.write_text(body);f.chmod(0o755);os.chown(f,1000,1000)
print(json.dumps({'directory':str(p),'inputSha256':hashlib.sha256(source.read_bytes()).hexdigest()}))'''
ssh(head,'sudo python3 -c '+shlex.quote(setup)+' '+shlex.quote(directory))
jobs=[]
for index in [1,2]:
 work=directory+'/worker'+str(index);comment='helix-preflight:'+namespace+':'+str(index)
 cmd='sbatch --parsable --partition=helix --nodes=1 --ntasks=1 --cpus-per-task=2 --mem=2G --time=00:01:00 --nodelist=helix-worker'+str(index)+' --comment='+comment+' --chdir='+work+' --output='+work+'/.command.log --error='+work+'/.command.err '+work+'/job.sh'
 r=ssh(head,cmd);job=r.stdout.strip().split(';')[0]
 if not job.isdigit():raise ValueError('Native preflight submission ID invalid')
 jobs.append({'id':job,'work':work,'node':'helix-worker'+str(index),'comment':comment})
start=time.time();records=[]
while time.time()-start<150:
 records=[]
 for job in jobs:
  r=ssh(head,'scontrol show job '+job['id']+' -o',check=False);records.append({**job,'exitCode':r.returncode,'stdout':r.stdout,'stderr':r.stderr})
 if all('JobState=COMPLETED'in r['stdout']and'ExitCode=0:0'in r['stdout']for r in records):break
 if any(any('JobState='+s in r['stdout']for s in ['FAILED','CANCELLED','TIMEOUT','NODE_FAIL'])for r in records):break
 time.sleep(2)
if not all('JobState=COMPLETED'in r['stdout']and'ExitCode=0:0'in r['stdout']for r in records):
 for job in jobs:ssh(head,'scancel '+job['id'],check=False)
 write(OUT/'summary.json',{'ready':False,'native':records,'stepsSha256':sha(OUT/'steps.json'),'noScienceDispatched':True});raise RuntimeError('Actual two-node native NFS preflight did not pass')
verify=r'''import json,pathlib,hashlib,sys
p=pathlib.Path(sys.argv[1]);out=[]
for index in [1,2]:
 w=p/('worker'+str(index));out.append({'node':'helix-worker'+str(index),'exitcode':(w/'.exitcode').read_text().strip(),'log':(w/'.command.log').read_text(),'stderr':(w/'.command.err').read_text(),'result':(w/'result.txt').read_text(),'dockerResult':(w/'docker-result.txt').read_text(),'inputHash':(w/'input.sha256').read_text().split()[0]})
assert all(x['exitcode']=='0'and x['node']in x['log']and x['stderr']==''and x['result']=='HELIX_NATIVE_NFS_OK\n'and x['dockerResult']=='HELIX_NATIVE_DOCKER_OK'and x['inputHash']==hashlib.sha256((p/'input.txt').read_bytes()).hexdigest()for x in out)
print(json.dumps(out))'''
r=ssh(head,'sudo python3 -c '+shlex.quote(verify)+' '+shlex.quote(directory))
write(OUT/'summary.json',{'ready':True,'native':records,'io':json.loads(r.stdout),'stepsSha256':sha(OUT/'steps.json'),'sourceSha256':sha(Path(__file__)),'directory':directory,'operationalPreflightOnly':True,'originalCasesRetried':False,'producerUnchanged':True,'scope':'Native two-CPU/two-GiB Slurm tasks read and write the restored NFS export on both workers, including Slurm stdout/err and explicit exitcode. This preflight is not a Helix full-client resource case.'})
print(json.dumps({'ready':True,'nativeIds':[j['id']for j in jobs],'directory':directory}),flush=True)
