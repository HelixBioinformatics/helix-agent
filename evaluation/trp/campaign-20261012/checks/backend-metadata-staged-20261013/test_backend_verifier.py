#!/usr/bin/env python3
"""Verify backend consistency/default rejection and explicit legacy qualification.
Metadata corrections below are isolated unit fixtures, never scientific evidence.
"""
import copy,hashlib,json,pathlib,runpy,shutil,subprocess,sys,tempfile,unittest
from datetime import datetime,timezone
ROOT=pathlib.Path('/home/webiwabou/Projects/bioinformatica-org');STAGE=pathlib.Path(__file__).resolve().parent;CAMP=ROOT/'evaluation/trp/campaign-20261012'
sha=lambda b:hashlib.sha256(b).hexdigest();canon=lambda d:json.dumps(d,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode();load=lambda p:json.loads(p.read_bytes());reports=[]

def seal(bundle):
 m=load(bundle/'manifest.json')
 for row in m['files']:
  raw=(bundle/row['path']).read_bytes();row['sha256']=sha(raw);row['bytes']=len(raw)
 (bundle/'manifest.json').write_bytes(canon(m));return sha((bundle/'manifest.json').read_bytes())
def change_json(p,fn):d=load(p);fn(d);p.write_bytes(canon(d))
def change_events(p,fn):
 es=[json.loads(l) for l in p.read_bytes().splitlines()];fn(es)
 for i,e in enumerate(es):e['sequence']=i;e['previous']=sha(canon(es[i-1])) if i else None
 p.write_bytes(b'\n'.join(canon(e) for e in es)+b'\n')
def modernize(bundle):
 backend=load(bundle/'run/execution.json')['backend'];change_json(bundle/'run/run.json',lambda d:d.__setitem__('backend',backend));change_events(bundle/'run/events.jsonl',lambda es:next(e for e in es if e['outcome']=='completed')['detail'].__setitem__('backend',backend));return seal(bundle)

class Backend(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.verify=staticmethod(runpy.run_path(str(STAGE/'verify_bundle.py.txt'))['verify']);cls.tmp=tempfile.TemporaryDirectory(prefix='helix-backend-verifier-');cls.path=pathlib.Path(cls.tmp.name)
  source=CAMP/'checks/strict-full-client-final-offline/attempt-2/copied-bundle';cls.historical=cls.path/'historical';shutil.copytree(source,cls.historical);cls.anchor=load(CAMP/'checks/strict-full-client-final-offline/attempt-2/externally-recorded-terminal.json')['terminal']['executed']['manifestSha256']
  cls.modern=cls.path/'modern-metadata-unitfixture';shutil.copytree(source,cls.modern);cls.modernAnchor=modernize(cls.modern)
 @classmethod
 def tearDownClass(cls):cls.tmp.cleanup()
 def reject(self,name,path,anchor,legacy=False,expect=None):
  with self.assertRaises(ValueError) as e:self.verify(path,anchor,legacy)
  if expect:self.assertIn(expect,str(e.exception))
  reports.append({'case':name,'rejected':True,'legacyOption':legacy,'error':str(e.exception)})
 def test_historical_default_refuses(self):self.reject('historical-strict150-default',self.historical,self.anchor,expect='backend differs')
 def test_legacy_requires_external_anchor(self):self.reject('legacy-without-external-anchor',self.historical,None,True,expect='requires an external')
 def test_historical_explicit_qualified(self):
  r=self.verify(self.historical,self.anchor,True);self.assertTrue(r['ok'] and r['externallyAnchored'] and r['legacyBackendMetadata']);self.assertEqual(r['files'],150);reports.append({'case':'historical-qualified150','result':r})
 def test_current_metadata_default_pass(self):
  r=self.verify(self.modern,self.modernAnchor);self.assertTrue(r['ok']);self.assertFalse(r['legacyBackendMetadata']);reports.append({'case':'modern-metadata-unitfixture-default','result':r,'scientificOutputRegenerated':False})
 def test_known_and_unknown_metadata_mismatches(self):
  for which,value in [('run','unknown'),('completion','unknown'),('run','trp-slurm-ssh/1.0.0'),('completion','trp-slurm-ssh/1.0.0')]:
   with tempfile.TemporaryDirectory(prefix='backend-mismatch-') as tmp:
    b=pathlib.Path(tmp)/'copy';shutil.copytree(self.modern,b)
    if which=='run':change_json(b/'run/run.json',lambda d:d.__setitem__('backend',value))
    else:change_events(b/'run/events.jsonl',lambda es:next(e for e in es if e['outcome']=='completed')['detail'].__setitem__('backend',value))
    anchor=seal(b)
    for opt in [False,True]:self.reject(which+':'+value+':'+str(opt),b,anchor,opt,expect='backend differs')
 def test_unknown_prepared_execution_backend(self):
  with tempfile.TemporaryDirectory(prefix='backend-unknown-') as tmp:
   b=pathlib.Path(tmp)/'copy';shutil.copytree(self.modern,b);change_json(b/'run/execution.json',lambda d:d.__setitem__('backend','unknown'))
   # Rebuild hypothetical approved digest only to reach the execution enum gate.
   # Later approvals are deliberately not repaired; this is a malformed test.
   change_json(b/'manifest.json',lambda m:m['bundle']['files'].__setitem__('execution.json',sha((b/'run/execution.json').read_bytes())))
   change_json(b/'manifest.json',lambda m:m['bundle'].__setitem__('digest',sha(canon({'engine':m['bundle']['engine'],'files':m['bundle']['files']}))))
   self.reject('unsupported-execution-backend',b,seal(b),expect='unsupported execution backend')
 def test_ordinary_mapped_cancel_negative_default_compatible(self):
  cases=[]
  x=load(CAMP/'trace/lab1-helix-reference.anchor.json');cases.append(('ordinary144',CAMP/'cloud/lab1/helix-reference/evidence',x['manifestSha256']))
  x=load(CAMP/'cloud/lab1/mapped-reference-protocol/driver-terminal.json');cases.append(('mapped156',CAMP/'cloud/lab1/mapped-reference/evidence',x['portable']['manifestSha256']))
  x=load(CAMP/'cloud/lab1/cancellation/next-ctx-abort/driver-terminal.json');cases.append(('clean143',CAMP/'cloud/lab1/cancellation/next-ctx-abort'/x['evidence'],x['manifestSha256']))
  for c in load(CAMP/'event-negative-contrasts/audit.json')['cases']:
   if c['automatic_failure_bundle_cold_verification']:
    p=(ROOT/next(z['path'] for z in c['records'] if z['path'].endswith('events.jsonl'))).parent/'evidence';cases.append((c['id']+'25',p,c['automatic_failure_bundle_cold_verification']['manifestSha256']))
  for name,source,anchor in cases:
   with self.subTest(name=name):
    b=self.path/name;shutil.copytree(source,b);r=self.verify(b,anchor);self.assertTrue(r['ok']);self.assertFalse(r['legacyBackendMetadata']);reports.append({'case':name,'result':r})
 def test_semantic_gaps_still_rejected_after_backend_fixed(self):
  for artifact,kind in [('methods.json','missingstrict'),('methods.md','prose'),('events.jsonl','missingrequest')]:
   with tempfile.TemporaryDirectory(prefix='backend-semantic-') as tmp:
    b=pathlib.Path(tmp)/'copy';shutil.copytree(self.modern,b)
    if kind=='missingstrict':change_json(b/'run'/artifact,lambda d:d['fields'].pop(16))
    elif kind=='prose':(b/'run'/artifact).write_bytes((b/'run'/artifact).read_bytes()+b'Unbacked assertion.\n')
    else:change_events(b/'run'/artifact,lambda es:es.pop(2))
    self.reject('semantic:'+kind,b,seal(b))
 def test_cli_actual_options_and_outputs(self):
  for suffix,args,code,qualified in [('default',[],1,False),('qualified',['--sha256',self.anchor,'--allow-legacy-strict-backend'],0,True),('missinganchor',['--allow-legacy-strict-backend'],1,False)]:
   command=[sys.executable,str(STAGE/'verify_bundle.py.txt'),str(self.historical),*args];r=subprocess.run(command,capture_output=True,text=True)
   self.assertEqual(r.returncode,code);result=json.loads(r.stdout)
   if qualified:self.assertTrue(result['legacyBackendMetadata'] and result['externallyAnchored'])
   reports.append({'case':'CLI:'+suffix,'exitCode':r.returncode,'output':result,'stderr':r.stderr})

if __name__=='__main__':
 result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Backend));d={'schema':'helix-backend-verifier-staging-test/1.0','at':datetime.now(timezone.utc).isoformat(),'tests':result.testsRun,'successful':result.wasSuccessful(),'errors':[(str(c),s) for c,s in result.errors],'failures':[(str(c),s) for c,s in result.failures],'cases':reports,'candidateSha256':sha((STAGE/'verify_bundle.py.txt').read_bytes()),'patchSha256':sha((STAGE/'verify_bundle.patch').read_bytes()),'scienceOrCloudReruns':0}
 (STAGE/'backend-verifier-test-results.json').write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n');raise SystemExit(0 if result.wasSuccessful() else 1)
