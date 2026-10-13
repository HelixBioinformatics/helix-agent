#!/usr/bin/env python3
"""Clone the public frozen runtime, overlay only repaired producer/harness bytes."""
import hashlib, importlib.util, json, shlex, subprocess, tarfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[6]
HERE = Path(__file__).resolve().parent
RUNTIME = '/opt/helix-post-campaign-runtime-20261013-r1'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    output = HERE / 'runtime'
    output.mkdir(exist_ok=False)
    archive = output / 'public-overlay.tar'
    paths = [ROOT / 'packages/helix/src/trp' / name for name in ['workflow.ts', 'remote_runner.py.txt', 'verify_bundle.py.txt']]
    paths += [HERE / name for name in ['full_client.ts', 'prepare_integration.ts', 'fault_native.py', 'drive_integration.py']]
    records = {}
    with tarfile.open(archive, 'w') as tar:
        for path in paths:
            name = str(path.relative_to(ROOT))
            records[name] = {'bytes':path.stat().st_size,'sha256':sha(path)}
            tar.add(path,arcname=name,recursive=False)
    frozen = json.loads((ROOT / 'evaluation/trp/campaign-20261012/aggregate-resource-contrasts/campaign-inputs/freeze.json').read_text())
    repaired = {str(path.relative_to(ROOT)) for path in paths[:3]}
    for path, digest in frozen['sourceHashes'].items():
        if path not in repaired and sha(ROOT / path) != digest:
            raise ValueError('Unreviewed producer/baseline drift: ' + path)
    report = {'schema':'helix-post-campaign-public-runtime/1.0','preparedAt':datetime.now(timezone.utc).isoformat(),
              'runtime':RUNTIME,'baseline':'/opt/helix-strict-runtime','sourceFiles':records,'archiveSha256':sha(archive),
              'baselineFrozenSourceHashes':frozen['sourceHashes'],
              'originalRuntimeModified':False,'privateCredentialsCopied':False,'userSDKFilesReadOrChanged':False,
              'scope':'Copies the old public immutable runtime/dependencies; overlays only three repaired producer modules and new integration harness. Actual SQLite/work/cache/temp/export remain in each assigned project. No private credentials or newly edited SDK are transferred.',
              'steps':[]}
    def save():
        (output / 'setup.json').write_text(json.dumps(report,indent=2)+'\n')
    save()
    spec = importlib.util.spec_from_file_location('academy',ROOT / 'script/tesis/aws_academy_cluster.py')
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    m.configure_lab('185395')
    state = m.refresh(m.ec2_client(),m.load())
    head = next(node for node in state['nodes'] if node['role']=='head')
    options = ['StrictHostKeyChecking=yes' if item=='StrictHostKeyChecking=accept-new' else item for item in m.ssh_options(head)]
    def ssh(command,timeout=180):
        process = subprocess.run(['ssh',*options,'ubuntu@'+head['public_ip'],'bash -lc '+shlex.quote(command)],capture_output=True,text=True,timeout=timeout)
        report['steps'].append({'at':datetime.now(timezone.utc).isoformat(),'command':command,'exitCode':process.returncode,'stdout':process.stdout,'stderr':process.stderr})
        save()
        if process.returncode:
            raise RuntimeError(process.stderr[-2000:])
        return process.stdout
    remote = '/tmp/helix-post-campaign-'+sha(archive)[:12]+'.tar'
    subprocess.run(['scp',*options,str(archive),'ubuntu@'+head['public_ip']+':'+remote],check=True,timeout=120)
    observed = ssh('sha256sum '+remote)
    if not observed.startswith(sha(archive)+' '):
        raise ValueError('Overlay transfer changed')
    ssh('test -z "$(squeue -h -o %i)" && sudo test ! -e '+RUNTIME+' && sudo cp -a /opt/helix-strict-runtime '+RUNTIME+' && sudo chmod -R u+w '+RUNTIME+' && sudo tar -xf '+remote+' -C '+RUNTIME+' && sudo chmod -R a-w '+RUNTIME,timeout=600)
    code = """import hashlib,json,pathlib,sys
root=pathlib.Path(sys.argv[1]);sources=json.loads(sys.argv[2]);result=[]
for name,record in sources.items():
 observed=hashlib.sha256((root/name).read_bytes()).hexdigest()
 assert observed==record['sha256'],name
 result.append({'path':name,'sha256':observed})
print(json.dumps(result))
"""
    report['verifiedOverlay'] = json.loads(ssh('sudo python3 -c '+shlex.quote(code)+' '+shlex.quote(RUNTIME)+' '+shlex.quote(json.dumps(records))))
    observed = ssh(RUNTIME+'/python/bin/python -c "import gemmi;print(gemmi.__version__)" && helix-strict-bun --version && sha256sum /usr/local/libexec/helix-remote-strict-check.py')
    if not observed.startswith('0.7.5\n1.3.14\n') or 'f7587626581f414ca8515b87997495f1f65785e07231e1a2151a33da395b9b50 ' not in observed:
        raise ValueError('Pinned runtime/checker identity differs')
    report['ready'] = True
    save()
    print(json.dumps({'ready':True,'runtime':RUNTIME,'overlayFiles':len(records),'oldRuntimeUntouched':True}))

if __name__=='__main__':
    main()
