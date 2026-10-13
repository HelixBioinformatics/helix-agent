"""Checker contracts are synthetic; live kernel admission needs root provisioning."""
import copy
import importlib.machinery
import importlib.util
import json
import hashlib
from pathlib import Path
from pathlib import PurePosixPath
import subprocess
import tempfile
from unittest.mock import patch
import unittest

ROOT = Path(__file__).resolve().parents[4]
SOURCE = ROOT / 'packages/helix/src/trp/remote_strict.py.txt'
loader = importlib.machinery.SourceFileLoader('strict_checker', str(SOURCE))
spec = importlib.util.spec_from_loader(loader.name, loader)
checker = importlib.util.module_from_spec(spec)
loader.exec_module(checker)
verifier_loader = importlib.machinery.SourceFileLoader('strict_cold_verifier', str(ROOT / 'packages/helix/src/trp/verify_bundle.py.txt'))
verifier = importlib.util.module_from_spec(importlib.util.spec_from_loader(verifier_loader.name, verifier_loader))
verifier_loader.exec_module(verifier)
runner_loader = importlib.machinery.SourceFileLoader('strict_controller', str(ROOT / 'packages/helix/src/trp/remote_runner.py.txt'))
runner = importlib.util.module_from_spec(importlib.util.spec_from_loader(runner_loader.name, runner_loader))
runner_loader.exec_module(runner)
POLICY = json.loads(r'''{
  "version": "trp-remote-strict/1.0.0",
  "id": "hrs0123456789abcdef",
  "uid": 1000,
  "hostname": "helix-head",
  "bootId": "REPLACE_WITH_PROC_BOOT_ID",
  "target": {
    "host": "127.0.0.1",
    "port": 22,
    "user": "ubuntu",
    "hostKeyAlias": "helix-lab2",
    "root": "/shared/helix-strict/allocation/remote",
    "partition": "helix",
    "selectNode": "helix-worker1",
    "geometryNode": "helix-worker2",
    "numericalProfile": "haswell-single-thread"
  },
  "filesystem": {
    "mountPoint": "/shared/helix-strict",
    "uuid": "REPLACE_XFS_UUID",
    "device": 0,
    "projectId": 142,
    "hardBytes": 67108864
  },
  "paths": {
    "allocationRoot": "/shared/helix-strict/allocation",
    "clientWorkspace": "/shared/helix-strict/allocation/client",
    "temporaryRoot": "/shared/helix-strict/allocation/tmp",
    "exportRoot": "/shared/helix-strict/allocation/export",
    "clientStateRoot": "/shared/helix-strict/allocation/state",
    "clientCacheRoot": "/shared/helix-strict/allocation/cache",
    "remoteRoot": "/shared/helix-strict/allocation/remote"
  },
  "controller": {
    "cgroup": "helix-strict-hrs0123456789abcdef.service",
    "cpus": 1,
    "memoryBytes": 2147483648,
    "swapBytes": 0
  },
  "entitlement": {
    "cpus": 3,
    "memoryBytes": 4294967296,
    "workBytes": 67108864,
    "wallSeconds": 1080
  },
  "checker": {
    "path": "/usr/local/libexec/helix-remote-strict-check.py",
    "sha256": "REPLACE_WITH_FINAL_CHECKER_SHA256"
  },
  "samplePath": "/run/helix-remote-strict/hrs0123456789abcdef.sample.json"
}''')
POLICY['filesystem']['uuid'] = '01234567-0123-0123-0123-0123456789ab'
POLICY['filesystem']['device'] = 123
POLICY['checker']['sha256'] = 'a' * 64


class Contracts(unittest.TestCase):
    def test_complete_supported_contract(self):
        checker.policy_contract(POLICY, POLICY['target'])

    def test_missing_target_keys_cannot_hide_behind_optional_keys(self):
        p = copy.deepcopy(POLICY)
        del p['target']['port']
        with self.assertRaisesRegex(ValueError, 'incomplete target'):
            checker.policy_contract(p, p['target'])

    def test_mismatched_destination(self):
        target = {**POLICY['target'], 'host': 'other-head'}
        with self.assertRaisesRegex(ValueError, 'target differs'):
            checker.policy_contract(POLICY, target)

    def test_root_client_cannot_claim_enforced_quota(self):
        p = copy.deepcopy(POLICY); p['uid'] = 0
        with self.assertRaisesRegex(ValueError, 'quota-exempt root'):
            checker.policy_contract(p, p['target'])

    def test_controller_caps_and_total_budget_cannot_be_raised(self):
        for section, field in [('controller', 'memoryBytes'), ('controller', 'cpus'), ('entitlement', 'memoryBytes')]:
            p = copy.deepcopy(POLICY); p[section][field] *= 2
            with self.assertRaises(ValueError):
                checker.policy_contract(p, p['target'])

    def test_policy_can_never_redirect_temporary_paths_outside_declared_plain_paths(self):
        p = copy.deepcopy(POLICY); p['paths']['temporaryRoot'] += ' -Djava.io.tmpdir=/tmp'
        with self.assertRaisesRegex(ValueError, 'unsafe'):
            checker.policy_contract(p, p['target'])

    def test_quota_report_reads_kernel_blocks_as_kibibytes(self):
        found = checker.quota_values('#142 12 0 65536 0 [------]\n', 142)
        self.assertEqual(found, {'usedBytes': 12288, 'softBytes': 0, 'hardBytes': 67108864})

    def test_missing_or_duplicate_kernel_project_is_rejected(self):
        for text in ['#143 12 0 65536 0\n', '#142 12 0 65536 0\n#142 10 0 65536 0\n']:
            with self.assertRaisesRegex(ValueError, 'absent or ambiguous'):
                checker.quota_values(text, 142)

    def test_arbitrary_user_path_rejected_before_root_or_kernel_operations(self):
        with self.assertRaisesRegex(ValueError, 'invalid immutable policy path'):
            checker.observe('/tmp/fake.json', {})

    def receipt(self):
        policy = copy.deepcopy(POLICY)
        policy_raw = json.dumps(policy)
        allocated = {'policy': policy, 'policySha256': hashlib.sha256(policy_raw.encode()).hexdigest()}
        sample = {'version': 'trp-remote-strict-sample/1.0.0', 'policySha256': allocated['policySha256'],
                  'observedAt': 1000, 'bootId': policy['bootId'], 'quota': {'projectId': 142, 'usedBytes': 12288,
                  'hardBytes': 67108864, 'reportSource': '#142 12 0 65536 0 [------]\n',
                  'stateSource': 'Accounting: ON\nEnforcement: ON\n', 'treeCheckExitCode': 0,
                  'treeCheckStdout': '', 'treeCheckStderr': ''}}
        raw = json.dumps(sample)
        receipt = {'version': checker.VERSION, 'policy': policy, 'policySha256': allocated['policySha256'],
                   'policyRaw': policy_raw, 'sampleRaw': raw, 'sampleSha256': hashlib.sha256(raw.encode()).hexdigest(),
                   'checkedAt': 1001, 'host': policy['hostname'], 'transport': 'co-located-python',
                   'membership': '0::/' + policy['controller']['cgroup'],
                   'cgroup': {'cpu.max': '100000 100000', 'memory.max': '2147483648', 'memory.swap.max': '0'},
                   'entitlement': policy['entitlement'], 'currentUsageIsSubtractedFromEntitlement': False,
                   'role': 'client', 'cwd': policy['paths']['clientWorkspace'],
                   'parentMembership': '0::/' + policy['controller']['cgroup'],
                   'paths': [{'name': name, 'path': path, 'device': 123, 'projectId': 142, 'inherit': True}
                             for name, path in policy['paths'].items()],
                   'mount': {'target': policy['filesystem']['mountPoint'], 'uuid': policy['filesystem']['uuid'],
                             'fstype': 'xfs', 'options': 'rw,prjquota'}}
        return receipt, allocated

    def test_cold_receipt_can_be_checked_without_linux_or_executing_checker(self):
        receipt, allocated = self.receipt()
        verifier.strict_receipt(receipt, allocated)

    def test_cold_receipt_rejects_changed_or_stale_sources_and_kernel_identity(self):
        for mode in ['policy-source', 'sampler-source', 'stale', 'membership', 'project', 'inherit', 'limits', 'parent']:
            receipt, allocated = self.receipt()
            if mode == 'policy-source': receipt['policyRaw'] += ' '
            if mode == 'sampler-source': receipt['sampleRaw'] += ' '
            if mode == 'stale': receipt['checkedAt'] += 10
            if mode == 'membership': receipt['membership'] += '/other'
            if mode == 'project': receipt['paths'][0]['projectId'] += 1
            if mode == 'inherit': receipt['paths'][0]['inherit'] = False
            if mode == 'limits': receipt['cgroup']['memory.max'] = '4294967296'
            if mode == 'parent': receipt['parentMembership'] = '0::/other'
            with self.assertRaises(ValueError, msg=mode):
                verifier.strict_receipt(receipt, allocated)

    def test_actual_observe_preserves_controller_entitlement_with_nonzero_current_usage(self):
        data = {'/proc/meminfo': 'MemAvailable: 4194304 kB\n', '/proc/self/cgroup': '0::/fixture\n',
                '/sys/fs/cgroup/fixture/cpu.max': '100000 100000',
                '/sys/fs/cgroup/fixture/memory.max': '2147483648',
                '/sys/fs/cgroup/fixture/memory.current': '52428800',
                '/sys/fs/cgroup/cpu.max': 'max 100000', '/sys/fs/cgroup/memory.max': 'max'}

        class KernelPath:
            def __init__(self, value): self.value = PurePosixPath(value)
            def __truediv__(self, value): return KernelPath(self.value / value)
            def __eq__(self, other): return isinstance(other, KernelPath) and self.value == other.value
            def __str__(self): return str(self.value)
            @property
            def parent(self): return KernelPath(self.value.parent)
            def is_relative_to(self, value): return self.value.is_relative_to(value)
            def exists(self): return str(self.value) in data
            def is_file(self): return False
            def read_text(self): return data[str(self.value)]

        def invoke(argv, **kwargs):
            if argv[1:3] == ['show', 'partition']: text = 'PartitionName=helix State=UP Nodes=worker1,worker2'
            elif argv[1:3] == ['show', 'hostnames']: text = 'worker1\nworker2\n'
            else: text = 'State=IDLE CPUTot=2 CPUAlloc=0 RealMemory=2048 AllocMem=0'
            return subprocess.CompletedProcess(argv, 0, text, '')

        receipt = {'policy': POLICY, 'entitlement': POLICY['entitlement'], 'cgroup': {'memory.current': '52428800'}}
        req = {'target': {'partition': 'helix', 'fingerprint': 'a' * 64, 'strict': {'synthetic': 'kernel reader contract fixture'}}}
        with tempfile.TemporaryDirectory() as root, patch.object(runner, 'Path', KernelPath), \
             patch.object(runner, 'target_root', return_value=Path(root)), patch.object(runner, 'invoke', side_effect=invoke), \
             patch.object(runner, 'strict_observation', return_value=receipt), patch.object(runner.os, 'sched_getaffinity', return_value={0, 1}):
            actual = runner.observe(req)
            self.assertEqual(actual['remote']['controllerCpus'], 1)
            self.assertEqual(actual['remote']['controllerMemoryBytes'], 2147483648)
            self.assertEqual(actual['remoteStrictObservation']['cgroup']['memory.current'], '52428800')
            self.assertEqual(actual['memoryBytes'], 4294967296)
            with patch.object(runner, 'strict_observation', return_value=None):
                ordinary = runner.observe(req)
                self.assertEqual(ordinary['remote']['controllerMemoryBytes'], 2147483648 - 52428800)


if __name__ == '__main__':
    unittest.main()
