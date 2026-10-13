#!/usr/bin/env python3
"""Offline engineering audit and faults on one copied strict full-client export.
Never runs payload scripts, model calls, scientific jobs, SSH or cloud APIs.
Run with --output a new directory. Originals are read and hashed only.
"""
import argparse, copy, csv, hashlib, io, json, pathlib, re, runpy, shutil, sqlite3, subprocess, sys
from collections import Counter
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parents[5]
BASE = ROOT/'evaluation/trp/campaign-20261012/aggregate-resource-contrasts'
TRUSTED = ROOT/'packages/helix/src/trp/verify_bundle.py.txt'
ORDINARY = ROOT/'script/tesis/audit_remote_campaign.py'

def sha(x): return hashlib.sha256(x).hexdigest()
def canon(x): return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def js(x): return json.dumps(x,ensure_ascii=False,separators=(',',':'),allow_nan=False)
def load(p): return json.loads(p.read_bytes())
def save(p,x): p.write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def demand(test,msg):
    if not test: raise ValueError(msg)
def lines(p): return [json.loads(x) for x in p.read_bytes().splitlines() if x.strip()]
def index(p): return {x.relative_to(p).as_posix():sha(x.read_bytes()) for x in p.rglob('*') if x.is_file() and not x.is_symlink()}
def now(): return datetime.now(timezone.utc).isoformat()

EXPECTED_METHODS = [
 ('protein','specification.json',['structure','value','pdb']),('chain','specification.json',['chain','value']),
 ('model','specification.json',['model','value']),('units','specification.json',['units','value','ranges']),
 ('insertions','specification.json',['insertions','value']),('coordinate contract','specification.json',['units','value','contract']),
 ('GeomeTRe revision','catalogue.json',None),('parameter contract','catalogue.json',None),
 ('input hash','specification.json',['structure','value','sha256']),('engine','execution.json',['engine']),
 ('image','execution.json',['container']),('command','execution.json',['run']),('counts','admission.json',['demand','counts']),
 ('storage estimate','admission.json',['demand','workBytes']),('status','run.json',['status']),
 ('co-located Slurm transport','execution.json',['transport']),('remote strict allocation','remote_strict_policy.json',[]),
 ('worker input staging','execution.json',['inputStaging']),('client storage estimate','admission.json',['demand','storage']),
 ('structural controls','structural_report.json',['summary']),('Nextflow version output','software.json',['nextflowVersionOutput']),
 ('execution backend','execution.json',['backend']),('remote infrastructure','execution.json',['target']),('numerical profile','execution.json',['numericalProfile'])]
LIMITATIONS = [
 'Author-PDB numbering; supplied units, not repeat detection; experimental B-factor is not pLDDT.',
 'The real Helix client runs on the verified head. Local Python transport invokes the controller; Slurm executes worker jobs. This is not an SSH transport experiment.',
 'Root-owned policy and kernel receipts bind one XFS project quota covering declared client work/temp/state/cache/export and NFS remote work. Real Helix and Python/Nextflow share 1 CPU/2 GiB/swap-zero controller cgroup; sequential worker containers use 2 CPU/2 GiB. Root sampler records current usage separately from total-run entitlement. Preloaded read-only software/image caches and external root-supervisor records are infrastructure outside workBytes.',
 'Offline verification checks bytes and declared links, not scientific truth or an authenticated human identity.',
 'Agent provider/model/cost are not observed by this workflow; task software is identified by the pinned catalogue reference and image.']


def methods_check(bundle):
    r=bundle/'run'; m=load(r/'methods.json'); c=load(r/'catalogue.json')
    gi=next(i for i,e in enumerate(c['entries']) if e['id']=='geometre.geometry')
    expected=copy.deepcopy(EXPECTED_METHODS)
    expected[6]=('GeomeTRe revision','catalogue.json',['entries',gi,'source','revision'])
    expected[7]=('parameter contract','catalogue.json',['entries',gi,'parameters'])
    demand([(f['name'],f['artifact'],f['pointer']) for f in m['fields']]==expected,'Exact24 field inventory/source pointers differ')
    checked=[]
    for f in m['fields']:
        demand(re.fullmatch(r'[a-zA-Z0-9_.-]+',f['artifact']) is not None,'Unsafe methods artifact')
        v=load(r/f['artifact'])
        for k in f['pointer']: v=v[k]
        demand(v==f['value'],'Methods value not source-backed: '+f['name'])
        checked.append({'name':f['name'],'artifact':f['artifact'],'pointer':f['pointer'],'sourceSha256':sha((r/f['artifact']).read_bytes()),'equal':True})
    demand(m['limitations']==LIMITATIONS and m['unavailable']==[], 'Strict limitations/software availability differs')
    s,e,a,t,w=load(r/'specification.json'),load(r/'execution.json'),load(r/'admission.json'),load(r/'run.json'),load(r/'software.json')
    paragraph=['# Métodos de la ejecución registrada','',
       f"Se procesó {s['structure']['value']['pdb']}, cadena autora {s['chain']['value']}, modelo {s['model']['value']}, con {len(s['units']['value']['ranges'])} unidades suministradas. La entrada se identifica mediante SHA-256 {s['structure']['value']['sha256']}.",'',
       f"El adaptador {e['engine']} generó la orden {js(e['run'])} y fijó la imagen {e['container']}. La revisión de GeomeTRe es {c['entries'][gi]['source']['revision']}; su contrato de parámetros es {js(c['entries'][gi]['parameters'])}. Se planificaron dos tareas simuladas y dos reales, sin reintentos; tareas científicas en infraestructura remota: {a['demand']['counts']['remoteScientificCalls']}. Estado registrado: {t['status']}.",'',
       f"Salida observada de la consulta de versión de Nextflow: {js(w['nextflowVersionOutput'])}.",'',
       f"La reserva estimada de almacenamiento fue {a['demand']['workBytes']} bytes. Los campos y sus fuentes se encuentran en methods.json; el inventario, el presupuesto, las decisiones y los eventos se conservan en archivos separados.",'',
       *['- '+l for l in LIMITATIONS],'']
    demand((r/'methods.md').read_text()=='\n'.join(paragraph),'Methods markdown differs from independent exact template')
    demand(e['backend']=='trp-slurm-colocated-strict/1.0.0' and e['transport']=='co-located-python','Methods transport differs')
    demand(w['imageId']==e['container'] and w['backend']==e['backend'],'Actual software image/backend differs')
    demand(w['nextflowVersionOutput']==(r/'remote-version.log').read_text(),'Nextflow version not linked to raw probe output')
    demand(w['slurmVersionOutput']=='slurm-wlm 23.11.4\n','Slurm version unexpected')
    demand(s['structure']['value']['sha256']==sha((r/'source.pdb').read_bytes()),'Input source hash differs')
    return {'fieldsChecked':len(checked),'requiredFields':24,'fields':checked,'markdownReconstructed':True,'exactLimitations':True,'scientificTruthEstablished':False}


def gate_check(bundle):
    r=bundle/'run'; ev=lines(r/'events.jsonl'); digest=load(r/'run.json')['digest']
    expected=[('admission','accepted-for-review'),('protocol','not-committed'),('permission','requested'),('permission','returned-allowed'),('approval','requested'),('approval','answered'),('admission','recheck-accepted'),('execution','remote-started'),('admission','analysis-accepted'),('execution','completed')]
    demand([(e['source'],e['outcome']) for e in ev]==expected,'Exact mandatory10 gate types/count/order differs')
    for i,e in enumerate(ev):
        demand(e['sequence']==i and e['previous']==(sha(canon(ev[i-1])) if i else None),'Event hash chain differs')
        if 'digest' in e['detail']: demand(e['detail']['digest']==digest,'Event proposal binding differs')
        dt=datetime.fromisoformat(e['at'].replace('Z','+00:00'));demand(dt.tzinfo is not None,'Event timestamp lacks timezone')
    demand(ev[0]['detail']==load(r/'admission.json'),'Initial admission event/source differs')
    demand(ev[1]['detail']==load(r/'protocol.json'),'Protocol event/source differs')
    for i,n in [(6,'recheck.json'),(8,'analysis-admission.json')]: demand(ev[i]['detail']==load(r/n)['decision'],'Recheck event differs: '+n)
    ap=load(r/'approval.json');demand(ap['channel']=='Question.Service' and ap['answer']=='Aprobar y ejecutar' and ap['digest']==digest,'Approval source differs')
    demand(ev[5]['detail']['answers']==[['Aprobar y ejecutar']],'Recorded approval answer differs')
    demand(ev[7]['detail']['controller']==load(r/'remote-controller-identity.json'),'Controller start gate identity differs')
    t=load(r/'run.json');demand(ev[9]['detail']['geometry']==t['geometry'] and ev[9]['detail']['measuredTasks']==t['measuredTasks'],'Completion detail/source differs')
    # The production completion detail still says generic Slurm SSH version;
    # execution.json/methods correctly distinguish strict co-located transport.
    return {'gatesChecked':10,'countBySource':dict(Counter(e['source'] for e in ev)), 'exactSequence':expected,'ledgerSourceBindings':True,'callbackActionsIndependentlyCaptured':False,'approval':'Synthetic engineering driver calling real Question.Service; no authenticated human',
      'qualification':'Successful mandatory-path coverage. No live success-path callback action oracle was emitted (gateRecords=[]); separate negative13 action contrast provides action-versus-ledger comparisons.',
      'legacyCompletionDetailBackend':ev[9]['detail'].get('backend'),'actualExecutionBackend':load(r/'execution.json')['backend']}


def strict_check(bundle,external,ordinary,ns):
    r=bundle/'run'; allocation=load(r/'remote_strict_policy.json');p=allocation['policy']; e=load(r/'execution.json');su=external['supervision']
    demand(e['target']['strict']==allocation and e['target']['fingerprint']==allocation['targetFingerprint'],'Strict target binding differs')
    b=load(r/'budget.json')
    demand(p['entitlement']=={k:b[k] for k in ['cpus','memoryBytes','workBytes','wallSeconds']},'Strict entitlement vs budget differs')
    demand(p['checker']['sha256']==sha((r/'remote_strict.py').read_bytes())==external['freeze']['sourceHashes']['packages/helix/src/trp/remote_strict.py.txt'],'Approved strict checker code differs')
    receipts=[]
    for name,rec in [('inventory.json',load(r/'inventory.json')['remoteStrictObservation']),('recheck.json',load(r/'recheck.json')['inventory']['remoteStrictObservation']),('analysis-admission.json',load(r/'analysis-admission.json')['inventory']['remoteStrictObservation']),('remote-strict-start.json',load(r/'remote-strict-start.json')),('remote-strict-before-science.json',load(r/'remote-strict-before-science.json'))]:
        ns['strict_receipt'](rec,allocation)
        demand(rec['role']==('controller' if name in ('remote-strict-before-science.json','analysis-admission.json') else 'client'),'Wrong receipt process role')
        receipts.append({'artifact':name,'role':rec['role'],'pid':rec['pid'],'membership':rec['membership'],'pathsWitnessed':len(rec['paths']),'sampleAgeSeconds':rec['checkedAt']-json.loads(rec['sampleRaw'])['observedAt'],'valid':True})
    config=(r/'nextflow.config').read_text();demand("process.stageInMode = 'copy'" in config and e['inputStaging']=='copy','Physical stageInMode not set')
    # Actual exported work inputs are regular copied files; no symbolic inputs.
    worker_inputs=[x for x in r.glob('work/*/*/*') if x.name in ('source.pdb','2xqh.pdb','settings.json')]
    demand(worker_inputs and all(x.is_file() and not x.is_symlink() for x in worker_inputs),'Worker copied files absent')
    runtime=ordinary['check_runtime'](r);native=ordinary['check_native_jobs'](r)
    demand(su['policySha256']==allocation['policySha256'] and su['actualExitCode']==0 and su['controllerAndTracerReaped'],'External root supervisor terminal differs')
    cg=su['finalCgroup'];demand(cg['cpu.max']=='100000 100000' and cg['memory.max']=='2147483648' and cg['memory.swap.max']=='0','Actual root final limits differ')
    demand(cg['cgroup.procs'].strip()=='' and 'populated 0' in cg['cgroup.events'] and su['nativeCleanup']['remaining']==[],'Client/controller/native cleanup not terminal')
    sample=su['finalQuota'];q=sample['quota'];demand(sample['policySha256']==allocation['policySha256'] and q['hardBytes']==p['filesystem']['hardBytes'],'External quota evidence differs')
    rows=re.findall(r'^#?'+str(p['filesystem']['projectId'])+r'\s+(\d+)\s+(\d+)\s+(\d+)\s',q['reportSource'],re.M)
    demand(len(rows)==1 and int(rows[0][0])*1024==q['usedBytes'] and int(rows[0][2])*1024==q['hardBytes'],'External raw kernel quota report differs')
    demand(q['treeCheckExitCode']==0 and not q['treeCheckStdout'].strip() and not q['treeCheckStderr'].strip(),'Final project inheritance check not clean')
    demand(q['usedBytes']<=q['hardBytes'],'Actual project over budget')
    dbs=list((external['retained']/'state').rglob('helix-local.db'));demand(len(dbs)==1,'Persistent SQLite DB not retained')
    db=dbs[0];con=sqlite3.connect(f'file:{db.resolve()}?mode=ro&immutable=1',uri=True)
    tables=[t[0] for t in con.execute("select name from sqlite_master where type='table'")];con.close();demand('session' in tables and len(tables)>=10,'Actual persistent SQLite schema missing')
    return {'strictReceipts':receipts,'projectId':p['filesystem']['projectId'],'quotaHardBytes':q['hardBytes'],'observedFinalProjectBytes':q['usedBytes'],'controllerCgroup':p['controller'],'actualFinalCgroup':cg,'workerRuntime':{k:v for k,v in runtime.items() if k not in ('hard_controller_limit_verified','hard_aggregate_disk_quota_verified')},'nativeJobs':native,'persistentSqlite':{'bytes':db.stat().st_size,'sha256':sha(db.read_bytes()),'tables':len(tables),'readonlyInspection':True},'copyStaging':True,'quotaScope':'Declared client/cache/state/temp/export+NFS work in one project; immutable preinstalled software/image caches and external root experiment telemetry excluded','globalCloudDiskQuotaClaim':False}


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--output',type=pathlib.Path,required=True);ap.add_argument('--case-root',type=pathlib.Path,default=BASE/'campaign-outcomes/AGG-01-generous');args=ap.parse_args()
    out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    case=args.case_root.resolve();recovered=next((case/'recovered').iterdir());original=recovered/'retained-allocation/export/portable-evidence';original_index=index(original)
    frozen=load(BASE/'campaign-inputs/freeze.json');item=next(x for x in frozen['cases'] if x['id']==case.name)
    trustedbytes=TRUSTED.read_bytes();demand(sha(trustedbytes)==frozen['sourceHashes'][str(TRUSTED.relative_to(ROOT))],'Trusted verifier changed from final freeze')
    (out/'trusted-verifier.py').write_bytes(trustedbytes);(out/'ordinary-auditor.py').write_bytes(ORDINARY.read_bytes())
    ns=runpy.run_path(str(out/'trusted-verifier.py'),run_name='trusted_verifier');verify=ns['verify'];ordinary=runpy.run_path(str(ORDINARY),run_name='ordinary_observer')
    raw=(recovered/'experiment-telemetry.stdout').read_bytes();terminal=[json.loads(l.split(b':',1)[1]) for l in raw.splitlines() if l.startswith(b'HELIX_FULL_TERMINAL:')];demand(len(terminal)==1,'One external terminal anchor required');terminal=terminal[0]
    anchor=terminal['terminal']['executed']['manifestSha256'];demand(not terminal['executionOracleForcedOnly'] and terminal['status']=='succeeded','Requires ordinary non-override successful strict case')
    save(out/'externally-recorded-terminal.json',terminal)
    bundle=out/'copied-bundle';shutil.copytree(original,bundle)
    baseline=verify(bundle,anchor);save(out/'baseline.json',baseline)
    compatibility=subprocess.run([sys.executable,str(ORDINARY),str(bundle),'--sha256',anchor,'--output',str(out/'ordinary-auditor-compatibility.json')],capture_output=True,text=True)
    (out/'ordinary-auditor-compatibility.stdout').write_text(compatibility.stdout);(out/'ordinary-auditor-compatibility.stderr').write_text(compatibility.stderr)
    external={'freeze':frozen,'case':item,'retained':recovered/'retained-allocation','supervision':load(recovered/'supervision.json')}
    report={'schema':'helix-strict-full-client-offline-review/1.0','at':now(),'case':case.name,'externalManifestSha256':anchor,'trustedVerifierSha256':sha(trustedbytes),'freezeSha256':sha((BASE/'campaign-inputs/freeze.json').read_bytes()),'externalTelemetrySha256':sha(raw),'sourceBundlePath':str(original.relative_to(ROOT)),'externalRootArchiveSha256':load(case/'recovery.json')['archiveSha256'],'checks':[],'limits':['Engineering development case2XQH/A; supplied units and same-image exact numerical gold, no independent biological truth.','No model/human evaluator involved. Root-owned evidence is not third-party remote attestation.','Successful ten-gate sequence has no separately captured callback oracle; negative13 contrast is separately cited.','All artifacts are faulted as exported; artifacts absent from this profile (SIFTS/optional steric/SASA) are covered by their separate campaigns, not this one.']}
    def checked(name,fn):
        try: value=fn();report['checks'].append({'name':name,'passed':True,'result':value});return value
        except (OSError,ValueError,KeyError,TypeError,StopIteration,AssertionError) as err: report['checks'].append({'name':name,'passed':False,'error':str(err)});return None
    checked('cold_portable_integrity_external_anchor',lambda:baseline)
    checked('all24_methods_source_pointers_and_exact_template',lambda:methods_check(bundle))
    checked('exact10_gates_sources_order_hash_chain',lambda:gate_check(bundle))
    checked('strict_policy_quota_cgroup_client_worker_native_scope',lambda:strict_check(bundle,external,ordinary,ns))
    actual=(bundle/'run/results/geometry.csv').read_bytes();goldpath=BASE/'campaign-inputs/gold'/item['graphId']/'geometry.csv'
    if not goldpath.exists():
        goldpath=ROOT/'evaluation/trp/campaign-20261012/cloud/lab2/r24-campaign/inputs/gold'/item['graphId']/'geometry.csv'
    checked('independently_frozen_per_input_gold',lambda: {'sha256':sha(actual),'goldSha256':sha(goldpath.read_bytes()),'byteIdentical':True,'graph':item['graphId']} if actual==goldpath.read_bytes() and sha(actual)==item['goldCsvSha256'] else (_ for _ in ()).throw(ValueError('Own frozen per-input gold differs')))
    report['ordinarySshAuditorCompatibility']={'exitCode':compatibility.returncode,'coLocatedSupported':False,'reason':'The old auditor fixes backend SSH and old limitations. Its reusable native/runtime readers are reused; new strict observer checks actual receipts/scope.'}
    # Every exported file including checker, policy, receipts, logs, inputs, caches and bundled verifier.
    faults=[];manifest_raw=(bundle/'manifest.json').read_bytes();m=load(bundle/'manifest.json')
    def reject(name,fn,level):
        try: fn()
        except (OSError,ValueError,KeyError,TypeError,RecursionError,StopIteration) as er: faults.append({'case':name,'detected':True,'level':level,'error':str(er)[:400]})
        else: faults.append({'case':name,'detected':False,'level':level})
    for f in m['files']:
        path=bundle/f['path'];payload=path.read_bytes();path.unlink()
        reject('missing:'+f['path'],lambda:verify(bundle,anchor),'external-anchor+bytes')
        path.write_bytes(bytes([payload[0]^1])+payload[1:] if payload else b'altered')
        reject('mutated:'+f['path'],lambda:verify(bundle,anchor),'external-anchor+bytes')
        path.unlink();path.symlink_to(original/f['path'])
        reject('symlink:'+f['path'],lambda:verify(bundle,anchor),'export-type')
        path.unlink();path.write_bytes(payload)
    mf=bundle/'manifest.json';mf.unlink();reject('missing:manifest.json',lambda:verify(bundle,anchor),'external-anchor');mf.write_bytes(manifest_raw+b' ');reject('mutated:manifest.json',lambda:verify(bundle,anchor),'external-anchor');mf.unlink();mf.symlink_to(original/'manifest.json');reject('symlink:manifest.json',lambda:verify(bundle,anchor),'export-type');mf.unlink();mf.write_bytes(manifest_raw)
    for name in ['../escape','/tmp/escape','run/../escape','C:\\escape','run//source.pdb']:
        bad=copy.deepcopy(m);bad['files'][0]['path']=name;save(mf,bad);reject('unsafe-path:'+name,lambda:verify(bundle),'path-without-anchor')
    mf.write_bytes(manifest_raw);(bundle/'unlisted.txt').write_text('extra');reject('unlisted',lambda:verify(bundle,anchor),'file-inventory');(bundle/'unlisted.txt').unlink();reject('wrong-anchor',lambda:verify(bundle,'0'*64),'external-anchor')
    # Re-seal the mutated artifact hash to distinguish semantic checks from byte-integrity.
    # This deliberately makes a NEW manifest anchor; never pretends it equals original.
    semantic=[]
    def semantic_case(name,artifact,mutate,observer=None):
        p=bundle/'run'/artifact;raw=p.read_bytes();mutate(p);new=copy.deepcopy(m)
        for row in new['files']:
            if row['path']=='run/'+artifact:row['sha256']=sha(p.read_bytes());row['bytes']=p.stat().st_size
        save(mf,new);testanchor=sha(mf.read_bytes())
        verifier_error=None;observer_error=None
        try:verify(bundle,testanchor)
        except (OSError,ValueError,KeyError,TypeError,RecursionError) as er:verifier_error=str(er)
        if observer:
            try:observer(bundle)
            except (OSError,ValueError,KeyError,TypeError,RecursionError,StopIteration) as er:observer_error=str(er)
        semantic.append({'case':name,'artifact':artifact,'originalAnchorIntentionallyNotUsed':True,'trustedVerifierDetected':verifier_error is not None,'separateObserverDetected':observer_error is not None,'detected':verifier_error is not None or observer_error is not None,'verifierError':verifier_error,'observerError':observer_error})
        p.write_bytes(raw);mf.write_bytes(manifest_raw)
    def change_json(p,fn):d=load(p);fn(d);save(p,d)
    for artifact in ['remote-strict-start.json','remote-strict-before-science.json']:
        semantic_case(artifact+':memory-cap',artifact,lambda p:change_json(p,lambda d:d['cgroup'].__setitem__('memory.max','4294967296')))
        semantic_case(artifact+':membership',artifact,lambda p:change_json(p,lambda d:d.__setitem__('membership','0::/init.scope')))
        semantic_case(artifact+':freshness',artifact,lambda p:change_json(p,lambda d:d.__setitem__('checkedAt',d['checkedAt']+10)))
        semantic_case(artifact+':path-project',artifact,lambda p:change_json(p,lambda d:d['paths'][0].__setitem__('projectId',0)))
        semantic_case(artifact+':subtract-usage',artifact,lambda p:change_json(p,lambda d:d.__setitem__('currentUsageIsSubtractedFromEntitlement',True)))
    semantic_case('policy:quota','remote_strict_policy.json',lambda p:change_json(p,lambda d:d['policy']['filesystem'].__setitem__('hardBytes',d['policy']['filesystem']['hardBytes']*2)))
    semantic_case('checker:bytes','remote_strict.py',lambda p:p.write_bytes(p.read_bytes()+b'\n# injected semantic checker mutation\n'))
    semantic_case('method:unsupported-value','methods.json',lambda p:change_json(p,lambda d:d['fields'][0].__setitem__('value','other')) ,methods_check)
    semantic_case('method:missing-strict-field','methods.json',lambda p:change_json(p,lambda d:d['fields'].pop(16)),methods_check)
    semantic_case('method:unsupported-prose','methods.md',lambda p:p.write_text(p.read_text()+'Unsupported injected claim.\n'),methods_check)
    def drop_gate(p):
        data=lines(p);data.pop(2)
        for i,ev in enumerate(data):ev['sequence']=i;ev['previous']=sha(canon(data[i-1])) if i else None
        p.write_bytes(b'\n'.join(canon(ev) for ev in data)+b'\n')
    semantic_case('gate:permission-request-removed-rechained','events.jsonl',drop_gate,gate_check)
    semantic_case('runtime:effective-memory','remote-task-runtime.json',lambda p:change_json(p,lambda d:d['records'][0].__setitem__('memoryMax','4294967296')))
    semantic_case('runtime:raw-link','remote-task-runtime.json',lambda p:change_json(p,lambda d:d['records'][0].__setitem__('hostname','tampered')),lambda b:ordinary['check_runtime'](b/'run'))
    semantic_case('native:raw-node','remote-native-jobs.jsonl',lambda p:p.write_text(p.read_text().replace('NodeList=helix-worker1','NodeList=helix-worker2')),lambda b:ordinary['check_native_jobs'](b/'run'))
    restored=verify(bundle,anchor);restored_methods=methods_check(bundle);restored_gates=gate_check(bundle)
    demand(index(bundle)==original_index,'Final copied bundle not restored exactly')
    demand(index(original)==original_index,'Original bundle changed during offline audit')
    faults_report={'schema':'helix-strict-full-client-faults/1.0','at':now(),'manifestAnchor':anchor,'trustedVerifierSha256':sha(trustedbytes),'listedArtifacts':len(m['files']),'newStrictArtifacts':[f['path'] for f in m['files'] if 'strict' in f['path']],'injected':len(faults),'detected':sum(x['detected'] for x in faults),'checks':faults,'semanticInjected':len(semantic),'semanticDetected':sum(x['detected'] for x in semantic),'semanticChecks':semantic,'baseline':baseline,'restored':restored,'finalCopyByteEqualToOriginal':True,'originalUnchanged':True,'limitations':['Deterministic byte/path/type and selected semantic robustness on one engineering export; no estimated adversary success rate.','All symlinks are rejected even when target bytes match.','Semantic mutations use newly resealed hypothetical anchors; they are not the externally anchored original. Separate observer closes exact10gate/24field/prose checks absent from the generic verifier.']}
    save(out/'fault-injection.json',faults_report)
    report['faultInjection']={'artifacts':len(m['files']),'injected':len(faults),'detected':sum(x['detected'] for x in faults),'semanticInjected':len(semantic),'semanticDetected':sum(x['detected'] for x in semantic),'restored':restored,'originalUnchanged':True}
    report['verified']=all(x['passed'] for x in report['checks']) and all(x['detected'] for x in faults+semantic)
    save(out/'audit.json',report);save(out/'original-file-hashes.json',original_index)
    print(json.dumps({'verified':report['verified'],'checks':[(x['name'],x['passed']) for x in report['checks']],'faults':report['faultInjection'],'output':str(out)},indent=2))
    return 0 if report['verified'] else 1

if __name__=='__main__':sys.exit(main())
