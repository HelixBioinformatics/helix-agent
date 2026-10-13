#!/usr/bin/env python3
"""Run the separately frozen six boundary cases after the original conductor.

No retry of original terminal cases, cloud lifecycle changes or producer edits.
"""
import hashlib,json,subprocess,time
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];HERE=Path(__file__).resolve().parent
out=HERE/'boundary-outcomes';out.mkdir(exist_ok=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
record={'at':datetime.now(timezone.utc).isoformat(),'originalFreezeSha256':sha(HERE/'campaign-inputs/freeze.json'),'boundaryFreezeSha256':sha(HERE/'boundary-inputs/freeze.json'),'namespace':60000,'checkpointUtc':'2026-10-13T08:30:00+00:00','onlyAfterOriginalTerminal':True,'retriesOriginal':False,'sourceSha256':sha(Path(__file__))}
(HERE/'boundary-orchestration-plan.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps({'status':'waiting-original-terminal','namespace':60000}),flush=True)
while True:
 p=HERE/'campaign-outcomes/terminal.json'
 if p.is_file()and json.loads(p.read_text()).get('allFrozenCasesObserved'):break
 time.sleep(3)
freeze=json.loads((HERE/'boundary-inputs/freeze.json').read_text())
for name,digest in freeze['sourceHashes'].items():
 if sha(ROOT/name)!=digest:raise RuntimeError('Frozen producer or harness changed: '+name)
print(json.dumps({'status':'starting-boundary6','at':datetime.now(timezone.utc).isoformat()}),flush=True)
r=subprocess.run(['uv','run','--with','boto3','python',str(HERE/'drive_campaign.py'),'--inputs',str(HERE/'boundary-inputs'),'--output',str(out),'--namespace','60000','--checkpoint','2026-10-13T08:30:00+00:00'])
(HERE/'boundary-conductor-result.json').write_text(json.dumps({'at':datetime.now(timezone.utc).isoformat(),'exitCode':r.returncode,'sourceSha256':sha(Path(__file__))},indent=2)+'\n')
raise SystemExit(r.returncode)
