#!/usr/bin/env python3
"""Prospective paired kernel quota copy control, not full workflow labels."""
import hashlib,importlib.util,json,shlex,subprocess,time
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[4];HERE=Path(__file__).resolve().parent
OUT=HERE/'copy-causal-controls';RUNTIME='/opt/helix-strict-runtime'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 OUT.mkdir(exist_ok=False)
 spec=importlib.util.spec_from_file_location('academy',ROOT/'script/tesis/aws_academy_cluster.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);m.configure_lab('185395');state=m.refresh(m.ec2_client(),m.load());head=next(n for n in state['nodes']if n['role']=='head');config=json.loads((m.PRIVATE/'remote.json').read_text())
 options=['StrictHostKeyChecking=yes'if v=='StrictHostKeyChecking=accept-new'else v for v in m.ssh_options(head)];sshargs=['ssh',*options,'ubuntu@'+head['public_ip']]
 source=RUNTIME+'/campaign/smoke7/G-valid-001/source.pdb';program=Path('/tmp/helix-copy-control/quota_copy_control.js')
 freeze={'schema':'helix-kernel-quota-copy-mechanism/1.0','frozenAt':datetime.now(timezone.utc).isoformat(),'programSha256':sha(program),'sourceSha256':'f674267d0ef4752a3d4da00497947bfc09f441a5c36d39593b72bc2ba390df0b','sourceBytes':359397,'operation':'Exact node:fs/promises.copyFile used by full client','cases':[{'id':'low64','workBytes':65536,'project':41000},{'id':'generous','workBytes':134217728,'project':41001}],'labelsBeforeOutputs':None,'fullWorkflowOracle':False,'sourceFiles':{'typescript':sha(HERE/'quota_copy_control.ts'),'driver':sha(Path(__file__))}}
 (OUT/'freeze.json').write_text(json.dumps(freeze,indent=2)+'\n')
 def checked(cmd,timeout=90):
  r=subprocess.run([*sshargs,'bash -lc '+shlex.quote(cmd)],capture_output=True,text=True,timeout=timeout)
  if r.returncode:raise RuntimeError(r.stderr[-3000:])
  return r.stdout
 subprocess.run(['scp',*options,str(program),'ubuntu@'+head['public_ip']+':/tmp/helix-quota-copy-control.js'],check=True,timeout=90)
 observed=checked('sha256sum /tmp/helix-quota-copy-control.js && sudo install -o root -g root -m444 /tmp/helix-quota-copy-control.js /opt/helix-quota-copy-control.js')
 if not observed.startswith(sha(program)+' '):raise ValueError('Control program transfer changed')
 rows=[]
 for case in freeze['cases']:
  local=OUT/case['id'];local.mkdir();guest='/srv/helix-strict-results/copy-control-'+case['id']
  checked('sudo python3 '+RUNTIME+'/script/tesis/provision_remote_strict_profile.py guest-allocation --work-bytes '+str(case['workBytes'])+' --project '+str(case['project'])+' --expiry '+shlex.quote(config['sessionExpiresAt'])+' --output '+guest+'-allocation.json')
  allocation=json.loads(checked('sudo cat '+guest+'-allocation.json'));(local/'allocation.json').write_text(json.dumps(allocation,indent=2)+'\n');destination=allocation['policy']['paths']['clientWorkspace']+'/input.pdb'
  precode="import os,json,pathlib;src=pathlib.Path("+repr(source)+");dst=pathlib.Path("+repr(destination)+");fs=os.statvfs(dst.parent);print(json.dumps({'globalFreeBytes':fs.f_bavail*fs.f_frsize,'globalFreeInodes':fs.f_favail,'sourceDevice':src.stat().st_dev,'sourceBytes':src.stat().st_size,'sourceBlocksBytes':src.stat().st_blocks*512,'destinationParentDevice':dst.parent.stat().st_dev,'destinationExistedBefore':dst.exists(),'sourceRegular':src.is_file()}))"
  health=json.loads(checked('sudo python3 -c '+shlex.quote(precode)));(local/'before.json').write_text(json.dumps(health,indent=2)+'\n')
  command='sudo env HELIX_TRP_PYTHON='+RUNTIME+'/python/bin/python python3 '+RUNTIME+'/script/tesis/provision_remote_strict_profile.py guest-supervise --allocation '+guest+'-allocation.json --deadline '+str(time.time()+60)+' --output '+guest+' -- /usr/bin/strace -f -Z -yy -ttt -e trace=write,pwrite64,writev,pwritev,openat,ftruncate,copy_file_range -s 256 /usr/local/bin/helix-strict-bun /opt/helix-quota-copy-control.js '+source+' '+destination
  terminal=checked(command,90);(local/'driver-terminal.txt').write_text(terminal)
  supervision=json.loads(checked('sudo cat '+guest+'/supervision.json'));stdout=checked('sudo cat '+guest+'/experiment-telemetry.stdout');stderr=checked('sudo cat '+guest+'/experiment-telemetry.stderr')
  (local/'supervision.json').write_text(json.dumps(supervision,indent=2)+'\n');(local/'stdout.txt').write_text(stdout);(local/'stderr.txt').write_text(stderr)
  markers={}
  for line in stdout.splitlines():
   if line.startswith('HELIX_COPY_'):k,v=line.split(':',1);markers[k]=json.loads(v)
  rows.append({'case':case['id'],'before':health,'markers':markers,'exit':supervision['actualExitCode'],'controllerAndTracerReaped':supervision['controllerAndTracerReaped'],'allocatedPeak':max(r['quota']['quota']['usedBytes']for r in supervision['samples']),'kernelFailureLines':[line for line in stderr.splitlines()if '= -1 ENOSPC'in line or'= -1 EDQUOT'in line],'allocationPolicySha256':allocation['policySha256']})
 result={'schema':'helix-kernel-quota-copy-mechanism/1.0','freezeSha256':sha(OUT/'freeze.json'),'rows':rows,'fullWorkflowOracle':False,'scope':'Fresh independently capped allocations; exact identical Bun copy primitive and same dense359397-byte source; all global health and enforced quota sources retained'}
 result['mechanismQualified']=rows[0]['exit']==1 and rows[1]['exit']==0 and rows[0]['markers'].get('HELIX_COPY_CONTROL_THROW',{}).get('code')=='ENOSPC'and rows[1]['markers'].get('HELIX_COPY_CONTROL_RESULT',{}).get('sha256')==freeze['sourceSha256']and all(r['before']['globalFreeBytes']>1024**3 and r['before']['globalFreeInodes']>1000 and r['before']['sourceRegular']and not r['before']['destinationExistedBefore']and r['controllerAndTracerReaped']for r in rows)
 (OUT/'summary.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'mechanismQualified':result['mechanismQualified'],'rows':len(rows),'fullWorkflowOracle':False}))
if __name__=='__main__':main()
