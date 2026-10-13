#!/usr/bin/env python3
"""Audit an explicit NUL-delimited Git candidate, with no input mutations.

Adds semantic private-coordinate checks to the immutable credential/container
scanner. Reports labels/counts/hashes only; never outputs matched bytes or xyz.
Whole-file PDB hash absence is explicitly not a derived-coordinate privacy proof.
"""
import argparse
import base64
import hashlib
import importlib.util
import io
import json
import math
import os
from pathlib import Path
import re
import sqlite3
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[2]
HELPER = Path(__file__).with_name('review_campaign_content.py')
EXPECTED_HELPER_SHA256 = '067b506c9e8359d3e2332cf8df67110dbcd2090e4574412bfd2a0413863cbbe7'
if hashlib.sha256(HELPER.read_bytes()).hexdigest() != EXPECTED_HELPER_SHA256:
    raise ValueError('Immutable scanner helper changed')
spec = importlib.util.spec_from_file_location('immutable_delivery_scanner', HELPER)
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
COORD_KEYS = {'xyz', 'atomxyz', 'coordinates', 'coordinate', 'coords', 'coord', 'centroid',
              'center', 'centre', 'centres', 'positions', 'position', 'atompositions',
              'atomcoordinates', 'cartesiancoordinates', 'cartesianxyz', 'sitescart'}
PRIVATE_PATH = re.compile(r'(?:^|[/])(?:pratt-original|AF2_models_PAE)(?:[/]|$)', re.I)


def key_normalized(key):
    return re.sub(r'[^a-z]', '', str(key).lower())


def number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def vector_count(value):
    if isinstance(value, list):
        if len(value) >= 3 and all(number(x) for x in value): return 1
        return sum(vector_count(x) for x in value if isinstance(x, (dict, list)))
    if isinstance(value, dict) and all(number(value.get(k)) for k in ('x', 'y', 'z')): return 1
    return 0


def pdb_atoms(raw):
    count = 0
    # PDB fixed columns distinguish data from a mere mention of ATOM/HETATM.
    for line in raw.splitlines():
        if line[:6] not in (b'ATOM  ', b'HETATM') or len(line) < 54: continue
        try:
            if not line[6:11].strip().isdigit() or not line[12:16].strip(): continue
            if all(math.isfinite(float(line[a:b])) for a, b in ((30,38),(38,46),(46,54))): count += 1
        except (ValueError, TypeError): pass
    return count


class SemanticScanner(base.Scanner):
    def __init__(self, secrets, private_coordinates, public_coordinates):
        super().__init__(secrets, private_coordinates)
        self.public_coordinates = public_coordinates
        self.coordinate_findings = []
        self.coordinate_seen = set()
        self.coordinate_allowed = []
        self.active_private_context = False
        self.active_public_context = False
        self.active_depth = 0

    def binding(self, path, raw):
        private = any(digest.encode() in raw for digest in self.private_coordinates) or bool(PRIVATE_PATH.search(str(path)))
        public = any(digest.encode() in raw for digest in self.public_coordinates)
        return private, public

    def coordinate(self, path, pointer, kind, count, private=False, public=False):
        classification = 'private_original_or_derived_coordinate_payload' if private else 'verified_public_coordinate_source' if public else 'unresolved_coordinate_origin'
        marker = (str(path), pointer, kind, classification)
        if marker in self.coordinate_seen: return
        self.coordinate_seen.add(marker)
        row = {'entity': self.label(path), 'field': self.label(pointer), 'kind': kind,
               'classification': classification, 'coordinateRecords': count,
               'coordinateValuesRecorded': False}
        if private or not public: self.coordinate_findings.append(row)
        else: self.coordinate_allowed.append(row)

    def inspect_semantic(self, path, raw, private=False, public=False, pointer='', depth=0):
        if depth > base.MAX_DEPTH:
            self.gaps.append({'entity': self.label(path), 'reason': 'semantic_nested_json_depth'})
            return
        ownprivate, ownpublic = self.binding(path, raw)
        private, public = private or ownprivate, public or ownpublic
        digest = base.sha(raw)
        if digest in self.private_coordinates:
            self.coordinate(path, pointer, 'exact_original_coordinate_bytes', 1, private=True)
        atom_count = pdb_atoms(raw)
        if atom_count:
            self.coordinate(path, pointer, 'pdb_fixed_column_atom_records', atom_count,
                            private, public or digest in self.public_coordinates)
        if len(raw) > 64 * 1024**2 or raw.lstrip()[:1] not in (b'{', b'['): return
        try: obj = json.loads(raw)
        except (ValueError, UnicodeError): return

        def walk(value, field):
            if isinstance(value, dict):
                if all(number(value.get(k)) for k in ('x', 'y', 'z')):
                    self.coordinate(path, field + '/{x,y,z}', 'numeric_cartesian_fields', 1, private, public)
                for key, child in value.items():
                    childfield = field + '/' + str(key)
                    count = vector_count(child) if key_normalized(key) in COORD_KEYS else 0
                    if count: self.coordinate(path, childfield, 'numeric_coordinate_field', count, private, public)
                    walk(child, childfield)
            elif isinstance(value, list):
                for index, child in enumerate(value): walk(child, field + '/' + str(index))
            elif isinstance(value, str):
                # Handles encoded log/SQLite JSON and PDB strings. Base64 binary
                # containers are independently traversed by the immutable helper.
                child = value.encode()
                if pdb_atoms(child) or child.lstrip()[:1] in (b'{', b'['):
                    self.inspect_semantic(path, child, private, public, field, depth + 1)
        walk(obj, pointer)

    def scan_raw(self, path, raw, offset=0):
        super().scan_raw(path, raw, offset)
        self.inspect_semantic(path, raw, self.active_private_context, self.active_public_context)

    def scan_bytes(self, path, raw, depth=0, sqlite_wal=None, private_context=False, public_context=False):
        old = self.active_private_context, self.active_public_context, self.active_depth
        # JSON binds descendant base64 payloads; binary archives/DBs must not bind
        # a public sibling to a private hash occurring elsewhere in the container.
        isjson = raw.lstrip()[:1] in (b'{', b'[')
        ownprivate, ownpublic = self.binding(path, raw) if isjson else (False, False)
        self.active_private_context = private_context or old[0] or ownprivate
        self.active_public_context = public_context or old[1] or ownpublic
        self.active_depth = depth
        try: super().scan_bytes(path, raw, depth, sqlite_wal)
        finally: self.active_private_context, self.active_public_context, self.active_depth = old

    def scan_sqlite(self, path, raw, wal=None):
        result = {'entity': self.label(path), 'sha256': base.sha(raw), 'tables': [], 'rows': 0,
                  'readOnlyMemoryInspection': True, 'originalJournalModeBytes': list(raw[18:20]),
                  'walSourceSha256': base.sha(wal) if wal is not None else None}
        db = sqlite3.connect(':memory:')
        try:
            inspected = bytearray(raw)
            if wal: inspected, result['walMemorySnapshot'] = base.sqlite_wal_snapshot(raw, wal)
            inspected[18] = inspected[19] = 1
            db.deserialize(bytes(inspected)); db.execute('PRAGMA temp_store=MEMORY'); db.execute('PRAGMA query_only=ON')
            tables = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")]
            for table in tables:
                cursor = db.execute('SELECT * FROM "' + table.replace('"', '""') + '"')
                names = [x[0] for x in cursor.description]; count = 0
                for row in cursor:
                    payloads = [v.encode() if isinstance(v, str) else v for v in row if isinstance(v, (str, bytes))]
                    private = any(self.binding(path, v)[0] for v in payloads)
                    public = any(self.binding(path, v)[1] for v in payloads)
                    field = '::sqlite/' + str(table) + '/row/' + str(count)
                    if all(k in names and number(row[names.index(k)]) for k in ('x','y','z')):
                        self.coordinate(path, field + '/{x,y,z}', 'sqlite_cartesian_columns', 1, private, public)
                    for index, value in enumerate(row):
                        cell = str(path) + field + '/cell/' + str(index)
                        if isinstance(value, str): value = value.encode()
                        if isinstance(value, bytes):
                            self.scan_bytes(cell, value, self.active_depth + 1, private_context=private, public_context=public)
                            if key_normalized(names[index]) in COORD_KEYS:
                                try: points = vector_count(json.loads(value))
                                except (ValueError, UnicodeError): points = 0
                                if points: self.coordinate(path, field + '/' + names[index], 'sqlite_coordinate_column', points, private, public)
                    count += 1
                result['tables'].append({'name': self.label(table), 'rows': count}); result['rows'] += count
        except Exception as exc:
            self.gaps.append({'entity': self.label(path), 'reason': 'sqlite_semantic_read_error:' + type(exc).__name__})
        finally: db.close()
        self.sqlite.append(result)


def registry(campaign):
    cases = json.loads((campaign / 'structural/cases.json').read_text())
    private, public = {}, {}
    for case in cases:
        file = Path(case['coordinatePath'])
        with file.open('rb') as stream: digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        if digest != case['coordinateSha256']: raise ValueError('Coordinate baseline changed')
        (private if case['group'] == 'pratt-original' else public)[digest] = case['id']
    if len(private) != 78:
        raise ValueError('Expected exactly78 original private coordinate baselines')
    # Public scoring PDBs are transformed from the allowed public structures.
    # Verify their actual bytes against the same frozen case, not a filename claim.
    for case in cases:
        if case['group'] == 'pratt-original': continue
        file = Path(case['scoreInputPath'])
        with file.open('rb') as stream: digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        if digest != case['scoreInputSha256'] or digest in private:
            raise ValueError('Public score input binding changed or equals a private original')
        public[digest] = case['id'] + '-public-score-input'
    # This publicly downloaded RCSB reference is already recorded by the thesis.
    reference = ROOT / 'evaluation/trp/reference/coordinate-20260921/2xqh.pdb'
    if reference.exists(): public[base.sha(reference.read_bytes())] = 'public-RCSB-2XQH'
    return private, public



def public_aliases(index, private, public):
    if index is None: return None
    raw = index.read_bytes(); metadata = json.loads(raw)
    if metadata.get('schema') != 'helix-coordinate-origin-qualified-aliases/1.0':
        raise ValueError('Unknown public coordinate lineage schema')
    for entry in metadata['entries']:
        digest = entry['source']['sha256']
        if digest in private:
            raise ValueError('A private original cannot be made public by an alias')
        if entry['kind'] not in ('synthetic-public-template-transform', 'public-RCSB-2XQH'):
            raise ValueError('Unqualified coordinate lineage kind')
        if not entry.get('evidence'): raise ValueError('No source evidence for public alias')
        for witness in [entry['source'], *entry['evidence']]:
            file = ROOT / witness['path']
            if not file.is_file() or file.is_symlink() or not file.resolve().is_relative_to(ROOT):
                raise ValueError('Public lineage source is not an ordinary repository file')
            with file.open('rb') as stream: found = hashlib.file_digest(stream, 'sha256').hexdigest()
            if found != witness['sha256']: raise ValueError('Public lineage source bytes changed')
        public[digest] = entry['id']
    return {'path':str(index), 'sha256':base.sha(raw), 'entries':len(metadata['entries']),
            'scope':'Explicit source/evidence files hash-verified; source qualification is operator-reviewed, not inferred from names.'}


def audit(selected, output, campaign, public_reference_index=None):
    if output.exists(): raise ValueError('Output already exists; preserve previous audits')
    output.mkdir(parents=True)
    rawselection = selected.read_bytes()
    if rawselection and not rawselection.endswith(b'\0'): raise ValueError('Selection must be NUL-delimited including last path')
    names = [os.fsdecode(x) for x in rawselection.split(b'\0') if x]
    if len(names) != len(set(names)): raise ValueError('Duplicate candidate paths')
    private, public = registry(campaign)
    lineage = public_aliases(public_reference_index, private, public)
    secrets, private_sources = base.private_registry()
    scanner = SemanticScanner(secrets, private, public)
    snapshots, failures = [], []
    for index, name in enumerate(names):
        file = ROOT / name
        if file.is_symlink() or not file.is_file() or not file.resolve().is_relative_to(ROOT) or Path(name).is_absolute() or '..' in Path(name).parts:
            failures.append({'entity': scanner.label(name), 'reason': 'outside_or_nonordinary_candidate'}); continue
        before = file.stat()
        try:
            raw = file.read_bytes(); walfile = Path(str(file)+'-wal')
            wal = walfile.read_bytes() if raw.startswith(b'SQLite format 3\0') and walfile.is_file() and not walfile.is_symlink() else None
            scanner.scan_bytes(name, raw, sqlite_wal=wal)
            after = file.stat(); stable = (before.st_size,before.st_mtime_ns,before.st_ino)==(after.st_size,after.st_mtime_ns,after.st_ino)
            snapshots.append({'path':scanner.label(name),'sha256':base.sha(raw),'bytes':len(raw),'stableDuringRead':stable})
        except Exception as exc: failures.append({'entity':scanner.label(name),'reason':type(exc).__name__})
        if index and index % 5000 == 0: print(json.dumps({'progressFiles':index,'candidateFiles':len(names)}),flush=True)
    confirmed = [f for f in scanner.findings if f['classification'].startswith('confirmed_private_state')]
    unresolved = [f for f in scanner.findings if f['classification'].startswith(('unresolved','potential'))]
    privatecoords = [f for f in scanner.coordinate_findings if f['classification']=='private_original_or_derived_coordinate_payload']
    unknowncoords = [f for f in scanner.coordinate_findings if f['classification']=='unresolved_coordinate_origin']
    eligible = not (confirmed or unresolved or privatecoords or unknowncoords or scanner.coordinates or scanner.gaps or failures or any(not x['stableDuringRead'] for x in snapshots))
    summary={'schema':'helix-selected-git-content-audit/1.0','finishedUTC':base.utc(),'candidateFiles':len(names),'candidateBytes':sum(x['bytes'] for x in snapshots),'candidateSelectionSha256':base.sha(rawselection),'auditorSha256':base.sha(Path(__file__).read_bytes()),'immutableScannerSha256':EXPECTED_HELPER_SHA256,'knownPrivateStateSources':len(private_sources),'knownValueVariantsInMemory':len(secrets),'privateOriginalReferenceHashes':len(private),'publicReferenceHashes':len(public),'publicLineageIndex':lineage,'confirmedPrivateCredentialFindings':len(confirmed),'unresolvedCredentialFindings':len(unresolved),'exactPrivateOriginalMatches':len(scanner.coordinates),'privateDerivedCoordinateFindings':len(privatecoords),'unresolvedCoordinateOrigins':len(unknowncoords),'verifiedPublicCoordinateFindings':len(scanner.coordinate_allowed),'archivesInspected':len(scanner.archives),'sqliteInspected':len(scanner.sqlite),'inspectionGaps':len(scanner.gaps),'inputFailures':len(failures),'unstableInputs':sum(not x['stableDuringRead'] for x in snapshots),'eligibleUnderAuditedScope':eligible,'allArbitrarySecretsOrTransformedCoordinatesDetectable':False,'noCoordinateValuesOrSecretsRecorded':True,'originalFilesChanged':False,'scope':'Explicit candidate only, not full campaign or final Git index; SHA absence alone is not a coordinate privacy proof'}
    base.save(output/'summary.json',summary);base.save(output/'snapshot.json',snapshots)
    base.save(output/'findings.json',{'credentials':scanner.findings,'coordinates':scanner.coordinate_findings,'exactOriginalMatches':scanner.coordinates,'gaps':scanner.gaps,'inputFailures':failures})
    # Compress repeated entity labels while retaining every field/count association.
    grouped = {}
    for row in scanner.coordinate_allowed:
        key = (row['entity'],row['kind'],row['classification'])
        item = grouped.setdefault(key, {'entity':row['entity'],'kind':row['kind'],
            'classification':row['classification'],'fields':[], 'coordinateValuesRecorded':False})
        item['fields'].append({'field':row['field'],'coordinateRecords':row['coordinateRecords']})
    base.save(output/'public-coordinate-sources.json',{'schema':'grouped-coordinate-source-fields/1.0','recordCount':len(scanner.coordinate_allowed),'groups':list(grouped.values())})
    base.save(output/'containers.json',{'archives':scanner.archives,'sqlite':scanner.sqlite})
    print(json.dumps(summary));return 0 if eligible else 2


def self_test():
    private = base.sha(b'synthetic-original-coordinate-data');public=base.sha(b'synthetic-public-coordinate-data')
    scanner=SemanticScanner({}, {private:'synthetic-private'}, {public:'synthetic-public'})
    privatejson=json.dumps({'inputSha256':private,'flat_results':[{'atomXYZ':[1.234,2.345,3.456]}]}).encode()
    scanner.scan_bytes('private-derived.json',privatejson)
    scanner.scan_bytes('public-derived.json',json.dumps({'inputSha256':public,'xyz':[7.123,8.234,9.345]}).encode())
    scanner.scan_bytes('unknown-origin.json',b'{"xyz":[4.321,5.432,6.543]}')
    db=sqlite3.connect(':memory:');db.execute('CREATE TABLE coord(source TEXT, xyz TEXT)');db.execute('INSERT INTO coord VALUES (?,?)',(private,'[1.234,2.345,3.456]'));db.commit();blob=db.serialize();db.close();scanner.scan_bytes('sqlite-private',blob)
    tar=io.BytesIO()
    with tarfile.open(fileobj=tar,mode='w:gz') as archive:
        member=tarfile.TarInfo('derived.json');member.size=len(privatejson);archive.addfile(member,io.BytesIO(privatejson))
    scanner.scan_bytes('nested.tar.gz',tar.getvalue())
    scanner.scan_bytes('encoded.json',json.dumps({'inputSha256':private,'payloadBase64':base64.b64encode(privatejson).decode()}).encode())
    kinds={f['kind'] for f in scanner.coordinate_findings}; assert 'numeric_coordinate_field' in kinds and 'sqlite_coordinate_column' in kinds
    assert len(scanner.coordinate_allowed)==1
    atom=b'ATOM      1  CA  ALA A   1       1.234   2.345   3.456  1.00 90.00           C\n'
    assert pdb_atoms(atom)==1
    scanner.scan_bytes('private-stderr.json',json.dumps({'inputSha256':private,'stderr':atom.decode()}).encode())
    scanner.scan_bytes('unbound-pdb-log.txt',atom)
    scanner.public_coordinates[base.sha(atom)]='synthetic-public-pdb'
    scanner.scan_bytes('public-coordinate.pdb',atom)
    assert any(f['kind']=='pdb_fixed_column_atom_records' and f['classification']=='private_original_or_derived_coordinate_payload' for f in scanner.coordinate_findings)
    assert any(f['kind']=='pdb_fixed_column_atom_records' and f['classification']=='unresolved_coordinate_origin' for f in scanner.coordinate_findings)
    assert len(scanner.coordinate_allowed)==2
    assert any(f['classification']=='unresolved_coordinate_origin' for f in scanner.coordinate_findings)
    assert any('::tar/' in f['entity'] for f in scanner.coordinate_findings)
    assert not scanner.gaps,scanner.gaps
    report=json.dumps(scanner.coordinate_findings);assert all(s not in report for s in ['1.234','2.345','3.456','4.321','5.432','6.543'])
    with tempfile.TemporaryDirectory() as folder:
        index=Path(folder)/'private-alias.json'
        index.write_text(json.dumps({'schema':'helix-coordinate-origin-qualified-aliases/1.0',
            'entries':[{'source':{'sha256':private},'kind':'synthetic-public-template-transform','evidence':[{'path':'unused'}]}]}))
        try: public_aliases(index,{private:'synthetic-private'}, {})
        except ValueError as error: assert 'private original' in str(error)
        else: raise AssertionError('A private hash was relabeled public')
    assert any(f['classification']=='private_original_or_derived_coordinate_payload' for f in scanner.coordinate_findings)
    assert any(f['classification']=='unresolved_coordinate_origin' for f in scanner.coordinate_findings)
    print(json.dumps({'selfTest':'passed','syntheticOnly':True,'privateHashJsonSqliteArchiveBase64':True,'publicSourcesRemainAllowed':True,'unlinkedCoordinatesRemainUnresolved':True,'numericCoordinateValuesRecorded':False}))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--selected-nul',type=Path);parser.add_argument('--output',type=Path)
    parser.add_argument('--campaign',type=Path,default=ROOT/'evaluation/trp/campaign-20261012')
    parser.add_argument('--public-reference-index',type=Path)
    parser.add_argument('--self-test',action='store_true');args=parser.parse_args()
    if args.self_test:self_test()
    else:
        if args.selected_nul is None or args.output is None:parser.error('--selected-nul and --output are required')
        raise SystemExit(audit(args.selected_nul.resolve(),args.output.resolve(),args.campaign.resolve(),args.public_reference_index.resolve() if args.public_reference_index else None))
