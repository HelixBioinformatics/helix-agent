#!/usr/bin/env python3
"""Audit author-shared originals, freeze a bounded challenge, and screen offline.

This is a diagnostic of fixed mechanical controls, not a complete T-STRUCT
campaign or independent experimental validation of all 78 predictions.
"""
import argparse
import csv
import hashlib
import json
import math
import platform
import re
import runpy
import subprocess
from collections import Counter
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT/'evaluation/trp/reference/pratt-author-20261001'
PUBLIC = ROOT/'evaluation/trp/reference/structural-f5/pratt'
ENGINE = ROOT/'packages/helix/src/trp/inspect_structure.py.txt'
SOURCES = [ENGINE, ROOT/'packages/helix/src/trp/structural_catalog.json', Path(__file__),
           ROOT/'evaluation/trp/protocol.json', PUBLIC/'mmc2.xlsx', PUBLIC/'pratt.xml']
PROBLEMS = {
    'FCTTCCIY': ('fig0015','Figure 3A: exposed hydrophobic stacks and residue clashes'),
    'SMKLTDNQQDAAIIIIVDCFCI': ('fig0015','Figure 3B: uncompensated internal aspartic-acid stacks'),
    'QNGITTKTKYGGRSHRDDDYD': ('fig0030','Figure 6: internal charges and lysine/histidine clashes'),
    'CKMVKFQIQICF': ('fig0035','Figure 7A: model identified as problematic by Verify3D'),
    'AVIHTPTYEAMNSVNKEHD': ('fig0035','Figure 7B: model identified as problematic by Verify3D'),
}
MISSING = [
    {'figure':'1 / S1','repeat':'QTSTVIGTIASTETSSSTGI','evidence':'permuted mucin-22 example'},
    {'figure':'14','repeat':'TVCWCMIWQCEEKFVIVEVM','evidence':'MD preliminary model 1'},
    {'figure':'14','repeat':'GDDPIYTKDNINPIGPYMGN','evidence':'MD preliminary model 2'},
]

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False)+'\n')

def table_rows():
    with ZipFile(PUBLIC/'mmc2.xlsx') as archive:
        ns={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
        strings=[''.join(x.itertext()) for x in ET.fromstring(archive.read('xl/sharedStrings.xml'))]
        for row in ET.fromstring(archive.read('xl/worksheets/sheet1.xml')).findall('.//s:row',ns):
            if row.get('r')=='1':continue
            cells={}
            for cell in row:
                column=re.match('[A-Z]+',cell.get('r')).group()
                v=cell.find('s:v',ns);value=v.text if v is not None else ''
                cells[column]=strings[int(value)] if cell.get('t')=='s' and value else value
            if cells.get('A'):
                yield {'identifier':cells['A'],'sheetRow':int(row.get('r')),'repeatSequence':cells['B'],
                       'publishedAF2MeanpLDDT':float(cells['E']),'publishedAF2Fold':cells['F']}

def source_records():
    return [{'path':p.relative_to(ROOT).as_posix(),'sha256':digest(p)} for p in SOURCES]

def request(case, units=None):
    raw=BASE/'originals'
    meta=json.loads((BASE/'metadata'/f"{case['identifier']}.json").read_text())
    width=len(case['repeatSequence'])
    return {'structure':(raw/meta['structureFile']).read_text(),
            'options':{'format':'pdb','model':1,'chain':'A','frame':'auth_seq_id',
                       'units':units or [{'start':i*width+1,'end':(i+1)*width} for i in range(10)],
                       'plddtMin':70,'paeMax':5},
            'colabfold':{'metadata':meta,'scores':(raw/meta['scoresFile']).read_text(),
                        'pae':(raw/meta['paeFile']).read_text()}}

def prepare():
    if (BASE/'freeze.json').exists():raise ValueError('freeze exists; verify or run it, never silently replace it')
    raw=BASE/'originals'
    files=sorted(p for p in raw.iterdir() if p.is_file())
    cases=list(table_rows())
    if len(cases)!=78 or len({c['identifier'] for c in cases})!=78:raise ValueError('Table S1 inventory')
    article=ET.parse(PUBLIC/'pratt.xml').getroot()
    captions={f.get('id'):''.join(f.itertext()) for f in article.findall('.//fig')}
    inspect=runpy.run_path(str(ENGINE))
    expected=set()
    for case in cases:
        identifier=case['identifier']
        structures=list(raw.glob(f'{identifier}_unrelaxed_rank_001_alphafold2_ptm_model_*_seed_000.pdb'))
        if len(structures)!=1:raise ValueError(f'{identifier}: exact rank-1/seed-0 model required')
        structure=structures[0]
        match=re.fullmatch(r'(.+)_unrelaxed_rank_(\d+)_alphafold2_ptm_model_(\d+)_seed_(\d+)\.pdb',structure.name)
        scores=raw/f'{identifier}_scores_rank_{int(match[2]):03d}_alphafold2_ptm_model_{match[3]}_seed_{int(match[4]):03d}.json'
        pae=raw/f'{identifier}_predicted_aligned_error_v1.json'
        for p in (structure,scores,pae):
            if not p.is_file():raise ValueError('missing '+str(p))
            expected.add(p.name)
        meta={'version':'colabfold-local/1.0.0','producer':'ColabFold','caseId':identifier,
              'modelType':'alphafold2_ptm','chain':'A','sequence':case['repeatSequence']*10,
              'rank':int(match[2]),'parameterModel':int(match[3]),'seed':int(match[4]),
              'structureFile':structure.name,'scoresFile':scores.name,'paeFile':pae.name,
              'structureSha256':digest(structure),'scoresSha256':digest(scores),'paeSha256':digest(pae),
              'source':'author-shared data reported by thesis author, via Daniel Rigden / Dr Price, 2026-10-01',
              'publicationDOI':'10.1016/j.csbj.2025.01.016','softwareVersion':None,
              'softwareVersionNote':'Article reports local v1.5.2; no original run log/version record in this bundle.'}
        save(BASE/'metadata'/f'{identifier}.json',meta)
        req=request(case)
        snapshot=inspect['pdb_snapshot'](req['structure'],req['options'])
        binding,matrix,matrix_ok=inspect['colabfold_binding'](req,snapshot)
        if not binding['metadataMatchesStructure'] or not matrix_ok:raise ValueError(f'{identifier}: invalid original pairing {binding}')
        data=json.loads(req['colabfold']['scores']);mean=sum(data['plddt'])/len(data['plddt'])
        case.update({'sequenceLength':len(meta['sequence']),'originalMeanpLDDT':mean,
                     'meanpLDDTDifference':mean-case['publishedAF2MeanpLDDT'],
                     'matchesPublishedOneDecimal':abs(mean-case['publishedAF2MeanpLDDT'])<=0.056,
                     'label':'unlabelled','labelEvidence':None,'structureSha256':meta['structureSha256']})
        problem=PROBLEMS.get(case['repeatSequence'])
        if problem:
            figure,meaning=problem
            if case['repeatSequence'] not in captions[figure]:raise ValueError('caption mismatch')
            case['label']='published_problem';case['labelEvidence']={'articleFigureId':figure,'reason':meaning,'doi':'10.1016/j.csbj.2025.01.016','scope':'published physical/validation concern, not a new experimental determination'}
    if expected!={p.name for p in files}:raise ValueError('unpaired or unexpected files in original bundle')
    if sum(c['label']=='published_problem' for c in cases)!=5:raise ValueError('published example inventory')
    motifs={c['repeatSequence'] for c in cases}
    if any(c['repeat'] in motifs for c in MISSING):raise ValueError('update missing-example inventory before freeze')
    manifest={'version':'pratt-author-originals/1.0.0','date':'2026-10-01',
              'source':'User reports direct author email: Daniel Rigden attached data recovered by Dr Price.',
              'authorshipAuthentication':'reported source, not cryptographically authenticated',
              'redistributionLicense':'not specified for the separately author-shared files; article license is not assumed to cover this bundle',
              'files':[{'path':'originals/'+p.name,'bytes':p.stat().st_size,'sha256':digest(p)} for p in files],
              'models':78,'ranksAvailable':[1],'seedsObserved':[0],
              'parameterModelNote':'model_1..5 identifies AF2 parameter sets, not prediction ranks 2..5',
              'missingExamples':MISSING}
    save(BASE/'manifest.json',manifest)
    save(BASE/'cases.json',cases)
    freeze={'version':'pratt-mechanical-challenge/1.0.0','date':'2026-10-01',
            'kind':'bounded diagnostic, not full reserved T-STRUCT; no claim of globally clean campaign freeze',
            'revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
            'worktreeStatus':subprocess.check_output(['git','status','--short'],cwd=ROOT,text=True).splitlines(),
            'sources':source_records(),'manifestSha256':digest(BASE/'manifest.json'),
            'casesSha256':digest(BASE/'cases.json'),
            'metadata':[{'path':p.name,'sha256':digest(p)} for p in sorted((BASE/'metadata').glob('*.json'))],
            'profiles':{'all-ten-repeats':{'plddtMin':70,'paeMax':5,'repeatIndices':list(range(10))},
                        'central-eight-repeats':{'plddtMin':70,'paeMax':5,'repeatIndices':list(range(1,9)),'kind':'prospectively specified diagnostic of terminal influence; not the primary profile'}},
            'units':'sequence motifs repeated ten times; not independent structural-repeat annotations',
            'labelPolicy':'Only the five caption-matched explicit problems are positive examples. The other 73 rows are unlabelled, including beta-solenoids. No confirmed negatives supplied.',
            'thresholdOrigin':'F2 fixed pLDDT>=70 and max of both directed interunit PAE blocks<=5 A; no retuning on these outcomes',
            'physicalMetricPolicy':'fold-plausibility not_evaluable is not a physical detection or a passed biological validation',
            'paidInference':False}
    save(BASE/'freeze.json',freeze)
    print(json.dumps({'prepared':len(cases),'files':len(files),'explicitProblems':5,'roundingDiscrepancies':[c['identifier'] for c in cases if not c['matchesPublishedOneDecimal']]}))

def verify():
    freeze=json.loads((BASE/'freeze.json').read_text())
    if freeze['sources']!=source_records():raise ValueError('frozen source changed; record an amendment, do not overwrite')
    for name,key in (('manifest.json','manifestSha256'),('cases.json','casesSha256')):
        if digest(BASE/name)!=freeze[key]:raise ValueError('frozen '+name+' changed')
    for entry in freeze['metadata']:
        if digest(BASE/'metadata'/entry['path'])!=entry['sha256']:raise ValueError('metadata changed')
    manifest=json.loads((BASE/'manifest.json').read_text())
    for entry in manifest['files']:
        path=BASE/entry['path']
        if path.stat().st_size!=entry['bytes'] or digest(path)!=entry['sha256']:raise ValueError('original changed: '+entry['path'])
    if {p.name for p in (BASE/'originals').iterdir()}!={Path(e['path']).name for e in manifest['files']}:raise ValueError('original inventory changed')
    return freeze

def wilson(k,n):
    if not n:return None
    z=1.959963984540054;p=k/n;d=1+z*z/n
    center=(p+z*z/(2*n))/d;half=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d
    return [center-half,center+half]

def run():
    freeze=verify()
    inspect=runpy.run_path(str(ENGINE))['inspect']
    cases=json.loads((BASE/'cases.json').read_text());rows=[];profiles={}
    for profile,config in freeze['profiles'].items():
        outputs=[];positive=[]
        for case in cases:
            width=len(case['repeatSequence'])
            units=[{'start':i*width+1,'end':(i+1)*width} for i in config['repeatIndices']]
            report=inspect(request(case,units))
            save(BASE/'reports'/profile/(case['identifier']+'.json'),report)
            by_id={c['id']:c for c in report['checks']};pae=by_id['interunit-pae']
            if pae['status'] not in ('pass','fail') or not report['provenance']['confidenceBinding']['metadataMatchesStructure']:raise ValueError('unexpected unevaluable pairing')
            row={'profile':profile,'identifier':case['identifier'],'sequence_length':case['sequenceLength'],
                 'published_fold':case['publishedAF2Fold'],'label':case['label'],
                 'published_mean_plddt':case['publishedAF2MeanpLDDT'],'original_mean_plddt':case['originalMeanpLDDT'],
                 'selected_minimum_plddt':pae['value']['selectedMinimum'],'maximum_interunit_pae':pae['value']['maximum'],
                 'interunit_pae':pae['status'],'mechanical_admission':report['summary']['mechanicalAdmission'],
                 'physical_plausibility':by_id['fold-plausibility']['status'],
                 'failed_controls':';'.join(report['summary']['failed']),
                 'not_evaluable_controls':';'.join(report['summary']['notEvaluable'])}
            rows.append(row);outputs.append(report)
            if case['label']=='published_problem':positive.append(row)
        flagged=sum(not x['mechanical_admission'] for x in positive)
        profiles[profile]={'modelsScreened':len(outputs),'mechanicallyAdmitted':sum(r['summary']['mechanicalAdmission'] for r in outputs),
                          'mechanicallyFlagged':sum(not r['summary']['mechanicalAdmission'] for r in outputs),
                          'publishedProblemExamples':len(positive),'publishedProblemsMechanicallyFlagged':flagged,
                          'publishedProblemMechanicalAlarmRate':flagged/len(positive),'wilson95':wilson(flagged,len(positive)),
                          'rateScope':'diagnostic on five illustrated problems; not physical sensitivity and not representative of all published failures',
                          'physicalEvaluable':0,'physicalCoverage':0,'physicalSensitivity':None,
                          'physicalConservativeDetectionRate':0,'specificity':None,'confirmedNegativeControls':0,
                          'controls':{key:dict(Counter(next(c['status'] for c in r['checks'] if c['id']==key) for r in outputs)) for key in ('confidence-scale','filter-direction','interunit-pae','residue-frame','construct-tags','assembly-annotation','unit-boundaries','element-coverage','fold-plausibility')}}
    path=BASE/'outcomes.csv'
    with path.open('w',newline='') as out:
        writer=csv.DictWriter(out,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    summary={'date':'2026-10-01','engineVersion':outputs[0]['version'],'python':platform.python_version(),
             'originalModelsRecovered':78,'originalFiles':234,'uniqueModelRanks':[1],
             'originalsIntegrityVerified':True,'freezeSha256':digest(BASE/'freeze.json'),
             'matchingTableS1Rows':78,'publishedBetaSolenoids':sum(c['publishedAF2Fold']=='Beta-solenoid' for c in cases),
             'meanRoundingDiscrepancies':[c['identifier'] for c in cases if not c['matchesPublishedOneDecimal']],
             'profiles':profiles,'R3.8':'original-data dependency resolved for Table S1 rank 1; full physical evaluation incomplete',
             'remaining':['Independent pertinent negative controls: at least 30 reviewed RepeatsDB controls required by protocol.',
                          'A physical plausibility control is not implemented or validated; confidence/PAE alarms do not identify the physical cause.',
                          'Illustrated Figure 1/S1 and Figure 14 original models absent; ranks 2..5 absent.'],
             'cost':{'modelCalls':0,'awsInstances':0},
             'outputs':[{'path':p.relative_to(BASE).as_posix(),'sha256':digest(p)} for p in sorted((BASE/'reports').rglob('*.json'))]+[{'path':'outcomes.csv','sha256':digest(path)}]}
    save(BASE/'summary.json',summary)
    print(json.dumps({'models':78,'profiles':{k:{q:v[q] for q in ('mechanicallyAdmitted','mechanicallyFlagged','publishedProblemsMechanicallyFlagged')} for k,v in profiles.items()},'physicalSensitivity':None,'specificity':None}))

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=['prepare','run','verify']);args=parser.parse_args()
    if args.action=='prepare':prepare()
    elif args.action=='run':run()
    else:
        verify();summary=json.loads((BASE/'summary.json').read_text())
        for entry in summary['outputs']:
            if digest(BASE/entry['path'])!=entry['sha256']:raise ValueError('output changed')
        print(json.dumps({'ok':True,'originals':234,'reports':156,'freezeSha256':digest(BASE/'freeze.json')}))

if __name__=='__main__':main()
