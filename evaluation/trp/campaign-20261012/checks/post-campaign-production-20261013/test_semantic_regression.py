#!/usr/bin/env python3
import copy, hashlib, json, pathlib, runpy, shutil, tempfile, unittest
from datetime import datetime,timezone
ROOT=pathlib.Path('/home/webiwabou/Projects/bioinformatica-org')
STAGE=pathlib.Path(__file__).resolve().parent
CAMP=ROOT/'evaluation/trp/campaign-20261012'
sha=lambda b:hashlib.sha256(b).hexdigest()
canon=lambda x:json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
load=lambda p:json.loads(p.read_bytes())
reports=[]

class Hardening(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.temp=tempfile.TemporaryDirectory(prefix='helix-verifier-hardening-tests-')
  cls.original=staticmethod(runpy.run_path(str(CAMP/'aggregate-resource-contrasts/source-snapshots/frozen-original40/packages/helix/src/trp/verify_bundle.py.txt'))['verify'])
  production_verify=runpy.run_path(str(ROOT/'packages/helix/src/trp/verify_bundle.py.txt'))['verify']
  # Historical strict backend is kept unchanged, explicitly qualified against each external anchor.
  # This reaches semantic gates; separate backend tests require default rejection.
  cls.patched=staticmethod(lambda path,expected:production_verify(path,expected,True))
  full=CAMP/'checks/strict-full-client-final-offline/attempt-2/copied-bundle'
  a=load(CAMP/'checks/strict-full-client-final-offline/attempt-2/externally-recorded-terminal.json')
  cls.fixtures=[('strict150',full,a['terminal']['executed']['manifestSha256'])]
  x=load(CAMP/'trace/lab1-helix-reference.anchor.json');cls.fixtures.append(('ordinary144',CAMP/'cloud/lab1/helix-reference/evidence',x['manifestSha256']))
  x=load(CAMP/'cloud/lab1/mapped-reference-protocol/driver-terminal.json');cls.fixtures.append(('mapped156',CAMP/'cloud/lab1/mapped-reference/evidence',x['portable']['manifestSha256']))
  x=load(CAMP/'cloud/lab1/cancellation/next-ctx-abort/driver-terminal.json');cls.fixtures.append(('cancelled143',CAMP/'cloud/lab1/cancellation/next-ctx-abort'/x['evidence'],x['manifestSha256']))
  x=load(CAMP/'event-negative-contrasts/audit.json')
  for c in x['cases']:
   if c['automatic_failure_bundle_cold_verification']:
    loc=load(ROOT/next(z['path'] for z in c['records'] if z['path'].endswith('evidence-location.json')))
    p=pathlib.Path(loc['directory']) if 'directory' in loc else None
    if p is None or not p.exists():
     prod=(ROOT/next(z['path'] for z in c['records'] if z['path'].endswith('events.jsonl'))).parent
     p=prod/'evidence'
    cls.fixtures.append((c['id']+'25',p,c['automatic_failure_bundle_cold_verification']['manifestSha256']))
  cls.copy=pathlib.Path(cls.temp.name)/'strict150';shutil.copytree(full,cls.copy)
  cls.manifest=(cls.copy/'manifest.json').read_bytes()
 @classmethod
 def tearDownClass(cls):cls.temp.cleanup()
 def resealed(self,artifact,mutate,stage=True):
  p=self.copy/'run'/artifact;raw=p.read_bytes()
  try:
   mutate(p);m=json.loads(self.manifest)
   for e in m['files']:
    if e['path']=='run/'+artifact:e['bytes']=p.stat().st_size;e['sha256']=sha(p.read_bytes())
   (self.copy/'manifest.json').write_bytes(canon(m))
   anchor=sha((self.copy/'manifest.json').read_bytes())
   return (self.patched if stage else self.original)(self.copy,anchor)
  finally:p.write_bytes(raw);(self.copy/'manifest.json').write_bytes(self.manifest)
 def rejects(self,name,artifact,mutate,old=None):
  if old is True:
   result=self.resealed(artifact,mutate,False);self.assertTrue(result['ok'])
  with self.assertRaises(ValueError) as raised:self.resealed(artifact,mutate)
  reports.append({'case':name,'detected':True,'originalAccepted':old,'error':str(raised.exception)})
 @staticmethod
 def cj(p,mutate):d=load(p);mutate(d);p.write_bytes(canon(d))
 @staticmethod
 def ce(p,mutate):
  ev=[json.loads(l) for l in p.read_bytes().splitlines()];mutate(ev)
  for i,e in enumerate(ev):e['sequence']=i;e['previous']=sha(canon(ev[i-1])) if i else None
  p.write_bytes(b'\n'.join(canon(e) for e in ev)+b'\n')
 def test_original_anchored_fixtures_compatible(self):
  for name,source,anchor in self.fixtures:
   with self.subTest(name=name):
    target=pathlib.Path(self.temp.name)/('baseline-'+name);shutil.copytree(source,target)
    out=self.patched(target,anchor);self.assertTrue(out['ok']);reports.append({'case':'baseline:'+name,'externallyAnchored':out['externallyAnchored'],'files':out['files'],'detected':True})
 def test_three_real_semantic_gaps(self):
  self.rejects('strict-field-removed','methods.json',lambda p:self.cj(p,lambda d:d['fields'].pop(16)),old=True)
  self.rejects('methods-prose-unbacked','methods.md',lambda p:p.write_bytes(p.read_bytes()+b'Injected unsupported assertion.\n'),old=True)
  self.rejects('permission-request-removed-rechained','events.jsonl',lambda p:self.ce(p,lambda es:es.pop(2)),old=True)
 def test_every_mandatory_method_field(self):
  for i in range(24):
   with self.subTest(i=i):self.rejects('missing-method-field:'+str(i),'methods.json',lambda p,i=i:self.cj(p,lambda d:d['fields'].pop(i)))
 def test_wrong_or_duplicate_method_source(self):
  self.rejects('duplicate-name','methods.json',lambda p:self.cj(p,lambda d:d['fields'].append(copy.deepcopy(d['fields'][0]))))
  def wrong(d):
   row=next(x for x in d['fields'] if x['name']=='remote strict allocation');row['artifact']='inventory.json';row['pointer']=['remoteStrict']
  self.rejects('strict-allocation-same-value-different-source','methods.json',lambda p:self.cj(p,wrong))
  self.rejects('unavailable-version-faked','methods.json',lambda p:self.cj(p,lambda d:d.__setitem__('unavailable',['assumed version'])))
  self.rejects('quota-exclusion-limitation-missing','methods.json',lambda p:self.cj(p,lambda d:d['limitations'].pop(2)))
 def test_all_mandatory_success_gates(self):
  for i in range(10):
   with self.subTest(i=i):self.rejects('missing-gate:'+str(i),'events.jsonl',lambda p,i=i:self.ce(p,lambda es:es.pop(i)))
  self.rejects('duplicate-request-gate','events.jsonl',lambda p:self.ce(p,lambda es:es.insert(3,copy.deepcopy(es[2]))))
  self.rejects('reordered-request-and-answer','events.jsonl',lambda p:self.ce(p,lambda es:es.__setitem__(slice(4,6),[es[5],es[4]])))
 def test_gate_sources_and_actual_approval(self):
  self.rejects('approval-rejection-success-claim','approval.json',lambda p:self.cj(p,lambda d:d.__setitem__('answer','Rechazar')),old=True)
  self.rejects('approval-channel-unknown','approval.json',lambda p:self.cj(p,lambda d:d.__setitem__('channel','unknown')),old=True)
  self.rejects('approval-digest-different','approval.json',lambda p:self.cj(p,lambda d:d.__setitem__('digest','0'*64)))
  self.rejects('event-digest-different','events.jsonl',lambda p:self.ce(p,lambda es:es[2]['detail'].__setitem__('digest','0'*64)))
  self.rejects('event-admission-decision-unbacked','events.jsonl',lambda p:self.ce(p,lambda es:es[0]['detail'].__setitem__('accepted',False)))
  self.rejects('event-controller-unbacked','events.jsonl',lambda p:self.ce(p,lambda es:es[7]['detail']['controller'].__setitem__('pid',1)))
  self.rejects('event-measured-counts-unbacked','events.jsonl',lambda p:self.ce(p,lambda es:es[9]['detail']['measuredTasks'].__setitem__('scientificTasks',3)))
 def test_final_restoration(self):
  self.assertTrue(self.patched(self.copy,sha(self.manifest))['ok'])

if __name__=='__main__':
 runner=unittest.TextTestRunner(verbosity=2);result=runner.run(unittest.defaultTestLoader.loadTestsFromTestCase(Hardening))
 report={'schema':'strict-verifier-production-semantic-regression/1.0','at':datetime.now(timezone.utc).isoformat(),'originalSha256':sha((CAMP/'aggregate-resource-contrasts/source-snapshots/frozen-original40/packages/helix/src/trp/verify_bundle.py.txt').read_bytes()),'candidateSha256':sha((ROOT/'packages/helix/src/trp/verify_bundle.py.txt').read_bytes()),'patchSha256':sha((CAMP/'checks/backend-metadata-staged-20261013/verify_bundle.patch').read_bytes()),'tests':result.testsRun,'successful':result.wasSuccessful(),'errors':[(str(c),s) for c,s in result.errors],'failures':[(str(c),s) for c,s in result.failures],'cases':reports,'cloudCalls':0,'scientificJobs':0,'legacyBackendOptionExplicit':True,'scope':'Production verifier on isolated copies; externally anchored historical strict metadata explicitly qualified. Frozen original comparison retained; no bundled payloads executed.'}
 (STAGE/'semantic-regression-results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 raise SystemExit(0 if result.wasSuccessful() else 1)
