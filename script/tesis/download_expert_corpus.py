#!/usr/bin/env python3
"""Retrieve public inputs and check technical admissibility, never run inference.
Requires biopython and gemmi. Reuse archived source bytes on reruns.
"""
import json,hashlib,urllib.request,urllib.parse,time,concurrent.futures,importlib.util,subprocess
from pathlib import Path
from Bio.PDB.MMCIF2Dict import MMCIF2Dict
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'evaluation/trp/corpus-20260930'; DATA=ROOT/'docs/tesis/evaluacion-experta-20260930/para-asesora/datos'
spec=importlib.util.spec_from_file_location('guard',ROOT/'script/tesis/strpsearch_guard.py');guard=importlib.util.module_from_spec(spec);spec.loader.exec_module(guard)
preflight=json.loads((BASE/'pdb-preflight-selection.json').read_text())['entries']
records=[]
def fetch(url,path):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
 if path.exists():return path.read_bytes()
 for attempt in range(2):
  try:
   result=subprocess.run(['curl','--fail','--location','--silent','--show-error','--max-time','25','--max-filesize','50000000',url],capture_output=True)
   if result.returncode:raise RuntimeError(result.stderr.decode(errors='replace')[:250])
   raw=result.stdout
   if len(raw)>50_000_000:raise ValueError('File over 50 MB')
   path.write_bytes(raw);return raw
  except Exception:
   if attempt==1:raise
   time.sleep(1)
def js(url,path):return json.loads(fetch(url,path))
def sha(x):return hashlib.sha256(x.encode()).hexdigest()
query='(reviewed:true) AND (ft_repeat:*) AND (length:[150 TO 600])'
url='https://rest.uniprot.org/uniprotkb/search?'+urllib.parse.urlencode({'query':query,'format':'json','size':500,'fields':'accession,id,protein_name,organism_name,length,sequence,ft_repeat,xref_pfam,xref_pdb'})
pool=js(url,BASE/'sources/uniprot-pool.json')['results']
excluded=set();dev=[]
for acc in ['Q9MCI8','P19148','P69905']:
 d=js('https://rest.uniprot.org/uniprotkb/'+acc+'.json',BASE/'sources'/f'development-{acc}.json');pf={x['id'] for x in d.get('uniProtKBCrossReferences',[]) if x['database']=='Pfam'};excluded|=pf;dev.append({'accession':acc,'pfam':sorted(pf)})
entries=[]
for d in pool:
 pf={r['id'] for r in d.get('uniProtKBCrossReferences',[]) if r['database']=='Pfam'}
 if not pf or pf&excluded:continue
 units=[]
 for f in d.get('features',[]):
  if f['type']!='Repeat':continue
  a,b=f['location']['start'],f['location']['end']
  if a.get('modifier')!='EXACT' or b.get('modifier')!='EXACT':continue
  if b['value']-a['value']+1>=8:units.append({'start':a['value'],'end':b['value'],'description':f.get('description',''),'evidences':f.get('evidences',[])})
 units.sort(key=lambda u:u['start'])
 if len(units)<3 or any(a['end']>=b['start'] for a,b in zip(units,units[1:])):continue
 entries.append({'acc':d['primaryAccession'],'pfam':sorted(pf),'units':units[:3],'record':d,'sort':sha('trp-eval-1.0.1|'+d['primaryAccession'])})
entries.sort(key=lambda d:d['sort'])
# Family components share any Pfam identifier; reserve whole components, never split into development.
parent={e['acc']:e['acc'] for e in entries}
def root(a):
 while parent[a]!=a:a=parent[a]
 return a
seen={}
for e in entries:
 for pf in e['pfam']:
  if pf in seen:parent[root(e['acc'])]=root(seen[pf])
  else:seen[pf]=e['acc']
components={}
for e in entries:components.setdefault(root(e['acc']),[]).append(e['acc'])
for e in entries:e['family']='F-'+sha('|'.join(sorted(components[root(e['acc'])])))[:12]
# Avoid large families occupying first positions; deterministic round-robin over components.
groups={}
for e in entries:groups.setdefault(e['family'],[]).append(e)
ordered=[]
while any(groups.values()):
 for key in sorted(groups,key=lambda k:sha('trp-eval-1.0.1|'+k)):
  if groups[key]:ordered.append(groups[key].pop(0))
(BASE/'selection-plan.json').write_text(json.dumps({'source_url':url,'pool_limit':500,'returned':len(pool),'eligible':len(entries),'development_exclusions':dev,'excluded_pfam':sorted(excluded),'rule':'Reviewed UniProt entries, length 150-600, >=3 disjoint exact Repeat features of length >=8, Pfam known and no development-family overlap. Finite first API page; not a census. Group by shared Pfam, reserve whole components. Hash-order components then accession; round-robin for coverage. 10 PDB detection +15 AFDB detection +25 AFDB supplied-unit geometry, unique accessions. All selections before agent inference.','freeze_status':'pending_expert_review','eligible_entries':[{'acc':e['acc'],'pfam':e['pfam'],'family':e['family'],'sort':e['sort']} for e in ordered]},ensure_ascii=False,indent=2))
print('pool',len(pool),'eligible',len(entries),'families',len(components),flush=True)
def name(d):return d.get('proteinDescription',{}).get('recommendedName',{}).get('fullName',{}).get('value',d['uniProtkbId'])
def build(e,kind):
 acc=e['acc'];d=e['record'];tmp=BASE/'sources'/acc;folder=DATA/acc;folder.mkdir(exist_ok=True)
 def save(n,raw,url=None):
  (folder/n).write_bytes(raw)
  return {'path':f'datos/{acc}/{n}','url':url,'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}
 files=[save('uniprot.json',json.dumps(d,ensure_ascii=False,indent=2).encode(),url)]
 if kind=='pdb':
  refs=sorted([r for r in d.get('uniProtKBCrossReferences',[]) if r['database']=='PDB'],key=lambda r:sha(r['id']))
  errors=[]
  refs=[r for r in refs if r['id'].lower()==preflight.get(acc)]
  for ref in refs:
   try:
    pdb=ref['id'].lower();u='https://files.rcsb.org/download/'+pdb.upper()+'.cif';raw=fetch(u,tmp/f'{pdb}.cif');cif=MMCIF2Dict(str(tmp/f'{pdb}.cif'))
    # Crossreference chains refer to author chain names; select only explicitly linked and present chains.
    cp=next(p['value'] for p in ref.get('properties',[]) if p['key']=='Chains')
    chains=sorted(set(c.strip() for spec in cp.split(',') for c in spec.split('=')[0].split('/')))
    auth=cif['_atom_site.auth_asym_id'];atoms=cif['_atom_site.label_atom_id'];mods=cif.get('_atom_site.pdbx_PDB_model_num',['1']*len(auth))
    counts={c:sum(a==c and t=='CA' and m=='1' for a,t,m in zip(auth,atoms,mods)) for c in chains}
    chain=next(c for c in chains if 30<=counts[c]<=650)
    checkdir=tmp/(pdb+'-input-check');checkdir.mkdir(exist_ok=True)
    guard.prepare_inner(tmp/f'{pdb}.cif',chain,checkdir)
    # Confirm accession identity independently in the selected RCSB polymer entity.
    idx=next(i for i,(a,t,m) in enumerate(zip(auth,atoms,mods)) if a==chain and t=='CA' and m=='1');ent=cif['_atom_site.label_entity_id'][idx]
    eu=f'https://data.rcsb.org/rest/v1/core/polymer_entity/{pdb.upper()}/{ent}';entity=js(eu,tmp/f'{pdb}-entity-{ent}.json')
    ids=entity['rcsb_polymer_entity_container_identifiers'].get('uniprot_ids',[])
    if acc not in ids:raise ValueError('UniProt accession not confirmed by RCSB')
    files+=[save(f'{pdb}.cif',raw,u),save('entidad-rcsb.json',json.dumps(entity,ensure_ascii=False,indent=2).encode(),eu)]
    return {'acc':acc,'kind':kind,'pdb':pdb,'chain':chain,'model':1,'family':e['family'],'pfam':e['pfam'],'protein':name(d),'organism':d['organism']['scientificName'],'length':d['sequence']['length'],'ca_count':counts[chain],'files':files}
   except Exception as ex:errors.append(str(ex)[:120])
  raise ValueError('PDB attempts: '+str(errors))
 else:
  au='https://alphafold.ebi.ac.uk/api/prediction/'+acc;api=js(au,tmp/'api.json')
  a=next(v for v in api if v.get('uniprotAccession')==acc and v.get('uniprotStart')==1 and v.get('uniprotEnd')==d['sequence']['length'] and v.get('uniprotSequence')==d['sequence']['value'])
  for field,n in [('cifUrl','modelo.cif'),('paeDocUrl','pae.json')]:
   raw=fetch(a[field],tmp/n);files.append(save(n,raw,a[field]))
  cif=MMCIF2Dict(str(tmp/'modelo.cif'));pae=json.loads((tmp/'pae.json').read_bytes())[0]['predicted_aligned_error'];ln=d['sequence']['length']
  if len(pae)!=ln or any(len(row)!=ln for row in pae):raise ValueError('PAE dimensions mismatch')
  if ''.join(cif['_entity_poly.pdbx_seq_one_letter_code'][0].split())!=d['sequence']['value']:raise ValueError('CIF canonical sequence mismatch')
  chains=set(cif['_atom_site.auth_asym_id']);chain=next(iter(chains))
  if len(chains)!=1:raise ValueError('Multiple chains')
  ca=[int(n) for n,t in zip(cif['_atom_site.auth_seq_id'],cif['_atom_site.label_atom_id']) if t=='CA']
  if sorted(ca)!=list(range(1,ln+1)):raise ValueError('CA numbering incomplete')
  checkdir=tmp/'afdb-input-check';checkdir.mkdir(exist_ok=True)
  guard.prepare_inner(tmp/'modelo.cif',chain,checkdir)
  files.append(save('procedencia-afdb.json',json.dumps(api,indent=2).encode(),au))
  units={'accession':acc,'entry':a['entryId'],'chain':chain,'numbering':'model-residue-number; full canonical sequence starts at 1; CA coverage verified','units':e['units'],'source':'UniProt Repeat features supplied as analysis inputs, not independently validated structural repeat boundaries','insertions':[],'thresholds':{'plddt_min':70,'interunit_pae_max_angstrom':5},'note':'Do not assume these confidence thresholds pass. A justified stop is an admissible outcome of the requested conditional plan.'}
  files.append(save('unidades.json',json.dumps(units,ensure_ascii=False,indent=2).encode()))
  return {'acc':acc,'kind':kind,'entry':a['entryId'],'chain':chain,'model':1,'family':e['family'],'pfam':e['pfam'],'protein':name(d),'organism':d['organism']['scientificName'],'length':ln,'units':e['units'],'files':files}
selected=[];attempts=[]
for kind in ['pdb','afdb']:
 candidates=[e for e in ordered if e['acc'] not in {s['acc'] for s in selected} and (kind!='pdb' or any(r['database']=='PDB' for r in e['record'].get('uniProtKBCrossReferences',[])))]
 if kind=='pdb':candidates=[e for e in candidates if e['acc'] in preflight]
 count=0
 target=10 if kind=='pdb' else 40
 for start in range(0,len(candidates),5):
  batch=candidates[start:start+min(5,target-count)]
  if not batch:break
  with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:
   future=[ex.submit(build,e,kind) for e in batch]
   for e,f in zip(batch,future):
    try:r=f.result();r['task']='detection' if kind=='pdb' or count<15 else 'predicted_geometry';selected.append(r);count+=1;attempts.append({'accession':e['acc'],'kind':kind,'status':'selected'});print(kind,count,e['acc'],r.get('pdb',r.get('entry')),flush=True)
    except Exception as err:attempts.append({'accession':e['acc'],'kind':kind,'status':'technical-exclusion-before-inference','reason':str(err)});print('skip',kind,e['acc'],str(err)[:110],flush=True)
  (BASE/'selected.json').write_text(json.dumps(selected,ensure_ascii=False,indent=2));(BASE/'retrieval-attempts.json').write_text(json.dumps(attempts,ensure_ascii=False,indent=2))
  if count==target:break
print('TOTAL',len(selected),flush=True)
