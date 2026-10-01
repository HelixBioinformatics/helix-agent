"""Producer contract tests on labelled synthetic development data, not Pratt cases."""
import copy
import hashlib
import json
import runpy
import unittest
from pathlib import Path

ENGINE = Path(__file__).resolve().parents[2]/'packages/helix/src/trp/inspect_structure.py.txt'
inspect = runpy.run_path(str(ENGINE))['inspect']

def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()

def fixture():
    sequence = 'ACGAACGA'
    names = {'A':'ALA','C':'CYS','G':'GLY'}
    structure = 'MODEL     1\n' + ''.join(
        f'ATOM  {i:5d}  CA  {names[aa]} A{i:4d}    {i*3.8:8.3f}{0:8.3f}{0:8.3f}{1:6.2f}{90:6.2f}           C\n'
        for i,aa in enumerate(sequence,1)) + 'ENDMDL\nEND\n'
    matrix = [[1.0]*8 for _ in range(8)]
    scores = json.dumps({'plddt':[90.0]*8,'pae':matrix,'max_pae':31.0,'ptm':0.9})
    pae = json.dumps({'predicted_aligned_error':matrix,'max_predicted_aligned_error':31.0})
    meta = {'version':'colabfold-local/1.0.0','producer':'ColabFold','caseId':'synthetic',
            'modelType':'alphafold2_ptm','sequence':sequence,'chain':'A','rank':1,'seed':0,'parameterModel':2,
            'structureFile':'synthetic_unrelaxed_rank_001_alphafold2_ptm_model_2_seed_000.pdb',
            'scoresFile':'synthetic_scores_rank_001_alphafold2_ptm_model_2_seed_000.json',
            'paeFile':'synthetic_predicted_aligned_error_v1.json',
            'structureSha256':sha(structure),'scoresSha256':sha(scores),'paeSha256':sha(pae)}
    return {'structure':structure,'options':{'format':'pdb','model':1,'chain':'A','frame':'auth_seq_id',
            'units':[{'start':1,'end':4},{'start':5,'end':8}]},
            'colabfold':{'metadata':meta,'scores':scores,'pae':pae}}

def control(request, name):
    return next(c for c in inspect(request)['checks'] if c['id']==name)

def change_sidecar(request, name, fn):
    data=json.loads(request['colabfold'][name]);fn(data)
    raw=json.dumps(data);request['colabfold'][name]=raw
    request['colabfold']['metadata'][name+'Sha256']=sha(raw)

class ColabFoldBinding(unittest.TestCase):
    def test_valid_local_contract_without_fake_afdb(self):
        report=inspect(fixture())
        self.assertTrue(report['summary']['mechanicalAdmission'])
        self.assertEqual(report['provenance']['confidenceScale'],'pLDDT_0_100')
        self.assertEqual(report['provenance']['confidenceBinding']['producer'],'ColabFold')
        self.assertEqual(control(fixture(),'fold-plausibility')['status'],'not_evaluable')
        self.assertEqual(report['summary']['biologicalValidity'],'not_established')

    def test_unattributed_pdb_does_not_gain_confidence_scale(self):
        r=fixture();del r['colabfold']
        self.assertEqual(control(r,'confidence-scale')['status'],'not_evaluable')

    def test_original_hashes_bind_each_artifact(self):
        for name in ('structure','scores','pae'):
            r=fixture()
            if name=='structure':r[name]+='\n'
            else:r['colabfold'][name]+='\n'
            with self.subTest(name=name):self.assertFalse(inspect(r)['summary']['mechanicalAdmission'])

    def test_same_length_wrong_sequence_rejected(self):
        r=fixture();r['colabfold']['metadata']['sequence']='A'*8
        self.assertEqual(control(r,'confidence-scale')['status'],'fail')

    def test_pair_identity_rejected(self):
        for key,value in (('rank',2),('seed',1),('parameterModel',5),('producer','Unknown')):
            r=fixture();r['colabfold']['metadata'][key]=value
            with self.subTest(key=key):self.assertEqual(control(r,'confidence-scale')['status'],'fail')

    def test_score_vs_pdb_confidence_rejected_even_with_updated_hash(self):
        r=fixture();change_sidecar(r,'scores',lambda d:d['plddt'].__setitem__(0,85))
        self.assertEqual(control(r,'confidence-scale')['status'],'fail')

    def test_pae_vs_scores_mismatch_rejected_even_with_updated_hash(self):
        r=fixture();change_sidecar(r,'pae',lambda d:d['predicted_aligned_error'][0].__setitem__(4,2))
        self.assertEqual(control(r,'interunit-pae')['status'],'fail')

    def test_matrix_shape_domain_and_boolean_scores_rejected(self):
        for change in (lambda d:d['predicted_aligned_error'].pop(),lambda d:d['predicted_aligned_error'][0].__setitem__(4,-1),lambda d:d['predicted_aligned_error'][0].__setitem__(4,True)):
            r=fixture();change_sidecar(r,'pae',change)
            self.assertEqual(control(r,'interunit-pae')['status'],'fail')
        r=fixture();change_sidecar(r,'scores',lambda d:d['pae'][0].__setitem__(4,True))
        self.assertEqual(control(r,'interunit-pae')['status'],'fail')

    def test_reverse_directed_block_is_checked(self):
        r=fixture()
        change_sidecar(r,'pae',lambda d:d['predicted_aligned_error'][4].__setitem__(0,6))
        change_sidecar(r,'scores',lambda d:d['pae'][4].__setitem__(0,6))
        c=control(r,'interunit-pae')
        self.assertEqual(c['status'],'fail');self.assertEqual(c['value']['pairs'][0]['reverseMax'],6)

    def test_producer_rounding_does_not_change_engineering_threshold(self):
        r=fixture()
        change_sidecar(r,'scores',lambda d:d.update(max_pae=1.996))
        change_sidecar(r,'pae',lambda d:d.update(max_predicted_aligned_error=1.996))
        for name,key in (('scores','pae'),('pae','predicted_aligned_error')):
            change_sidecar(r,name,lambda d,k=key:d[k][0].__setitem__(4,2.0))
        self.assertEqual(control(r,'interunit-pae')['status'],'pass')
        for name,key in (('scores','pae'),('pae','predicted_aligned_error')):
            change_sidecar(r,name,lambda d,k=key:d[k][0].__setitem__(4,2.01))
        self.assertEqual(control(r,'interunit-pae')['status'],'fail')

    def test_multiple_chains_or_models_cannot_use_monomer_axes(self):
        for append in ('ATOM      9  CA  ALA B   1       0.000   0.000   0.000  1.00 90.00           C\n','MODEL     2\nENDMDL\n'):
            r=fixture();r['structure']+=append;r['colabfold']['metadata']['structureSha256']=sha(r['structure'])
            self.assertEqual(control(r,'confidence-scale')['status'],'fail')

    def test_missing_or_ambiguous_residue_cannot_bind_pae(self):
        for change in (lambda s:s.replace(' A   4',' A   5'),lambda s:s.replace(' A   4 ',' A   4A')):
            r=fixture();r['structure']=change(r['structure']);r['colabfold']['metadata']['structureSha256']=sha(r['structure'])
            self.assertEqual(control(r,'interunit-pae')['status'],'fail')

    def test_conflicting_producers_rejected(self):
        r=fixture();r['api']=[{}]
        with self.assertRaisesRegex(ValueError,'mixed-confidence-producers'):inspect(r)

if __name__=='__main__':unittest.main()
