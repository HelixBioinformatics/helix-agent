from pathlib import Path
import difflib,hashlib
root=Path('/home/webiwabou/Projects/bioinformatica-org');stage=Path('/tmp/helix-backend-consistency-20261013')
s=(Path('/tmp/helix-strict-verifier-hardening-20261013')/'verify_bundle.py.txt').read_text()
s=s.replace('def verify(root, expected=None):','def verify(root, expected=None, allow_legacy_strict_backend=False):')
s=s.replace("    root = Path(root).resolve(strict=True)\n    names = walk(root)","    if type(allow_legacy_strict_backend) is not bool:\n        raise ValueError('legacy backend option must be boolean')\n    if allow_legacy_strict_backend and expected is None:\n        raise ValueError('legacy strict backend compatibility requires an external manifest anchor')\n    root = Path(root).resolve(strict=True)\n    names = walk(root)")
s=s.replace("    strict = execution.get('backend') == 'trp-slurm-colocated-strict/1.0.0'", "    if execution.get('backend') not in (None, 'trp-slurm-ssh/1.0.0', 'trp-slurm-colocated-strict/1.0.0'):\n        raise ValueError('unsupported execution backend')\n    strict = execution.get('backend') == 'trp-slurm-colocated-strict/1.0.0'")
start="    if run['status'] == 'succeeded':\n        for name in ['approval.json'"
replace="""    legacy_backend_metadata = False
    if remote and run['status'] == 'succeeded':
        completions = [event for event in events if event['source'] == 'execution' and event['outcome'] == 'completed']
        if len(completions) != 1:
            raise ValueError('remote completion backend is missing/duplicated')
        declared = execution['backend']
        recorded_run = run.get('backend')
        recorded_event = completions[0]['detail'].get('backend')
        if recorded_run != declared or recorded_event != declared:
            # Historical strict runs retained the generic SSH family label in
            # these two metadata records. An explicit operator option and the
            # external immutable anchor are necessary; never rewrite old bytes.
            if (not allow_legacy_strict_backend or expected is None or not strict
                or recorded_run != 'trp-slurm-ssh/1.0.0' or recorded_event != 'trp-slurm-ssh/1.0.0'):
                raise ValueError('remote run/completion backend differs from verified execution')
            legacy_backend_metadata = True
    if run['status'] == 'succeeded':
        for name in ['approval.json'"""
assert s.count(start)==1;s=s.replace(start,replace)
s=s.replace("'status': run['status'], 'externallyAnchored': expected is not None,", "'status': run['status'], 'externallyAnchored': expected is not None,\n            'legacyBackendMetadata': legacy_backend_metadata,")
s=s.replace("    parser.add_argument('--sha256')", "    parser.add_argument('--sha256')\n    parser.add_argument('--allow-legacy-strict-backend', action='store_true',\n                        help='With an external anchor only: preserve historical strict exports whose run/completion metadata used the generic SSH family label; reports legacyBackendMetadata=true')")
s=s.replace("result = verify(args.bundle, args.sha256)","result = verify(args.bundle, args.sha256, args.allow_legacy_strict_backend)")
(stage/'verify_bundle.py.txt').write_text(s)
(stage/'verify_bundle.patch').write_text(''.join(difflib.unified_diff((root/'packages/helix/src/trp/verify_bundle.py.txt').read_text().splitlines(True),s.splitlines(True),fromfile='a/packages/helix/src/trp/verify_bundle.py.txt',tofile='b/packages/helix/src/trp/verify_bundle.py.txt')))
print('candidate',hashlib.sha256(s.encode()).hexdigest(),'patch',hashlib.sha256((stage/'verify_bundle.patch').read_bytes()).hexdigest())
