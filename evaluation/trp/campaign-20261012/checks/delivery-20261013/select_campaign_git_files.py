#!/usr/bin/env python3
from pathlib import Path
from collections import defaultdict
from datetime import datetime,timezone
import json,subprocess,hashlib,argparse,re
ROOT=Path('/home/webiwabou/Projects/bioinformatica-org');CAMP=ROOT/'evaluation/trp/campaign-20261012'
parser=argparse.ArgumentParser(description='Read-only dated-campaign Git selection; write only a new external proposal directory.')
parser.add_argument('--output',type=Path,required=True);args=parser.parse_args();OUT=args.output.resolve()
if OUT.is_relative_to(ROOT):raise SystemExit('Proposal output must stay outside the repository')
if OUT.exists() and any(OUT.iterdir()):raise SystemExit('Refusing to overwrite an existing proposal')
OUT.mkdir(parents=True,exist_ok=True)
tracked=set(subprocess.check_output(['git','ls-files','-z',str(CAMP.relative_to(ROOT))],cwd=ROOT).decode().split('\0'));tracked.discard('')
pratt_manifest=json.loads((ROOT/'evaluation/trp/reference/pratt-author-20261001/manifest.json').read_text())
pratt_hashes={r['sha256'] for r in pratt_manifest['files'] if r['path'].endswith('.pdb')}
pratt_marker=re.compile(b'|'.join(h.encode() for h in pratt_hashes))
private_derived_records=[]
def vector(v):
 return isinstance(v,list) and len(v)>=3 and all(isinstance(x,(int,float)) and not isinstance(x,bool) for x in v)
def coordinate_keys(node,path=()):
 result=[]
 if isinstance(node,dict):
  if all(k in node and isinstance(node[k],(int,float)) for k in ['x','y','z']):result.append('/'.join(path)+':x/y/z')
  for k,v in node.items():
   if k.lower() in {'xyz','coordinates','coordinate','coords','centroid','center','centres','positions'} and (vector(v) or (isinstance(v,list) and any(vector(x) for x in v))):result.append('/'.join(path+(k,)))
   result.extend(coordinate_keys(v,path+(k,)))
 elif isinstance(node,list):
  for i,v in enumerate(node):result.extend(coordinate_keys(v,path+(str(i),)))
 return result
def private_derived(f):
 if f.suffix!='.json':return False
 raw=f.read_bytes()
 if not pratt_marker.search(raw):return False
 try:data=json.loads(raw)
 except ValueError:return False
 keys=coordinate_keys(data)
 if keys:
  private_derived_records.append({'path':str(f.relative_to(ROOT)),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'coordinateFieldCount':len(keys),'coordinateFieldExamples':keys[:3],'numericCoordinateValuesRecorded':False})
 return bool(keys)
raw={'.pdb','.cif','.mmcif','.xml','.npy','.pile','.pyc','.db','.db-wal','.db-shm','.sqlite','.sqlite3'}
text={'.py','.ts','.txt','.md','.json','.jsonl','.csv','.tsv','.log','.stdout','.stderr','.sh','.nf','.config','.toml','.yaml','.yml','.svg','.png','.pdf','.patch','.sha256','.original','.bak','.err','.out','.trace','.dat'}
# Exact observation/receipt names are retained even inside recovered allocations.
receipt_names={
 'manifest.json','evidence-location.json','run.json','events.jsonl','approval.json','proposal.json','admission.json','analysis-admission.json','inventory.json','remote-inventory.json','remote-analysis-inventory.json','budget.json','specification.json','execution.json','settings.json','protocol.json','methods.json','methods.md','structural_report.json','remote-controller.json','remote-retrieval.json','remote-transfer.json','remote-result.json','remote-terminal.json','remote-job.json','remote-native-jobs.jsonl','remote-native-state.json','remote-cancel.json','remote-task-runtime.json','remote-analysis-approval.json','remote-strict-start.json','remote-strict-before-science.json','remote-strict-after-science.json','remote_strict_policy.json','software.json','mapping_source_report.json','verification.json','trace.tsv','dry-trace.tsv','stdout.log','stderr.log','nextflow.stdout.log','nextflow.stderr.log','nextflow.log','remote-stdout.log','remote-stderr.log','.nextflow.log','supervision.json','export-ready.json','owner-quiescence.json','retained-paths.json','side_effects.json'
}
rows=[];before=datetime.now(timezone.utc).isoformat()
def classify(f):
 rel=f.relative_to(CAMP);parts=rel.parts;n=f.name;ext=f.suffix.lower();rp=str(f.relative_to(ROOT))
 if rp in tracked:return True,True,'already-tracked-retained'
 if private_derived(f):return False,False,'private-Pratt-derived-coordinate-JSON-external-private-archive-only'
 if any(n.endswith(s) for s in ['.tar','.tar.gz','.tgz','.zip','.zst','.7z']):return False,False,'raw-archive-complete-external-only'
 if n.endswith('.xml.gz') or n.endswith('.pdb.gz') or n.endswith('.cif.gz') or ext in raw:return False,False,'raw-coordinates-mapping-array-or-allocated-binary'
 # Exclude only payloads under observed cache locations, retaining cache metadata elsewhere.
 cache_payload=('__pycache__' in parts or ('retained-allocation' in parts and 'cache' in parts[parts.index('retained-allocation')+1:]) or ('bootstrap-import-contrasts' in parts and 'cache' in parts))
 if cache_payload:return False,False,'measured-runtime-cache-payload-external-only'
 if n.startswith('.command.') and not n.endswith('.run'):return True,True,'raw-task-diagnostic-log'
 if 'retained-allocation' in parts:
  tail=parts[parts.index('retained-allocation')+1:]
  if n in receipt_names or n.startswith('remote-strict-') or n.startswith('remote-native-') or n.endswith('.stderr') or n.endswith('.stdout'):
   return True,True,'native-receipt-or-run-decision-metadata'
  if ext in text or n.startswith('.command.') or n in {'.exitcode','.command.exit'}:
   return True,False,'materialized-allocation-duplicate-external-only-in-compact'
  return False,False,'other-materialized-allocation-payload-external-only'
 # Standalone copied bundles are archived in full; Git keeps their anchors/links/logs.
 materialized=('evidence' in parts or 'portable-evidence' in parts or 'copied-bundle' in parts or ('dry-run' in parts))
 if materialized:
  if n in receipt_names or n.startswith('remote-strict-') or n.startswith('remote-native-'):
   return True,True,'portable-receipt-or-run-decision-metadata'
  if ext in text or n in {'.exitcode','.command.exit'}:
   return True,False,'materialized-portable-copy-external-only-in-compact'
  return False,False,'other-materialized-portable-payload-external-only'
 if ext in text or n in {'HEAD','.exitcode'} or n.startswith('.command.'):
  return True,True,'plans-source-freeze-review-science-summary-or-figure'
 return False,False,'other-runtime-payload-external-only'
for f in sorted(CAMP.rglob('*')):
 if f.is_symlink():rows.append({'path':str(f.relative_to(ROOT)),'bytes':0,'symlink':True,'comprehensive':False,'compact':False,'class':'symlink-preserve-only-in-full-external-archive'});continue
 if not f.is_file():continue
 st=f.stat();wide,compact,reason=classify(f);rows.append({'path':str(f.relative_to(ROOT)),'bytes':st.st_size,'mtimeNs':st.st_mtime_ns,'comprehensive':wide,'compact':compact,'class':reason})
for option in ['compact','comprehensive']:
 selected=[r for r in rows if r[option]];(OUT/(option+'-paths.nul')).write_bytes(b''.join(r['path'].encode()+b'\0' for r in selected));(OUT/(option+'-paths.json')).write_text(json.dumps([r['path'] for r in selected],indent=2)+'\n')
classes=defaultdict(lambda:{'files':0,'bytes':0,'compactFiles':0,'compactBytes':0,'comprehensiveFiles':0,'comprehensiveBytes':0})
for r in rows:
 d=classes[r['class']];d['files']+=1;d['bytes']+=r['bytes']
 for o in ['compact','comprehensive']:
  if r[o]:d[o+'Files']+=1;d[o+'Bytes']+=r['bytes']
options={}
for o in ['compact','comprehensive']:
 rs=[r for r in rows if r[o]];options[o]={'files':len(rs),'bytes':sum(r['bytes'] for r in rs),'maxIndividualBytes':max((r['bytes'] for r in rs),default=0),'filesOver100MB':[r['path'] for r in rs if r['bytes']>100000000],'excludedFiles':len(rows)-len(rs),'excludedBytes':sum(r['bytes'] for r in rows if not r[o])}
# No hash/content mutation is needed to propose selection; paths and sizes are a live snapshot.
d={'schema':'helix-campaign-git-selection-proposal/1.0','observedStartUtc':before,'observedEndUtc':datetime.now(timezone.utc).isoformat(),'campaignPath':str(CAMP.relative_to(ROOT)),'campaignFiles':len(rows),'campaignBytes':sum(r['bytes'] for r in rows),'trackedCampaignPaths':len(tracked),'alreadyTrackedNeverExcluded':all(r['compact'] for r in rows if r['path'] in tracked),'options':options,'classes':dict(classes),'fileInventory':rows,'recommendedOption':'comprehensive','selectedByParent':'comprehensive, conditional on private full archive outside repo','privateDerivedCoordinateFiles':private_derived_records,'selectionScriptSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'selectionOnly':True,'gitMutation':False,'archiveCreated':False,'fullArchivePrerequisiteSatisfied':False,'requiresFinalRefreshAfterQuiescence':True,'scope':'Only the dated campaign; no SDK, other untracked work or global ignore rules are changed.'}
(OUT/'selection-review.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps({k:v for k,v in d.items() if k not in ['fileInventory','classes']},indent=2));print(json.dumps(dict(classes),indent=2))
