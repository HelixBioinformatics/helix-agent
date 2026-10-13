#!/usr/bin/env python3
"""Read-only delivery review of a dated campaign, including archive/SQLite data.

Known secrets are loaded only into process memory from private operator state.
No matched value, password, private key or secret fingerprint is ever reported.
Outputs are outside the inventoried input set; growing campaigns need a rerun.
"""
import argparse
import base64
import configparser
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import sqlite3
import subprocess
import tarfile
import tempfile
import urllib.parse
import zipfile

ROOT = Path(__file__).resolve().parents[2]
CAMPAIGN = ROOT / 'evaluation/trp/campaign-20261012'
REVIEW = CAMPAIGN / 'checks/versioning-content-review-20261013'
MAX_CONTAINER = 256 * 1024 ** 2
MAX_DEPTH = 4
PATTERNS = {
    'aws_access_key': re.compile(rb'(?<![A-Z0-9])(?:AKIA|ASIA)[A-Z0-9]{16}(?![A-Z0-9])'),
    'github_token': re.compile(rb'(?:gh[pousr]_[A-Za-z0-9]{20,255}|github_pat_[A-Za-z0-9_]{40,255})'),
    'openai_or_provider_key': re.compile(rb'(?<![A-Za-z0-9])sk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{20,255}'),
    'private_key_header': re.compile(rb'-----BEGIN (?:RSA |DSA |EC |OPENSSH |ENCRYPTED )?PRIVATE KEY-----'),
    'oauth_jwt_candidate': re.compile(rb'eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}'),
}
SECRET_FIELD = re.compile(r'(password|secret|token|authorization|private.?key|access.?key)', re.I)


def utc():
    return datetime.now(timezone.utc).isoformat()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + '\n')


def private_registry(extra_files=()):
    """Never returns secret values to a report; source metadata has counts only."""
    home = Path.home()
    files = [home / '.aws' / ('helix-academy-' + str(i) + '.credentials') for i in (1, 2)]
    files += [home / '.local/share/helix/auth.json', home / '.config/gh/hosts.yml']
    state = home / '.local/state/helix/aws-academy'
    for directory in ('cluster', 'cluster-185395'):
        files += [state / directory / name for name in ('ssh-ed25519', 'munge-key-base64', 'state.json', 'remote.json')]
    files += [Path(p).resolve() for p in extra_files]
    values, sources = {}, []

    def add(value, category):
        if isinstance(value, str): value = value.encode()
        if not isinstance(value, bytes) or len(value) < 8: return
        values.setdefault(value, category)

    def recurse(value, key='', parent=''):
        if isinstance(value, dict):
            for name, child in value.items(): recurse(child, str(name), key)
        elif isinstance(value, list):
            for child in value: recurse(child, key, parent)
        elif isinstance(value, str) and (SECRET_FIELD.search(key) or key.lower() in ('access', 'refresh')):
            add(value, 'private_auth_field')

    for path in dict.fromkeys(files):
        if not path.is_file(): continue
        raw = path.read_bytes()
        stat = path.stat()
        before = len(values)
        if path.name == 'ssh-ed25519':
            add(raw, 'private_ssh_file')
            lines = raw.splitlines()
            body = b''.join(line for line in lines if not line.startswith(b'-----'))
            add(body, 'private_ssh_payload')
        elif path.name == 'munge-key-base64':
            add(raw.strip(), 'private_munge_encoded')
            try: add(base64.b64decode(raw, validate=False), 'private_munge_binary')
            except Exception: pass
        elif path.suffix == '.json':
            try: recurse(json.loads(raw))
            except Exception: pass
        else:
            for line in raw.splitlines():
                if b'=' in line:
                    key, value = line.split(b'=', 1)
                    if SECRET_FIELD.search(key.decode(errors='replace')): add(value.strip(), 'private_credentials_field')
                elif b':' in line:
                    key, value = line.split(b':', 1)
                    if SECRET_FIELD.search(key.decode(errors='replace')): add(value.strip(), 'private_credentials_field')
        sources.append({'path': str(path), 'mtimeNs': stat.st_mtime_ns, 'bytes': stat.st_size,
                        'loadedValuesAdded': len(values) - before})
    original = list(values.items())
    for value, kind in original:
        add(base64.b64encode(value), kind + '_base64')
        try:
            text = value.decode('utf-8')
            add(json.dumps(text)[1:-1], kind + '_json_escaped')
            add(urllib.parse.quote(text, safe=''), kind + '_url_encoded')
        except UnicodeError: pass
    # Values exist only in this dictionary; the returned metadata contains none.
    return values, sources


class Scanner:
    def __init__(self, secrets, private_coordinates):
        self.secrets = secrets
        self.private_coordinates = private_coordinates
        self.findings, self.coordinates, self.archives, self.sqlite = [], [], [], []
        self.gaps, self.entities, self.archive_links = [], [], []
        self.seen = set()
        self.entity_bytes = 0

    def label(self, value):
        value = str(value)
        encoded = value.encode()
        if any(secret in encoded for secret in self.secrets): return '[redacted-path-' + sha(encoded)[:16] + ']'
        for regex in PATTERNS.values():
            if regex.search(encoded): return '[redacted-path-' + sha(encoded)[:16] + ']'
        return value

    def finding(self, path, kind, classification, offset=None):
        key = (path, kind, classification, offset)
        if key in self.seen: return
        self.seen.add(key)
        self.findings.append({'entity': self.label(path), 'kind': kind, 'classification': classification,
                              'offset': offset, 'matchedValueRecorded': False})

    def scan_raw(self, path, raw, offset=0):
        for secret, category in self.secrets.items():
            found = raw.find(secret)
            if found >= 0: self.finding(path, 'known_private_secret', 'confirmed_private_state_match:' + category, offset + found)
        for kind, regex in PATTERNS.items():
            for match in regex.finditer(raw):
                candidate = match.group()
                if any(secret == candidate or candidate in secret for secret in self.secrets):
                    classification = 'confirmed_private_state_value'
                elif any(word in candidate.lower() for word in (b'fixture', b'synthetic', b'example', b'placeholder', b'redacted')):
                    classification = 'explicit_nonproduction_fixture_spelling'
                elif kind == 'private_key_header':
                    tail = raw[match.end():match.end() + 8192]
                    end = re.search(rb'-----END [A-Z ]*PRIVATE KEY-----', tail)
                    body = tail[:end.start()] if end else tail
                    try:
                        decoded = base64.b64decode(re.sub(rb'\s', b'', body), validate=True)
                        classification = 'potential_private_key_material' if decoded.startswith((b'openssh-key-v1\0', b'0')) else 'unresolved_private_key_marker'
                    except Exception: classification = 'unresolved_private_key_marker'
                else:
                    classification = 'unresolved_pattern_candidate'
                self.finding(path, kind, classification, offset + match.start())

    def scan_bytes(self, path, raw, depth=0):
        digest = sha(raw)
        self.entities.append({'entity': self.label(path), 'sha256': digest, 'bytes': len(raw), 'depth': depth})
        self.entity_bytes += len(raw)
        if digest in self.private_coordinates:
            self.coordinates.append({'entity': self.label(path), 'sha256': digest,
                                     'privateReference': self.private_coordinates[digest]})
        self.scan_raw(path, raw)
        if depth > MAX_DEPTH:
            self.gaps.append({'entity': self.label(path), 'reason': 'maximum_nested_container_depth'})
            return
        if raw.startswith(b'SQLite format 3\0'): self.scan_sqlite(path, raw)
        if zipfile.is_zipfile(io.BytesIO(raw)):
            self.scan_zip(path, raw, depth)
        elif len(raw) > 262 and (raw[257:262] == b'ustar' or raw[:2] == b'\x1f\x8b'):
            self.scan_tar(path, raw, depth)
        if len(raw) <= 64 * 1024 ** 2 and raw.lstrip()[:1] in (b'{', b'['):
            try: obj = json.loads(raw)
            except Exception: return

            def fields(value, pointer=''):
                if isinstance(value, dict):
                    for key, child in value.items():
                        if isinstance(child, str) and str(key).lower().endswith('base64'):
                            try:
                                decoded = base64.b64decode(child, validate=True)
                                if len(decoded) <= MAX_CONTAINER: self.scan_bytes(path + '::json' + pointer + '/' + str(key), decoded, depth + 1)
                                else: self.gaps.append({'entity': self.label(path), 'reason': 'encoded_json_payload_limit'})
                            except Exception: pass
                        else: fields(child, pointer + '/' + str(key))
                elif isinstance(value, list):
                    for i, child in enumerate(value): fields(child, pointer + '/' + str(i))
            fields(obj)

    def scan_sqlite(self, path, raw):
        result = {'entity': self.label(path), 'sha256': sha(raw), 'tables': [], 'rows': 0,
                  'readOnlyMemoryInspection': True}
        db = sqlite3.connect(':memory:')
        try:
            db.deserialize(raw)
            db.execute('PRAGMA query_only=ON')
            db.execute('PRAGMA temp_store=MEMORY')
            tables = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")]
            for table in tables:
                count = 0
                quoted = '"' + table.replace('"', '""') + '"'
                for row in db.execute('SELECT * FROM ' + quoted):
                    for index, value in enumerate(row):
                        if isinstance(value, str): self.scan_raw(path + '::sqlite-row/' + str(count) + '/cell/' + str(index), value.encode())
                        elif isinstance(value, bytes): self.scan_raw(path + '::sqlite-row/' + str(count) + '/cell/' + str(index), value)
                    count += 1
                result['tables'].append({'name': self.label(table), 'rows': count})
                result['rows'] += count
        except Exception as exc:
            self.gaps.append({'entity': self.label(path), 'reason': 'sqlite_read_error:' + type(exc).__name__})
        finally: db.close()
        self.sqlite.append(result)

    def scan_tar(self, path, raw, depth):
        result = {'entity': self.label(path), 'sha256': sha(raw), 'compressedBytes': len(raw),
                  'members': 0, 'fileMembers': 0, 'expandedBytes': 0, 'duplicateExtractedMembers': 0}
        try:
            with tarfile.open(fileobj=io.BytesIO(raw), mode='r:*') as archive:
                for member in archive:
                    result['members'] += 1
                    name = PurePosixPath(member.name)
                    label = path + '::tar/' + member.name
                    if name.is_absolute() or '..' in name.parts:
                        self.archive_links.append({'entity': self.label(label), 'kind': 'unsafe_archive_member_path'})
                    if member.issym() or member.islnk():
                        if PurePosixPath(member.linkname).is_absolute() or '..' in PurePosixPath(member.linkname).parts:
                            self.archive_links.append({'entity': self.label(label), 'kind': 'external_or_relative_archive_link',
                                                       'automaticExtractionAuthorized': False})
                    if not member.isfile(): continue
                    result['fileMembers'] += 1
                    result['expandedBytes'] += member.size
                    if member.size > MAX_CONTAINER:
                        self.gaps.append({'entity': self.label(label), 'reason': 'archive_member_memory_limit', 'bytes': member.size})
                        continue
                    stream = archive.extractfile(member)
                    self.scan_bytes(label, stream.read(), depth + 1)
        except Exception as exc:
            self.gaps.append({'entity': self.label(path), 'reason': 'tar_read_error:' + type(exc).__name__})
        self.archives.append(result)

    def scan_zip(self, path, raw, depth):
        result = {'entity': self.label(path), 'sha256': sha(raw), 'compressedBytes': len(raw),
                  'members': 0, 'fileMembers': 0, 'expandedBytes': 0, 'duplicateExtractedMembers': 0}
        try:
            with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                for member in archive.infolist():
                    result['members'] += 1
                    if member.is_dir(): continue
                    result['fileMembers'] += 1
                    result['expandedBytes'] += member.file_size
                    label = path + '::zip/' + member.filename
                    if member.file_size > MAX_CONTAINER:
                        self.gaps.append({'entity': self.label(label), 'reason': 'archive_member_memory_limit', 'bytes': member.file_size})
                        continue
                    self.scan_bytes(label, archive.read(member), depth + 1)
        except Exception as exc:
            self.gaps.append({'entity': self.label(path), 'reason': 'zip_read_error:' + type(exc).__name__})
        self.archives.append(result)


def review(campaign, output, extras):
    output = output.resolve()
    if output.exists(): raise ValueError('Output already exists; preserve previous review snapshots')
    output.mkdir(parents=True)
    secrets, private_sources = private_registry(extras)
    cases = json.loads((campaign / 'structural/cases.json').read_text())
    coordinates = {}
    for case in cases:
        if case['group'] != 'pratt-original': continue
        file = Path(case['coordinatePath'])
        digest = hashlib.file_digest(file.open('rb'), 'sha256').hexdigest()
        if digest != case['coordinateSha256']: raise ValueError('Private coordinate baseline changed')
        coordinates[digest] = case['id']
    assert len(coordinates) == 78
    start = utc()
    paths = sorted(p for p in campaign.rglob('*') if p.is_file() and not p.is_relative_to(REVIEW))
    initial = [{'path': str(p.relative_to(ROOT)), 'bytes': p.stat().st_size, 'mtimeNs': p.stat().st_mtime_ns,
                'inode': p.stat().st_ino} for p in paths]
    protocol = {'schema': 'campaign-content-review/1.0', 'startedUTC': start, 'campaign': str(campaign.relative_to(ROOT)),
                'scannerSha256': sha(Path(__file__).read_bytes()), 'initialFiles': len(initial),
                'knownPrivateStateSources': private_sources, 'knownValueVariantsInMemory': len(secrets),
                'privatePrattCoordinateHashes': len(coordinates), 'maxNestedDepth': MAX_DEPTH,
                'maxContainerMemberBytes': MAX_CONTAINER, 'noExtractionToDisk': True,
                'valuesRecorded': False, 'passwordExactMatchingLimitedToIdentifiedPrivateFiles': True,
                'allArbitraryPasswordsDetectable': False, 'campaignMayGrow': True}
    save(output / 'protocol.json', protocol)
    scanner = Scanner(secrets, coordinates)
    snapshots, failures, changed = [], [], []
    for i, record in enumerate(initial):
        p = ROOT / record['path']
        try:
            with p.open('rb') as stream: raw = stream.read(record['bytes'])
            scanner.scan_bytes(record['path'], raw)
            now = p.stat()
            stable = now.st_size == record['bytes'] and now.st_mtime_ns == record['mtimeNs'] and now.st_ino == record['inode'] and len(raw) == record['bytes']
            snapshots.append({**record, 'sha256': sha(raw), 'stableDuringRead': stable})
            if not stable: changed.append(record['path'])
        except Exception as exc:
            failures.append({'path': scanner.label(record['path']), 'reason': type(exc).__name__})
        if i and i % 3000 == 0: print(json.dumps({'progressFiles': i, 'initialFiles': len(initial)}), flush=True)
    # Matching extracted content is evidence of duplication, never deletion authority.
    direct = {}
    for r in snapshots: direct.setdefault(r['sha256'], []).append(r['path'])
    duplicate_members = []
    for r in scanner.entities:
        if r['depth'] and r['sha256'] in direct:
            duplicate_members.append({**r, 'existingExtractedPaths': direct[r['sha256']]})
    archives_anchored = {}
    archive_digests = {a['sha256'] for a in scanner.archives}
    for r in snapshots:
        if not r['path'].endswith('.json') or r['bytes'] > 64 * 1024 ** 2: continue
        try: text = (ROOT / r['path']).read_text()
        except Exception: continue
        for digest in archive_digests:
            if digest in text: archives_anchored.setdefault(digest, []).append(r['path'])
    for a in scanner.archives:
        a['duplicateExtractedMembers'] = sum(m['entity'].startswith(a['entity'] + '::') for m in duplicate_members)
        a['referencesToArchiveHash'] = archives_anchored.get(a['sha256'], [])
        a['deliveryRecommendation'] = 'preserve_raw_archive_and_anchors; extraction is duplicate if hashes match; no files were removed'
    tracked = subprocess.run(['git', 'ls-files', '-z', '--', str(campaign.relative_to(ROOT))], cwd=ROOT, capture_output=True, check=True).stdout.decode().split('\0')
    tracked = set(filter(None, tracked))
    ending_paths = {str(p.relative_to(ROOT)): (p.stat().st_size, p.stat().st_mtime_ns) for p in campaign.rglob('*') if p.is_file() and not p.is_relative_to(REVIEW)}
    initial_paths = {r['path'] for r in initial}
    mutations = {'addedAfterInventory': sorted(set(ending_paths) - initial_paths), 'removedAfterInventory': sorted(initial_paths - set(ending_paths)),
                 'changedDuringRead': changed, 'changedAfterInventory': [r['path'] for r in initial if r['path'] in ending_paths and ending_paths[r['path']] != (r['bytes'], r['mtimeNs'])]}
    confirmed = [f for f in scanner.findings if f['classification'].startswith('confirmed_private_state')]
    unresolved = [f for f in scanner.findings if f['classification'].startswith(('unresolved', 'potential'))]
    summary = {'schema': 'campaign-content-review-summary/1.0', 'startedUTC': start, 'finishedUTC': utc(),
               'initialFiles': len(initial), 'initialBytes': sum(r['bytes'] for r in initial), 'filesRead': len(snapshots),
               'entitiesIncludingArchiveAndDecodedPayloads': len(scanner.entities), 'entityBytesInspectedWithDuplicates': scanner.entity_bytes,
               'archivesInspected': len(scanner.archives), 'sqliteInspections': len(scanner.sqlite),
               'knownPrivateStateSources': len(private_sources), 'knownValueVariantsInMemory': len(secrets),
               'confirmedPrivateStateMatches': len(confirmed), 'unresolvedPatternCandidates': len(unresolved),
               'explicitNonproductionFixtureCandidates': sum(f['classification'] == 'explicit_nonproduction_fixture_spelling' for f in scanner.findings),
               'privatePrattOriginalCoordinateMatches': len(scanner.coordinates), 'filesOver100MiB': [r for r in snapshots if r['bytes'] > 100 * 1024 ** 2],
               'readFailures': failures, 'containerOrSQLiteCoverageGaps': scanner.gaps, 'campaignChanges': mutations,
               'finalCampaignCleanClaimed': False, 'valuesOrPrivateCoordinatesCopiedToReport': False,
               'productionWordCanonAwsOrFrozenArtifactsMutated': False, 'requiresFinalRepeat': True}
    save(output / 'snapshot.json', snapshots)
    save(output / 'findings.json', {'findings': scanner.findings, 'privateCoordinateMatches': scanner.coordinates, 'archiveLinks': scanner.archive_links})
    save(output / 'archives.json', scanner.archives)
    save(output / 'sqlite.json', scanner.sqlite)
    save(output / 'duplicate-content.json', duplicate_members)
    save(output / 'git-deliverability.json', {'trackedCampaignPaths': len(tracked), 'untrackedInventoryPaths': len(initial_paths - tracked),
        'totalInventoryBytes': summary['initialBytes'], 'filesOver100MiB': summary['filesOver100MiB'],
        'pycInventory': [r for r in snapshots if r['path'].endswith('.pyc')],
        'canonicalArchiveSelectionPerformed': False, 'noPrimaryEvidenceDiscarded': True,
        'recommendation': 'Review confirmed/unresolved findings before staging. Preserve raw measured archives and their anchors; choose deliverable extraction or archive only after all referencing manifests are audited, retaining immutable originals. No mutation authorized by this scan.'})
    save(output / 'summary.json', summary)
    print(json.dumps({k: v for k, v in summary.items() if k not in ('campaignChanges', 'filesOver100MiB', 'readFailures', 'containerOrSQLiteCoverageGaps')}, ensure_ascii=False), flush=True)


def self_test():
    # Artificial known values prove matching without copying real credentials.
    value = b'ASIAFIXTUREKEY0000000'
    coordinate = b'ATOM synthetic coordinate fixture\n'
    scanner = Scanner({value: 'synthetic_test_only'}, {sha(coordinate): 'synthetic_coordinate_only'})
    db = sqlite3.connect(':memory:')
    db.execute('CREATE TABLE fixture(value TEXT)')
    db.execute('INSERT INTO fixture VALUES (?)', (value.decode(),))
    raw_db = db.serialize(); db.close()
    archive = io.BytesIO()
    with tarfile.open(fileobj=archive, mode='w:gz') as t:
        for name, data in [('coordinate.pdb', coordinate), ('fixture.sqlite', raw_db), ('token.txt', value)]:
            member = tarfile.TarInfo(name); member.size = len(data); t.addfile(member, io.BytesIO(data))
    scanner.scan_bytes('synthetic-fixture.tar.gz', archive.getvalue())
    scanner.scan_bytes('synthetic-json', json.dumps({'base64': base64.b64encode(value).decode()}).encode())
    assert len(scanner.coordinates) == 1 and len(scanner.sqlite) == 1 and len(scanner.archives) == 1
    assert any('sqlite-row' in f['entity'] and f['kind'] == 'known_private_secret' for f in scanner.findings)
    assert any('::json' in f['entity'] and f['kind'] == 'known_private_secret' for f in scanner.findings)
    serialized = json.dumps(scanner.findings).encode()
    assert value not in serialized and coordinate not in serialized
    print(json.dumps({'selfTest': 'passed', 'syntheticOnly': True, 'archiveSqliteBase64AndPrivateHashDetection': True, 'matchedValuesOmitted': True}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--campaign', type=Path, default=CAMPAIGN)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--private-file', action='append', default=[])
    parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args()
    if args.self_test: self_test()
    else:
        output = args.output or REVIEW / ('snapshot-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
        review(args.campaign.resolve(), output, args.private_file)
