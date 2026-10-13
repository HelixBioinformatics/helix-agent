#!/usr/bin/env python3
"""Resumable one-dispatch full-client strict-profile campaign.

Transport observation failure is never permission to resubmit. Guest guard keeps
running independently, and the actual allocation is retained before export.
"""
import argparse,hashlib,importlib.util,json,shlex,subprocess,time,tarfile
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[6]
HERE=Path(__file__).resolve().parent
RUNTIME='/opt/helix-post-campaign-runtime-20261013-r1'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):p.write_text(json.dumps(v,indent=2,allow_nan=False)+'\n')
def main():
 p=argparse.ArgumentParser();p.add_argument('--inputs',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--namespace',type=int,required=True);p.add_argument('--checkpoint',default='2026-10-13T19:20:00+00:00');a=p.parse_args()
 freeze=json.loads((a.inputs/'freeze.json').read_text());mode=freeze['mode'];a.output.mkdir(parents=True,exist_ok=True)
 deadline=datetime.fromisoformat(a.checkpoint).timestamp()
 spec=importlib.util.spec_from_file_location('academy',ROOT/'script/tesis/aws_academy_cluster.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);m.configure_lab('185395')
 state=m.refresh(m.ec2_client(),m.load());head=next(n for n in state['nodes']if n['role']=='head')
 options=['StrictHostKeyChecking=yes'if v=='StrictHostKeyChecking=accept-new'else v for v in m.ssh_options(head)]
 config=json.loads((m.PRIVATE/'remote.json').read_text());expiry=config['sessionExpiresAt']
 if deadline>datetime.fromisoformat(expiry).timestamp()-300:raise ValueError('Checkpoint lacks guest/Academy margin')
 sshargs=['ssh',*options,'ubuntu@'+head['public_ip']]
 def ssh(cmd,timeout=90):return subprocess.run([*sshargs,'bash -lc '+shlex.quote(cmd)],capture_output=True,text=True,timeout=timeout)
 def checked(cmd,timeout=90):
  r=ssh(cmd,timeout)
  if r.returncode:raise RuntimeError(r.stderr[-4000:])
  return r.stdout
 runtime_inputs=RUNTIME+'/campaign/'+freeze.get('guestInputNamespace',mode)
 marker=a.output/'transfer.json'
 if not marker.exists():
  archive=a.output/'inputs.tar'
  with tarfile.open(archive,'w')as tar:
   for path in sorted(a.inputs.rglob('*')):
    if path.is_file():tar.add(path,arcname=str(path.relative_to(a.inputs)),recursive=False)
  remote='/tmp/helix-aggregate-'+mode+'-'+sha(archive)[:12]+'.tar'
  subprocess.run(['scp',*options,str(archive),'ubuntu@'+head['public_ip']+':'+remote],check=True,timeout=180)
  observed=checked('sha256sum '+remote)
  if not observed.startswith(sha(archive)+' '):raise ValueError('Frozen input archive transfer changed')
  checked('sudo test ! -e '+runtime_inputs+' && sudo chmod u+w '+RUNTIME+' && sudo mkdir -p '+runtime_inputs+' && sudo tar -xf '+remote+' -C '+runtime_inputs+' && sudo chmod -R a-w '+runtime_inputs+' && sudo chmod a-w '+RUNTIME)
  write(marker,{'archiveSha256':sha(archive),'freezeSha256':sha(a.inputs/'freeze.json'),'guestDirectory':runtime_inputs,'immutableGuestReference':True,'credentialsTransferred':False})
 for index,item in enumerate(freeze['cases']):
  cid=item['id'];local=a.output/cid;local.mkdir(exist_ok=True)
  if (local/'recovery.json').exists():continue
  intent=local/'dispatch-intent.json'
  guest='/srv/helix-strict-results/'+mode+'-'+str(a.namespace)+'-'+cid
  if not intent.exists():
   if time.time()>deadline-180:write(local/'not-dispatched.json',{'reason':'Checkpoint preserves recovery margin','at':datetime.now(timezone.utc).isoformat()});break
   allocation_cmd='sudo python3 '+RUNTIME+'/script/tesis/provision_remote_strict_profile.py guest-allocation --work-bytes '+str(item['budget']['workBytes'])+' --project '+str(a.namespace+index)+' --expiry '+shlex.quote(expiry)+' --output '+guest+'-allocation.json'
   stdout=checked(allocation_cmd)
   raw=checked('sudo cat '+guest+'-allocation.json');allocation=json.loads(raw);write(local/'allocation.json',allocation)
   launch='sudo env NXF_HOME=/home/ubuntu/.nextflow HELIX_MODELS_PATH='+RUNTIME+'/packages/core/test/plugin/fixtures/models-dev.json HELIX_TRP_PYTHON='+RUNTIME+'/python/bin/python nohup python3 '+RUNTIME+'/script/tesis/provision_remote_strict_profile.py guest-supervise --allocation '+guest+'-allocation.json --deadline '+str(deadline)+' --output '+guest+' -- /usr/bin/strace -f -Z -yy -ttt -e trace=write,pwrite64,writev,pwritev,openat,ftruncate,copy_file_range -s 256 /usr/local/bin/helix-strict-bun '+RUNTIME+'/evaluation/trp/campaign-20261012/checks/post-campaign-production-20261013/cloud/full_client_amended.ts '+runtime_inputs+'/'+cid+'.json >'+shlex.quote('/tmp/'+cid+'-'+str(a.namespace)+'.supervisor.stdout')+' 2>'+shlex.quote('/tmp/'+cid+'-'+str(a.namespace)+'.supervisor.stderr')+' < /dev/null &'
   # Record BEFORE sending one launch. A lost response never clears this intent.
   write(intent,{'at':datetime.now(timezone.utc).isoformat(),'guest':guest,'allocationSha256':sha(local/'allocation.json'),'freezeSha256':sha(a.inputs/'freeze.json'),'command':launch,'case':cid,'budget':item['budget'],'retryForbiddenOnUnknownTransport':True})
   if item.get('faultInjection'):
    fault_intent=local/'native-fault-intent.json'
    fault_deadline=min(deadline,time.time()+600)
    fault='sudo nohup python3 '+RUNTIME+'/evaluation/trp/campaign-20261012/checks/post-campaign-production-20261013/cloud/fault_native.py --allocation '+guest+'-allocation.json --deadline '+str(fault_deadline)+' --output '+guest+'-native-fault.json >'+shlex.quote('/tmp/'+cid+'-'+str(a.namespace)+'.native-fault.stdout')+' 2>'+shlex.quote('/tmp/'+cid+'-'+str(a.namespace)+'.native-fault.stderr')+' < /dev/null &'
    write(fault_intent,{'at':datetime.now(timezone.utc).isoformat(),'command':fault,'allocationSha256':sha(local/'allocation.json'),'oneInjectionOnly':True,'globalDeadline':deadline,'faultDeadline':fault_deadline})
    observed_fault=ssh(fault,30);write(local/'native-fault-launch-observation.json',{'exitCode':observed_fault.returncode,'stdout':observed_fault.stdout,'stderr':observed_fault.stderr})
   observed=ssh(launch,30);write(local/'launch-observation.json',{'exitCode':observed.returncode,'stdout':observed.stdout,'stderr':observed.stderr})
  while True:
   status=ssh('if sudo test -f '+guest+'/export-ready.json; then echo READY; elif sudo test -d '+guest+'; then echo LIVE; else echo UNKNOWN; fi',30)
   if status.returncode:
    write(local/'transport-observation.json',{'exitCode':status.returncode,'stdout':status.stdout,'stderr':status.stderr,'resubmitted':False});time.sleep(2);continue
   if status.stdout.strip()=='READY':break
   if time.time()>deadline+45:write(local/'checkpoint-observation.json',{'terminalUnknown':True,'resubmitted':False});return
   time.sleep(2)
  archive=local/'actual-allocation-and-supervisor.tar'
  command='sudo tar -cf - -C '+shlex.quote(str(Path(guest).parent))+' '+shlex.quote(Path(guest).name)
  with archive.open('wb')as f:
   r=subprocess.run([*sshargs,command],stdout=f,stderr=subprocess.PIPE,timeout=120)
  if r.returncode:raise RuntimeError('Actual retained evidence copy failed; never resubmit: '+r.stderr.decode()[-2000:])
  links=[]
  with tarfile.open(archive)as tar:
   ordinary=[]
   for member in tar.getmembers():
    if member.issym()or member.islnk():
     links.append({'path':member.name,'target':member.linkname,'type':'symlink'if member.issym()else'hardlink'});continue
    ordinary.append(member)
   tar.extractall(local/'recovered',members=ordinary,filter='data')
  write(local/'symlink-records.json',{'rawArchivePreserved':True,'archiveSha256':sha(archive),'links':links})
  if item.get('faultInjection'):
   actual_fault=checked('sudo cat '+shlex.quote(guest+'-native-fault.json'))
   (local/'native-fault-external.json').write_text(actual_fault)
  report=json.loads((local/'recovered'/Path(guest).name/'supervision.json').read_text())
  write(local/'recovery.json',{'archiveSha256':sha(archive),'bytes':archive.stat().st_size,'actualExitCode':report['actualExitCode'],'terminationCause':report['terminationCause'],'ownedComments':report['ownedComments'],'nativeCleanup':report['nativeCleanup'],'retrievedAt':datetime.now(timezone.utc).isoformat()})
  print(json.dumps({'case':cid,'exitCode':report['actualExitCode'],'terminationCause':report['terminationCause'],'remainingOwnedJobs':report['nativeCleanup']['remaining']}),flush=True)
  # Smoke failure is retained and stops development before the final freeze.
  if mode=='smoke'and item['cohort']=='generous'and report['actualExitCode']!=0:return
 write(a.output/'terminal.json',{'at':datetime.now(timezone.utc).isoformat(),'allFrozenCasesObserved':all((a.output/x['id']/'recovery.json').exists()for x in freeze['cases']),'counts':len(freeze['cases']),'noCaseResubmission':True})
if __name__=='__main__':main()
