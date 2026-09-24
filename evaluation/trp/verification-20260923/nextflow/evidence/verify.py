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
        if len(controls) != len(expected_ids) or {c['id'] for c in controls} != expected_ids:
            raise ValueError('structural inventory differs')
        if structural['version'] != 'trp-structural/1.0.0' or structural['provenance']['structureSha256'] != digest((root / 'run/source.pdb').read_bytes()):
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
    if 'enforcement' in inventory:
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
    elif budget['requireHardStorageLimit']:
        raise ValueError('hard budget without enforcement')
    if admission['inventoryHash'] != digest(canonical(inventory)) or admission['budgetHash'] != digest(canonical(budget)):
        raise ValueError('admission hash links differ')
    d = admission['demand']
    if d['counts'] != {'scientificTasks': 2, 'stubTasks': 2, 'remoteScientificCalls': 0, 'retries': 0}:
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
        if len(processes) != 6 or any(p.get('exitCode') != 0 for p in processes):
            raise ValueError('successful controller command count differs')
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
