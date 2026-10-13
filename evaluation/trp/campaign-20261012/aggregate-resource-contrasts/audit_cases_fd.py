#!/usr/bin/env python3
"""Independent cold physical-feasibility audit of same-scope full-client runs.

Never infer labels from budget/cohort/estimator or portable approval claims.
Counterfactual gate overrides are identified separately from actual decisions.
"""
import argparse,csv,hashlib,json,re,runpy,sqlite3
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text())
def telemetry(p):
 result={}
 for line in p.read_text().splitlines():
  if line.startswith('HELIX_')and ':'in line:
   kind,value=line.split(':',1)
   try:result.setdefault(kind,[]).append(json.loads(value))
   except json.JSONDecodeError:pass
 return result

def audit(local,item):
 allocation=load(local/'allocation.json');policy=allocation['policy']
 guest=Path(load(local/'dispatch-intent.json')['guest']).name
 base=local/'recovered'/guest;s=load(base/'supervision.json')
 t=telemetry(base/'experiment-telemetry.stdout');stderr=(base/'experiment-telemetry.stderr').read_text()
 checks=[]
 def require(name,ok,detail=None):checks.append({'name':name,'ok':bool(ok),'detail':detail});return bool(ok)
 require('root-allocation-policy-binding',s['policySha256']==allocation['policySha256'])
 require('exact-kernel-budget',policy['entitlement']=={'cpus':3,'memoryBytes':4*1024**3,'workBytes':item['budget']['workBytes'],'wallSeconds':1080})
 require('owner-quiescence',s['nativeCleanup']['remaining']==[])
 if 'finalCgroup'in s:
  require('real-controller-and-tracer-reaped',s['controllerAndTracerReaped']and s['finalCgroup']['cgroup.procs']==''and 'populated 0'in s['finalCgroup']['cgroup.events'])
 quotas=[s['initialQuota'],*[x['quota']for x in s['samples']],s['finalQuota']]
 for index,q in enumerate(quotas):
  q=q['quota'];raw=q.get('treeCheckRawStdout',q['treeCheckStdout']);expected=[f"Checking project {policy['filesystem']['projectId']} (path {policy['paths']['allocationRoot']})...",f"Processed 1 (/etc/projects and cmdline) paths for project {policy['filesystem']['projectId']} with recursion depth infinite (-1)."]
  normalized=''if raw.splitlines()==expected else raw
  # Retain genuine older refusal in failed smoke; never reinterpret its checker.
  normalization=(q['treeCheckStdout']==normalized)if q.get('treeCheckStdoutIsDiagnostics')else(q['treeCheckStdout']==raw)
  require('raw-recursive-source-'+str(index),normalization)
  require('kernel-project-quota-'+str(index),q['hardBytes']==item['budget']['workBytes']and q['usedBytes']<=q['hardBytes']and q['treeCheckExitCode']==0 and not q['treeCheckStderr'])
 for index,row in enumerate(s['samples']):
  c=row['cgroup'];require('shared-client-controller-cap-'+str(index),c['cpu.max']=='100000 100000'and c['memory.max']=='2147483648'and c['memory.swap.max']=='0')
 decisions=t.get('HELIX_REAL_ADMISSION',[]);decision=decisions[0]['decision']if len(decisions)==1 else None
 if decision is not None:
  require('actual-unmodified-decision-source',decisions[0]['sourceSha256']==sha(ROOT/'packages/helix/src/trp/resources.ts'))
  require('actual-bound-decision-policy',decisions[0]['policySha256']==allocation['policySha256'])
  require('actual-decision-budget-hash',decision['budgetHash']==hashlib.sha256(json.dumps(item['budget'],sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest())
 label=None;reason='Not established from terminal production or causal kernel evidence'
 outcome=t.get('HELIX_FULL_TERMINAL',[None])[-1]
 database=[];allocationTree=base/'retained-allocation'
 for db in allocationTree.rglob('*.db'):
  if db.read_bytes()[:16]==b'SQLite format 3\x00':database.append({'path':str(db.relative_to(allocationTree)),'bytes':db.stat().st_size,'sha256':sha(db)})
 native=[];cold=None
 if outcome and outcome.get('status')=='succeeded':
  export=allocationTree/'export/portable-evidence';manifest=load(export/'manifest.json')
  # This independently checks every actual exported byte before semantic checks.
  listed=manifest['files'];listed=listed.items()if isinstance(listed,dict)else((r['path'],r)for r in listed)
  manifestOK=True
  for name,record in listed:
   p=export/name
   digest=record['sha256']if isinstance(record,dict)else record
   manifestOK=manifestOK and p.is_file()and sha(p)==digest
  require('actual-portable-export-integrity',manifestOK)
  trusted=runpy.run_path(str(ROOT/'packages/helix/src/trp/verify_bundle.py.txt'),run_name='trusted_cold')
  try:cold=trusted['verify'](export,sha(export/'manifest.json'))
  except Exception as error:cold={'ok':False,'error':str(error)}
  require('ordinary-default-cold-verification',outcome['executionOracleForcedOnly']or cold['ok'],cold)
  require('actual-persistent-sqlite',len(database)>0,database)
  run=export/'run';ids=set()
  for filename in ['trace.tsv','dry-run/trace.tsv']:
   rows=list(csv.DictReader((run/filename).read_text().splitlines(),delimiter='\t'))
   require('actual-two-completed-'+filename,len(rows)==2 and all(r['status']=='COMPLETED'and r['exit']=='0'for r in rows))
   ids.update(r['native_id']for r in rows)
  require('actual-four-distinct-native-jobs',len(ids)==4,sorted(ids))
  snapshots=[json.loads(x)for x in(run/'remote-native-jobs.jsonl').read_text().splitlines()if x]
  observed={str(r['id']):r for x in snapshots for r in x['records']if r['state']=='COMPLETED'}
  require('native-completion-and-placement',ids<=set(observed)and all(observed[i]['nodes']in ['helix-worker1','helix-worker2']for i in ids),observed)
  runtime=load(run/'remote-task-runtime.json')['records']
  require('actual-worker-runtime-caps',len(runtime)==2 and all(r['cpuMax']=='200000 100000'and r['memoryMax']=='2147483648'and r['swapMax']=='0'and r['threads']=='1'and r['numericalProfile']=='Haswell'for r in runtime))
  require('correct-own-input-gold',sha(run/'results/geometry.csv')==item['goldCsvSha256'])
  for name in ['remote-strict-start.json','remote-strict-before-science.json']:
   try:trusted['strict_receipt'](load(run/name),load(run/'remote_strict_policy.json'));ok=True
   except Exception as error:ok=False
   require('actual-strict-receipt-'+name,ok)
  reproduction=t.get('HELIX_DEMAND_REPRODUCED',[])
  require('actual-prospective-count-reproducibility',len(reproduction)==1 and reproduction[0]['prospective']==reproduction[0]['actual']==decision['demand'])
  if all(x['ok']for x in checks):label=True;reason='Full actual client, native four tasks, own-input gold, persistent SQLite, portable export, kernel quota and cgroups verified'
 else:
  exceptions=t.get('HELIX_CLIENT_THROW',[])
  causalEDQUOT=any(x.get('code')=='EDQUOT'or x.get('errno')==-122 for x in exceptions)
  kernelQuotaFailures=[];pending={}
  mechanismPath=Path(__file__).parent/'copy-causal-controls/mechanism-review.json'
  qualified=mechanismPath.is_file()and load(mechanismPath).get('mechanismQualified')is True
  health=s.get('initialGlobalFilesystemHealth',{})
  globalHealthy=health.get('globalFreeBytes',0)>max(item['sourceInputSha256']and 359397,16*1024**2)and health.get('globalFreeInodes',0)>1000 and health.get('device')==policy['filesystem']['device']
  permitEnospc=qualified and globalHealthy
  for line in stderr.splitlines():
   pid=re.match(r'\[pid\s+(\d+)\]',line);key=pid.group(1)if pid else 'main'
   if '<unfinished ...>'in line:pending[key]=line;continue
   resumed=re.search(r'<\.\.\. (\w+) resumed>',line)
   source=line
   if resumed:
    entry=pending.pop(key,'')
    if re.search(r'\b'+resumed.group(1)+r'\(',entry):source=entry+'\n'+line
   if ('= -1 EDQUOT (Disk quota exceeded)'in line or (permitEnospc and '= -1 ENOSPC (No space left on device)'in line))and policy['paths']['allocationRoot']in source:kernelQuotaFailures.append(source)
  # Ignored optional cache writes cannot label an unrelated terminal failure.
  causallyLinked=[]
  for failure in exceptions:
   fatalIo=bool(re.search(r'EDQUOT|ENOSPC|Disk quota exceeded|No space left on device|database or disk is full|disk I/O error',failure.get('message',''),re.I))or(failure.get('code')=='SQLITE_CANTOPEN'and failure.get('message')=='unable to open database file')
   paths=[failure.get(k)for k in ['path','dest']if failure.get(k)]
   if failure.get('code')=='SQLITE_CANTOPEN':paths.append(policy['paths']['clientStateRoot']+'/data/helix/helix-local.db')
   paths+=re.findall(re.escape(policy['paths']['allocationRoot'])+r'''[^\s'"<>)]*''',failure.get('message',''))
   # Bun reports the terminal descriptor in its fatal error diagnostics even
   # when fs.writeFile does not expose a path on the Error object. This link
   # requires that exact descriptor, a matching failed write, and the solely
   # owned strace process tree. It does not infer a filename from the estimator.
   terminalFds=[]
   if failure.get('code')=='ENOSPC'and failure.get('syscall')=='write':
    terminalFds=[int(v)for v in re.findall(r'fd:\s*(\d+),\s*syscall:\s*"write",\s*errno:\s*-28,\s*code:\s*"ENOSPC"',stderr)]
   for syscall in kernelQuotaFailures:
    if terminalFds:
     descriptor=re.search(r'\b(?:write|pwrite64|writev|pwritev)\((\d+)<([^>]+)>',syscall)
     tracedPid=re.search(r'\[pid\s+(\d+)\]',syscall)
     owned=(tracedPid is not None and (int(tracedPid.group(1))==failure.get('pid')or('Process '+tracedPid.group(1)+' attached')in stderr))
     argv=s.get('clientArgv',[])
     dedicatedTrace=argv[:5]==['/usr/bin/strace','-f','-Z','-yy','-ttt']and any(str(v).endswith('/aggregate-resource-contrasts/full_client.ts')for v in argv)and str(argv[-1]).endswith('/'+item['id']+'.json')
     if descriptor and int(descriptor.group(1))in terminalFds and owned and dedicatedTrace and descriptor.group(2).startswith(policy['paths']['allocationRoot']+'/'):paths.append(descriptor.group(2))

    times=[float(v)for v in re.findall(r'(?:^|\] )([0-9]{10}\.[0-9]+)',syscall,re.M)]
    at=failure.get('failedAtEpochSeconds')
    # JavaScript Date.now() has millisecond resolution, whereas strace emits
    # microseconds. A syscall from the same rounded millisecond can therefore
    # appear up to one millisecond after the logged terminal exception.
    near=at is not None and times and -.001<=at-max(times)<=5
    pathMatches=any(str(v)in syscall for v in paths)or(not paths and bool(re.search(r'\.db(?:-wal|-journal)?[>\"]',syscall)))
    if fatalIo and near and pathMatches:causallyLinked.append({'failure':failure,'kernelSyscall':syscall})
  if causallyLinked and all(x['ok']for x in checks):label=False;reason='Actual terminal I/O failure linked by path and timestamp to kernel EDQUOT or independently qualified quota-reservation ENOSPC under matching enforced quota'
  elif s['terminationCause']=='actual-controller-cgroup-oom'and all(x['ok']for x in checks):label=False;reason='Actual shared controller kernel cgroup OOM observed'
 peak=max(q['quota']['usedBytes']for q in quotas);predicted=decision['demand']['workBytes']if decision else None
 return {'case':item['id'],'physicalFeasibilityLabel':label,'labelReason':reason,'actualDecision':decision,
  'defaultPortableVerifier':cold,'executionOracleForcedOnly':outcome.get('executionOracleForcedOnly')if outcome else (t.get('HELIX_ORACLE_MODE',[{}])[-1].get('executionOracleForcedOnly')),
  'allocatedBlockBytesObservedPeak':peak,'allocatedBlockBytesFinal':s['finalQuota']['quota']['usedBytes'],
  'predictedWorkBytes':predicted,'observedUnderestimateBytes':max(0,peak-predicted)if predicted else None,
  'observedOverestimationFraction':(predicted-peak)/peak if predicted and label is True else None,
  'kernelMemoryPeak':max(int(x['cgroup']['memory.peak'])for x in s['samples']),
  'causalKernelQuotaFailures':kernelQuotaFailures if not outcome else [],
  'causallyLinkedTerminalIoFailures':causallyLinked if not outcome else [],
  'actualExitCode':s['actualExitCode'],'terminationCause':s['terminationCause'],'elapsedSeconds':s['elapsedSeconds'],
  'persistentSqlite':database,'checks':checks,'checksPassed':sum(c['ok']for c in checks),'checksTotal':len(checks),
  'supervisionSha256':sha(base/'supervision.json'),'retainedArchiveSha256':sha(local/'actual-allocation-and-supervisor.tar'),
  'causalTimestampQuantizationToleranceSeconds':.001,'scientificR24Rate':None,'scope':'Engineering, one development protein, actual aggregate client/head declared paths plus sequential worker tasks; infrastructure/runtime/Docker caches and experiment-only root telemetry excluded'}

def main():
 p=argparse.ArgumentParser();p.add_argument('--inputs',type=Path,required=True);p.add_argument('--outcomes',type=Path,required=True);a=p.parse_args();plan=load(a.inputs/'freeze.json');rows=[]
 for item in plan['cases']:
  local=a.outcomes/item['id']
  if not(local/'recovery.json').is_file():continue
  try:r=audit(local,item)
  except Exception as error:r={'case':item['id'],'physicalFeasibilityLabel':None,'auditError':str(error),'scientificR24Rate':None}
  output=local/'review-fd.json';encoded=json.dumps(r,indent=2)+'\n'
  if output.is_file()and output.read_text()!=encoded:
   historical=local/'review-history';historical.mkdir(exist_ok=True)
   archived=historical/(sha(output)+'.json')
   if not archived.exists():archived.write_bytes(output.read_bytes())
  r['frozenAuditSha256']=sha(local/'independent-audit.json');r['reviewSourceSha256']=sha(Path(__file__));r['amendmentSha256']=sha(Path(__file__).parent/'auditor-fd-amendment.json');encoded=json.dumps(r,indent=2)+'\n'
  output.write_text(encoded);rows.append(r)
 summary={'schema':'helix-aggregate-resource-causal-review/1.0','freezeSha256':sha(a.inputs/'freeze.json'),'rows':rows,'actualObservedCases':len(rows),'actualFeasible':sum(r['physicalFeasibilityLabel']is True for r in rows),'actualInfeasible':sum(r['physicalFeasibilityLabel']is False for r in rows),'unknown':sum(r['physicalFeasibilityLabel']is None for r in rows),'scientificR24Rate':None,'auditSourceSha256':sha(Path(__file__))}
 (a.outcomes/'review-fd-summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps({k:v for k,v in summary.items()if k!='rows'}))
if __name__=='__main__':main()
