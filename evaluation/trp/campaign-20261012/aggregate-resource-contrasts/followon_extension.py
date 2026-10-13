#!/usr/bin/env python3
"""Freeze a separate minimum-support cohort, then run it after boundary six.

Quantities respond to observed original unknowns, which remain unchanged. New
graph IDs and budgets are fixed before their own outputs; no terminal retry.
"""
import hashlib,json,os,subprocess,time
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];HERE=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def now():return datetime.now(timezone.utc).isoformat()
while True:
 summary=HERE/'summary.json';terminal=HERE/'campaign-outcomes/terminal.json'
 if terminal.is_file()and json.loads(terminal.read_text()).get('allFrozenCasesObserved')and summary.is_file():
  data=json.loads(summary.read_text());counts=data['originalCounts']
  if counts['observed']==40 and counts['decisionObserved']==40:break
 time.sleep(3)
positive=max(0,20-counts['feasible']);negative=max(0,20-counts['infeasible'])
if positive+negative==0:
 (HERE/'extension-not-required.json').write_text(json.dumps({'at':now(),'originalCounts':counts,'allRequiredClassesPresent':True},indent=2)+'\n');raise SystemExit(0)
for name,digest in json.loads((HERE/'campaign-inputs/freeze.json').read_text())['sourceHashes'].items():
 if sha(ROOT/name)!=digest:raise RuntimeError('Frozen source changed before supplementary freeze: '+name)
request={'schema':'helix-engineering-minimum-supplement/1.0','at':now(),'originalCounts':counts,'originalSummarySha256':sha(summary),'plannedGenerous':positive,'plannedSmall':negative,'firstNewGraph':'G-valid-024','generousBudgetBytes':128*2**20,'smallBudgetsBytes':[64*1024,128*1024],'original40DenominatorUnchanged':True,'boundary6DenominatorUnchanged':True,'newCasesObserved':0,'reason':'Only provide separately reported actual feasible/infeasible support after original observations leave their prospective minimum unfulfilled. Preserve original unknowns; never replace their cases.','sourceSha256':sha(Path(__file__))}
(HERE/'extension-request.json').write_text(json.dumps(request,indent=2)+'\n')
python=subprocess.run(['uv','run','--with','gemmi==0.7.5','python','-c','import sys,gemmi; assert gemmi.__version__=="0.7.5"; print(sys.executable)'],capture_output=True,text=True,check=True).stdout.strip()
env={**os.environ,'HELIX_TRP_PYTHON':python}
r=subprocess.run(['bun',str(HERE/'prepare_extension.ts'),str(HERE/'extension-inputs'),str(positive),str(negative),'minimum-extension'],env=env,capture_output=True,text=True)
(HERE/'extension-freeze-command.json').write_text(json.dumps({'at':now(),'exitCode':r.returncode,'stdout':r.stdout,'stderr':r.stderr,'gemmiVersion':'0.7.5','frozenSourceSha256':sha(HERE/'prepare_extension.ts')},indent=2)+'\n')
if r.returncode:raise RuntimeError('Separate prospective extension freeze failed; no cloud cases submitted')
print(json.dumps({'status':'extension-frozen','positive':positive,'negative':negative,'waitingBoundaryTerminal':True}),flush=True)
while True:
 p=HERE/'boundary-outcomes/terminal.json'
 if p.is_file()and json.loads(p.read_text()).get('allFrozenCasesObserved'):break
 time.sleep(3)
freeze=json.loads((HERE/'extension-inputs/freeze.json').read_text())
for name,digest in freeze['sourceHashes'].items():
 if sha(ROOT/name)!=digest:raise RuntimeError('Frozen source changed before supplement dispatch: '+name)
print(json.dumps({'status':'starting-extension','at':now(),'planned':positive+negative}),flush=True)
r=subprocess.run(['uv','run','--with','boto3','python',str(HERE/'drive_campaign.py'),'--inputs',str(HERE/'extension-inputs'),'--output',str(HERE/'extension-outcomes'),'--namespace','61000','--checkpoint','2026-10-13T08:30:00+00:00'])
(HERE/'extension-conductor-result.json').write_text(json.dumps({'at':now(),'exitCode':r.returncode,'sourceSha256':sha(Path(__file__))},indent=2)+'\n')
raise SystemExit(r.returncode)
