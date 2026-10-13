#!/usr/bin/env python3
import hashlib,json,pathlib,runpy,shutil,subprocess,tempfile
from datetime import datetime,timezone
ROOT=pathlib.Path('/home/webiwabou/Projects/bioinformatica-org');STAGE=pathlib.Path(__file__).resolve().parent;BASE=ROOT/'evaluation/trp/campaign-20261012/aggregate-resource-contrasts/campaign-outcomes';verify=runpy.run_path(str(ROOT/'packages/helix/src/trp/verify_bundle.py.txt'))['verify'];sha=lambda b:hashlib.sha256(b).hexdigest();load=lambda p:json.loads(p.read_bytes());report={'schema':'actual-failed-strict-backend-verifier/1.0','at':datetime.now(timezone.utc).isoformat(),'candidateSha256':sha((ROOT/'packages/helix/src/trp/verify_bundle.py.txt').read_bytes()),'productionChanged':False,'cloudOperations':0,'cases':[]}
with tempfile.TemporaryDirectory(prefix='helix-failed-strict-read-') as tmp:
 for name in ['AGG-13-generous','AGG-14-generous']:
  case=BASE/name;location=next(case.glob('recovered/*/retained-allocation/client/.helix/trp/*/evidence-location.json'));original=location.parent/'evidence';loc=load(location);anchor=loc['manifestSha256'];recovery=load(case/'recovery.json')
  archive=case/'actual-allocation-and-supervisor.tar';assert sha(archive.read_bytes())==recovery['archiveSha256']
  copy=pathlib.Path(tmp)/name;shutil.copytree(original,copy);result=verify(copy,anchor)
  assert result['ok'] and result['status']=='failed' and not result['legacyBackendMetadata']
  report['cases'].append({'case':name,'copiedBundleFiles':result['files'],'manifestSha256':anchor,'externalProducerSidecar':str(location.relative_to(ROOT)),'externalSidecarSha256':sha(location.read_bytes()),'retainedArchiveSha256':recovery['archiveSha256'],'runStatus':'failed','coldVerification':result,'softwarePresent':(copy/'run/software.json').exists(),'structuralReportPresent':(copy/'run/structural_report.json').exists(),'methodsFields':len(load(copy/'run/methods.json')['fields']),'rawError':load(copy/'run/run.json')['error'],'scientificFeasibilityEstablished':False})
 # Meaningful optional-software absence: use actual unchanged E.methods to
 # regenerate metadata on an isolated failed fixture; never replace its original.
 fixture=pathlib.Path(tmp)/'failed-without-software-unitfixture';shutil.copytree(original,fixture);(fixture/'run/software.json').unlink()
 script=STAGE/'regenerate_failed_methods.ts'
 script.write_text('await import("'+str(ROOT/'packages/core/src/global')+'");\nawait import("'+str(ROOT/'packages/core/src/fs-util')+'");\nconst {TrpEvidence}=await import("'+str(ROOT/'packages/helix/src/trp/evidence')+'");\nawait TrpEvidence.methods(process.argv[2]);\n')
 process=subprocess.run(['bun',str(script),str(fixture/'run')],cwd=ROOT,capture_output=True,text=True,timeout=20)
 if process.returncode:raise RuntimeError(process.stderr[-4000:])
 manifest=load(fixture/'manifest.json');manifest['files']=[row for row in manifest['files'] if row['path']!='run/software.json']
 for row in manifest['files']:
  raw=(fixture/row['path']).read_bytes();row['bytes']=len(raw);row['sha256']=sha(raw)
 (fixture/'manifest.json').write_text(json.dumps(manifest,sort_keys=True,ensure_ascii=False,separators=(',',':')))
 result=verify(fixture,sha((fixture/'manifest.json').read_bytes()));assert result['ok'] and result['status']=='failed'
 report['optionalSoftwareUnitFixture']={'sourceFailedCase':name,'metadataGenerator':'Unmodified production TrpEvidence.methods','metadataGeneratorSha256':sha((ROOT/'packages/helix/src/trp/evidence.ts').read_bytes()),'generatorExitCode':process.returncode,'generatorStderr':process.stderr,'methodsFields':len(load(fixture/'run/methods.json')['fields']),'declaredUnavailable':load(fixture/'run/methods.json')['unavailable'],'verification':result,'actualNewExecution':False,'sourceDataReplaced':False,'scope':'Unit test of absent optional software metadata, not a claim the real failed case lacked its observed version.'}
 report['verified']=True
(STAGE/'failed-strict-results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'verified':report['verified'],'cases':[(c['case'],c['copiedBundleFiles'],c['runStatus']) for c in report['cases']],'optionalSoftwareFields':report['optionalSoftwareUnitFixture']['methodsFields']},indent=2))
