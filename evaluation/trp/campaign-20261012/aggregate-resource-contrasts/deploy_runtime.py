#!/usr/bin/env python3
"""Sanitized public runtime transfer and strict allocation infrastructure.

Only execute --deploy after the parent confirms the current guest window.
Never touches any credential inside guest runtime or previous campaign volume.
"""
import argparse,hashlib,importlib.util,json,os,shlex,subprocess,tarfile
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[4]
RUNTIME='/opt/helix-strict-runtime'
OUT=Path(__file__).resolve().parent

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--deploy',action='store_true');p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 a.output.mkdir(parents=True,exist_ok=False)
 archive=a.output/'public-sources.tar'
 records=[]
 with tarfile.open(archive,'w')as tar:
  candidates=[ROOT/'package.json',ROOT/'bun.lock',ROOT/'tsconfig.json',ROOT/'script/tesis/provision_remote_strict_profile.py']
  for package in (ROOT/'packages').iterdir():
   if not package.is_dir():continue
   for value in ['package.json','tsconfig.json','src','migration']:
    path=package/value
    if path.is_dir():candidates.extend(p for p in path.rglob('*')if p.is_file())
    elif path.is_file():candidates.append(path)
  for value in ['src','migration','package.json','tsconfig.json']:
   path=ROOT/'packages/sdk/js'/value
   if path.is_dir():candidates.extend(p for p in path.rglob('*')if p.is_file())
   elif path.is_file():candidates.append(path)
  candidates.append(ROOT/'packages/core/test/plugin/fixtures/models-dev.json')
  catalogue=json.loads((ROOT/'packages/helix/src/trp/catalog.json').read_text())
  ref=next(x for x in catalogue['entries']if x['id']=='geometre.geometry')['reference']
  candidates.extend(ROOT/x['path']for x in [ref['record'],*ref['inputs'],*ref['outputs']])
  candidates.extend(p for p in OUT.rglob('*')if p.is_file()and p.suffix in ['.ts','.py']and '__pycache__'not in p.parts)
  checker=Path("/tmp/helix-remote-strict-stage/packages/helix/src/trp/remote_strict.py.txt")
  if sha(checker)!="f7587626581f414ca8515b87997495f1f65785e07231e1a2151a33da395b9b50":raise ValueError("Approved checker source changed")
  tar.add(checker,arcname="packages/helix/src/trp/remote_strict.py.txt",recursive=False)
  records.append({"path":"packages/helix/src/trp/remote_strict.py.txt","bytes":checker.stat().st_size,"sha256":sha(checker),"source":"Root-approved isolated stage"})
  for path in sorted(set(candidates)):
   if path.name=="remote_strict.py.txt" or "__pycache__" in path.parts:continue
   if not path.is_file():continue
   relative=path.relative_to(ROOT).as_posix()
   if any(v in relative.lower()for v in ['.env','private_key','auth.json','credentials']):raise ValueError('Unexpected sensitive source path')
   records.append({'path':relative,'bytes':path.stat().st_size,'sha256':sha(path)})
   tar.add(path,arcname=relative,recursive=False)
 report={'schema':'helix-strict-public-runtime/1.0','preparedAt':datetime.now(timezone.utc).isoformat(),
         'sourceFiles':records,'sourceArchiveSha256':sha(archive),'dependencyArchiveSha256':sha(Path('/tmp/helix-strict-dependencies.tar.zst')),
         'dependencyBytes':Path('/tmp/helix-strict-dependencies.tar.zst').stat().st_size,'bunSha256':sha(Path('/home/webiwabou/.bun/bin/bun')),
         'credentialsIncluded':False,'runtimeScope':'Preinstalled immutable code/dependencies/Nextflow/image references outside per-run allocation; actual SQLite, preparation,tmp,state,cache and requested portable export inside quota',
         'steps':[]}
 def save():(a.output/'setup.json').write_text(json.dumps(report,indent=2)+'\n')
 save()
 if not a.deploy:print(json.dumps({'prepared':True,'sourceFiles':len(records),'sourceArchive':str(archive)}));return
 spec=importlib.util.spec_from_file_location('academy',ROOT/'script/tesis/aws_academy_cluster.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);m.configure_lab('185395')
 state=m.refresh(m.ec2_client(),m.load());head=next(n for n in state['nodes']if n['role']=='head');workers=[n for n in state['nodes']if n['role']!='head']
 if any(n['state']!='running'for n in state['nodes']):raise ValueError('Recorded three nodes must be running')
 def options(n):return ['StrictHostKeyChecking=yes'if v=='StrictHostKeyChecking=accept-new'else v for v in m.ssh_options(n)]
 def ssh(n,cmd,timeout=90):
  r=subprocess.run(['ssh',*options(n),'ubuntu@'+n['public_ip'],'bash -lc '+shlex.quote(cmd)],capture_output=True,text=True,timeout=timeout)
  report['steps'].append({'node':n['name'],'command':cmd,'exitCode':r.returncode,'stdout':r.stdout,'stderr':r.stderr});save()
  if r.returncode:raise RuntimeError(r.stderr[-2000:])
  return r.stdout
 def scp(path,remote,timeout=600):
  subprocess.run(['scp',*options(head),str(path),'ubuntu@'+head['public_ip']+':'+remote],check=True,timeout=timeout)
 ssh(head,'test -z "$(squeue --noheader --format=%k | sed -n \'/helix:/p\')" && sudo test ! -e '+RUNTIME)
 for source,dest in [(archive,'/tmp/helix-strict-public-sources.tar'),(Path('/tmp/helix-strict-dependencies.tar.zst'),'/tmp/helix-strict-dependencies.tar.zst'),(Path('/home/webiwabou/.bun/bin/bun'),'/tmp/helix-strict-bun')]:scp(source,dest)
 for source,dest in [(archive,'/tmp/helix-strict-public-sources.tar'),(Path('/tmp/helix-strict-dependencies.tar.zst'),'/tmp/helix-strict-dependencies.tar.zst')]:
  observed=ssh(head,'sha256sum '+dest)
  if not observed.startswith(sha(source)+' '):raise ValueError('Transferred public runtime changed')
 setup='\n'.join(['set -euo pipefail','sudo apt-get update -qq','sudo apt-get install -y -qq zstd python3-venv',
  'sudo mkdir -p '+RUNTIME,'sudo tar -xf /tmp/helix-strict-public-sources.tar -C '+RUNTIME,
  'sudo tar -I zstd -xf /tmp/helix-strict-dependencies.tar.zst -C '+RUNTIME,
  'sudo install -o root -g root -m755 /tmp/helix-strict-bun /usr/local/bin/helix-strict-bun',
  'sudo python3 -m venv '+RUNTIME+'/python','sudo '+RUNTIME+'/python/bin/pip -q install gemmi==0.7.5',
  'sudo mkdir -p /usr/local/libexec',
  'sudo install -o root -g root -m644 '+RUNTIME+'/packages/helix/src/trp/remote_strict.py.txt /usr/local/libexec/helix-remote-strict-check.py',
  'sudo chmod -R a-w '+RUNTIME,
  'sudo python3 '+RUNTIME+'/script/tesis/provision_remote_strict_profile.py guest-init --output /srv/helix-strict-store/filesystem.json',
  'sudo mkdir -p /srv/helix-strict-results',
  *['sudo exportfs -o rw,sync,no_subtree_check,root_squash '+shlex.quote(n['private_ip']+':/shared/helix-strict')for n in workers],
  'sudo exportfs -v','helix-strict-bun --version',RUNTIME+'/python/bin/python -c "import gemmi;print(gemmi.__version__)"',
  'sha256sum /usr/local/libexec/helix-remote-strict-check.py','du -sb '+RUNTIME,
  'findmnt -n -M /shared/helix-strict -o SOURCE,FSTYPE,OPTIONS,UUID'])
 ssh(head,setup,600)
 for n in workers:
  ssh(n,'sudo mkdir -p /shared/helix-strict && sudo mount -t nfs4 '+shlex.quote(head['private_ip']+':/shared/helix-strict')+' /shared/helix-strict && findmnt -n -M /shared/helix-strict -o SOURCE,FSTYPE,OPTIONS')
 report['ready']=True;report['completedAt']=datetime.now(timezone.utc).isoformat();save();print(json.dumps({'ready':True,'sourceFiles':len(records),'privateCredentialsCopied':False}))
if __name__=='__main__':main()
