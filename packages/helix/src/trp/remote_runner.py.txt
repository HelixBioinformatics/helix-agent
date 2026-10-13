#!/usr/bin/env python3
"""Owner-scoped SSH/Slurm controller. Requests arrive on stdin, never shell data.
The exact script and target are bound to the immutable scientific approval.
"""
import base64
import fcntl
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import runpy
import shutil
import signal
import socket
import stat
import subprocess
import sys
import time
from datetime import datetime, timezone

VERSION = 'trp-slurm-ssh/1.0.0'
STRICT_VERSION = 'trp-remote-strict/1.0.0'


def strict_observation(req, role='client'):
    fixed = req['target'].get('strict')
    if fixed is None:
        return None
    if fixed.get('version') != STRICT_VERSION or req['target'].get('transport') != 'co-located-python':
        raise ValueError('Unrecognized strict co-located transport')
    checker = Path('/usr/local/libexec/helix-remote-strict-check.py')
    for file, directory in [(checker.parent, True), (checker, False)]:
        found = file.lstat()
        if found.st_uid != 0 or found.st_mode & 0o022 or file.is_symlink() or file.resolve(strict=True) != file:
            raise ValueError('Strict root checker path is untrusted')
        if directory and not file.is_dir() or not directory and not file.is_file():
            raise ValueError('Strict root checker is not an ordinary file')
    if hashlib.sha256(checker.read_bytes()).hexdigest() != fixed['policy']['checker']['sha256']:
        raise ValueError('Strict root checker changed')
    receipt = runpy.run_path(str(checker))['observe'](fixed['policyPath'], req['target'], fixed['policySha256'], role)
    if receipt['policy'] != fixed['policy'] or fixed['targetFingerprint'] != req['target']['fingerprint']:
        raise ValueError('Strict allocation differs from approved target')
    return receipt


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
    strict = strict_observation(req, 'controller' if req.get('strictController') else 'client')
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
            'cpus': strict['entitlement']['cpus'] if strict else cpus + best['cpus'],
            'memoryBytes': strict['entitlement']['memoryBytes'] if strict else memory + best['memoryBytes'],
            'freeBytes': strict['entitlement']['workBytes'] if strict else capacity.f_bavail * capacity.f_frsize,
            **({'remoteStrict': req['target']['strict'], 'remoteStrictObservation': strict} if strict else {}),
            'remote': {'version': VERSION, 'fingerprint': req['target']['fingerprint'], 'partition': queue,
                       # The strict total-run entitlement includes the real client.
                       # Its current consumption stays in the separate receipt.
                       'controllerCpus': strict['policy']['controller']['cpus'] if strict else cpus,
                       'controllerMemoryBytes': strict['policy']['controller']['memoryBytes'] if strict else memory,
                       'nodes': nodes, 'requiredNodes': [req['target'][key] for key in ['selectNode', 'geometryNode'] if req['target'].get(key)], 'secondsRemaining': seconds},
            'sources': (['Root-owned co-located policy and fresh kernel XFS quota sample', 'FSGETXATTR project/inheritance; findmnt UUID/device; /proc boot/host/cgroup and controller limits', 'scontrol partition/nodes', 'current controller usage recorded separately from allocation entitlement'] if strict else ['SSH host key verified by local client', '/proc/meminfo:MemAvailable', '/proc/self/cgroup and ancestor limits', 'os.statvfs shared root', 'scontrol partition/nodes', 'Academy expiry and per-boot guard when available']),
            'limitations': (['Real Helix client and Python/Nextflow controller share the fixed controller cgroup; sequential worker tasks have separate Docker limits.',
                             'One XFS project covers declared client and NFS worker-visible work paths; preloaded read-only runtime/image caches and root supervisor records are outside workBytes.',
                             'Local Python transport on the verified head is explicit; this strict profile is not an SSH transport test. Worker memory is never pooled.',
                             'Allocated controller entitlement is not reduced by its own current usage. CPU quota is bandwidth, not exclusive cores.'] if strict else ['Capacity is observed, not an exclusive reservation. Controller and worker capacity are separate; one task must fit one worker.',
                            'Slurm CPU/memory requests and Docker effective task limits are recorded separately. No aggregate disk quota or hard controller-memory limit is claimed.',
                            'Image caches and distributions are infrastructure outside workBytes. Cluster shared filesystem availability is tested by actual execution.'])}


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
    strict = strict_observation(req)
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
    if strict:
        if json.loads((root / 'remote_strict_policy.json').read_text()) != req['target']['strict'] or sha((root / 'remote_strict.py').read_bytes()) != strict['policy']['checker']['sha256']:
            raise ValueError('Strict policy/checker are not bound to the approval digest')
        write(root, 'remote-strict-start.json', strict)
    with (root / 'remote-controller.log').open('wb') as out, (root / 'remote-controller.stderr').open('wb') as err:
        child = subprocess.Popen([sys.executable, str(root / 'remote_runner.py'), 'controller', base64.b64encode(canonical({k: v for k, v in req.items() if k != 'files'}).encode()).decode()],
                                 stdin=subprocess.DEVNULL, stdout=out, stderr=err, start_new_session=True,
                                 cwd=root if strict else None)
    ticks = (Path('/proc') / str(child.pid) / 'stat').read_text().split()[21]
    state = {'pid': child.pid, 'startTicks': ticks, 'id': req['id'], 'digest': req['digest'], 'status': 'starting', 'startedAt': now()}
    write(root, 'remote-controller-identity.json', state)
    return {'ok': True, 'directory': str(root), 'controller': state}


NATIVE_TRACKING_VERSION = 'trp-native-jobs/1.0.0'
NATIVE_FAILURE_STATES = frozenset(('BOOT_FAIL', 'CANCELLED', 'DEADLINE', 'FAILED',
                                  'NODE_FAIL', 'OUT_OF_MEMORY', 'PREEMPTED', 'TIMEOUT', 'REVOKED'))


class NativeJobFailure(ValueError):
    pass


def native_fields(raw):
    # Empty NodeList is valid for PENDING; do not consume the next key as its value.
    return dict(re.findall(r'(\w+)=([^\s]*)', raw))


def checked_native(req, job, raw):
    value = native_fields(raw)
    uid = re.fullmatch(r'[^()]+\((\d+)\)', value.get('UserId', ''))
    if value.get('JobId') != job or value.get('Comment') != comment(req) or not uid or int(uid[1]) != os.getuid():
        raise ValueError('Native job ownership differs: ' + job)
    return value


def native_failed(value):
    native_state = value.get('JobState', '').split('+', 1)[0]
    return native_state in NATIVE_FAILURE_STATES or native_state == 'COMPLETED' and value.get('ExitCode') not in (None, '0:0')


def tracking_file(root, name, flags):
    # Status/controller can run concurrently. The same owner may not redirect a
    # tracking file through a symlink or special file; the lock covers all updates.
    fd = os.open(root / name, flags | os.O_NOFOLLOW, 0o600)
    value = os.fstat(fd)
    if value.st_uid != os.getuid() or not stat.S_ISREG(value.st_mode):
        os.close(fd)
        raise ValueError('Native tracking path is not an owner-controlled ordinary file')
    return os.fdopen(fd, 'r+' if flags & os.O_RDWR else 'r')


def tracking_state(req, root):
    file = root / 'remote-native-state.json'
    if file.exists() or file.is_symlink():
        with tracking_file(root, file.name, os.O_RDONLY) as stream:
            state = json.load(stream)
        if state.get('version') != NATIVE_TRACKING_VERSION or state.get('id') != req['id'] or state.get('digest') != req['digest'] or state.get('comment') != comment(req):
            raise ValueError('Native tracking owner or approval differs')
        return state
    state = {'version': NATIVE_TRACKING_VERSION, 'id': req['id'], 'digest': req['digest'],
             'comment': comment(req), 'jobs': {}, 'snapshotSignature': None}
    # Upgrade a run whose older observer already saw a job. Only raw native
    # ownership establishes membership; JSON summary fields are not an oracle.
    journal = root / 'remote-native-jobs.jsonl'
    if journal.exists() or journal.is_symlink():
        with tracking_file(root, journal.name, os.O_RDONLY) as stream:
            for line in stream:
                snapshot = json.loads(line)
                for job in snapshot['records']:
                    if not re.fullmatch('[0-9]+', job.get('id', '')) or not job.get('source'):
                        continue
                    value = checked_native(req, job['id'], job['source'])
                    record = native_record(req, root, job['id'], value, job['source'], 'legacy-journal')
                    previous = state['jobs'].get(job['id'], {})
                    state['jobs'][job['id']] = {'id': job['id'], 'ownership': 'confirmed',
                        'firstSeenAt': previous.get('firstSeenAt', snapshot.get('at', now())),
                        'traversals': list(dict.fromkeys([*previous.get('traversals', []), record['traversal']])),
                        'lastConfirmed': record, 'current': record,
                        **({'failure': previous.get('failure', record)} if native_failed(value) or previous.get('failure') else {})}
    return state


def native_record(req, root, job, value, raw, traversal):
    work = Path(value.get('WorkDir', '/'))
    if work.is_relative_to(root / 'dry-run'):
        traversal = 'stub'
    elif work.is_relative_to(root / 'work'):
        traversal = 'science'
    elif traversal not in ('stub', 'science'):
        traversal = 'unknown'
    return {'id': job, 'source': raw, 'state': value.get('JobState', 'UNKNOWN'),
            'comment': value['Comment'], 'userId': value['UserId'], 'nodes': value.get('NodeList'),
            'exitCode': value.get('ExitCode'), 'reason': value.get('Reason'),
            'traversal': traversal, 'ownership': 'confirmed', 'observation': 'scontrol'}


def snapshot_jobs(req, root, traversal=None):
    with tracking_file(root, 'remote-native-state.lock', os.O_CREAT | os.O_RDWR) as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        state = tracking_state(req, root)
        original = canonical(state)
        found = owned_jobs(req)
        queue = {job['id']: job for job in found}
        # Persist queue-owned IDs before a potentially unavailable scontrol
        # query. Losing a transport request must not erase a job already seen.
        for job in found:
            entry = state['jobs'].setdefault(job['id'], {'id': job['id'], 'ownership': 'confirmed',
                'firstSeenAt': now(), 'traversals': []})
            entry['ownership'] = 'confirmed'
            entry['lastQueue'] = job
            entry.setdefault('current', {'id': job['id'], 'source': '', 'state': 'UNKNOWN',
                'nodes': job['nodes'], 'ownership': 'confirmed', 'observation': 'squeue-owned-awaiting-scontrol',
                'queueState': job['state'], 'traversal': traversal if traversal in ('stub', 'science') else 'unknown'})
        if canonical(state) != original:
            write(root, 'remote-native-state.json', state)
        ids = set(state['jobs']) | set(queue)
        for trace in [root / 'trace.tsv', root / 'dry-run/trace.tsv']:
            if trace.is_file():
                lines = [line.split('\t') for line in trace.read_text().strip().splitlines()]
                if lines and 'native_id' in lines[0]:
                    index = lines[0].index('native_id')
                    ids.update(row[index] for row in lines[1:] if len(row) > index and re.fullmatch('[0-9]+', row[index]))
        records = []
        for job in sorted(ids, key=int):
            entry = state['jobs'].setdefault(job, {'id': job, 'ownership': 'unconfirmed', 'firstSeenAt': now(), 'traversals': []})
            if job in queue:
                entry['ownership'] = 'confirmed'  # squeue was filtered by current UID and exact UUID.
                entry['lastQueue'] = queue[job]
            result = invoke(['scontrol', 'show', 'job', job, '--oneliner'], check=False)
            raw = result.stdout.strip()
            if raw:
                value = checked_native(req, job, raw)
            if result.returncode == 0 and raw:
                record = native_record(req, root, job, value, raw, traversal)
                entry['ownership'] = 'confirmed'
                entry['lastConfirmed'] = record
                if native_failed(value):
                    entry.setdefault('failure', record)
            else:
                # MinJobAge/accounting can remove a record. Absence is not a
                # completion or a failure, even when the previous state was RUNNING.
                record = {'id': job, 'source': raw, 'state': 'UNKNOWN', 'nodes': None,
                          'ownership': entry['ownership'], 'observation': 'scontrol-missing',
                          'queryExitCode': result.returncode, 'queryStderr': result.stderr[-4096:],
                          'previousState': entry.get('lastConfirmed', {}).get('state'),
                          'traversal': traversal if traversal in ('stub', 'science') else 'unknown'}
            if record['traversal'] not in entry['traversals']:
                entry['traversals'].append(record['traversal'])
            entry['current'] = record
            records.append(record)
        signature = sha(canonical(records).encode())
        if records and signature != state['snapshotSignature']:
            # Append actual transitions, with raw sources retained. Polling the
            # same state does not fill a bounded workspace with duplicate records.
            with tracking_file(root, 'remote-native-jobs.jsonl', os.O_CREAT | os.O_RDWR) as stream:
                stream.seek(0, os.SEEK_END)
                stream.write(canonical({'at': now(), 'records': records}) + '\n')
            state['snapshotSignature'] = signature
        if canonical(state) != original or not (root / 'remote-native-state.json').exists():
            write(root, 'remote-native-state.json', state)
        return found


def native_status(req, root):
    with tracking_file(root, 'remote-native-state.lock', os.O_CREAT | os.O_RDWR) as lock:
        fcntl.flock(lock, fcntl.LOCK_SH)
        state = tracking_state(req, root)
    jobs = [entry['current'] for _, entry in sorted(state['jobs'].items(), key=lambda pair: int(pair[0]))]
    failures = []
    for entry in state['jobs'].values():
        record = entry.get('failure') or entry.get('lastConfirmed')
        if not record:
            continue
        value = checked_native(req, record['id'], record['source'])
        if native_failed(value):
            failures.append(record)
    return {'nativeJobs': jobs, 'nativeFailures': failures,
            'stateUnknown': [job['id'] for job in jobs if job['state'] == 'UNKNOWN']}



def ensure_native_completion(req, root, traversal):
    trace = root / ('dry-run/trace.tsv' if traversal == 'stub' else 'trace.tsv')
    if not trace.is_file():
        raise ValueError('Native completion unknown: trace is absent for ' + traversal)
    lines = [line.split('\t') for line in trace.read_text().strip().splitlines()]
    if not lines or 'native_id' not in lines[0]:
        raise ValueError('Native completion unknown: trace has no native IDs')
    column = lines[0].index('native_id')
    ids = [row[column] for row in lines[1:] if len(row) > column]
    if len(ids) != 2 or len(set(ids)) != 2 or any(not re.fullmatch('[0-9]+', job) for job in ids):
        raise ValueError('Native completion unknown: expected two distinct tasks for ' + traversal)
    with tracking_file(root, 'remote-native-state.lock', os.O_CREAT | os.O_RDWR) as lock:
        fcntl.flock(lock, fcntl.LOCK_SH)
        state = tracking_state(req, root)
    for job in ids:
        entry = state['jobs'].get(job, {})
        record = entry.get('lastConfirmed')
        if not record:
            raise ValueError('Native completion unknown: ' + job)
        value = checked_native(req, job, record['source'])
        # A preserved exact terminal source remains evidence after Slurm purges
        # it. No missing response or Nextflow trace can manufacture COMPLETED.
        if value.get('JobState') != 'COMPLETED' or value.get('ExitCode') != '0:0' or entry.get('failure'):
            raise ValueError('Native completion unverified: ' + job + ' state ' + value.get('JobState', 'UNKNOWN'))


def stop_process(child):
    # The Nextflow subprocess owns a new process group, separate from the
    # controller/client. Its descendants cannot outlive an interrupted monitor.
    if child.poll() is not None:
        return
    try:
        os.killpg(child.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        child.wait(timeout=5)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(child.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        child.wait(timeout=5)


def process_run(root, argv, cwd, timeout, req=None, traversal=None):
    begin = time.monotonic()
    started = now()
    code = None
    child = None
    label = 'version' if '-version' in argv else 'config' if 'config' in argv else 'stdout'
    outpath, errpath = cwd / ('remote-' + label + '.log'), cwd / ('remote-' + label + '.stderr')
    try:
        if req is None:
            result = invoke(argv, cwd=cwd, timeout=timeout, check=False)
            code = result.returncode
            outpath.write_text(result.stdout)
            errpath.write_text(result.stderr)
        else:
            with outpath.open('w') as out, errpath.open('w') as err:
                child = subprocess.Popen(argv, cwd=cwd, stdin=subprocess.DEVNULL, stdout=out, stderr=err, start_new_session=True)
                while True:
                    snapshot_jobs(req, root, traversal)
                    observation = native_status(req, root)
                    if observation['nativeFailures']:
                        write(root, 'remote-native-failure.json', {'at': now(), **observation})
                        raise NativeJobFailure('Verified native Slurm failure: ' + canonical(observation['nativeFailures']))
                    code = child.poll()
                    if code is not None:
                        break
                    if time.monotonic() - begin > timeout:
                        raise subprocess.TimeoutExpired(argv, timeout)
                    time.sleep(1)
            result = subprocess.CompletedProcess(argv, code, outpath.read_text(), errpath.read_text())
        if code:
            raise ValueError('Command exit ' + str(code) + ': ' + argv[0] + ': ' + (result.stderr[-4096:] or result.stdout[-4096:]))
        return result.stdout
    finally:
        if child is not None:
            stop_process(child)
            code = child.poll()
        with (root / 'remote-processes.jsonl').open('a') as stream:
            stream.write(canonical({'argv': argv, 'startedAt': started, 'durationMs': int((time.monotonic()-begin)*1000), 'exitCode': code,
                                    **({'traversal': traversal, 'monitoredNativeJobs': True} if req else {})}) + '\n')


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
    if req['target'].get('strict'):
        req['strictController'] = True
    root = run_root(req)
    signal.signal(signal.SIGTERM, lambda *_: (_ for _ in ()).throw(InterruptedError('Controller cancelled')))
    status = 'failed'
    error = None
    try:
        verify(req, root)
        observed = observe(req)
        write(root, 'remote-head-observation.json', observed)
        if req['target'].get('strict'):
            temporary = req['target']['strict']['policy']['paths']['temporaryRoot']
            os.environ['NXF_TEMP'] = temporary
            # Bind Java temporary files before version/configuration probes too.
            os.environ['NXF_OPTS'] = os.environ.get('NXF_OPTS', '') + ' -Djava.io.tmpdir=' + temporary
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
                                      'slurmVersionOutput': invoke(['scontrol', '--version']).stdout,
                                      'backend': 'trp-slurm-colocated-strict/1.0.0' if req['target'].get('strict') else VERSION})
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
        process_run(root, [*args, '-stub-run'], dry, min(480, req['budget']['wallSeconds']), req, 'stub')
        snapshot_jobs(req, root, 'stub')
        ensure_native_completion(req, root, 'stub')
        verify(req, root)
        if req['target'].get('strict'):
            write(root, 'remote-strict-before-science.json', strict_observation(req, 'controller'))
        analysis_inventory = observe(req)
        write(root, 'remote-analysis-inventory.json', analysis_inventory)
        if analysis_inventory['remote']['controllerCpus'] < 1 or analysis_inventory['remote']['controllerMemoryBytes'] < 2147483648 or not any(n['eligible'] and n['cpus'] >= 2 and n['memoryBytes'] >= 2147483648 for n in analysis_inventory['remote']['nodes']):
            raise ValueError('Capacity lost after stub traversal')
        deadline = time.monotonic() + 90
        while not (root / 'remote-analysis-approval.json').exists():
            if time.monotonic() > deadline:
                raise ValueError('Client did not grant fresh analysis resource admission')
            time.sleep(0.5)
        if req['target'].get('strict'):
            write(root, 'remote-strict-before-science.json', strict_observation(req, 'controller'))
        process_run(root, args, root, min(480, req['budget']['wallSeconds']), req, 'science')
        snapshot_jobs(req, root, 'science')
        ensure_native_completion(req, root, 'science')
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
            if (root / 'remote-native-state.json').exists() and native_status(req, root)['nativeFailures']:
                status = 'failed'
        except Exception as tracking:
            # A quota-truncated/corrupt tracker is a failure of observation,
            # never a reason to skip bounded cancellation of owned work.
            status = 'failed'
            error += '; Native tracking validation failed: ' + str(tracking)
        try:
            write(root, 'remote-job-cancellation.json', cancel_jobs(req))
        except Exception as cancellation:
            write(root, 'remote-job-cancellation.json', {'confirmed': False, 'error': str(cancellation)})
    finally:
        final_native = {}
        try:
            if (root / 'remote-native-state.json').exists():
                final_native = native_status(req, root)
                if final_native['nativeFailures']:
                    status = 'failed'
        except Exception as tracking:
            status = 'failed'
            error = (error or '') + '; Native tracking validation failed: ' + str(tracking)
        write(root, 'remote-terminal.json', {'status': status, 'error': error, 'finishedAt': now(), 'digest': req['digest'], 'id': req['id'], **final_native})


def status(req):
    root = run_root(req)
    identity = json.loads((root / 'remote-controller-identity.json').read_text())
    jobs = snapshot_jobs(req, root)
    terminal = root / 'remote-terminal.json'
    result = json.loads(terminal.read_text()) if terminal.exists() else {'status': 'running', 'digest': req['digest'], 'id': req['id']}
    inventory_file = root / 'remote-analysis-inventory.json'
    return {'ok': True, **result, 'controllerAlive': controller_alive(identity), 'jobs': jobs, 'controller': identity,
            'analysisInventory': json.loads(inventory_file.read_text()) if inventory_file.exists() else None,
            'analysisAdmitted': (root / 'remote-analysis-approval.json').exists(), **native_status(req, root)}


def admit_analysis(req):
    root = run_root(req)
    verify(req, root)
    decision = req['decision']
    raw = json.loads((root / 'remote-analysis-inventory.json').read_text())
    inventory = {key: raw[key] for key in ['observedAt', 'platform', 'architecture', 'host', 'workspace', 'filesystem', 'cpus', 'memoryBytes', 'freeBytes', 'sources', 'limitations', 'remote']}
    if raw.get('remoteStrict'):
        inventory.update(remoteStrict=raw['remoteStrict'], remoteStrictObservation=raw['remoteStrictObservation'])
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
