#!/usr/bin/env python3
"""Bounded AFDB geometry: prepare a hashed proposal, then execute that exact digest.

The derived CA-only PDB is a transport format, never an experimental structure.
Confidence stays pLDDT, and units remain supplied hypotheses, not detected repeats.
"""
import argparse
import csv
import datetime
import hashlib
import io
import json
import math
import os
from pathlib import Path
import runpy
import subprocess
import signal
import uuid

ENGINE = Path(__file__).with_name('inspect_structure.py')
IMAGE = 'sha256:1dd91e70acb153a0bd9a51346fc001dd5025f851c9598697cdd37f07d9490b0a'
VERSION = 'trp-predicted-geometry/1.1.0'

def canonical(x): return json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False)
def sha(x): return hashlib.sha256(x).hexdigest()

def derive(request):
    engine=runpy.run_path(str(ENGINE))
    options=request['options']
    if options.get('format')!='mmcif' or options.get('frame')!='label_seq_id':
        raise ValueError('predicted-route-requires-mmcif-label-frame')
    if len(options.get('units',[]))<3:
        raise ValueError('GeomeTRe-circle-fit-requires-three-units')
    if not request.get('api') or not request.get('pae'):
        raise ValueError('AFDB-API-and-PAE-required')
    report=engine['inspect'](request)
    if not report['summary']['mechanicalAdmission']:
        raise ValueError('structural-rejection:'+','.join(report['summary']['blocking']))
    if report['provenance']['confidenceScale']!='pLDDT_0_100':
        raise ValueError('AFDB-pLDDT-contract-required')
    chain=options['chain']
    if len(chain)!=1 or not chain.isalnum(): raise ValueError('legacy-chain-encoding')
    rows={r['label']:r for r in report['mapping']}
    units=[]; selected=[]
    for interval in options['units']:
        if interval['end']-interval['start']+1<6: raise ValueError('GeomeTRe-window-six')
        values=[]
        for label in range(interval['start'],interval['end']+1):
            row=rows[label]
            author=int(row['auth'])
            if not 1<=author<=9999: raise ValueError('legacy-author-encoding')
            if row['insertion'] or row['alt']: raise ValueError('ambiguous-residue')
            if any(not math.isfinite(v) or not -999.999<=v<=9999.999 for v in row['xyz']):
                raise ValueError('legacy-coordinate-encoding')
            if len(row['name'])!=3 or not row['name'].isalnum(): raise ValueError('legacy-residue-encoding')
            values.append(author); selected.append(row)
        if values!=list(range(values[0],values[-1]+1)): raise ValueError('noncontiguous-author-unit')
        units.append({'start':values[0],'end':values[-1]})
    # No HEADER containing a fictitious PDB ID and no EXPDTA. File basename is
    # merely GeomeTRe's four-character output key; identity is in the manifest.
    lines=['REMARK 900 DERIVED ALPHAFOLD CA COORDINATES; NOT EXPERIMENTAL',
           'REMARK 900 B COLUMN IS PLDDT 0-100; UNITS ARE USER-SUPPLIED']
    for serial,row in enumerate(selected,1):
        x,y,z=row['xyz']
        lines.append(f"ATOM  {serial:5d}  CA  {row['name']:>3s} {chain}{int(row['auth']):4d}    {x:8.3f}{y:8.3f}{z:8.3f}{1.0:6.2f}{row['b']:6.2f}          C ")
    lines+=['TER','END']
    return report,units,'\n'.join(lines)+'\n'

def prepare(request, destination):
    report,units,pdb=derive(request)
    destination=Path(destination)
    destination.mkdir(parents=True,exist_ok=False)
    files={'request.json':canonical(request)+'\n','inspection.json':canonical(report)+'\n',
           'afdb.pdb':pdb,'inspect_structure.py':ENGINE.read_text(),
           'predicted_geometry.py':Path(__file__).read_text()}
    for name,data in files.items(): (destination/name).write_text(data)
    manifest={'version':VERSION,'kind':'bounded_geometry_of_supplied_predicted_units',
              'entry':report['provenance']['entry'],'transportCode':'afdb',
              'confidenceScale':'pLDDT_0_100','biologicalValidity':'not_established',
              'chain':request['options']['chain'],'units':units,'image':IMAGE,
              'limits':{'cpus':2,'memoryBytes':2*1024**3,'timeoutSeconds':120},
              'files':{k:sha(v.encode()) for k,v in files.items()},
              'limitations':['Supplied units are not independently validated repeats',
                             'PAE/pLDDT do not establish physical fold plausibility',
                             'Agent-admitted bounded route; not a held-out performance campaign',
                             'Docker memory/CPU limits; no aggregate disk quota']}
    data=canonical(manifest)+'\n'; (destination/'proposal.json').write_text(data)
    return {'directory':str(destination),'digest':sha(data.encode()),'proposal':manifest}

def validate_csv(text,manifest):
    rows=list(csv.DictReader(io.StringIO(text)))
    if len(rows)!=len(manifest['units'])+2: raise ValueError('unit-count')
    if [(r['unit_start'],r['unit_end']) for r in rows[:-2]]!=[(str(u['start']),str(u['end'])) for u in manifest['units']]:
        raise ValueError('unit-boundaries')
    if [r['unit_start'] for r in rows[-2:]]!=['mean','std']: raise ValueError('summary-rows')
    for row in rows:
        if row['pdb_id']!='afdb' or row['chain']!=manifest['chain']: raise ValueError('geometry-identity')
        for key in ('curvature','twist','twist_hand','pitch','pitch_hand','tmscore','yaw'):
            if not math.isfinite(float(row[key])): raise ValueError('nonfinite-geometry')
        if not 0<=float(row['tmscore'])<=1: raise ValueError('tmscore-domain')
    return rows

def verify_proposal(destination,digest):
    destination=Path(destination).resolve()
    data=(destination/'proposal.json').read_bytes()
    if sha(data)!=digest: raise ValueError('proposal-digest-mismatch')
    manifest=json.loads(data)
    if manifest['version']!=VERSION or manifest['image']!=IMAGE: raise ValueError('execution-contract')
    expected={'request.json','inspection.json','afdb.pdb','inspect_structure.py','predicted_geometry.py'}
    if set(manifest['files'])!=expected: raise ValueError('file-contract')
    for name,hash_ in manifest['files'].items():
        if (destination/name).is_symlink() or sha((destination/name).read_bytes())!=hash_:
            raise ValueError('input-changed:'+name)
    if sha(ENGINE.read_bytes())!=manifest['files']['inspect_structure.py']:
        raise ValueError('parser-changed-reprepare')
    if sha(Path(__file__).read_bytes())!=manifest['files']['predicted_geometry.py']:
        raise ValueError('runner-changed-reprepare')
    request=json.loads((destination/'request.json').read_text())
    report,units,pdb=derive(request)
    if units!=manifest['units'] or sha(pdb.encode())!=manifest['files']['afdb.pdb'] or manifest['chain']!=request['options']['chain']:
        raise ValueError('derivation-mismatch')
    if manifest['entry']!=report['provenance']['entry']: raise ValueError('source-identity')
    return destination,manifest

def execute(destination,digest):
    destination,manifest=verify_proposal(destination,digest)
    endpoint=os.environ.get('DOCKER_HOST') or subprocess.run(['docker','context','inspect','--format','{{.Endpoints.docker.Host}}'],capture_output=True,text=True,check=True,timeout=10).stdout.strip()
    if not endpoint.startswith('unix://'): raise ValueError('local-docker-required')
    actual=subprocess.run(['docker','image','inspect','--format','{{.Id}}',IMAGE],capture_output=True,text=True,check=True,timeout=10).stdout.strip()
    if actual!=IMAGE: raise ValueError('pinned-image-unavailable')
    if any((destination/n).exists() for n in ('geometry.csv','geometry.npy','execution.json','stdout.log','stderr.log')):
        raise ValueError('previous-or-injected-output')
    with (destination/'execution-claim.json').open('x') as f:
        f.write(canonical({'digest':digest,'at':datetime.datetime.now(datetime.timezone.utc).isoformat()})+'\n')
    units=','.join(f"{u['start']}_{u['end']}" for u in manifest['units'])
    name='thesis-predicted-'+uuid.uuid4().hex
    def interrupt(signum,frame):
        subprocess.run(['docker','kill',name],capture_output=True,timeout=10)
        raise RuntimeError('execution-interrupted')
    signal.signal(signal.SIGTERM,interrupt)
    signal.signal(signal.SIGINT,interrupt)
    command=['docker','run','--rm','--pull','never','--name',name,'--network','none','--read-only',
             '--cap-drop','ALL','--security-opt','no-new-privileges','--cpus','2',
             '--memory','2g','--memory-swap','2g','--pids-limit','128','--tmpfs','/tmp:rw,nosuid,size=256m',
             '--user',f'{os.getuid()}:{os.getgid()}',
             '--mount',f'type=bind,src={destination},dst=/work',IMAGE,
             'single','/work/afdb.pdb',manifest['chain'],'/work/geometry.csv',units]
    record={'version':VERSION,'proposalDigest':digest,'command':command,
            'sourceEntry':manifest['entry'],'transportCode':'afdb','status':'failed'}
    try:
        process=subprocess.run(command,capture_output=True,timeout=120)
        record['exitCode']=process.returncode
        (destination/'stdout.log').write_bytes(process.stdout)
        (destination/'stderr.log').write_bytes(process.stderr)
        if process.returncode!=0: raise ValueError('process-failed')
        rows=validate_csv((destination/'geometry.csv').read_text(),manifest)
        # Check no source/proposal changed while the container was running.
        verify_proposal(destination,digest)
        record.update(status='succeeded',unitCount=len(rows)-2,
                      geometrySha256=sha((destination/'geometry.csv').read_bytes()),
                      biologicalValidity='not_established')
    except subprocess.TimeoutExpired:
        subprocess.run(['docker','stop','--time','2',name],capture_output=True,timeout=10)
        record['error']='timeout'
        raise
    except Exception as error:
        record['error']=str(error)
        raise
    finally:
        subprocess.run(['docker','rm','-f',name],capture_output=True,timeout=10)
        (destination/'execution.json').write_text(json.dumps(record,indent=2)+'\n')
    return record

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='action',required=True)
    p=sub.add_parser('prepare'); p.add_argument('request',type=Path);p.add_argument('destination',type=Path)
    p=sub.add_parser('run');p.add_argument('destination',type=Path);p.add_argument('--digest',required=True)
    args=parser.parse_args()
    result=prepare(json.loads(args.request.read_text()),args.destination) if args.action=='prepare' else execute(args.destination,args.digest)
    print(json.dumps(result,indent=2))

if __name__=='__main__': main()
