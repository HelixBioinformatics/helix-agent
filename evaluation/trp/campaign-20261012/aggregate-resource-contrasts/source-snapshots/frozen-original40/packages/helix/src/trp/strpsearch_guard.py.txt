#!/usr/bin/env python3
"""Pinned, offline STRPsearch adapter. prepare produces an approval-bound plan;
run requires its SHA256. Output uses observed PDB author residue numbers only.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import uuid

IMAGE = 'sha256:640de175f40ca77bad6317bc53f3ee2f2e4a689e757a98c82715fe02b99496e0'
REVISION = 'ed325a7f6b77578ee96753f31dbdcfda4931cca8'
DATABASE = '8c7341b2c789e6e0769c751bce4e5bfaeb3d750bde90985c406b51f2f4d8854d'
AA = set('ALA ARG ASN ASP CYS GLN GLU GLY HIS ILE LEU LYS MET PHE PRO SER THR TRP TYR VAL'.split())

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')

def finite(value):
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError('Nonfinite scientific output')
    if isinstance(value, dict):
        for item in value.values(): finite(item)
    elif isinstance(value, list):
        for item in value: finite(item)

def validate_profile(value):
    finite(value)
    if not isinstance(value, dict): raise ValueError('Malformed score profile')
    x, y = value.get('x'), value.get('y')
    if not isinstance(x,list) or not isinstance(y,list) or not x or len(x) != len(y):
        raise ValueError('Missing or mismatched profile axes')
    for axis in (x,y):
        if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) for v in axis):
            raise ValueError('Nonnumeric or nonfinite score profile')
    if any(a >= b for a,b in zip(x,x[1:])):
        raise ValueError('Ambiguous profile coordinate axis')

def validate(log, annotations, residues, chain):
    completions = re.findall(r'Task finished with (\d+) errors', log)
    if not completions or any(int(x) for x in completions):
        raise ValueError('Missing success marker or scientific errors, regardless of exit code')
    if re.search(r'Traceback|Error:|exception|nonfinite|\bnan\b', log, re.I):
        raise ValueError('Scientific failure in diagnostic output')
    if not isinstance(annotations, list) or not annotations:
        raise ValueError('No validated prediction; absence of output is not a negative label')
    finite(annotations)
    units, regions = [], []
    for row in annotations:
        if row.get('chain_id') != chain or row.get('reviewed') is not False:
            raise ValueError('Unexpected chain or reviewed flag')
        if row.get('origin') != 'Predicted' or row.get('type') not in ('unit', 'region'):
            raise ValueError('Unexpected annotation type or origin')
        bounds = [row.get('start'), row.get('end')]
        if any(isinstance(v, bool) or not re.fullmatch(r'[1-9]\d*', str(v)) for v in bounds):
            raise ValueError('Ambiguous author residue bound')
        start, end = map(int, bounds)
        if start > end or any(i not in residues for i in range(start, end + 1)):
            raise ValueError('Annotation outside observed continuous source coordinates')
        target = units if row['type'] == 'unit' else regions
        target.append({'start':start, 'end':end, 'region_id':row.get('region_id')})
    if not units or not regions:
        raise ValueError('Prediction must contain units and regions')
    units.sort(key=lambda u: u['start'])
    if any(a['end'] >= b['start'] for a,b in zip(units, units[1:])):
        raise ValueError('Overlapping or duplicate units are ambiguous')
    for unit in units:
        matching = [r for r in regions if r['region_id'] == unit['region_id'] and
                    r['start'] <= unit['start'] <= unit['end'] <= r['end']]
        if len(matching) != 1:
            raise ValueError('Unit does not belong to exactly one region')
    return units, regions

def prepare_inner(source, chain, output):
    import gemmi
    st = gemmi.read_structure(str(source))
    if len(st) != 1:
        raise ValueError('Exactly one structural model is required')
    matches = [c for c in st[0] if c.name == chain]
    if len(matches) != 1:
        raise ValueError('Author chain is missing or ambiguous')
    chosen = matches[0]
    numbers, removed = [], 0
    for i in range(len(chosen)-1, -1, -1):
        residue = chosen[i]
        if residue.name not in AA:
            if residue.het_flag == 'A' or gemmi.find_tabulated_residue(residue.name).is_amino_acid():
                raise ValueError('Unsupported noncanonical polymer residue')
            del chosen[i]
            removed += 1
    for residue in chosen:
        if residue.seqid.icode.strip() or residue.seqid.num <= 0:
            raise ValueError('Insertion codes/nonpositive author numbers are unsupported')
        names = set()
        for atom in residue:
            if atom.altloc not in ('\x00', ' '):
                raise ValueError('Alternate locations require explicit resolution')
            if atom.name in names or not all(math.isfinite(x) for x in (atom.pos.x,atom.pos.y,atom.pos.z)):
                raise ValueError('Duplicate atoms or nonfinite coordinates')
            names.add(atom.name)
        if 'CA' not in names:
            raise ValueError('Each protein residue must contain CA')
        numbers.append(residue.seqid.num)
    if not numbers or numbers != list(range(numbers[0], numbers[-1]+1)):
        raise ValueError('Author coordinates must be unique, ascending and contiguous')
    for i in range(len(st[0])-1, -1, -1):
        if st[0][i].name != chain: del st[0][i]
    st.make_mmcif_document().write_file(str(output/'query.cif'))
    write(output/'coordinates.json', {'chain':chain,'numbering':'pdb-author',
        'insertionCodes':'rejected','alternateLocations':'rejected','residues':numbers,
        'removedNonproteinResidues':removed,'proteinResidues':len(numbers),
        'sourceSha256':digest(source),'preparedSha256':digest(output/'query.cif')})

def container(work, args, timeout=300):
    name = 'thesis-strp-' + uuid.uuid4().hex
    command = ['docker','run','--rm','--name',name,'--network','none','--read-only',
      '--cap-drop','ALL','--security-opt','no-new-privileges','--pids-limit','256',
      '--cpus','2','--memory','8g','--tmpfs','/tmp:rw,nosuid,size=1g',
      '--user',f'{os.getuid()}:{os.getgid()}', '-e','MPLCONFIGDIR=/tmp/matplotlib',
      '-e','XDG_CACHE_HOME=/tmp/cache','-e','OMP_NUM_THREADS=2','-e','OPENBLAS_NUM_THREADS=1',
      '--mount',f'type=bind,src={work},dst=/work',
      '--mount',f'type=bind,src={Path(__file__).resolve()},dst=/guard.py,readonly',
      '--mount',f'type=bind,src={work}/mime.types,dst=/etc/mime.types,readonly',
      '--entrypoint','python',IMAGE,*args]
    def interrupted(signum, frame):
        subprocess.run(['docker','kill',name],capture_output=True,timeout=15)
        raise SystemExit(128 + signum)
    old_handlers = {sig:signal.signal(sig,interrupted) for sig in (signal.SIGTERM,signal.SIGINT)}
    try:
        result = subprocess.run(command,capture_output=True,text=True,timeout=timeout)
    except subprocess.TimeoutExpired:
        subprocess.run(['docker','kill',name],capture_output=True,timeout=15)
        raise
    finally:
        for sig,handler in old_handlers.items(): signal.signal(sig,handler)
    return result, command

def prepare(source, chain, work):
    source, work = Path(source).resolve(), Path(work).resolve()
    if not re.fullmatch(r'[A-Za-z0-9]+', chain): raise ValueError('Unsupported chain ID')
    work.mkdir(parents=True, exist_ok=False)
    target = work/('source'+source.suffix.lower())
    if source.suffix.lower() not in ('.pdb','.cif','.mmcif'): raise ValueError('PDB/mmCIF required')
    shutil.copyfile(source,target)
    (work/'mime.types').write_text('chemical/x-mmcif cif mmcif\nchemical/x-pdb pdb\n')
    result, command = container(work,['/guard.py','inner',str('/work/'+target.name),chain,'/work'])
    (work/'prepare.log').write_text(result.stdout+result.stderr)
    if result.returncode: raise ValueError('Preprocessing failed; see prepare.log')
    plan = {'schemaVersion':1,'image':IMAGE,'sourceRevision':REVISION,'databaseSha256':DATABASE,
       'chain':chain,'sourceFile':target.name,'sourceSha256':digest(target),
       'preparedSha256':digest(work/'query.cif'),'coordinatesSha256':digest(work/'coordinates.json'),
       'adapterSha256':digest(__file__),'mimeSha256':digest(work/'mime.types'),
       'parameters':{'minHeight':0.4,'maxEval':0.01,'chainsaw':False},
       'resources':{'cpus':2,'memoryGiB':8,'timeoutSeconds':300},
       'scope':'engineering validation only; bundled database can include query family'}
    write(work/'plan.json',plan)
    return {'plan':str(work/'plan.json'),'approvalSha256':digest(work/'plan.json')}

def run(work, approval):
    work = Path(work).resolve()
    if digest(work/'plan.json') != approval: raise ValueError('Approval does not match plan')
    plan = json.loads((work/'plan.json').read_text())
    if plan['image'] != IMAGE or plan['databaseSha256'] != DATABASE or plan['sourceRevision'] != REVISION:
        raise ValueError('Unrecognized frozen environment')
    if plan['parameters'] != {'minHeight':0.4,'maxEval':0.01,'chainsaw':False} or plan['resources'] != {'cpus':2,'memoryGiB':8,'timeoutSeconds':300}:
        raise ValueError('Unsupported approved parameters or resources')
    for field,path in [('sourceSha256',work/plan['sourceFile']),('preparedSha256',work/'query.cif'),
        ('coordinatesSha256',work/'coordinates.json'),('adapterSha256',Path(__file__)),
        ('mimeSha256',work/'mime.types')]:
        if digest(path) != plan[field]: raise ValueError('Changed artifact: '+field)
    if (work/'results').exists(): raise ValueError('Refusing stale detector output')
    coordinates = json.loads((work/'coordinates.json').read_text())
    if coordinates['chain'] != plan['chain']: raise ValueError('Coordinate chain mismatch')
    result, command = container(work,['/app/bin/strpsearch.py','query-file','/work/query.cif',
        '/work/results','--chain',plan['chain'],'--temp-dir','/work/tmp',
        '--db','/app/data/databases','--min-height','0.4','--max-eval','0.01',
        '--keep-temp','--no-pymol-pse','--no-chainsaw'])
    log = result.stdout+result.stderr
    (work/'run.log').write_text(log)
    record = {'exitCode':result.returncode,'command':command,'approvalSha256':approval,
              'scientificSuccess':False,'image':IMAGE}
    try:
        if result.returncode: raise ValueError('Detector process failed')
        annotations = []
        for path in sorted((work/'results').rglob('region_*/*.json')):
            content = json.loads(path.read_text())
            finite(content)
            if path.name.endswith('_profile.json'):
                validate_profile(content)
                continue
            profile = path.with_name(path.stem+'_profile.json')
            if not profile.is_file(): raise ValueError('Missing scientific score profile')
            if not isinstance(content,list): raise ValueError('Malformed annotation document')
            annotations.extend(content)
        units, regions = validate(log,annotations,set(coordinates['residues']),plan['chain'])
        output = {'detector':'STRPsearch','numbering':'pdb-author','chain':plan['chain'],
           'sourceSha256':plan['sourceSha256'],'preparedSha256':plan['preparedSha256'],
           'units':units,'regions':regions,'reviewed':False,'scope':plan['scope']}
        write(work/'annotations.json',output)
        record.update(scientificSuccess=True,unitCount=len(units),regionCount=len(regions),
                      outputSha256=digest(work/'annotations.json'))
    except Exception as error:
        record['failure'] = str(error)
        raise
    finally: write(work/'execution.json',record)
    return record

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='operation', required=True)
    p = sub.add_parser('prepare'); p.add_argument('source'); p.add_argument('chain'); p.add_argument('work')
    p = sub.add_parser('run'); p.add_argument('work'); p.add_argument('--approve-sha256', required=True)
    p = sub.add_parser('inner'); p.add_argument('source'); p.add_argument('chain'); p.add_argument('work')
    args = parser.parse_args()
    try:
        if args.operation == 'prepare': answer = prepare(args.source,args.chain,args.work)
        elif args.operation == 'run': answer = run(args.work,args.approve_sha256)
        else: answer = prepare_inner(Path(args.source),args.chain,Path(args.work))
        print(json.dumps(answer,indent=2))
    except Exception as error:
        print(str(error),file=sys.stderr); sys.exit(1)
