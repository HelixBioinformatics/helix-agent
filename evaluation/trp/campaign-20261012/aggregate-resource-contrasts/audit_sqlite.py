#!/usr/bin/env python3
"""Reopen retained actual SQLite files in immutable, read-only mode.

This is an additional cold artifact check. It does not rerun or migrate Helix,
change a resource label, or write to the retained database/WAL.
"""
import argparse,hashlib,json,sqlite3
from pathlib import Path
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--outcomes',type=Path,required=True);a=p.parse_args();rows=[]
 for folder in sorted(a.outcomes.glob('*')):
  if not folder.is_dir()or not(folder/'recovery.json').is_file():continue
  reports=[]
  for db in sorted((folder/'recovered').rglob('helix-local.db')):
   before=sha(db)
   try:
    with sqlite3.connect(db.resolve().as_uri()+'?mode=ro&immutable=1',uri=True)as connection:
     check=connection.execute('PRAGMA quick_check').fetchall();tables=[r[0]for r in connection.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
     projects=connection.execute('SELECT COUNT(*) FROM project').fetchone()[0]if'project'in tables else None
    ok=check==[('ok',)]and 'project'in tables and projects is not None and projects>=1
    reports.append({'path':str(db.relative_to(folder)),'databaseSha256':before,'bytes':db.stat().st_size,'quickCheck':check,'tables':tables,'projectCount':projects,'validRealProjectDatabase':ok,'unchanged':sha(db)==before})
   except sqlite3.DatabaseError as error:reports.append({'path':str(db.relative_to(folder)),'databaseSha256':before,'error':str(error),'validRealProjectDatabase':False,'unchanged':sha(db)==before})
  row={'case':folder.name,'databases':reports,'immutableReadOnly':True,'sourceSha256':sha(Path(__file__))};(folder/'sqlite-cold-reopen.json').write_text(json.dumps(row,indent=2)+'\n');rows.append(row)
 report={'schema':'helix-actual-sqlite-cold-reopen/1.0','rows':rows,'casesWithRealProjectDatabase':sum(any(d['validRealProjectDatabase']and d['unchanged']for d in r['databases'])for r in rows),'sourceSha256':sha(Path(__file__)),'scientificMetricsSubstituted':False}
 (a.outcomes/'sqlite-cold-summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items()if k!='rows'}))
if __name__=='__main__':main()
