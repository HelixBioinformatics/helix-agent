#!/usr/bin/env python3
"""Pause only the local conductor, recover its same guest run, and prove quiescence.

This supplementary lifecycle observer does not change frozen sources, inputs,
budgets or cases. It never submits, retries or cancels a guest workflow. The
independent guest supervisor keeps its original kernel/session guard.
"""
import argparse,hashlib,importlib.util,json,os,shlex,signal,subprocess,tarfile,time
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def write(path,value):path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')
def now():return datetime.now(timezone.utc).isoformat()

def main():
 p=argparse.ArgumentParser();p.add_argument('--driver-pid',type=int,required=True);p.add_argument('--checkpoint',required=True);p.add_argument('--inputs',type=Path,required=True);p.add_argument('--outcomes',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 a.output.mkdir(parents=True,exist_ok=True)
 deadline=datetime.fromisoformat(a.checkpoint).timestamp();plan=json.loads((a.inputs/'freeze.json').read_text())
 cmdline=Path('/proc')/str(a.driver_pid)/'cmdline';command=cmdline.read_bytes().replace(b'\x00',b' ').decode()
 if 'drive_campaign.py'not in command or str(a.outcomes)not in command:raise ValueError('Driver identity does not match the declared campaign')
 write(a.output/'prospective-checkpoint.json',{'createdAt':now(),'checkpoint':a.checkpoint,'driverPid':a.driver_pid,'driverCommand':command,'freezeSha256':sha(a.inputs/'freeze.json'),'observerSha256':sha(Path(__file__)),'scope':'Local conductor termination only; existing guest submission remains untouched; same run recovery; no retry or cloud lifecycle mutation'})
 print(json.dumps({'status':'checkpoint-armed','at':now(),'checkpoint':a.checkpoint}),flush=True)
 while time.time()<deadline:
  if not cmdline.exists():
   write(a.output/'driver-already-terminal.json',{'at':now(),'noSignalSent':True});return
  time.sleep(min(20,max(.1,deadline-time.time())))
 # Signal only the verified local Python conductor. Its detached guest
 # supervisor and native tasks retain their original lifecycle and bounds.
 actual=cmdline.read_bytes().replace(b'\x00',b' ').decode()
 if actual!=command:raise ValueError('Driver PID was reused; signal refused')
 os.kill(a.driver_pid,signal.SIGTERM)
 write(a.output/'local-driver-stop.json',{'at':now(),'driverPid':a.driver_pid,'signal':'SIGTERM','guestTasksSignalled':False,'frozenSourceOrArgsModified':False})
 spec=importlib.util.spec_from_file_location('academy',ROOT/'script/tesis/aws_academy_cluster.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);m.configure_lab('185395')
 state=m.refresh(m.ec2_client(),m.load());head=next(n for n in state['nodes']if n['role']=='head')
 options=['StrictHostKeyChecking=yes'if v=='StrictHostKeyChecking=accept-new'else v for v in m.ssh_options(head)]
 sshargs=['ssh',*options,'ubuntu@'+head['public_ip']]
 def ssh(code,timeout=60):return subprocess.run([*sshargs,'bash -lc '+shlex.quote(code)],text=True,capture_output=True,timeout=timeout)
 pending=[]
 for item in plan['cases']:
  local=a.outcomes/item['id']
  if not(local/'dispatch-intent.json').is_file()or(local/'recovery.json').is_file():continue
  guest=json.loads((local/'dispatch-intent.json').read_text())['guest'];pending.append(item['id'])
  while True:
   r=ssh('sudo test -f '+shlex.quote(guest+'/export-ready.json'),30)
   if r.returncode==0:break
   if time.time()>deadline+600:raise RuntimeError('Same run not terminal within recovery window; never resubmit or authorize instance stop')
   time.sleep(2)
  archive=local/'actual-allocation-and-supervisor.tar'
  with archive.open('wb')as out:r=subprocess.run([*sshargs,'sudo tar -cf - -C '+shlex.quote(str(Path(guest).parent))+' '+shlex.quote(Path(guest).name)],stdout=out,stderr=subprocess.PIPE,timeout=120)
  if r.returncode:raise RuntimeError('Same-run recovery copy failed: '+r.stderr.decode()[-2000:])
  links=[]
  with tarfile.open(archive)as tar:
   ordinary=[]
   for member in tar.getmembers():
    if member.issym()or member.islnk():links.append({'path':member.name,'target':member.linkname,'type':'symlink'if member.issym()else'hardlink'});continue
    ordinary.append(member)
   tar.extractall(local/'recovered',members=ordinary,filter='data')
  write(local/'symlink-records.json',{'rawArchivePreserved':True,'archiveSha256':sha(archive),'links':links})
  report=json.loads((local/'recovered'/Path(guest).name/'supervision.json').read_text())
  write(local/'recovery.json',{'archiveSha256':sha(archive),'bytes':archive.stat().st_size,'actualExitCode':report['actualExitCode'],'terminationCause':report['terminationCause'],'ownedComments':report['ownedComments'],'nativeCleanup':report['nativeCleanup'],'retrievedAt':now(),'recoveryObserverSha256':sha(Path(__file__)),'sameExistingSubmission':True,'resubmitted':False})
  print(json.dumps({'case':item['id'],'recoveredSameRun':True,'actualExitCode':report['actualExitCode']}),flush=True)
 # Verify every completed case's preserved EOF and exact owned comments,
 # then observe global scheduler idleness before asking the root to reboot.
 completed=[];comments=[];all_reaped=True
 for item in plan['cases']:
  local=a.outcomes/item['id']
  if not(local/'recovery.json').is_file():continue
  recovery=json.loads((local/'recovery.json').read_text());comments+=recovery['ownedComments'];completed.append(item['id'])
  guest=Path(json.loads((local/'dispatch-intent.json').read_text())['guest']).name
  s=json.loads((local/'recovered'/guest/'supervision.json').read_text())
  all_reaped=all_reaped and s.get('controllerAndTracerReaped',False)and s['nativeCleanup']['remaining']==[]
 observation=ssh("sudo squeue -h -o '%i|%T|%j|%k'; sudo sh -c 'pgrep -af \"[p]rovision_remote_strict_profile.py guest-supervise\" || true'",60)
 ready=all_reaped and observation.returncode==0 and not observation.stdout.strip()
 report={'at':now(),'readyForParentInstanceLifecycle':ready,'guestSupervisorAndSchedulerObservation':{'exitCode':observation.returncode,'stdout':observation.stdout,'stderr':observation.stderr},'allCompletedControllerAndTracerReaped':all_reaped,'exactOwnedComments':sorted(set(comments)),'completedCaseIds':completed,'recoveredAtCheckpoint':pending,'neverDispatchedCaseIds':[i['id']for i in plan['cases']if not(a.outcomes/i['id']/'dispatch-intent.json').exists()],'freezeSha256':sha(a.inputs/'freeze.json'),'sourceSha256':sha(Path(__file__)),'noResubmission':True,'cloudLifecycleMutated':False}
 write(a.output/'quiescence.json',report);print(json.dumps({'status':'quiescence','readyForParentInstanceLifecycle':ready,'completed':len(completed),'pending':len(report['neverDispatchedCaseIds'])}),flush=True)
 if not ready:raise RuntimeError('Quiescence not proven; parent must not stop instances based on this observer')
if __name__=='__main__':main()
