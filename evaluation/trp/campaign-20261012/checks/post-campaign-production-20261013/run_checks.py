#!/usr/bin/env python3
"""Owned local post-campaign checks. Never launches live scientific/cloud runs."""
import argparse,hashlib,json,os,pathlib,re,subprocess,sys,time
from datetime import datetime,timezone
ROOT=pathlib.Path(__file__).resolve().parents[5];OUT=pathlib.Path(__file__).resolve().parent
PYTHON='/home/webiwabou/.local/state/helix/freesasa-20261012/venv/bin/python'
sha=lambda x:hashlib.sha256(x).hexdigest()
parser=argparse.ArgumentParser();parser.add_argument('--check',choices=['backend','broad','typecheck'],required=True);args=parser.parse_args()
commands={
 'backend':['bun','test','test/trp/workflow-backend.test.ts','--timeout','60000'],
 'broad':['bun','test','test/trp','test/bio','test/nfcore','test/tool/trp-detect.test.ts','test/tool/trp-detect-question.test.ts','test/tool/trp-predicted.test.ts','test/plugin/codex.test.ts','--timeout','30000'],
 'typecheck':['bun','run','typecheck'],
}
env=os.environ.copy();removed=[]
for k in list(env):
 if k.startswith('TRP_') or k.startswith('HELIX_TRP_'):
  removed.append(k);env.pop(k)
env['HELIX_TRP_PYTHON']=PYTHON
if args.check=='backend':
 evidence=OUT/'backend-results';evidence.mkdir(exist_ok=True);env['TRP_BACKEND_TEST_OUTPUT']=str(evidence)
log=OUT/(args.check+'.log');summary=OUT/(args.check+'-summary.json')
if log.exists() or summary.exists():raise SystemExit('Refusing overwrite: choose a new owned review directory or explicitly preserve prior failure first')
pinned=subprocess.run([PYTHON,'-c','import gemmi;print(gemmi.__version__)'],capture_output=True,text=True,timeout=10)
assert pinned.returncode==0 and pinned.stdout.strip()=='0.7.5'
start=time.monotonic()
with log.open('wb') as stream:process=subprocess.run(commands[args.check],cwd=ROOT/'packages/helix',env=env,stdout=stream,stderr=subprocess.STDOUT)
text=log.read_text(errors='replace');stats={}
for name,pattern in [('passed',r'^\s*(\d+) pass\s*$'),('skipped_opt_in',r'^\s*(\d+) skip\s*$'),('failed',r'^\s*(\d+) fail\s*$'),('assertions',r'^\s*(\d+) expect\(\) calls\s*$')]:
 values=re.findall(pattern,text,re.M);stats[name]=int(values[-1]) if values else None
match=re.findall(r'Ran (\d+) tests across (\d+) files?',text)
if match:stats.update(tests=int(match[-1][0]),files=int(match[-1][1]))
result={'schema':'helix-post-campaign-production-local-check/1.0','observedAtUtc':datetime.now(timezone.utc).isoformat(),'command':commands[args.check],'cwd':'packages/helix','environment':{'HELIX_TRP_PYTHON':PYTHON,'gemmiVersion':'0.7.5','liveSwitchesCleared':True,'removedVariableNames':removed,'TRP_BACKEND_TEST_OUTPUT':env.get('TRP_BACKEND_TEST_OUTPUT')},'exitCode':process.returncode,'elapsedSeconds':time.monotonic()-start,'logSha256':sha(log.read_bytes()),'statistics':stats,'sourceHashes':{n:sha((ROOT/n).read_bytes()) for n in ['packages/helix/src/trp/workflow.ts','packages/helix/src/trp/verify_bundle.py.txt','packages/helix/src/trp/remote_runner.py.txt','packages/helix/test/trp/workflow-backend.test.ts']},'scope':'Local production regression/type checks only; mocked unit boundaries and optional skips retain their declared scope. No new science/model/cloud observations.'}
summary.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False,indent=2));raise SystemExit(process.returncode)
