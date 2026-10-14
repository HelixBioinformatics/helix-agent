"""Synthetic coordinate contracts, not experimental biological reference labels."""
import importlib.machinery
import importlib.util
import json
import math
from pathlib import Path
import sys
import unittest

SOURCE = Path(__file__).resolve().parents[2] / 'src/trp/physical_diagnostic.py.txt'
loader = importlib.machinery.SourceFileLoader('physical_warning', str(SOURCE))
spec = importlib.util.spec_from_loader(loader.name, loader)
physical = importlib.util.module_from_spec(spec)
loader.exec_module(physical)


def pdb_atom(serial, atom, residue, chain, number, point, element, hetero=False, charge=''):
    return f'{"HETATM" if hetero else "ATOM  "}{serial:5d} {atom:>4s} {residue:3s} {chain:1s}{number:4d}    {point[0]:8.3f}{point[1]:8.3f}{point[2]:8.3f}{1:6.2f}{90:6.2f}          {element:>2s}{charge:>2s}'


def fixture(kind='charge'):
    lines = []

    def atom(name, residue, chain, number, point, element, hetero=False, charge=''):
        lines.append(pdb_atom(len(lines) + 1, name, residue, chain, number, point, element, hetero, charge))

    asp_positions = []
    for index in range(26):
        if index in (5, 10, 15, 20):
            z = (index // 5 - 1) * 4.8
            asp_positions.append((index + 1, z))
            points = {'N': (-3, 1, z), 'CA': (-3, 0, z), 'C': (-4.5, 0, z), 'O': (-5.5, 0, z),
                      'CB': (-1.6, 0, z), 'CG': (-0.2, 0, z), 'OD1': (0.8, 0.6, z), 'OD2': (0.8, -0.6, z)}
            if kind == 'hydrophobic':
                points = {n: p for n, p in points.items() if n in ('N', 'CA', 'C', 'O', 'CB')}
            for name, point in points.items():
                if kind == 'missing' and index == 10 and name == 'OD1':
                    continue
                atom(name, 'ALA' if kind == 'hydrophobic' else 'ASP', 'A', index + 1, point, 'N' if name == 'N' else 'O' if name.startswith('O') else 'C')
        else:
            x = 100 + index * 8
            for name, point in {'N': (x - 1.4, 0, 0), 'CA': (x, 0, 0), 'C': (x + 1.5, 0, 0), 'O': (x + 2.4, 0.8, 0)}.items():
                atom(name, 'GLY', 'A', index + 1, point, 'N' if name == 'N' else 'O' if name == 'O' else 'C')
    if kind not in ('exposed', 'hydrophobic'):
        counter = 0
        for _, z in asp_positions:
            # A synthetic carbon cage controls solvent exposure without supplying countercharge.
            for i in range(72):
                y = 1 - 2 * (i + 0.5) / 72
                r = math.sqrt(1 - y * y)
                theta = math.pi * (3 - math.sqrt(5)) * i
                point = (0.8 + 3.0 * r * math.cos(theta), 3.0 * y, z + 3.0 * r * math.sin(theta))
                counter += 1
                atom('CB', 'ALA', 'B', counter, point, 'C')
    if kind in ('calcium', 'iron-unknown', 'iron-explicit'):
        for number, z in enumerate((2.4, 12.0), 1):
            element = 'CA' if kind == 'calcium' else 'FE'
            atom(element, element, 'I', number, (0.8, 0, z), element, True, '2+' if kind == 'iron-explicit' else '')
    if kind == 'histidine':
        for number, (_, z) in enumerate(asp_positions, 1):
            atom('NE2', 'HIS', 'H', number, (0.8, 2, z), 'N')
    if kind == 'terminal':
        # Each separate chain contributes a terminal nitrogen close to a candidate.
        for chain, (_, z) in zip('CDEF', asp_positions):
            atom('N', 'GLY', chain, 1, (0.8, 2, z), 'N')
    return {'structure': '\n'.join(lines) + '\nEND\n',
            'options': {'format': 'pdb', 'model': 1, 'chain': 'A', 'frame': 'auth_seq_id',
                        'units': [{'start': 1, 'end': 13}, {'start': 14, 'end': 26}]}}


def segmented_cif(ambiguous=False):
    request = fixture('calcium')
    fields = ['group_PDB', 'id', 'type_symbol', 'label_atom_id', 'label_alt_id', 'label_comp_id', 'label_asym_id',
              'label_entity_id', 'label_seq_id', 'pdbx_PDB_ins_code', 'Cartn_x', 'Cartn_y', 'Cartn_z',
              'occupancy', 'B_iso_or_equiv', 'auth_seq_id', 'auth_comp_id', 'auth_asym_id', 'auth_atom_id', 'pdbx_PDB_model_num']
    rows = []
    for line in request['structure'].splitlines():
        if not line.startswith(('ATOM  ', 'HETATM')):
            continue
        chain = line[21:22]
        name, residue, number = line[12:16].strip(), line[17:20].strip(), line[22:26].strip()
        atom = [line[:6].strip(), str(len(rows) + 1), line[76:78].strip(), name, '.', residue, chain,
                '1' if chain == 'A' else '2' if chain == 'B' else '3', number if chain != 'I' else '.', '?',
                line[30:38].strip(), line[38:46].strip(), line[46:54].strip(), '1', '90', number, residue,
                chain if chain != 'I' else 'A', name, '1']
        rows.append(atom)
    rows.append(['HETATM', str(len(rows) + 1), 'O', 'O', '.', 'HOH', 'W', '4', '.', '?', '1000', '0', '0', '1', '0', '1001', 'HOH', 'A', 'O', '1'])
    if ambiguous:
        duplicate = [row.copy() for row in rows if row[6] == 'A']
        for row in duplicate:
            row[1] = str(len(rows) + 1)
            row[6], row[7] = 'X', '5'
            rows.append(row)
    request['structure'] = 'data_synthetic\nloop_\n' + '\n'.join('_atom_site.' + name for name in fields) + '\n' + '\n'.join(' '.join(row) for row in rows) + '\n'
    request['options']['format'] = 'mmcif'
    return request


class MoietyRepresentation(unittest.TestCase):
    def column(self, first=0.01, second=0.01, whole=0.75):
        return [{'key': f'A:{i}:LYS', 'index': i * 5, 'points': [(0, 0, i * 4.8)], 'sign': 1,
                 'complete': True, 'relativeSidechainArea': whole, 'chargedGroupArea': 0.1,
                 'relativePolarMoietyArea1p4': first, 'relativePolarMoietyArea2p0': second,
                 'uncertainty': []} for i in range(4)]

    def test_exposed_alkyl_chain_cannot_veto_buried_polar_group(self):
        buried, columns = physical.charge_columns(self.column(whole=0.75), [])
        self.assertEqual(len(buried), 4)
        self.assertTrue(columns[0]['alert'])

    def test_buried_methylene_cannot_hide_exposed_terminal_group(self):
        buried, columns = physical.charge_columns(self.column(first=.5, second=.4, whole=0), [])
        self.assertEqual(buried, [])
        self.assertEqual(columns, [])

    def test_both_probe_conditions_required_including_boundaries(self):
        buried, _ = physical.charge_columns(self.column(first=.08, second=.02), [])
        self.assertEqual(len(buried), 4)
        self.assertEqual(physical.charge_columns(self.column(first=.08001, second=0), [])[0], [])
        self.assertEqual(physical.charge_columns(self.column(first=0, second=.02001), [])[0], [])

    def test_independent_reference_geometries_reproduce_both_probes(self):
        import freesasa
        import gemmi
        reference = Path(__file__).resolve().parents[4] / 'evaluation/trp/followup-20261014/physical'
        classifier = freesasa.Classifier.getStandardClassifier('protor')
        for name, group in physical.GROUP.items():
            structure = gemmi.read_pdb(str(reference / 'sources' / f'freesasa-reference-{name}.pdb'))
            atoms = [(r, a) for c in structure[0] for r in c for a in r if not a.element.is_hydrogen]
            coordinates = [v for _, a in atoms for v in (a.pos.x, a.pos.y, a.pos.z)]
            radii = [classifier.radius(r.name, a.name.strip()) for r, a in atoms]
            for probe in (1.4, 2.0):
                areas = freesasa.calcCoord(coordinates, radii, freesasa.Parameters(
                    {'algorithm': freesasa.LeeRichards, 'probe-radius': probe, 'n-slices': 20, 'n-threads': 1}))
                observed = sum(areas.atomArea(i) for i, (r, a) in enumerate(atoms)
                               if r.seqid.num == 2 and a.name.strip() in group)
                self.assertAlmostEqual(observed, physical.RULES['referenceMoietyAreaAngstromSquared'][name][str(probe)], places=9)

    def test_real_surface_calculation_buried_NZ_exposed_alkyl(self):
        request = fixture()
        lines = []
        for line in request['structure'].splitlines():
            if line.startswith('ATOM') and line[17:20] == 'ASP':
                atom = line[12:16].strip()
                if atom == 'OD2':
                    continue
                line = line[:17] + 'LYS' + line[20:]
                if atom == 'OD1':
                    line = line[:12] + f'{"NZ":>4s}' + line[16:38] + f'{0.:8.3f}' + line[46:76] + ' N'
                lines.append(line)
                if atom == 'CG':
                    number = int(line[22:26]); z = float(line[46:54])
                    for name, x in [('CD', -6), ('CE', -8)]:
                        lines.append(pdb_atom(9000 + len(lines), name, 'LYS', 'A', number, (x, 0, z), 'C'))
            else:
                lines.append(line)
        request['structure'] = '\n'.join(lines) + '\n'
        report = physical.measure(request)
        lys = [g for g in report['chargedResidueObservations'] if g['key'].endswith(':LYS')]
        self.assertEqual(len(lys), 4)
        self.assertTrue(all(g['relativeSidechainArea'] > .05 for g in lys))
        self.assertTrue(all(g['relativePolarMoietyArea1p4'] <= .08 and g['relativePolarMoietyArea2p0'] <= .02 for g in lys))
        self.assertTrue(report['measurement']['chargeAlert'])


class ChargeMatching(unittest.TestCase):
    def groups(self, count=4):
        return [{'key': f'A:{i}:ASP', 'index': i * 5, 'points': [(0, 0, i * 2)], 'sign': -1,
                 'complete': True, 'relativeSidechainArea': 0, 'chargedGroupArea': 0,
                 'relativePolarMoietyArea1p4': 0, 'relativePolarMoietyArea2p0': 0, 'uncertainty': []}
                for i in range(count)]

    def test_one_calcium_cannot_veto_four_group_column(self):
        groups = self.groups()
        ion = {'key': 'Ca:1', 'points': [(0, 0, 3)], 'capacity': 2, 'sign': 1, 'cutoff': 3, 'kind': 'observed-positive-ion'}
        _, columns = physical.charge_columns(groups, [ion])
        self.assertEqual(len(columns), 1)
        self.assertEqual(len(columns[0]['possibleCompensation']), 2)
        self.assertEqual(len(columns[0]['uncompensatedResidues']), 2)
        self.assertTrue(columns[0]['alert'])

    def test_capacity_is_not_reused_between_components(self):
        groups = self.groups(6)
        for i, group in enumerate(groups):
            group['points'] = [(i % 3, 0, 0 if i < 3 else 11)]
        ion = {'key': 'Ca:1', 'points': [(1, 0, 5.5)], 'capacity': 2, 'sign': 1, 'cutoff': 6, 'kind': 'test-resource'}
        assigned = physical.assign_compensators(groups, [ion])
        self.assertEqual(len(assigned), 2)

    def test_opposite_charge_compensates_one_group_only(self):
        groups = self.groups()
        counter = {'key': 'B:1:LYS', 'points': [(0, 0, 3)], 'capacity': 1, 'sign': 1, 'cutoff': 4, 'kind': 'nominal-opposite-protein-charge'}
        _, columns = physical.charge_columns(groups, [counter])
        self.assertEqual(len(columns[0]['possibleCompensation']), 1)
        self.assertTrue(columns[0]['alert'])

    def test_triangle_is_not_a_column(self):
        groups = self.groups(3)
        for group, point in zip(groups, [(0, 0, 0), (5, 0, 0), (2.5, math.sqrt(18.75), 0)]):
            group['points'] = [point]
        self.assertEqual(physical.charge_columns(groups, [])[1], [])

    def test_exposed_groups_do_not_alert(self):
        groups = self.groups()
        for group in groups:
            group['relativeSidechainArea'] = 0.8
            group['relativePolarMoietyArea1p4'] = 0.8
            group['relativePolarMoietyArea2p0'] = 0.8
        self.assertEqual(physical.charge_columns(groups, [])[1], [])


class PackingGeometry(unittest.TestCase):
    def atoms(self, positions, element='C', name='CB', residue='ALA'):
        return [{'key': f'A:{i * 5}:{residue}:{name}', 'residueKey': f'A:{i * 5}:{residue}', 'index': i * 5,
                 'point': p, 'element': element, 'name': name, 'residueName': residue, 'ordinal': i}
                for i, p in enumerate(positions)]

    def test_three_disjoint_nonlocal_collisions_alert(self):
        atoms = self.atoms([(0, 0, 0), (1, 0, 0), (20, 0, 0), (21, 0, 0), (40, 0, 0), (41, 0, 0)])
        result = physical.packing_conflicts(atoms)
        self.assertTrue(result['alert'])
        self.assertEqual(result['disjointResiduePairs'], 3)

    def test_single_bad_residue_is_not_three_independent_conflicts(self):
        atoms = self.atoms([(0, 0, 0), (2, 0, 0), (-2, 0, 0), (0, 2, 0)])
        result = physical.packing_conflicts(atoms)
        self.assertEqual(result['nonlocalResiduePairs'], 3)
        self.assertEqual(result['disjointResiduePairs'], 1)
        self.assertFalse(result['alert'])

    def test_plausible_disulfide_is_not_clash_but_absurd_short_contact_is(self):
        valid = self.atoms([(0, 0, 0), (2.05, 0, 0)], 'S', 'SG', 'CYS')
        invalid = self.atoms([(0, 0, 0), (0.5, 0, 0)], 'S', 'SG', 'CYS')
        self.assertEqual(physical.packing_conflicts(valid)['nonlocalResiduePairs'], 0)
        self.assertEqual(physical.packing_conflicts(invalid)['nonlocalResiduePairs'], 1)

    def test_declared_nonlocal_covalent_link_is_not_nonbonded_contact(self):
        atoms = self.atoms([(0, 0, 0), (1.5, 0, 0)])
        self.assertEqual(physical.packing_conflicts(atoms)['nonlocalResiduePairs'], 1)
        self.assertEqual(physical.packing_conflicts(atoms, [(atoms[0]['key'], atoms[1]['key'])])['nonlocalResiduePairs'], 0)


class WholeModelContract(unittest.TestCase):
    def measure(self, kind):
        return physical.measure(fixture(kind))

    def test_buried_column_alert_and_no_coordinate_leak(self):
        report = self.measure('charge')
        self.assertTrue(report['measurement']['chargeAlert'])
        self.assertEqual(report['decision'], 'alert')
        self.assertEqual(report['globalFoldValidity'], 'not_established')
        def inspect(value):
            if isinstance(value, dict):
                self.assertFalse({'xyz', 'point', 'points', 'coordinates', 'structure'}.intersection(value))
                for child in value.values():
                    inspect(child)
            elif isinstance(value, list):
                for child in value:
                    inspect(child)
        inspect(report)

    def test_external_calcium_changes_per_residue_compensation(self):
        raw, calcium = self.measure('charge'), self.measure('calcium')
        self.assertTrue(raw['measurement']['chargeAlert'])
        self.assertFalse(calcium['measurement']['chargeAlert'])
        self.assertEqual(calcium['decision'], 'no_targeted_failure_detected')
        self.assertEqual(sum(len(c['possibleCompensation']) for c in calcium['chargeColumns']), 4)

    def test_iron_unknown_valence_is_inconclusive_not_guessed_divalent(self):
        report = self.measure('iron-unknown')
        self.assertFalse(report['measurement']['chargeAlert'])
        self.assertEqual(report['decision'], 'inconclusive')
        self.assertTrue(any(c['uncertainResidues'] for c in report['chargeColumns']))

    def test_explicit_formal_iron_valence_can_be_recorded_as_compensation(self):
        report = self.measure('iron-explicit')
        self.assertEqual(report['decision'], 'no_targeted_failure_detected')
        self.assertTrue(any(c['possibleCompensation'] for c in report['chargeColumns']))

    def test_histidine_is_local_uncertainty_not_ignored_or_column_member(self):
        report = self.measure('histidine')
        self.assertEqual(report['decision'], 'inconclusive')
        self.assertEqual(report['measurement']['chargedGroups'], 4)

    def test_nearby_chain_terminus_is_uncertainty(self):
        self.assertEqual(self.measure('terminal')['decision'], 'inconclusive')

    def test_exposed_ionizable_groups_and_hydrophobic_surface_alone_are_not_alerts(self):
        self.assertEqual(self.measure('exposed')['decision'], 'no_targeted_failure_detected')
        report = self.measure('hydrophobic')
        self.assertEqual(report['decision'], 'no_targeted_failure_detected')
        self.assertGreater(report['measurement']['exposedHydrophobicResidues'], 0)

    def test_no_charged_groups_still_evaluates_packing_failure(self):
        request = fixture('hydrophobic')
        lines = []
        move = {1: 500, 7: 500.9, 2: 510, 8: 510.9, 3: 520, 9: 520.9}
        for line in request['structure'].splitlines():
            if line.startswith('ATOM  ') and line[21:22] == 'A' and line[12:16].strip() == 'CA' and int(line[22:26]) in move:
                line = line[:30] + f'{move[int(line[22:26])]:8.3f}{0:8.3f}{0:8.3f}' + line[54:]
            lines.append(line)
        request['structure'] = '\n'.join(lines) + '\n'
        report = physical.measure(request)
        self.assertEqual(report['measurement']['chargedGroups'], 0)
        self.assertTrue(report['measurement']['packingAlert'])
        self.assertEqual(report['decision'], 'alert')

    def test_missing_relevant_atom_cannot_produce_clean_no_alert(self):
        request = fixture('missing')
        # Remove cages as well, so the remaining charge column is exposed and cannot alert.
        request['structure'] = '\n'.join(x for x in request['structure'].splitlines() if x[21:22] != 'B') + '\n'
        report = physical.measure(request)
        self.assertEqual(report['decision'], 'inconclusive')
        self.assertTrue(report['unresolvedChargedSidechains'])

    def test_model_chain_and_dependency_selection_are_explicit(self):
        request = fixture('charge')
        request['options']['chain'] = 'missing'
        with self.assertRaisesRegex(ValueError, 'ambiguous-author-chain'):
            physical.measure(request)

    def test_deterministic_repetition(self):
        self.assertEqual(self.measure('charge'), self.measure('charge'))

    def test_author_chain_hetero_and_water_parts_remain_context_not_ambiguity(self):
        report = physical.measure(segmented_cif())
        self.assertEqual(report['decision'], 'no_targeted_failure_detected')
        self.assertEqual(report['scope']['selectedResidues'], 26)
        self.assertGreaterEqual(report['scope']['modelChains'].count('A'), 2)
        self.assertEqual(report['scope']['waterAtomsRetainedAsContext'], 1)
        self.assertEqual(report['scope']['contextHeavyAtoms'], 290)

    def test_two_true_polymer_parts_with_one_author_chain_are_still_ambiguous(self):
        with self.assertRaisesRegex(ValueError, 'ambiguous-author-chain'):
            physical.measure(segmented_cif(ambiguous=True))


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == '--fixture':
        print(json.dumps(fixture(sys.argv[2]), sort_keys=True))
    else:
        unittest.main()
