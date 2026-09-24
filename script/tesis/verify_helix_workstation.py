#!/usr/bin/env python3
"""Recheck released Helix and a pinned development geometry on another workstation.
Input directory contains helix-install, verify_bundle.py, evidence/, 2xqh.pdb,
and expected-geometry.csv. No model/API calls; synthetic corpus tests integrity only.
"""
import argparse,hashlib,json,os,platform,shutil,subprocess,time,uuid
from pathlib import Path

def main():
    p=argparse.ArgumentParser();p.add_argument('input',type=Path);p.add_argument('output',type=Path);args=p.parse_args()
    src=args.input.resolve();out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    env=dict(os.environ);env['PATH']=str(Path.home()/'.helix/bin')+':'+str(Path.home()/'.local/bin')+':'+env['PATH'];env['HELIX_DISABLE_AUTOUPDATE']='1'
    def run(label,cmd,timeout=120):
        start=time.monotonic();r=subprocess.run(cmd,capture_output=True,env=env,timeout=timeout)
        (out/(label+'.stdout')).write_bytes(r.stdout);(out/(label+'.stderr')).write_bytes(r.stderr)
        return {'exit_code':r.returncode,'elapsed_seconds':round(time.monotonic()-start,3),'command':cmd}
    results={};results['version']=run('version',['helix','--version']);results['environment']=run('environment',['helix','debug','env']);results['nextflow']=run('nextflow',['nextflow','-version'])
    binary=Path(shutil.which('helix',path=env['PATH']));before=hashlib.sha256(binary.read_bytes()).hexdigest()
    results['reinstall_same_version']=run('reinstall',['bash',str(src/'helix-install'),'--version','0.3.0','--no-modify-path'])
    after=hashlib.sha256(binary.read_bytes()).hexdigest()
    anchor='07293b0c40b7dbeac80ea5d6289815cc772c2767fd3dafa22f5fb940e150aaa0'
    cmd=['python3',str(src/'verify_bundle.py'),str(src/'evidence'),'--sha256',anchor]
    results['portable_intact']=run('portable-intact',cmd)
    damaged=out/'damaged-evidence';shutil.copytree(src/'evidence',damaged)
    with (damaged/'run/source.pdb').open('ab') as f:f.write(b'\nREMARK injected integrity test\n')
    results['portable_altered']=run('portable-altered',[*cmd[:2],str(damaged),*cmd[3:]])
    shutil.rmtree(damaged)
    corpus=out/'synthetic-corpus';corpus.mkdir();data=b'{"accession":"P69905"}\n'
    (corpus/'data.ndjson').write_bytes(data)
    (corpus/'data.manifest.json').write_text(json.dumps({'source':'synthetic integrity fixture, not scientific data','endpoint':'https://example.invalid/fixture','fetchedAt':'2026-09-23T00:00:00Z','data':'data.ndjson','rows':1,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}))
    results['cli_intact']=run('cli-intact',['helix','verify',str(corpus),'--no-color'])
    (corpus/'data.ndjson').write_bytes(data+b'{}\n');results['cli_altered']=run('cli-altered',['helix','verify',str(corpus),'--no-color'])
    (corpus/'data.ndjson').write_bytes(data)
    work=out/'geometry';work.mkdir();shutil.copy2(src/'2xqh.pdb',work/'2xqh.pdb')
    image='sha256:1dd91e70acb153a0bd9a51346fc001dd5025f851c9598697cdd37f07d9490b0a';name='helix-reference-'+uuid.uuid4().hex
    units='161_175,176_189,190_203,204_217,218_233,234_249,250_263,264_276,305_326,327_350,373_392,393_416'
    command=['docker','run','--rm','--name',name,'--network','none','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','--pids-limit','128','--cpus','2','--memory','2g','--tmpfs','/tmp','--user',f'{os.getuid()}:{os.getgid()}','--mount',f'type=bind,src={work},dst=/work',image,'single','/work/2xqh.pdb','A','/work/geometry.csv',units,'-ins_def','351_372']
    try:results['geometry']=run('geometry',command)
    except subprocess.TimeoutExpired:
        subprocess.run(['docker','stop','--time','2',name],capture_output=True,timeout=15);raise
    csv=work/'geometry.csv';identical=csv.exists() and csv.read_bytes()==(src/'expected-geometry.csv').read_bytes()
    ok=all(v['exit_code']==0 for k,v in results.items() if k not in ('portable_altered','cli_altered')) and all(results[k]['exit_code']!=0 for k in ('portable_altered','cli_altered')) and identical and before==after
    report={'kind':'development and deployment verification; not held-out evaluation','hostname':platform.node(),'kernel':platform.release(),'cpu_count':os.cpu_count(),'helix_binary':str(binary),'helix_sha256':before,'installer_idempotent':before==after,'geometry_identical':identical,'geometry_units':12,'results':results,'ok':ok,'llm_calls':0,'limitations':['No hard storage quota for this geometry run.','Released CLI and pinned scientific container are tested separately; this is not natural-language end-to-end evaluation.']}
    (out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'ok':ok,'results':{k:v['exit_code'] for k,v in results.items()},'geometry_identical':identical}));return 0 if ok else 1
if __name__=='__main__':raise SystemExit(main())
