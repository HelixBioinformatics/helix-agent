#!/usr/bin/env python3
"""Owner-scoped SSH/Slurm controller. Requests arrive on stdin, never shell data.
The exact script and target are bound to the immutable scientific approval.
"""
import base64
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import signal
import socket
import stat
import subprocess
import sys
import time
from datetime import datetime, timezone

VERSION = 'trp-slurm-ssh/1.0.0'


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'))


def now():
    return datetime.now(timezone.utc).isoformat()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write(root, name, value):
    temp = root / (name + '.tmp')
    temp.write_text(canonical(value) + '\n')
    temp.replace(root / name)


def invoke(argv, cwd=None, timeout=20, check=True):
    value = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    if check and value.returncode:
        raise ValueError('Command failed: ' + argv[0] + ': ' + value.stderr[-4096:])
    return value


def target_root(req):
    target = req['target']
    if target['version'] != VERSION:
        raise ValueError('Unsupported target')
    root = Path(target['root'])
    if not root.is_absolute() or root.resolve(strict=True) != root or not root.is_dir():
        raise ValueError('Shared root must be an existing ordinary directory')
    if root.stat().st_uid != os.getuid() or not os.access(root, os.W_OK):
        raise ValueError('Shared root is not owned by the SSH user')
    return root


def run_root(req, exists=True):
    root = target_root(req)
    if not re.fullmatch('[0-9a-f]{64}', req['digest']) or not re.fullmatch('[0-9a-f-]{36}', req['id']):
        raise ValueError('Invalid run identity')
    destination = root / ('trp-' + req['digest'][:12] + '-' + req['id'])
    if exists and (destination.is_symlink() or destination.resolve(strict=True) != destination or destination.stat().st_uid != os.getuid()):
        raise ValueError('Run ownership or path changed')
    return destination


def comment(req):
    return 'helix:' + req['id']


def owned_jobs(req):
    text = invoke(['squeue', '--noheader', '--user', str(os.getuid()), '--format', '%i|%k|%T|%j|%N']).stdout
    result = []
    for line in text.splitlines():
        values = line.strip().split('|')
        if len(values) == 5 and values[1] == comment(req) and re.fullmatch('[0-9]+', values[0]):
            result.append(dict(zip(['id', 'comment', 'state', 'name', 'nodes'], values)))
    return result


def cancel_jobs(req):
    jobs = owned_jobs(req)
    if jobs:
        invoke(['scancel', *[job['id'] for job in jobs]])
    deadline = time.monotonic() + 15
    remaining = owned_jobs(req)
    while remaining and time.monotonic() < deadline:
        time.sleep(0.5)
        remaining = owned_jobs(req)
    return {'requested': jobs, 'remaining': remaining, 'confirmed': not remaining, 'at': now()}


def fields(text):
    return dict(re.findall(r'(\w+)=([^\s]+)', text))


def observe(req):
    root = target_root(req)
    queue = req['target']['partition']
    partition = fields(invoke(['scontrol', 'show', 'partition', queue, '--oneliner']).stdout)
    if partition.get('PartitionName') != queue or partition.get('State') != 'UP':
        raise ValueError('Slurm partition is unavailable')
    names = invoke(['scontrol', 'show', 'hostnames', partition['Nodes']]).stdout.splitlines()
    nodes = []
    for name in names:
        raw = invoke(['scontrol', 'show', 'node', name, '--oneliner']).stdout
        node = fields(raw)
        state = node.get('State', '')
        available_cpus = int(node.get('CPUTot', '0')) - int(node.get('CPUAlloc', '0'))
        available_mem = max(0, int(node.get('RealMemory', '0')) - int(node.get('AllocMem', '0'))) * 1048576
        eligible = state.split('+')[0] in ('IDLE', 'MIXED') and not any(x in state for x in ('DRAIN', 'DOWN', 'FAIL', 'UNKNOWN'))
        nodes.append({'name': name, 'cpus': available_cpus, 'memoryBytes': available_mem, 'state': state, 'eligible': eligible, 'source': raw.strip()})
    memory = int(re.search(r'^MemAvailable:\s+(\d+) kB$', Path('/proc/meminfo').read_text(), re.M)[1]) * 1024
    cpus = len(os.sched_getaffinity(0))
    membership = re.search(r'^0::([^\n]+)', Path('/proc/self/cgroup').read_text(), re.M)[1]
    group = Path('/sys/fs/cgroup') / membership.lstrip('/')
    while group.is_relative_to('/sys/fs/cgroup'):
        if (group / 'cpu.max').exists():
            quota, period = (group / 'cpu.max').read_text().split()
            if quota != 'max':
                cpus = min(cpus, int(quota) // int(period))
        if (group / 'memory.max').exists():
            maximum = (group / 'memory.max').read_text().strip()
            if maximum != 'max':
                memory = min(memory, max(0, int(maximum) - int((group / 'memory.current').read_text())))
        if group == Path('/sys/fs/cgroup'):
            break
        group = group.parent
    capacity = os.statvfs(root)
    workers = [n for n in nodes if n['eligible']]
    best = max(workers, key=lambda n: (n['memoryBytes'], n['cpus']), default={'cpus': 0, 'memoryBytes': 0})
    seconds = None
    if req['target'].get('sessionExpiresAt'):
        seconds = int((datetime.fromisoformat(req['target']['sessionExpiresAt'].replace('Z', '+00:00')) - datetime.now(timezone.utc)).total_seconds())
    # The known Academy per-boot guard is independently observed when installed.
    guard = Path('/etc/systemd/system/helix-session-stop.timer')
    if guard.is_file() and 'OnBootSec=180min' in guard.read_text() and invoke(['systemctl', 'is-active', 'helix-session-stop.timer'], check=False).returncode == 0:
        guard_seconds = max(0, int(180 * 60 - float(Path('/proc/uptime').read_text().split()[0])))
        seconds = min(seconds, guard_seconds) if seconds is not None else guard_seconds
    return {'ok': True, 'observedAt': now(), 'platform': platform.system().lower(), 'architecture': 'x64' if platform.machine() == 'x86_64' else platform.machine(),
            'host': socket.gethostname(), 'workspace': str(root), 'filesystem': str(os.stat(root).st_dev),
            'cpus': cpus + best['cpus'], 'memoryBytes': memory + best['memoryBytes'], 'freeBytes': capacity.f_bavail * capacity.f_frsize,
            'remote': {'version': VERSION, 'fingerprint': req['target']['fingerprint'], 'partition': queue,
                       'controllerCpus': cpus, 'controllerMemoryBytes': memory, 'nodes': nodes, 'requiredNodes': [req['target'][key] for key in ['selectNode', 'geometryNode'] if req['target'].get(key)], 'secondsRemaining': seconds},
            'sources': ['SSH host key verified by local client', '/proc/meminfo:MemAvailable', '/proc/self/cgroup and ancestor limits', 'os.statvfs shared root', 'scontrol partition/nodes', 'Academy expiry and per-boot guard when available'],
            'limitations': ['Capacity is observed, not an exclusive reservation. Controller and worker capacity are separate; one task must fit one worker.',
                            'Slurm CPU/memory requests and Docker effective task limits are recorded separately. No aggregate disk quota or hard controller-memory limit is claimed.',
                            'Image caches and distributions are infrastructure outside workBytes. Cluster shared filesystem availability is tested by actual execution.']}


def verify(req, root):
    manifest = json.loads((root / 'remote-approved.json').read_text())
    if manifest['id'] != req['id'] or manifest['digest'] != req['digest'] or manifest['target'] != req['target']:
        raise ValueError('Approved target or run identity changed')
    for name, expected in manifest['files'].items():
        file = root / name
        if file.is_symlink() or not file.is_file() or sha(file.read_bytes()) != expected:
            raise ValueError('Approved file changed: ' + name)
    execution = json.loads((root / 'execution.json').read_text())
    if manifest['budget'] != json.loads((root / 'budget.json').read_text()):
        raise ValueError('Approved budget differs')
    bundle = {'engine': execution['engine'], 'files': manifest['files']}
    if sha(canonical(bundle).encode()) != req['digest']:
        raise ValueError('Approval digest mismatch')
    return manifest


def controller_alive(state):
    try:
        proc = Path('/proc') / str(state['pid'])
        return proc.exists() and (proc / 'stat').read_text().split()[21] == state['startTicks'] and 'remote_runner.py' in (proc / 'cmdline').read_text().replace('\x00', ' ')
    except (OSError, KeyError):
        return False


def start(req):
    root = run_root(req, False)
    if root.exists():
        raise ValueError('Run already exists; automatic resubmission is forbidden')
    # NFS root_squash requires daemon traversal; contents remain owner-only.
    root.mkdir(mode=0o711)
    for name, text in req['files'].items():
        if not re.fullmatch('[a-z][a-z0-9_.]*', name):
            raise ValueError('Invalid approved filename')
        (root / name).write_text(text)
        (root / name).chmod(0o600)
    manifest = {'id': req['id'], 'digest': req['digest'], 'target': req['target'], 'budget': req['budget'],
                'files': {name: sha(text.encode()) for name, text in req['files'].items()}}
    write(root, 'remote-approved.json', manifest)
    verify(req, root)
    # Transported script must equal the script currently serving this request.
    if (root / 'remote_runner.py').read_text() != SCRIPT_SELF:
        raise ValueError('Runner bytes differ from approved runner')
    with (root / 'remote-controller.log').open('wb') as out, (root / 'remote-controller.stderr').open('wb') as err:
        child = subprocess.Popen([sys.executable, str(root / 'remote_runner.py'), 'controller', base64.b64encode(canonical({k: v for k, v in req.items() if k != 'files'}).encode()).decode()],
                                 stdin=subprocess.DEVNULL, stdout=out, stderr=err, start_new_session=True)
    ticks = (Path('/proc') / str(child.pid) / 'stat').read_text().split()[21]
    state = {'pid': child.pid, 'startTicks': ticks, 'id': req['id'], 'digest': req['digest'], 'status': 'starting', 'startedAt': now()}
    write(root, 'remote-controller-identity.json', state)
    return {'ok': True, 'directory': str(root), 'controller': state}


def process_run(root, argv, cwd, timeout):
    begin = time.monotonic()
    started = now()
    code = None
    try:
        result = invoke(argv, cwd=cwd, timeout=timeout, check=False)
        code = result.returncode
        (cwd / ('remote-' + ('version' if '-version' in argv else 'config' if 'config' in argv else 'stdout') + '.log')).write_text(result.stdout)
        (cwd / ('remote-' + ('version' if '-version' in argv else 'config' if 'config' in argv else 'stderr') + '.stderr')).write_text(result.stderr)
        if code:
            raise ValueError('Command exit ' + str(code) + ': ' + argv[0] + ': ' + (result.stderr[-4096:] or result.stdout[-4096:]))
        return result.stdout
    finally:
        with (root / 'remote-processes.jsonl').open('a') as stream:
            stream.write(canonical({'argv': argv, 'startedAt': started, 'durationMs': int((time.monotonic()-begin)*1000), 'exitCode': code}) + '\n')


def snapshot_jobs(req, root):
    found = owned_jobs(req)
    ids = {job['id'] for job in found}
    for trace in [root / 'trace.tsv', root / 'dry-run/trace.tsv']:
        if trace.is_file():
            lines = [line.split('\t') for line in trace.read_text().strip().splitlines()]
            if lines and 'native_id' in lines[0]:
                index = lines[0].index('native_id')
                ids.update(row[index] for row in lines[1:] if len(row) > index and re.fullmatch('[0-9]+', row[index]))
    records = []
    for job in sorted(ids, key=int):
        raw = invoke(['scontrol', 'show', 'job', job, '--oneliner'], check=False).stdout.strip()
        if raw:
            if fields(raw).get('Comment') != comment(req):
                raise ValueError('Native job ownership differs')
            records.append({'id': job, 'source': raw, 'state': fields(raw).get('JobState'), 'nodes': fields(raw).get('NodeList')})
    if records:
        with (root / 'remote-native-jobs.jsonl').open('a') as stream:
            stream.write(canonical({'at': now(), 'records': records}) + '\n')
    return found


def runtime_records(root):
    records = []
    for file in sorted((root / 'work').glob('*/*/.command.out')):
        for line in file.read_text(errors='replace').splitlines():
            if line.startswith('HELIX_RUNTIME:'):
                row = json.loads(line.split(':', 1)[1])
                row['source'] = str(file.relative_to(root))
                quota, period = map(int, row['cpuMax'].split())
                if quota / period != 2 or int(row['memoryMax']) != 2147483648 or int(row['swapMax']) != 0 or row['threads'] != '1':
                    raise ValueError('Effective Docker task limits differ')
                records.append(row)
    if len(records) != 2:
        raise ValueError('Expected effective cgroup observations for two scientific tasks')
    write(root, 'remote-task-runtime.json', {'records': records, 'scope': 'Docker container effective cgroup limits; Slurm requests and native nodes recorded separately; no disk quota'})


def controller(req):
    root = run_root(req)
    signal.signal(signal.SIGTERM, lambda *_: (_ for _ in ()).throw(InterruptedError('Controller cancelled')))
    status = 'failed'
    error = None
    try:
        verify(req, root)
        observed = observe(req)
        write(root, 'remote-head-observation.json', observed)
        image = json.loads((root / 'execution.json').read_text())['container']
        endpoint = invoke(['docker', 'context', 'inspect', '--format', '{{.Endpoints.docker.Host}}']).stdout.strip()
        endpoint = os.environ.get('DOCKER_HOST') or endpoint
        if not endpoint.startswith('unix://'):
            raise ValueError('Head Docker daemon must be local')
        exact_image = invoke(['docker', 'image', 'inspect', '--format', '{{.Id}}', image]).stdout.strip()
        if exact_image != image:
            raise ValueError('Exact approved image unavailable on head')
        write(root, 'docker-endpoint.json', {'endpoint': endpoint, 'exitCode': 0, 'scope': 'remote head; tasks verify execution through exact image ID and effective limits'})
        version = process_run(root, ['nextflow', '-version'], root, 30)
        if not re.search(r'version\s+25\.10\.4(?:\s|$)', version):
            raise ValueError('Nextflow 25.10.4 is required')
        write(root, 'software.json', {'imageId': exact_image, 'nextflowVersionOutput': version,
                                      'slurmVersionOutput': invoke(['scontrol', '--version']).stdout, 'backend': VERSION})
        process_run(root, ['nextflow', '-C', 'nextflow.config', 'config', '-flat'], root, 30)
        manifest = verify(req, root)
        dry = root / 'dry-run'
        dry.mkdir(mode=0o711)
        for name in manifest['files']:
            shutil.copyfile(root / name, dry / name)
            (dry / name).chmod(0o600)
        args = ['nextflow', '-C', 'nextflow.config', 'run', 'main.nf', '-ansi-log', 'false', '-with-trace', 'trace.tsv']
        env = os.environ.copy()
        env.update({'NXF_OFFLINE': 'true', 'NXF_DISABLE_CHECK_LATEST': 'true'})
        os.environ.update(env)
        process_run(root, [*args, '-stub-run'], dry, min(480, req['budget']['wallSeconds']))
        snapshot_jobs(req, root)
        verify(req, root)
        analysis_inventory = observe(req)
        write(root, 'remote-analysis-inventory.json', analysis_inventory)
        if analysis_inventory['remote']['controllerCpus'] < 1 or analysis_inventory['remote']['controllerMemoryBytes'] < 2147483648 or not any(n['eligible'] and n['cpus'] >= 2 and n['memoryBytes'] >= 2147483648 for n in analysis_inventory['remote']['nodes']):
            raise ValueError('Capacity lost after stub traversal')
        deadline = time.monotonic() + 90
        while not (root / 'remote-analysis-approval.json').exists():
            if time.monotonic() > deadline:
                raise ValueError('Client did not grant fresh analysis resource admission')
            time.sleep(0.5)
        process_run(root, args, root, min(480, req['budget']['wallSeconds']))
        snapshot_jobs(req, root)
        verify(req, root)
        runtime_records(root)
        if req['target'].get('numericalProfile') and any(row['numericalProfile'] != 'Haswell' or not any(blas.get('architecture') == 'Haswell' and blas.get('num_threads') == 1 for blas in row['blas']) for row in json.loads((root / 'remote-task-runtime.json').read_text())['records']):
            raise ValueError('Numerical profile differs')
        status = 'succeeded'
    except BaseException as exc:
        error = str(exc)
        if isinstance(exc, InterruptedError) or (root / 'remote-cancel-request.json').exists():
            status = 'cancelled'
        try:
            write(root, 'remote-job-cancellation.json', cancel_jobs(req))
        except Exception as cancellation:
            write(root, 'remote-job-cancellation.json', {'confirmed': False, 'error': str(cancellation)})
    finally:
        write(root, 'remote-terminal.json', {'status': status, 'error': error, 'finishedAt': now(), 'digest': req['digest'], 'id': req['id']})


def status(req):
    root = run_root(req)
    identity = json.loads((root / 'remote-controller-identity.json').read_text())
    jobs = snapshot_jobs(req, root)
    terminal = root / 'remote-terminal.json'
    result = json.loads(terminal.read_text()) if terminal.exists() else {'status': 'running', 'digest': req['digest'], 'id': req['id']}
    inventory_file = root / 'remote-analysis-inventory.json'
    return {'ok': True, **result, 'controllerAlive': controller_alive(identity), 'jobs': jobs, 'controller': identity,
            'analysisInventory': json.loads(inventory_file.read_text()) if inventory_file.exists() else None,
            'analysisAdmitted': (root / 'remote-analysis-approval.json').exists()}


def admit_analysis(req):
    root = run_root(req)
    verify(req, root)
    decision = req['decision']
    raw = json.loads((root / 'remote-analysis-inventory.json').read_text())
    inventory = {key: raw[key] for key in ['observedAt', 'platform', 'architecture', 'host', 'workspace', 'filesystem', 'cpus', 'memoryBytes', 'freeBytes', 'sources', 'limitations', 'remote']}
    inventory['version'] = 'trp-resources/1.2.0'
    admission = json.loads((root / 'admission.json').read_text())
    budget = json.loads((root / 'budget.json').read_text())
    if not decision['accepted'] or decision['rejections'] or decision['inventoryHash'] != sha(canonical(inventory).encode()) or decision['budgetHash'] != sha(canonical(budget).encode()) or decision['demand'] != admission['demand']:
        raise ValueError('Fresh analysis admission does not match observed resources/approved budget')
    if (datetime.now(timezone.utc) - datetime.fromisoformat(raw['observedAt'])).total_seconds() > 300:
        raise ValueError('Analysis inventory is stale')
    write(root, 'remote-analysis-approval.json', {'decision': decision, 'acceptedAt': now()})
    return {'ok': True, 'accepted': True}


def cancel(req):
    root = run_root(req)
    write(root, 'remote-cancel-request.json', {'reason': req.get('reason'), 'requestedAt': now()})
    identity_file = root / 'remote-controller-identity.json'
    if identity_file.exists():
        identity = json.loads(identity_file.read_text())
        if controller_alive(identity):
            os.killpg(identity['pid'], signal.SIGTERM)
    jobs = cancel_jobs(req)
    deadline = time.monotonic() + 15
    while identity_file.exists() and controller_alive(identity) and time.monotonic() < deadline:
        time.sleep(0.25)
    return {'ok': True, **jobs, 'controllerStopped': not identity_file.exists() or not controller_alive(identity)}


def export(req):
    root = run_root(req)
    files = []
    total = 0
    for file in sorted(root.rglob('*')):
        if file.is_symlink():
            resolved = file.resolve(strict=True)
            if not resolved.is_relative_to(root) or not resolved.is_file():
                raise ValueError('External or directory symlink in remote run')
        if file.is_dir():
            continue
        if not stat.S_ISREG(file.stat().st_mode):
            raise ValueError('Special file in remote run')
        data = file.read_bytes()
        total += len(data)
        if total > req['maxBytes']:
            raise ValueError('Remote evidence exceeds reviewed workspace estimate/budget; preserved on head')
        files.append({'path': str(file.relative_to(root)), 'bytes': len(data), 'sha256': sha(data), 'base64': base64.b64encode(data).decode()})
    return {'ok': True, 'files': files, 'totalBytes': total}


# Read our exact bytes on detached execution. For python -c, the source is supplied
# by the client and reconstructed from its approved payload during start.
SCRIPT_SELF = Path(__file__).read_text() if '__file__' in globals() else None
def main():
    global SCRIPT_SELF
    if len(sys.argv) == 3 and sys.argv[1] == 'controller':
        controller(json.loads(base64.b64decode(sys.argv[2])))
    else:
        try:
            req = json.load(sys.stdin)
            if req['action'] == 'start' and SCRIPT_SELF is None:
                SCRIPT_SELF = req['files']['remote_runner.py']
            result = {'observe': observe, 'start': start, 'status': status, 'cancel': cancel, 'export': export, 'admit-analysis': admit_analysis}[req['action']](req)
        except Exception as exc:
            result = {'ok': False, 'code': 'remote-controller-error', 'error': str(exc)}
        print(canonical(result))
        sys.exit(0 if result['ok'] else 1)


if __name__ == '__main__':
    main()
