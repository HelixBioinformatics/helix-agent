#!/usr/bin/env python3
"""Read original guest filesystem census and preserve failed operator metadata."""
import argparse,hashlib,importlib.util,json,shlex,subprocess
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[4]
def main():
 p=argparse.ArgumentParser();p.add_argument('--allocation',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();allocation=json.loads(a.allocation.read_text());policy=allocation['policy']
 spec=importlib.util.spec_from_file_location('academy',ROOT/'script/tesis/aws_academy_cluster.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);m.configure_lab('185395');state=m.refresh(m.ec2_client(),m.load());head=next(n for n in state['nodes']if n['role']=='head')
 code='''import json,os,pathlib,subprocess,sys,stat
p=json.loads(sys.argv[1]);rows=[]
for name in ['clientWorkspace','clientStateRoot','clientCacheRoot','temporaryRoot','remoteRoot','exportRoot']:
 root=pathlib.Path(p['paths'][name]);files=[];seen=set();total=0;logical=0;links=[]
 for current,dirs,names in os.walk(root,followlinks=False):
  for item in dirs+names:
   q=pathlib.Path(current)/item;s=q.lstat();key=(s.st_dev,s.st_ino)
   if key in seen:continue
   seen.add(key)
   if q.is_symlink():links.append({'path':str(q),'target':os.readlink(q)});continue
   total+=s.st_blocks*512
   if stat.S_ISREG(s.st_mode):logical+=s.st_size;files.append({'path':str(q.relative_to(root)),'bytes':s.st_size,'blocksBytes':s.st_blocks*512,'device':s.st_dev})
 rows.append({'name':name,'path':str(root),'logicalRegularBytes':logical,'actualFilesystemBlocksBytes':total,'regularFiles':len(files),'files':files,'links':links})
group=pathlib.Path('/sys/fs/cgroup')/p['controller']['cgroup']
print(json.dumps({'at':__import__('time').time(),'rows':rows,'cgroup':{n:(group/n).read_text().strip()for n in ['cgroup.procs','cgroup.events','memory.events','memory.peak']},'quotaRaw':subprocess.check_output(['xfs_quota','-x','-c','report -p -b -n',p['filesystem']['mountPoint']],text=True),'scope':'Actual original guest stat blocks after terminal, not local retained-copy allocation and not a sampled peak'}))
'''
 cmd='sudo python3 -c '+shlex.quote(code)+' '+shlex.quote(json.dumps(policy))
 options=['StrictHostKeyChecking=yes'if v=='StrictHostKeyChecking=accept-new'else v for v in m.ssh_options(head)]
 r=subprocess.run(['ssh',*options,'ubuntu@'+head['public_ip'],cmd],text=True,capture_output=True,timeout=60)
 report={'observerSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'observedAt':datetime.now(timezone.utc).isoformat(),'command':cmd,'exitCode':r.returncode,'stdout':r.stdout,'stderr':r.stderr,'allocationSha256':hashlib.sha256(a.allocation.read_bytes()).hexdigest()}
 if r.returncode==0:report['census']=json.loads(r.stdout)
 a.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'exitCode':r.returncode,'originalGuestCensus':r.returncode==0}))
if __name__=='__main__':main()
