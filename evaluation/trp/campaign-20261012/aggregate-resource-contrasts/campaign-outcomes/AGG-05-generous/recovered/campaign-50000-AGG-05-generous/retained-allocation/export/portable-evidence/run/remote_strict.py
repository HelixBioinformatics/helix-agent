#!/usr/bin/env python3
"""Read-only kernel and root-policy validation for co-located Slurm clients.

Never allocates resources, changes cgroups or sets quotas. A root supervisor
must create the immutable policy and refresh the independently queried quota.
"""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import pwd
import re
import socket
import stat
import struct
import subprocess
import sys
import time

VERSION = 'trp-remote-strict/1.0.0'
POLICY_ROOT = Path('/run/helix-remote-strict')
CHECKER = Path('/usr/local/libexec/helix-remote-strict-check.py')
FS_IOC_FSGETXATTR = 0x801c581f
FS_XFLAG_PROJINHERIT = 0x00000200


def sha(data):
    return hashlib.sha256(data).hexdigest()


def fail(detail):
    raise ValueError('Strict remote allocation unverified: ' + detail)


def root_owned(file, directory=False):
    file = Path(file)
    found = file.lstat()
    if found.st_uid != 0 or found.st_mode & 0o022 or file.is_symlink():
        fail('root ownership or permissions: ' + str(file))
    if directory and not stat.S_ISDIR(found.st_mode) or not directory and not stat.S_ISREG(found.st_mode):
        fail('ordinary root file/directory required: ' + str(file))
    if file.resolve(strict=True) != file:
        fail('root policy path contains a symlink')


def root_json(pointer):
    root_owned(POLICY_ROOT, True)
    root_owned(pointer)
    raw = Path(pointer).read_bytes()
    return json.loads(raw), sha(raw), raw.decode('utf-8')


def project_attributes(directory):
    descriptor = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        result = bytearray(28)
        fcntl.ioctl(descriptor, FS_IOC_FSGETXATTR, result, True)
        flags, _, _, project, _ = struct.unpack('=5I', result[:20])
        return {'projectId': project, 'inherit': bool(flags & FS_XFLAG_PROJINHERIT), 'flags': flags}
    finally:
        os.close(descriptor)


def quota_values(source, project):
    rows = re.findall(r'^#?' + str(project) + r'\s+(\d+)\s+(\d+)\s+(\d+)\s', source, re.M)
    if len(rows) != 1:
        fail('exact project quota absent or ambiguous in root kernel report')
    used, soft, hard = map(int, rows[0])
    return {'usedBytes': used * 1024, 'softBytes': soft * 1024, 'hardBytes': hard * 1024}


def policy_contract(policy, target):
    if set(policy) != {'version', 'id', 'uid', 'hostname', 'bootId', 'target', 'filesystem', 'paths', 'controller', 'entitlement', 'checker', 'samplePath'}:
        fail('unsupported policy fields')
    if policy['version'] != VERSION or not re.fullmatch(r'hrs[0-9a-f]{16}', policy['id']):
        fail('unsupported policy version/identity')
    if not isinstance(policy['uid'], int) or isinstance(policy['uid'], bool) or policy['uid'] <= 0:
        fail('quota-exempt root cannot be the scientific client')
    if set(policy['target']) - {'host', 'port', 'user', 'hostKeyAlias', 'root', 'partition', 'selectNode', 'geometryNode', 'numericalProfile'}:
        fail('unsupported target policy fields')
    for key, value in policy['target'].items():
        if target.get(key) != value:
            fail('target differs from root policy: ' + key)
    if not {'host', 'port', 'user', 'hostKeyAlias', 'root', 'partition'} <= set(policy['target']):
        fail('incomplete target binding')
    fs = policy['filesystem']
    if set(fs) != {'mountPoint', 'uuid', 'device', 'projectId', 'hardBytes'}:
        fail('incomplete filesystem binding')
    if not re.fullmatch(r'[0-9a-fA-F-]{36}', fs['uuid']) or not isinstance(fs['device'], int) or fs['device'] <= 0:
        fail('unsupported filesystem identity')
    if not isinstance(fs['projectId'], int) or fs['projectId'] <= 0 or not isinstance(fs['hardBytes'], int) or fs['hardBytes'] <= 0 or fs['hardBytes'] % 4096:
        fail('unsupported project quota')
    expected_paths = {'allocationRoot', 'clientWorkspace', 'temporaryRoot', 'exportRoot', 'clientStateRoot', 'clientCacheRoot', 'remoteRoot'}
    if set(policy['paths']) != expected_paths or policy['paths']['remoteRoot'] != target['root']:
        fail('incomplete co-located path binding')
    for value in [fs['mountPoint'], *policy['paths'].values()]:
        if not isinstance(value, str) or not re.fullmatch(r'/[a-zA-Z0-9_./-]+', value) or '..' in value or value == '/':
            fail('unsafe or unsupported allocation path')
    if policy['controller'] != {'cgroup': 'helix-strict-' + policy['id'] + '.service', 'cpus': 1, 'memoryBytes': 2147483648, 'swapBytes': 0}:
        fail('unsupported controller allocation')
    entitlement = policy['entitlement']
    if entitlement != {'cpus': 3, 'memoryBytes': 4294967296, 'workBytes': fs['hardBytes'], 'wallSeconds': 1080}:
        fail('unsupported run entitlement')
    if policy['checker']['path'] != str(CHECKER) or not re.fullmatch(r'[0-9a-f]{64}', policy['checker']['sha256']):
        fail('unrecognized root checker')
    if policy['samplePath'] != str(POLICY_ROOT / (policy['id'] + '.sample.json')):
        fail('unexpected sampler path')


def observe(pointer, target, expected_policy_sha=None, role='client'):
    if not re.fullmatch(r'/run/helix-remote-strict/hrs[0-9a-f]{16}\.json', pointer):
        fail('invalid immutable policy path')
    policy, policy_sha, policy_raw = root_json(pointer)
    policy_contract(policy, target)
    if expected_policy_sha is not None and policy_sha != expected_policy_sha:
        fail('root policy changed after preparation')
    if os.geteuid() != policy['uid'] or target['user'] != pwd.getpwuid(os.geteuid()).pw_name:
        fail('client or controller user differs')
    if Path(pointer).stem != policy['id']:
        fail('policy identity differs from root filename')
    if socket.gethostname() != policy['hostname'] or Path('/proc/sys/kernel/random/boot_id').read_text().strip() != policy['bootId']:
        fail('co-located head/boot identity differs')
    root_owned(CHECKER.parent, True)
    root_owned(CHECKER)
    if sha(CHECKER.read_bytes()) != policy['checker']['sha256']:
        fail('root checker differs from fixed policy')
    sample, sample_sha, sample_raw = root_json(policy['samplePath'])
    if sample['version'] != 'trp-remote-strict-sample/1.0.0' or sample['policySha256'] != policy_sha or sample['bootId'] != policy['bootId']:
        fail('quota sample binding differs')
    age = time.time() - sample['observedAt']
    if not -1 <= age <= 5:
        fail('root quota sample is stale')
    quota = sample['quota']
    fs = policy['filesystem']
    values = quota_values(quota['reportSource'], fs['projectId'])
    if values['hardBytes'] != fs['hardBytes'] or quota['hardBytes'] != values['hardBytes'] or quota['usedBytes'] != values['usedBytes'] or quota['projectId'] != fs['projectId']:
        fail('kernel quota differs from root allocation')
    if 'Accounting: ON' not in quota['stateSource'] or 'Enforcement: ON' not in quota['stateSource']:
        fail('kernel project quota enforcement is inactive')
    if quota['treeCheckExitCode'] != 0 or quota['treeCheckStdout'].strip() or quota['treeCheckStderr'].strip():
        fail('root recursive project inheritance check failed')
    paths = policy['paths']
    root = Path(paths['allocationRoot'])
    mount = Path(fs['mountPoint'])
    if not root.is_absolute() or root.resolve(strict=True) != root or root == mount or not root.is_relative_to(mount):
        fail('allocation root is not an ordinary child of XFS mount')
    observations = []
    for name, value in paths.items():
        file = Path(value)
        if not file.is_absolute() or file.resolve(strict=True) != file or not file.is_dir() or not file.is_relative_to(root):
            fail('path outside quota or containing symlinks: ' + name)
        if file.stat().st_dev != fs['device'] or file.stat().st_uid != policy['uid']:
            fail('path device/ownership differs: ' + name)
        attributes = project_attributes(str(file))
        if attributes['projectId'] != fs['projectId'] or not attributes['inherit']:
            fail('directory project/inherit flag differs: ' + name)
        observations.append({'name': name, 'path': value, 'device': file.stat().st_dev, **attributes})
    command = ['findmnt', '--json', '--target', str(root), '--output', 'TARGET,SOURCE,FSTYPE,OPTIONS,UUID']
    found = subprocess.run(command, capture_output=True, text=True, timeout=10, check=True)
    mounts = json.loads(found.stdout)['filesystems']
    if len(mounts) != 1:
        fail('ambiguous mount identity')
    observed_mount = mounts[0]
    options = set(observed_mount['options'].split(','))
    if observed_mount['target'] != str(mount) or observed_mount['fstype'] != 'xfs' or observed_mount['uuid'] != fs['uuid'] or not options & {'prjquota', 'pquota'} or options & {'pqnoenforce', 'noquota'}:
        fail('XFS UUID/mount/enforcement options differ')
    cwd = Path.cwd().resolve(strict=True)
    expected_cwd = Path(paths['clientWorkspace' if role == 'client' else 'remoteRoot'])
    if role not in ('client', 'controller') or not cwd.is_relative_to(expected_cwd):
        fail('client/controller cwd outside assigned project path')
    environment = {'TMPDIR': 'temporaryRoot', 'XDG_STATE_HOME': 'clientStateRoot', 'XDG_CACHE_HOME': 'clientCacheRoot'}
    for variable, name in environment.items():
        if os.environ.get(variable) != paths[name]:
            fail('client temporary/state/cache path differs: ' + variable)
    for variable, value in {'XDG_DATA_HOME': paths['clientStateRoot'] + '/data',
                            'XDG_CONFIG_HOME': paths['clientStateRoot'] + '/config',
                            'BUN_INSTALL_CACHE_DIR': paths['clientCacheRoot'] + '/bun'}.items():
        if os.environ.get(variable) != value:
            fail('client data/config/Bun cache path differs: ' + variable)
    membership = Path('/proc/self/cgroup').read_text().strip()
    group = Path('/sys/fs/cgroup') / policy['controller']['cgroup']
    if membership != '0::/' + policy['controller']['cgroup']:
        fail('client/controller outside the shared controller cgroup')
    parent_membership = Path('/proc/' + str(os.getppid()) + '/cgroup').read_text().strip()
    if role == 'client' and parent_membership != membership:
        fail('real client parent is outside the shared controller cgroup')
    root_owned(group, True)
    limits = {name: (group / name).read_text().strip() for name in ('cpu.max', 'memory.max', 'memory.swap.max', 'memory.current', 'memory.peak')}
    for name in ('cpu.max', 'memory.max', 'memory.swap.max'):
        root_owned(group / name)
    cpu = limits['cpu.max'].split()
    if len(cpu) != 2 or cpu[0] == 'max' or int(cpu[0]) != int(cpu[1]) or limits['memory.max'] != '2147483648' or limits['memory.swap.max'] != '0':
        fail('effective shared controller bounds differ')
    ancestors = []
    parent = group.parent
    while parent != Path('/sys/fs/cgroup'):
        cpu = (parent / 'cpu.max').read_text().split()
        maximum = (parent / 'memory.max').read_text().strip()
        if cpu[0] != 'max' and int(cpu[0]) < int(cpu[1]) or maximum != 'max' and int(maximum) < 2147483648:
            fail('ancestor cannot supply the declared controller entitlement')
        ancestors.append(str(parent))
        parent = parent.parent
    return {'version': VERSION, 'policy': policy, 'policySha256': policy_sha,
            'sampleSha256': sample_sha, 'sampleRaw': sample_raw, 'policyRaw': policy_raw,
            'observedAt': sample['observedAt'], 'checkedAt': time.time(), 'role': role,
            'transport': 'co-located-python', 'host': socket.gethostname(), 'pid': os.getpid(),
            'cwd': str(cwd), 'membership': membership, 'cgroup': limits, 'ancestors': ancestors,
            'parentPid': os.getppid(), 'parentMembership': parent_membership,
            'mount': observed_mount, 'paths': observations, 'quota': values,
            'entitlement': policy['entitlement'], 'currentUsageIsSubtractedFromEntitlement': False}


if __name__ == '__main__':
    try:
        request = json.load(sys.stdin)
        result = observe(request['policyPath'], request['target'], request.get('policySha256'), request.get('role', 'client'))
        print(json.dumps({'ok': True, **result}, sort_keys=True))
    except Exception as error:
        print(json.dumps({'ok': False, 'code': 'remote-strict-unverified', 'error': str(error)}))
        sys.exit(1)
