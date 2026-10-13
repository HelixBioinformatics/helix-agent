#!/usr/bin/env python3
"""Install an anchored public source revision before a prospective campaign."""
import argparse,importlib.util,json,shlex,subprocess,hashlib
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[4]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--sources',type=Path,required=True);a=p.parse_args()
 setup=json.loads((a.sources/'setup.json').read_text());archive=a.sources/'public-sources.tar'
 if sha(archive)!=setup['sourceArchiveSha256']:raise ValueError('Anchored source package changed')
 spec=importlib.util.spec_from_file_location('academy',ROOT/'script/tesis/aws_academy_cluster.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);m.configure_lab('185395');state=m.refresh(m.ec2_client(),m.load());head=next(n for n in state['nodes']if n['role']=='head')
 options=['StrictHostKeyChecking=yes'if x=='StrictHostKeyChecking=accept-new'else x for x in m.ssh_options(head)]
 remote='/tmp/helix-strict-source-'+sha(archive)[:12]+'.tar'
 subprocess.run(['scp',*options,str(archive),'ubuntu@'+head['public_ip']+':'+remote],check=True,timeout=120)
 cmd='sudo apt-get install -y -qq strace && strace --version && test -z "$(squeue -h --format=%k | sed -n \'/helix:/p\')" && sha256sum '+remote+' && sudo chmod -R u+w /opt/helix-strict-runtime && sudo tar -xf '+remote+' -C /opt/helix-strict-runtime && sudo chmod -R a-w /opt/helix-strict-runtime && sha256sum /opt/helix-strict-runtime/packages/helix/src/trp/remote_runner.py.txt /opt/helix-strict-runtime/packages/helix/src/trp/remote_strict.py.txt /usr/local/libexec/helix-remote-strict-check.py'
 r=subprocess.run(['ssh',*options,'ubuntu@'+head['public_ip'],'bash -lc '+shlex.quote(cmd)],capture_output=True,text=True,timeout=120)
 report={'at':datetime.now(timezone.utc).isoformat(),'archiveSha256':sha(archive),'sourceFiles':setup['sourceFiles'],'exitCode':r.returncode,'stdout':r.stdout,'stderr':r.stderr,'jobsSubmitted':0,'privateCredentialsCopied':False}
 (a.sources/'applied.json').write_text(json.dumps(report,indent=2)+'\n')
 if r.returncode or sha(archive)+' ' not in r.stdout:raise ValueError('Source refresh failed or transfer differed')
 print(json.dumps({'applied':True,'sourceFiles':len(setup['sourceFiles']),'archiveSha256':sha(archive)}))
if __name__=='__main__':main()
