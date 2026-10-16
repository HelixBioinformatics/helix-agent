"""Offline installer regression tests: no network or changes to the user's home.

Run with python3 script/test-install.py.
"""
import io
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
import unittest

INSTALL = Path(__file__).resolve().parents[1] / 'install'


class InstallerTest(unittest.TestCase):
    def run_install(self, downloaders, *, version=False, fail=False, snap=False, local=False):
        with tempfile.TemporaryDirectory(prefix='helix-install-test-') as temp:
            root = Path(temp)
            home = root / 'home'
            home.mkdir()
            bin_dir = root / 'tools'
            bin_dir.mkdir()
            for tool in ['bash', 'mkdir', 'uname', 'tr', 'grep', 'ldd', 'sed', 'tar', 'gzip',
                         'mv', 'chmod', 'rm', 'getent', 'id', 'cut', 'basename', 'readlink', 'cp']:
                source = shutil.which(tool)
                if source:
                    (bin_dir / tool).symlink_to(source)
            payload = b'#!/bin/sh\necho 9.8.7\n'
            archive = root / 'fixture.tar.gz'
            with tarfile.open(archive, 'w:gz') as tar:
                info = tarfile.TarInfo('helix')
                info.size = len(payload)
                info.mode = 0o755
                tar.addfile(info, io.BytesIO(payload))
            for tool in downloaders:
                path = bin_dir / tool
                path.write_text('''#!/bin/bash
printf '%s\\n' "$0 $*" >> "$TEST_LOG"
if [[ "$*" == *api.github.com* ]]; then
    printf '{"tag_name":"v9.8.7"}\\n'
    exit 0
fi
[[ "$TEST_FAIL" == 1 ]] && exit 22
output=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --output) output="$2"; shift ;;
        --output-document=*) output="${1#*=}" ;;
    esac
    shift
done
cp "$TEST_ARCHIVE" "$output"
''')
                path.chmod(0o755)
            path_value = str(bin_dir)
            if snap:
                snap_bin = root / 'snap' / 'bin'
                snap_bin.mkdir(parents=True)
                curl = snap_bin / 'curl'
                curl.write_text('#!/bin/bash\necho snap-invoked >> "$TEST_LOG"\nexit 99\n')
                curl.chmod(0o755)
                path_value = str(snap_bin) + ':' + path_value
            log = root / 'downloads.log'
            env = {**os.environ, 'HOME': str(home), 'PATH': path_value, 'SHELL': '/bin/bash',
                   'TMPDIR': str(root), 'TEST_LOG': str(log), 'TEST_ARCHIVE': str(archive),
                   'TEST_FAIL': str(int(fail)), 'VERSION': '', 'GITHUB_ACTIONS': 'false'}
            args = ['/bin/bash', str(INSTALL), '--no-modify-path']
            if version:
                args += ['--version', '9.8.7']
            if local:
                binary = root / 'local-binary'
                binary.write_bytes(payload)
                args += ['--binary', str(binary)]
            result = subprocess.run(args, env=env, capture_output=True, text=True, timeout=15)
            target = home / '.helix' / 'bin' / 'helix'
            logs = log.read_text() if log.exists() else ''
            self.assertNotIn('snap-invoked', logs)
            if fail or (not downloaders and not local):
                self.assertNotEqual(result.returncode, 0, result.stdout)
                self.assertFalse(target.exists())
            else:
                self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
                self.assertEqual(target.read_bytes(), payload)
                self.assertTrue(os.access(target, os.X_OK))
                self.assertIn('Helix Agent', result.stdout)
            if version:
                self.assertNotIn('api.github.com', logs)
            return logs, result

    def test_wget_without_curl(self):
        logs, _ = self.run_install(['wget'])
        self.assertIn('api.github.com', logs)
        self.assertIn('/wget ', logs)
        self.assertIn('api.github.com/repos/HelixBioinformatics/helix-agent/releases/latest', logs)
        self.assertIn('github.com/HelixBioinformatics/helix-agent/releases/latest/download/helix-', logs)

    def test_curl_without_wget(self):
        self.run_install(['curl'])

    def test_snap_curl_with_wget(self):
        self.run_install(['wget'], snap=True)

    def test_snap_shadowing_native_curl(self):
        self.run_install(['curl'], snap=True)

    def test_pinned_release_with_wget(self):
        self.run_install(['wget'], version=True)

    def test_http_error_does_not_install(self):
        self.run_install(['curl'], fail=True)

    def test_no_native_downloader_has_actionable_error(self):
        _, result = self.run_install([], snap=True)
        self.assertIn('native curl or wget', result.stderr)

    def test_local_binary_needs_no_downloader(self):
        self.run_install([], local=True)


if __name__ == '__main__':
    unittest.main()
