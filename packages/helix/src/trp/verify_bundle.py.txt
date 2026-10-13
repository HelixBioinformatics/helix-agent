#!/usr/bin/env python3
"""Offline TRP evidence verifier. Python standard library; never executes payloads.
Usage: python3 verify.py BUNDLE [--sha256 EXTERNALLY_RECORDED_MANIFEST_HASH]
Integrity is relative to the manifest/optional external anchor, not authorship or biological truth.
"""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import re
import sys


def digest(data):
    return hashlib.sha256(data).hexdigest()


def unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate JSON key: ' + key)
        result[key] = value
    return result


def invalid_number(value):
    raise ValueError('non-finite JSON number: ' + value)


def parse(data):
    return json.loads(data, object_pairs_hook=unique, parse_constant=invalid_number)


def canonical(data):
    return json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()


def safe_name(name):
    if not isinstance(name, str) or not name or '\\' in name or ':' in name or '\x00' in name:
        raise ValueError('unsafe path')
    if name.startswith('/') or any(p in ('', '.', '..') for p in name.split('/')):
        raise ValueError('unsafe path: ' + name)
    return name


def strict_receipt(receipt, allocated):
    """Check preserved receipt semantics, never execute its root checker."""
    p = allocated['policy']
    if receipt['version'] != 'trp-remote-strict/1.0.0' or receipt['policy'] != p or receipt['policySha256'] != allocated['policySha256']:
        raise ValueError('strict root policy receipt differs')
    if digest(receipt['policyRaw'].encode()) != allocated['policySha256'] or parse(receipt['policyRaw']) != p:
        raise ValueError('strict root policy source differs')
    sample = parse(receipt['sampleRaw'])
    if digest(receipt['sampleRaw'].encode()) != receipt['sampleSha256'] or sample['policySha256'] != allocated['policySha256'] or sample['bootId'] != p['bootId']:
        raise ValueError('strict root sampler source differs')
    if not -1 <= receipt['checkedAt'] - sample['observedAt'] <= 5:
        raise ValueError('strict root sampler was stale when checked')
    if receipt['host'] != p['hostname'] or receipt['transport'] != 'co-located-python' or receipt['membership'] != '0::/' + p['controller']['cgroup']:
        raise ValueError('strict controller host/transport/membership differs')
    limits = receipt['cgroup']
    cpu = limits['cpu.max'].split()
    if len(cpu) != 2 or cpu[0] == 'max' or int(cpu[0]) != int(cpu[1]) or limits['memory.max'] != '2147483648' or limits['memory.swap.max'] != '0':
        raise ValueError('strict shared controller limits differ')
    if receipt['currentUsageIsSubtractedFromEntitlement'] or receipt['entitlement'] != p['entitlement']:
        raise ValueError('strict entitlement was reduced by current usage')
    if receipt['role'] not in ('client', 'controller'):
        raise ValueError('strict receipt role differs')
    cwd = Path(receipt['cwd'])
    if not cwd.is_relative_to(p['paths']['clientWorkspace' if receipt['role'] == 'client' else 'remoteRoot']):
        raise ValueError('strict cwd was outside allocation')
    if receipt['role'] == 'client' and receipt['parentMembership'] != receipt['membership']:
        raise ValueError('real client parent was outside strict controller')
    if {r['name'] for r in receipt['paths']} != set(p['paths']) or len(receipt['paths']) != len(p['paths']):
        raise ValueError('strict path witness set differs')
    for row in receipt['paths']:
        if row['path'] != p['paths'][row['name']] or row['device'] != p['filesystem']['device'] or row['projectId'] != p['filesystem']['projectId'] or not row['inherit']:
            raise ValueError('strict project/device/path witness differs')
    mount = receipt['mount']
    if mount['target'] != p['filesystem']['mountPoint'] or mount['uuid'] != p['filesystem']['uuid'] or mount['fstype'] != 'xfs' or not {'pquota', 'prjquota'} & set(mount['options'].split(',')):
        raise ValueError('strict filesystem witness differs')
    q = sample['quota']
    rows = re.findall(r'^#?' + str(p['filesystem']['projectId']) + r'\s+(\d+)\s+(\d+)\s+(\d+)\s', q['reportSource'], re.M)
    if len(rows) != 1 or int(rows[0][0]) * 1024 != q['usedBytes'] or int(rows[0][2]) * 1024 != q['hardBytes'] or q['hardBytes'] != p['filesystem']['hardBytes']:
        raise ValueError('strict kernel quota source differs')
    if 'Accounting: ON' not in q['stateSource'] or 'Enforcement: ON' not in q['stateSource'] or q['treeCheckExitCode'] != 0 or q['treeCheckStdout'].strip() or q['treeCheckStderr'].strip():
        raise ValueError('strict kernel quota/inheritance was not enforced')


def walk(root):
    result = set()
    for item in root.rglob('*'):
        if item.is_symlink():
            raise ValueError('symlink in exported evidence: ' + str(item))
        if item.is_file():
            result.add(item.relative_to(root).as_posix())
        elif not item.is_dir():
            raise ValueError('special file: ' + str(item))
    return result


def verify(root, expected=None):
    root = Path(root).resolve(strict=True)
    names = walk(root)
    raw = (root / 'manifest.json').read_bytes()
    manifest_hash = digest(raw)
    if expected is not None and (not re.fullmatch('[0-9a-f]{64}', expected) or manifest_hash != expected):
        raise ValueError('external manifest hash mismatch')
    m = parse(raw)
    if m['version'] != 'trp-evidence/1.0.0' or not isinstance(m['files'], list) or not m['files']:
        raise ValueError('unsupported or empty manifest')
    listed = set()
    total = 0
    for entry in m['files']:
        name = safe_name(entry['path'])
        if name in listed or name == 'manifest.json':
            raise ValueError('duplicate/self-referential artifact')
        listed.add(name)
        if type(entry['bytes']) is not int or entry['bytes'] < 0 or not re.fullmatch('[0-9a-f]{64}', entry['sha256']):
            raise ValueError('invalid size/hash: ' + name)
        data = (root / name).read_bytes()
        if len(data) != entry['bytes'] or digest(data) != entry['sha256']:
            raise ValueError('artifact mismatch: ' + name)
        total += len(data)
    if names != listed | {'manifest.json'}:
        raise ValueError('unlisted or missing artifacts: ' + repr(sorted(names ^ (listed | {'manifest.json'}))))
    required = {'verify.py', 'run/run.json', 'run/events.jsonl', 'run/methods.json', 'run/methods.md',
                'run/inventory.json', 'run/budget.json', 'run/admission.json', 'run/protocol.json',
                'run/source.pdb', 'run/selection.pdb', 'run/validation.json', 'run/specification.json',
                'run/catalogue.json', 'run/catalogue_evidence.json'}
    if not required <= listed:
        raise ValueError('missing mandatory evidence')
    def record(name):
        return parse((root / 'run' / name).read_bytes())
    # The exact immutable file set is recorded independently from generated logs/results.
    bundle = m['bundle']
    spec = record('specification.json')
    if 'coordinateMapping' in spec:
        mapping = spec['coordinateMapping']['value']
        needed = {'mapping_source.cif', 'mapping_source_report.json', 'coordinate_mapping.json'}
        if not needed <= set(bundle['files']): raise ValueError('missing coordinate evidence')
        audit = record('coordinate_mapping.json')
        if digest((root/'run/mapping_source.cif').read_bytes()) != mapping['sha256'] or audit['sourceSha256'] != mapping['sha256']:
            raise ValueError('mapping source differs')
        if audit['targetSha256'] != digest((root/'run/source.pdb').read_bytes()) or audit['units'] != spec['units']['value']['ranges'] or audit['inputUnits'] != mapping['units']:
            raise ValueError('mapping target or units differ')
        if audit['sourceFrame'] != mapping['frame'] or audit['chain'] != spec['chain']['value'] or audit['model'] != spec['model']['value']:
            raise ValueError('mapping identity differs')
        if mapping['frame'] == 'uniprot':
            if not {'sifts_source.xml', 'sifts_mapping.json', 'sifts_residues.py'} <= set(bundle['files']): raise ValueError('missing SIFTS evidence')
            sifts = record('sifts_mapping.json')
            if digest((root/'run/sifts_source.xml').read_bytes()) != mapping['sifts']['sha256'] or sifts['sha256'] != mapping['sifts']['sha256'] or sifts['accession'] != mapping['sifts']['accession']:
                raise ValueError('SIFTS binding differs')
    if bundle['engine'] in {'trp-nextflow/1.2.0', 'trp-nextflow/1.3.0', 'trp-nextflow/1.4.0'}:
        needed = {'structural_report.json', 'structural_catalogue.json', 'inspect_structure.py'}
        if not needed <= set(bundle['files']):
            raise ValueError('missing approved structural controls')
        structural = record('structural_report.json')
        expected_ids = {c['id'] for c in record('structural_catalogue.json')['controls']}
        controls = structural['checks']
        fold = next((c for c in controls if c['id'] == 'fold-plausibility'), None)
        if fold and isinstance(fold.get('value'), dict) and 'stericDiagnostic' in fold['value']:
            if 'steric_diagnostic.py' not in bundle['files'] or fold['value'].get('wrapperSha256') != digest((root/'run/steric_diagnostic.py').read_bytes()):
                raise ValueError('optional steric diagnostic source differs')
            if fold['status'] != 'not_evaluable':
                raise ValueError('steric diagnostic cannot establish broad fold plausibility')
        if fold and isinstance(fold.get('value'), dict) and 'surfaceDiagnostic' in fold['value']:
            value = fold['value']; diagnostic = value['surfaceDiagnostic']
            if 'surface_diagnostic.py' not in bundle['files'] or value.get('surfaceWrapperSha256') != digest((root/'run/surface_diagnostic.py').read_bytes()):
                raise ValueError('optional surface diagnostic source differs')
            if fold['status'] != 'not_evaluable' or diagnostic.get('version') != 'helix-surface-diagnostic/1.0.0' or diagnostic.get('status') not in ('measured', 'not_evaluable'):
                raise ValueError('surface diagnostic cannot establish broad fold plausibility')
            if diagnostic['status'] == 'measured':
                if diagnostic.get('sourceSha256') != structural['provenance']['structureSha256'] or diagnostic.get('scope', {}).get('authorChain') != spec['chain']['value'] or diagnostic.get('scope', {}).get('modelOrdinal') != spec['model']['value']:
                    raise ValueError('surface diagnostic selection differs')
                if diagnostic.get('foldVerdict') != 'not_established' or diagnostic.get('burialThreshold') is not None or diagnostic.get('confidenceScoresUsed') is not False:
                    raise ValueError('unsupported surface fold verdict')
        if len(controls) != len(expected_ids) or {c['id'] for c in controls} != expected_ids:
            raise ValueError('structural inventory differs')
        if structural['version'] not in ('trp-structural/1.0.0', 'trp-structural/1.1.0') or structural['provenance']['structureSha256'] != digest((root / 'run/source.pdb').read_bytes()):
            raise ValueError('structural input differs')
        if not structural['summary']['mechanicalAdmission'] or structural['summary']['biologicalValidity'] != 'not_established':
            raise ValueError('structural admission differs')
        if any(c['status'] == 'fail' or c['status'] not in {'pass', 'not_evaluable', 'not_applicable'} for c in controls):
            raise ValueError('failed structural controls in admitted bundle')
        if any(c['status'] == 'not_evaluable' and c['id'] in {'confidence-scale', 'filter-direction', 'interunit-pae'} for c in controls):
            raise ValueError('unevaluated required structural control')
    if digest(canonical({'engine': bundle['engine'], 'files': bundle['files']})) != bundle['digest']:
        raise ValueError('bundle digest mismatch')
    for name, sha in bundle['files'].items():
        safe_name(name)
        if digest((root / 'run' / name).read_bytes()) != sha:
            raise ValueError('approved bundle changed: ' + name)
    admission, inventory, budget = record('admission.json'), record('inventory.json'), record('budget.json')
    execution = record('execution.json')
    strict = execution.get('backend') == 'trp-slurm-colocated-strict/1.0.0'
    remote = strict or execution.get('backend') == 'trp-slurm-ssh/1.0.0'
    if remote:
        if not {'remote_target.json', 'remote_runner.py'} <= set(bundle['files']):
            raise ValueError('missing approved remote target/controller')
        if record('remote_target.json') != execution['target'] or inventory['remote']['fingerprint'] != execution['target']['fingerprint']:
            raise ValueError('remote target differs')
        config = (root/'run/nextflow.config').read_text()
        if "process.executor = 'slurm'" not in config or '--memory=2g' not in config or '--memory-swap=2g' not in config:
            raise ValueError('remote executor or effective task memory limits missing')
    if 'enforcement' in inventory:
        if strict:
            raise ValueError('local sandbox cannot authorize strict Slurm allocation')
        enforced = record('enforcement.json')
        if enforced != inventory['enforcement'] or 'enforcement.json' not in bundle['files']:
            raise ValueError('unbound resource enforcement')
        for key in ('cpus', 'memoryBytes', 'workBytes', 'wallSeconds'):
            if enforced[key] > budget[key]:
                raise ValueError('enforced limit exceeds approved budget: ' + key)
        config = (root / 'run/nextflow.config').read_text()
        for option in ('--cgroup-parent=' + enforced['dockerParent'], '--label=trp.sandbox=' + enforced['id'],
                       '--memory-swap=2g', '--log-driver=none'):
            if option not in config:
                raise ValueError('Docker task allocation missing: ' + option)
    elif strict:
        if not {'remote_strict_policy.json', 'remote_strict.py'} <= set(bundle['files']):
            raise ValueError('strict policy/checker not approved')
        allocated = record('remote_strict_policy.json')
        if execution.get('inputStaging') != 'copy' or "process.stageInMode = 'copy'" not in config:
            raise ValueError('strict worker inputs must be physical project-accounted copies')
        if allocated != inventory.get('remoteStrict') or allocated != execution['target'].get('strict') or allocated['targetFingerprint'] != inventory['remote']['fingerprint'] or execution.get('transport') != 'co-located-python':
            raise ValueError('strict target/allocation differs')
        p = allocated['policy']
        if p['version'] != 'trp-remote-strict/1.0.0' or p['controller'] != {'cgroup': 'helix-strict-' + p['id'] + '.service', 'cpus': 1, 'memoryBytes': 2147483648, 'swapBytes': 0}:
            raise ValueError('strict controller policy differs')
        if p['entitlement'] != {'cpus': 3, 'memoryBytes': 4294967296, 'workBytes': p['filesystem']['hardBytes'], 'wallSeconds': 1080}:
            raise ValueError('strict total-run entitlement differs')
        if digest((root/'run/remote_strict.py').read_bytes()) != p['checker']['sha256']:
            raise ValueError('strict checker code differs')
        for key in ('cpus', 'memoryBytes', 'workBytes', 'wallSeconds'):
            if p['entitlement'][key] > budget[key]:
                raise ValueError('strict allocation exceeds approved budget')
        strict_receipt(inventory['remoteStrictObservation'], allocated)
    elif budget['requireHardStorageLimit']:
        raise ValueError('hard budget without enforcement')
    if admission['inventoryHash'] != digest(canonical(inventory)) or admission['budgetHash'] != digest(canonical(budget)):
        raise ValueError('admission hash links differ')
    d = admission['demand']
    if d['counts'] != {'scientificTasks': 2, 'stubTasks': 2, 'remoteScientificCalls': 2 if remote else 0, 'retries': 0}:
        raise ValueError('unexpected deterministic counts')
    if d['sourceBytes'] != (root / 'run/source.pdb').stat().st_size or d['selectionBytes'] != (root / 'run/selection.pdb').stat().st_size:
        raise ValueError('input byte count differs')
    base = {k: v for k, v in bundle['files'].items() if k not in {'inventory.json', 'budget.json', 'admission.json', 'protocol.json', 'validation.json'}}
    # validation.json is augmented after admission; its original size is recorded in countInputs.
    counted = sum((root / 'run' / k).stat().st_size for k in base) + m['countInputs']['validationBytes']
    if d['version'] == 'trp-resources/1.0.0':
        estimated = 64*1048576 + 4*d['bundleBytes'] + 4*d['selectionBytes']
    elif d['version'] in {'trp-resources/1.1.0', 'trp-resources/1.2.0'}:
        copies, headroom = (5, 14) if d['version'] == 'trp-resources/1.1.0' else (7, 12)
        numerator = headroom*1048576 + copies*d['bundleBytes'] + 4*d['selectionBytes']
        estimated = ((numerator + 4095) // 4096) * 4096
    else:
        raise ValueError('unknown resource estimator')
    if counted != d['bundleBytes'] or d['workBytes'] != estimated:
        raise ValueError('cold storage calculation differs')
    if record('specification.json')['structure']['value']['sha256'] != digest((root / 'run/source.pdb').read_bytes()):
        raise ValueError('source identity differs')
    for artifact in record('catalogue_evidence.json'):
        data = base64.b64decode(artifact['base64'], validate=True)
        if len(data) != artifact['bytes'] or digest(data) != artifact['sha256']:
            raise ValueError('catalogue reference differs')
    spec = record('specification.json')
    if digest(canonical(record('catalogue.json'))) != spec['catalogHash']:
        raise ValueError('catalogue identity differs')
    events = [parse(line) for line in (root / 'run/events.jsonl').read_bytes().splitlines()]
    for i, event in enumerate(events):
        if event['sequence'] != i or event['previous'] != (digest(canonical(events[i-1])) if i else None):
            raise ValueError('event sequence differs')
    run = record('run.json')
    if run['digest'] != bundle['digest']:
        raise ValueError('run identity differs')
    if run['status'] == 'succeeded':
        for name in ['approval.json', 'recheck.json', 'analysis-admission.json', 'software.json', 'processes.jsonl', 'trace.tsv', 'dry-run/trace.tsv', 'results/geometry.csv']:
            if 'run/' + name not in listed:
                raise ValueError('successful run lacks ' + name)
        if record('approval.json')['digest'] != bundle['digest'] or not record('recheck.json')['decision']['accepted']:
            raise ValueError('approval/admission differs')
        if not admission['accepted'] or not record('validation.json')['valid']:
            raise ValueError('run succeeded without accepted validation and admission')
        for name in ['recheck.json', 'analysis-admission.json']:
            r = record(name)
            if r['inventory'].get('enforcement') != inventory.get('enforcement'):
                raise ValueError('allocation changed during execution')
            if strict:
                if r['inventory'].get('remoteStrict') != allocated:
                    raise ValueError('strict allocation changed during execution')
                strict_receipt(r['inventory']['remoteStrictObservation'], allocated)
            if (not r['decision']['accepted'] or r['decision']['inventoryHash'] != digest(canonical(r['inventory']))
                    or r['decision']['budgetHash'] != admission['budgetHash'] or r['decision']['demand'] != d):
                raise ValueError('resource recheck differs')
        sources = [(e['source'], e['outcome']) for e in events]
        for required_event in [('permission', 'returned-allowed'), ('approval', 'answered'), ('execution', 'completed')]:
            if required_event not in sources:
                raise ValueError('missing successful gate event')
        if not sources.index(('permission', 'returned-allowed')) < sources.index(('approval', 'answered')) < sources.index(('execution', 'completed')):
            raise ValueError('gate event order differs')
        processes = [parse(line) for line in (root/'run/processes.jsonl').read_bytes().splitlines()]
        if not remote and (len(processes) != 6 or any(p.get('exitCode') != 0 for p in processes)):
            raise ValueError('successful controller command count differs')
        if remote:
            if strict:
                for name in ['remote-strict-start.json', 'remote-strict-before-science.json']:
                    if 'run/' + name not in listed:
                        raise ValueError('successful strict run lacks ' + name)
                    strict_receipt(record(name), allocated)
            for name in ['remote-terminal.json', 'remote-approved.json', 'remote-transfer.json', 'remote-processes.jsonl', 'remote-native-jobs.jsonl', 'remote-task-runtime.json']:
                if 'run/' + name not in listed:
                    raise ValueError('successful remote run lacks ' + name)
            approved = record('remote-approved.json')
            if approved['digest'] != bundle['digest'] or approved['files'] != bundle['files'] or approved['target'] != execution['target']:
                raise ValueError('remote approval links differ')
            terminal = record('remote-terminal.json')
            if terminal['digest'] != bundle['digest'] or terminal['status'] != 'succeeded':
                raise ValueError('remote terminal state differs')
            if record('remote-analysis-approval.json')['decision'] != record('analysis-admission.json')['decision']:
                raise ValueError('remote scientific admission handshake differs')
            for file in record('remote-transfer.json')['files']:
                if digest((root/'run'/safe_name(file['path'])).read_bytes()) != file['sha256']:
                    raise ValueError('remote retrieval hash differs')
            controller = [parse(line) for line in (root/'run/remote-processes.jsonl').read_bytes().splitlines()]
            if len(controller) != 4 or any(p.get('exitCode') != 0 for p in controller):
                raise ValueError('remote Nextflow controller commands differ')
            observations = record('remote-task-runtime.json')['records']
            if len(observations) != 2:
                raise ValueError('remote effective task observation count differs')
            for observation in observations:
                quota, period = map(int, observation['cpuMax'].split())
                if quota / period != 2 or int(observation['memoryMax']) != 2147483648 or int(observation['swapMax']) != 0 or observation['threads'] != '1':
                    raise ValueError('remote effective limits differ')
                if execution['numericalProfile'] == 'haswell-single-thread' and (observation['numericalProfile'] != 'Haswell' or not any(b.get('architecture') == 'Haswell' and b.get('num_threads') == 1 for b in observation['blas'])):
                    raise ValueError('remote BLAS profile differs')
            native = {}
            for line in (root/'run/remote-native-jobs.jsonl').read_bytes().splitlines():
                for job in parse(line)['records']:
                    if job['state'] == 'COMPLETED':
                        native[job['id']] = job
            for trace in ['trace.tsv', 'dry-run/trace.tsv']:
                lines = (root/'run'/trace).read_text().strip().splitlines()
                headers = lines[0].split('\t')
                for line in lines[1:]:
                    job_id = line.split('\t')[headers.index('native_id')]
                    if job_id not in native or 'Comment=helix:' + approved['id'] not in native[job_id]['source']:
                        raise ValueError('native Slurm completion/ownership not verified')
        if run['geometry']['sha256'] != digest((root / 'run/results/geometry.csv').read_bytes()):
            raise ValueError('result hash differs')
        for name, count in [('trace.tsv', 2), ('dry-run/trace.tsv', 2)]:
            rows = (root / 'run' / name).read_text().strip().splitlines()
            if len(rows) != count+1:
                raise ValueError('trace task count differs')
            headers = rows[0].split('\t')
            status, exit_code = headers.index('status'), headers.index('exit')
            if any(row.split('\t')[status] != 'COMPLETED' or row.split('\t')[exit_code] != '0' for row in rows[1:]):
                raise ValueError('trace task failed')
    methods = record('methods.json')
    required_methods = {'protein', 'chain', 'model', 'units', 'insertions', 'coordinate contract',
                        'GeomeTRe revision', 'parameter contract', 'input hash', 'engine', 'image', 'command',
                        'counts', 'storage estimate', 'status'}
    if run['status'] == 'succeeded':
        required_methods.add('Nextflow version output')
    if bundle['engine'] in {'trp-nextflow/1.2.0', 'trp-nextflow/1.3.0', 'trp-nextflow/1.4.0'}:
        required_methods.add('structural controls')
    if not required_methods <= {item['name'] for item in methods['fields']}:
        raise ValueError('methods fields missing')
    for item in methods['fields']:
        target = record(item['artifact'])
        for key in item['pointer']:
            target = target[key]
        if target != item['value']:
            raise ValueError('unsupported methods field: ' + item['name'])
    return {'ok': True, 'files': len(listed), 'bytes': total, 'manifestSha256': manifest_hash,
            'status': run['status'], 'externallyAnchored': expected is not None,
            'scope': 'integrity, declared links and cold counts; not biological accuracy or authorship'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('bundle')
    parser.add_argument('--sha256')
    args = parser.parse_args()
    try:
        result = verify(args.bundle, args.sha256)
    except (OSError, ValueError, KeyError, TypeError, RecursionError) as error:
        result = {'ok': False, 'error': str(error)}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if result['ok'] else 1)
