#!/usr/bin/env python3
"""Audit only newly recovered guest evidence; no cloud action or resubmission."""
import argparse,json,subprocess,sys,time
from pathlib import Path
HERE=Path(__file__).resolve().parent
def main():
 p=argparse.ArgumentParser();p.add_argument('--group',choices=['campaign','boundary','extension'],required=True);a=p.parse_args();inputs=HERE/(a.group+'-inputs');outcomes=HERE/(a.group+'-outcomes');last=None
 while True:
  seen=tuple(sorted(str(x)for x in outcomes.glob('*/recovery.json')))
  if seen!=last and seen:
   for name in ['audit_cases.py','audit_cases_resolution.py','audit_cases_fd.py']:
    r=subprocess.run([sys.executable,str(HERE/name),'--inputs',str(inputs),'--outcomes',str(outcomes)],capture_output=True,text=True)
    if r.returncode:print(json.dumps({'audit':name,'exitCode':r.returncode,'stderr':r.stderr[-3000:]}),flush=True);raise RuntimeError('Derived audit failed; no guest work repeated')
   r=subprocess.run([sys.executable,str(HERE/'audit_sqlite.py'),'--outcomes',str(outcomes)],capture_output=True,text=True,check=True)
   summary=subprocess.run([sys.executable,str(HERE/'summarize_campaign.py')],capture_output=True,text=True,check=True);print(summary.stdout.strip(),flush=True);last=seen
  terminal=outcomes/'terminal.json'
  if terminal.is_file()and json.loads(terminal.read_text()).get('allFrozenCasesObserved'):
   print(json.dumps({'group':a.group,'allFrozenCasesObserved':True,'recovered':len(seen)}),flush=True);return
  time.sleep(3)
if __name__=='__main__':main()
