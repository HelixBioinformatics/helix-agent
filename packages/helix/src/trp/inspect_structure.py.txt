"""Bounded offline structural screening. JSON on stdin/stdout; never fetch or execute inputs.

mmCIF syntax is parsed by Gemmi 0.7.5. The legacy PDB branch only uses the
already supported fixed-width CA/model/author route. No sequence alignment,
repeat detection, physical scoring, or structure prediction is implemented here.
"""
import hashlib
import json
import math
import platform
import re
import sys

VERSION = 'trp-structural/1.1.0'
GEMMI = '0.7.5'
LIMIT = 20_000_000

def sha(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()

def finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)

def number(text):
    try:
        value = float(text)
        return value if math.isfinite(value) else None
    except (TypeError, ValueError):
        return None

def integer(value):
    return isinstance(value, int) and not isinstance(value, bool)

def colabfold_binding(request, snap):
    """Bind a local monomer PDB to original score/PAE bytes, never to AFDB URLs.

    The operator declares the source. Hashes and matching sequence/confidence
    verify the pairing, not authorship or biological validity.
    """
    bundle = request['colabfold']
    if request.get('api') is not None or request.get('pae') is not None:
        raise ValueError('mixed-confidence-producers')
    if not isinstance(bundle, dict): raise ValueError('colabfold-bundle')
    meta = bundle.get('metadata')
    if not isinstance(meta, dict): raise ValueError('colabfold-metadata')
    raw_scores, raw_pae = bundle.get('scores'), bundle.get('pae')
    if any(not isinstance(x, str) or len(x.encode()) > LIMIT for x in (raw_scores, raw_pae)):
        raise ValueError('colabfold-sidecar-size')
    def decode(raw):
        return json.loads(raw, parse_constant=lambda s: (_ for _ in ()).throw(ValueError('nonfinite-json')))
    scores, pae = decode(raw_scores), decode(raw_pae)
    if not isinstance(scores, dict) or not isinstance(pae, dict): raise ValueError('colabfold-sidecar')
    rows, errors = snap['rows'], []
    seq = meta.get('sequence')
    letters = dict(zip(('ALA','ARG','ASN','ASP','CYS','GLN','GLU','GLY','HIS','ILE','LEU','LYS','MET','PHE','PRO','SER','THR','TRP','TYR','VAL'), 'ARNDCQEGHILKMFPSTWYV'))
    observed = ''.join(letters.get(r['name'], '?') for r in rows)
    if meta.get('version') != 'colabfold-local/1.0.0' or meta.get('producer') != 'ColabFold' or meta.get('modelType') != 'alphafold2_ptm':
        errors.append('producer-contract')
    identifier, rank, seed, parameter = (meta.get(k) for k in ('caseId','rank','seed','parameterModel'))
    if not isinstance(identifier,str) or not re.fullmatch(r'[A-Za-z0-9_-]+',identifier) or not integer(rank) or not 1<=rank<=5 or not integer(seed) or seed<0 or not integer(parameter) or not 1<=parameter<=5:
        errors.append('run-identity')
    else:
        suffix = f'rank_{rank:03d}_alphafold2_ptm_model_{parameter}_seed_{seed:03d}'
        if meta.get('structureFile') != f'{identifier}_unrelaxed_{suffix}.pdb' or meta.get('scoresFile') != f'{identifier}_scores_{suffix}.json' or meta.get('paeFile') != f'{identifier}_predicted_aligned_error_v1.json':
            errors.append('paired-filenames')
    options = request['options']
    atoms = [l for l in request['structure'].splitlines() if l[:6] in ('ATOM  ','HETATM')]
    if options['format'] != 'pdb' or options['model'] != 1 or options['frame'] != 'auth_seq_id' or snap['methods'] or len([l for l in request['structure'].splitlines() if l.startswith('MODEL ')]) > 1:
        errors.append('monomer-pdb-contract')
    if not atoms or {l[21:22] for l in atoms} != {options['chain']} or meta.get('chain') != options['chain']:
        errors.append('single-chain')
    if not rows or len(rows)>2000 or any(r['auth'] != str(i+1) or r['insertion'] or r['alt'] or any(v is None for v in r['xyz']) for i,r in enumerate(rows)) or not isinstance(seq,str) or not seq or observed != seq:
        errors.append('complete-sequence-axes')
    for key, raw in (('structureSha256',request['structure']),('scoresSha256',raw_scores),('paeSha256',raw_pae)):
        if meta.get(key) != sha(raw): errors.append(key+'-mismatch')
    plddt = scores.get('plddt')
    if not isinstance(plddt,list) or len(plddt)!=len(rows) or any(not finite(v) or not 0<=v<=100 for v in plddt):
        errors.append('score-plddt-domain')
    else:
        if any(r['b'] is None or abs(r['b']-v)>0.011 for r,v in zip(rows,plddt)):
            errors.append('score-plddt-disagreement')
    n = len(rows)
    matrix, maximum = pae.get('predicted_aligned_error'), pae.get('max_predicted_aligned_error')
    # ColabFold rounds matrix cells to two decimals but keeps max_pae at full
    # precision (batch.py v1.5.2). Allow only that serialization half-step;
    # engineering PAE thresholds below remain unchanged.
    cap = maximum + 0.005000001 if finite(maximum) else -1
    matrix_valid = isinstance(matrix,list) and len(matrix)==n and finite(maximum) and maximum>=0 and all(isinstance(row,list) and len(row)==n and all(finite(v) and 0<=v<=cap for v in row) for row in matrix)
    score_matrix = scores.get('pae')
    matrix_valid = matrix_valid and isinstance(score_matrix,list) and len(score_matrix)==n and all(isinstance(row,list) and len(row)==n and all(finite(v) and 0<=v<=cap for v in row) for row in score_matrix)
    matrix_valid = matrix_valid and finite(scores.get('max_pae')) and score_matrix == matrix and scores.get('max_pae') == maximum
    binding = {'producer':'ColabFold','caseId':identifier,'rank':rank,'seed':seed,'parameterModel':parameter,
               'structureSha256':meta.get('structureSha256'),'scoresSha256':meta.get('scoresSha256'),'paeSha256':meta.get('paeSha256'),
               'metadataMatchesStructure':not errors,'errors':sorted(set(errors)),'paeSerializationTolerance':0.005000001,
               'attribution':'operator-declared local source; byte/sequence pairing verified, authorship not authenticated'}
    return binding, matrix, bool(matrix_valid)

def cif_snapshot(text, options):
    import gemmi
    if gemmi.__version__ != GEMMI:
        raise ValueError('parser-version: install gemmi==' + GEMMI)
    doc = gemmi.cif.read_string(text)
    if len(doc) != 1:
        raise ValueError('cif-block: exactly one data block required')
    block = doc.sole_block()
    def category(prefix):
        data = block.get_mmcif_category(prefix)
        if not data: return []
        return [dict(zip(data, row)) for row in zip(*data.values())]
    def values(tag):
        return [gemmi.cif.as_string(x) for x in block.find_values(tag)]
    atoms = category('_atom_site.')
    if len(atoms) > 200_000: raise ValueError('atom-limit')
    models = list(dict.fromkeys(str(a.get('pdbx_PDB_model_num', '1')) for a in atoms))
    ordinal = options['model']
    model = models[ordinal-1] if 0 < ordinal <= len(models) else None
    rows = []
    for atom in atoms:
        if str(atom.get('pdbx_PDB_model_num', '1')) != model or atom.get('label_atom_id') != 'CA': continue
        if atom.get('auth_asym_id') != options['chain'] or not atom.get('label_seq_id'): continue
        label = str(atom['label_seq_id'])
        if not re.fullmatch(r'[1-9][0-9]*', label): raise ValueError('label-seq-id')
        rows.append({'label':int(label), 'auth':str(atom.get('auth_seq_id') or ''),
                     'insertion':atom.get('pdbx_PDB_ins_code') or '', 'labelChain':atom.get('label_asym_id'),
                     'name':atom.get('label_comp_id'), 'alt':atom.get('label_alt_id') or '',
                     'b':number(atom.get('B_iso_or_equiv')), 'xyz':[number(atom.get('Cartn_'+a)) for a in 'xyz']})
    metrics = {str(m.get('id')):m for m in category('_ma_qa_metric.')}
    local = []
    for m in category('_ma_qa_metric_local.'):
        definition = metrics.get(str(m.get('metric_id')), {})
        if definition.get('type','').lower() != 'plddt' or definition.get('mode') != 'local': continue
        if str(m.get('model_id')) != model: continue
        local.append({'chain':m.get('label_asym_id'), 'label':int(m['label_seq_id']), 'value':number(m.get('metric_value'))})
    software = category('_software.')
    groups = values('_ma_model_list.model_group_name')
    af2 = any(s.get('name','').lower() == 'alphafold' and str(s.get('version','')).startswith('v2') for s in software)
    af2 = af2 and any('AlphaFold Monomer' in group for group in groups)
    sequence = values('_entity_poly.pdbx_seq_one_letter_code_can')
    sequences = [re.sub(r'\s+', '', s) for s in sequence]
    observed_sequence = ''.join(gemmi.find_tabulated_residue(r['name']).one_letter_code for r in rows)
    return {'parser':'gemmi/'+gemmi.__version__, 'entry':(values('_entry.id') or [block.name])[0],
            'model':model, 'rows':rows, 'methods':values('_exptl.method'), 'af2':af2, 'local':local,
            'software':software, 'groups':groups, 'sequences':sequences, 'observedSequence':observed_sequence,
            'synthetic':category('_pdbx_entity_src_syn.'), 'differences':category('_struct_ref_seq_dif.')}

def pdb_snapshot(text, options):
    rows, methods = [], []
    model, ordinal = 1, 0
    for line in text.splitlines():
        if line.startswith('MODEL '):
            ordinal += 1
            model = ordinal
        if line.startswith('ENDMDL'): model = 0
        if line.startswith('EXPDTA'): methods.append(line[10:].strip())
        if line[:6] not in ('ATOM  ', 'HETATM') or len(line)<66: continue
        if model != options['model'] or line[21:22] != options['chain'] or line[12:16].strip() != 'CA': continue
        rows.append({'label':None, 'auth':line[22:26].strip(), 'insertion':line[26:27].strip(),
                     'labelChain':None, 'name':line[17:20].strip(), 'alt':line[16:17].strip(),
                     'b':number(line[60:66]), 'xyz':[number(line[a:a+8]) for a in (30,38,46)]})
    return {'parser':'legacy-pdb-ca/1.0.0', 'entry':next((l[62:66].strip() for l in text.splitlines() if l.startswith('HEADER')), None),
            'model':str(options['model']), 'rows':rows, 'methods':methods, 'af2':False, 'local':[],
            'software':[], 'groups':[], 'sequences':[], 'observedSequence':'', 'synthetic':[], 'differences':[]}

def inspect(request):
    text, options = request['structure'], request['options']
    if not isinstance(text,str) or len(text.encode())>LIMIT: raise ValueError('input-size')
    if not integer(options.get('model')) or options['model'] < 1: raise ValueError('model-ordinal')
    if not isinstance(options.get('chain'),str) or not options['chain']: raise ValueError('author-chain')
    if options.get('frame') not in ('auth_seq_id','label_seq_id'): raise ValueError('unsupported-frame')
    if options.get('format') not in ('pdb','mmcif'): raise ValueError('unsupported-format')
    ranges = options.get('units', [])
    if not isinstance(ranges,list) or not 2 <= len(ranges) <= 1000: raise ValueError('unit-count')
    if any(not integer(r.get('start')) or not integer(r.get('end')) or r['start']>r['end'] for r in ranges): raise ValueError('unit-range')
    if sum(r['end']-r['start']+1 for r in ranges)>10_000: raise ValueError('residue-limit')
    plddt_min, pae_max = options.get('plddtMin',70), options.get('paeMax',5)
    if not finite(plddt_min) or not 0<=plddt_min<=100 or not finite(pae_max) or not 0<=pae_max<=100: raise ValueError('threshold-domain')
    snap = cif_snapshot(text, options) if options['format']=='mmcif' else pdb_snapshot(text, options)
    colabfold = colabfold_binding(request, snap) if 'colabfold' in request else None
    rows, checks = snap['rows'], []
    def check(code, status, value, threshold, reason):
        checks.append({'id':code,'status':status,'value':value,'threshold':threshold,'reason':reason})
    experimental = bool(snap['methods']) and all(m.upper() in ('X-RAY DIFFRACTION','ELECTRON MICROSCOPY','NEUTRON DIFFRACTION','ELECTRON CRYSTALLOGRAPHY') for m in snap['methods'])
    scale = 'pLDDT_0_100' if snap['af2'] and not snap['methods'] and snap['local'] else 'Bfactor_A2' if experimental and not snap['af2'] and not snap['local'] else 'Unset'
    if colabfold and colabfold[0]['metadataMatchesStructure']:
        scale = 'pLDDT_0_100'
        snap['software'] = [{'name':'ColabFold','modelType':'alphafold2_ptm','version':None,'source':'declared local bundle'}]
    local = {}
    duplicated_local = False
    for item in snap['local']:
        key=(item['chain'],item['label'])
        if key in local: duplicated_local = True
        local[key] = item['value']
    errors=[]
    for row in rows:
        b=row['b']
        if b is None or b<0 or scale=='pLDDT_0_100' and b>100: errors.append('value-domain')
        if scale=='pLDDT_0_100' and not colabfold:
            value=local.get((row['labelChain'],row['label']))
            if value is None or not 0<=value<=100 or b is None or abs(value-b)>0.011: errors.append('local-metric-disagreement')
    if duplicated_local: errors.append('duplicate-local-metric')
    if colabfold: errors.extend(colabfold[0]['errors'])
    check('confidence-scale','fail' if errors else 'not_evaluable' if scale=='Unset' else 'fail' if not rows else 'pass',
          {'scale':scale,'methods':snap['methods'],'producer':snap['software'],'errors':sorted(set(errors))},
          {'Bfactor_A2':[0,None],'pLDDT_0_100':[0,100],'localTolerance':0.011},
          'Scale comes from method/producer and local metrics, never from numeric magnitude alone.')
    requested_filter = options.get('filter')
    if requested_filter is None:
        check('filter-direction','not_applicable',None,None,'No confidence filter requested; no residues are removed.')
    elif scale=='Unset':
        check('filter-direction','not_evaluable',requested_filter,{'knownScale':True},'Cannot apply a filter with an unknown scale.')
    else:
        operator = '>=' if scale=='pLDDT_0_100' else '<='
        t = requested_filter.get('threshold')
        ok=requested_filter.get('scale')==scale and requested_filter.get('operator')==operator and finite(t) and t>=0 and (scale!='pLDDT_0_100' or t<=100)
        check('filter-direction','pass' if ok else 'fail',requested_filter,{'scale':scale,'operator':operator,'domain':[0,100 if scale=='pLDDT_0_100' else None]},'Checks the requested direction and threshold; inspection never applies or silently reverses the filter.')
    lookup={}
    for index,row in enumerate(rows):
        key=str(row['label']) if options['frame']=='label_seq_id' and row['label'] is not None else row['auth'] if options['frame']=='auth_seq_id' else None
        lookup.setdefault(key,[]).append(index)
    units=[[str(i) for i in range(r['start'],r['end']+1)] for r in ranges]
    requested=[i for u in units for i in u]
    missing=[i for i in requested if i not in lookup]
    ambiguous=[i for i in requested if len(lookup.get(i,[]))>1 or any(rows[j]['insertion'] or rows[j]['alt'] for j in lookup.get(i,[]))]
    mapping=[rows[lookup[i][0]] for i in requested if i in lookup and len(lookup[i])==1]
    label_keys=[(r['labelChain'],r['label']) for r in rows if r['label'] is not None]
    auth_keys=[(r['auth'],r['insertion']) for r in rows]
    duplicate_map=len(label_keys)!=len(set(label_keys)) or len(auth_keys)!=len(set(auth_keys))
    frame_bad=bool(ambiguous) or duplicate_map or options['frame']=='label_seq_id' and options['format']=='pdb'
    check('residue-frame','fail' if frame_bad else 'pass',{'frame':options['frame'],'ambiguous':ambiguous,'duplicateMap':duplicate_map,'mapped':len(mapping)}, {'ambiguous':0,'duplicateMap':False}, 'Mapping uses atom-site keys. Author insertion codes and ambiguous alternate observations are refused; no UniProt/SIFTS offset is inferred.')
    invalid=[i for i in requested for j in lookup.get(i,[]) if any(v is None for v in rows[j]['xyz'])]
    overlap=len(requested)-len(set(requested))
    coverage_ok=not (missing or ambiguous or invalid or overlap)
    check('element-coverage','pass' if coverage_ok else 'fail',{'requested':len(requested),'observedUnique':len(set(requested)-set(missing)-set(ambiguous)),'missing':missing,'ambiguous':ambiguous,'invalidCoordinates':invalid,'overlap':overlap}, {'missing':0,'ambiguous':0,'invalidCoordinates':0,'overlap':0,'coverageFraction':1}, 'Every requested position requires one finite CA; no automatic dropping of units or residues.')
    selected_plddt=[r['b'] for r in mapping if r['b'] is not None]
    confidence_summary={'selectedMinimum':min(selected_plddt) if selected_plddt else None,'plddtMinimumThreshold':plddt_min}
    pae=request.get('pae')
    api=request.get('api')
    metadata = api[0] if isinstance(api,list) and len(api)==1 and isinstance(api[0],dict) else {}
    binding = {'entry':metadata.get('entryId') or metadata.get('modelEntityId'),'modelVersion':metadata.get('latestVersion'),
               'modelCreatedDate':metadata.get('modelCreatedDate'),'structureUrl':options.get('structureUrl'),
               'paeUrl':options.get('paeUrl'),'metadataMatchesStructure':False,
               'attribution':'declared URLs; not authenticated by inspection'} if metadata else None
    if scale=='Bfactor_A2':
        check('interunit-pae','not_applicable',None,{'angstromMax':pae_max},'Experimental coordinates: AFDB PAE is not applicable; this does not certify orientation accuracy.')
    elif colabfold:
        binding, matrix, matrix_ok = colabfold
        axes = binding['metadataMatchesStructure'] and coverage_ok and not frame_bad
        if not axes or not matrix_ok:
            check('interunit-pae','fail',{'axesMatch':bool(axes),'matrixValid':matrix_ok,'residues':len(rows)}, {'axesMatch':True,'matrixValid':True,'angstromMax':pae_max},'Local ColabFold requires hash-bound score/PAE bytes, identical matrices, full sequence and unambiguous monomer axes. No AFDB provenance is inferred.')
        else:
            indices=[[lookup[k][0] for k in unit] for unit in units]
            pairs=[]
            for i in range(len(indices)):
                for j in range(i+1,len(indices)):
                    forward=max(matrix[a][b] for a in indices[i] for b in indices[j])
                    reverse=max(matrix[b][a] for a in indices[i] for b in indices[j])
                    pairs.append({'units':[i+1,j+1],'forwardMax':forward,'reverseMax':reverse})
            worst=max(max(p['forwardMax'],p['reverseMax']) for p in pairs)
            ok=worst<=pae_max and len(selected_plddt)==len(requested) and min(selected_plddt)>=plddt_min
            check('interunit-pae','pass' if ok else 'fail',{'maximum':worst,'pairs':pairs,**confidence_summary}, {'angstromMax':pae_max,'plddtMin':plddt_min,'reducer':'max of both directed cross-unit blocks'},'Same previously fixed engineering profile as AFDB; neither local confidence nor PAE establishes physical plausibility.')
    elif scale!='pLDDT_0_100' or pae is None or api is None:
        check('interunit-pae','not_evaluable',{'paePresent':pae is not None,'apiPresent':api is not None}, {'angstromMax':pae_max,'plddtMin':plddt_min},'Predicted geometry needs bound PAE axes and producer/sequence metadata; local confidence alone is insufficient.')
    else:
        matrix = pae[0].get('predicted_aligned_error') if isinstance(pae,list) and len(pae)==1 and isinstance(pae[0],dict) else None
        metadata=api[0] if isinstance(api,list) and len(api)==1 and isinstance(api[0],dict) else {}
        n=len(rows)
        sequence=metadata.get('sequence')
        entry=metadata.get('entryId') or metadata.get('modelEntityId')
        version=metadata.get('latestVersion')
        expected_prefix='https://alphafold.ebi.ac.uk/files/'+str(entry)
        axes = bool(rows) and n<=2000 and coverage_ok and not frame_bad and len(set(r['labelChain'] for r in rows))==1 and [r['label'] for r in rows]==list(range(1,n+1))
        axes = axes and sequence==snap['observedSequence'] and snap['sequences']==[sequence] and metadata.get('chainId')==options['chain'] and not metadata.get('isComplex',True)
        axes = axes and snap['entry']==entry and snap['model']=='1' and metadata.get('cifUrl')==expected_prefix+'-model_v'+str(version)+'.cif'
        axes = axes and metadata.get('paeDocUrl')==expected_prefix+'-predicted_aligned_error_v'+str(version)+'.json'
        axes = axes and options.get('structureUrl')==metadata.get('cifUrl') and options.get('paeUrl')==metadata.get('paeDocUrl')
        binding = {'entry':entry,'modelVersion':version,'modelCreatedDate':metadata.get('modelCreatedDate'),
                   'structureUrl':options.get('structureUrl'),'paeUrl':options.get('paeUrl'),
                   'metadataMatchesStructure':bool(axes),'attribution':'declared URLs; not authenticated by inspection'}
        max_error=pae[0].get('max_predicted_aligned_error') if matrix is not None else None
        matrix_ok=isinstance(matrix,list) and len(matrix)==n and finite(max_error) and max_error>=0 and all(isinstance(row,list) and len(row)==n and all(finite(v) and 0<=v<=max_error for v in row) for row in matrix)
        if not axes or not matrix_ok:
            check('interunit-pae','fail',{'axesMatch':bool(axes),'matrixValid':bool(matrix_ok),'residues':n}, {'axesMatch':True,'matrixValid':True,'angstromMax':pae_max},'PAE cannot be attached by length alone: full chain, sequence, entry, versioned URLs and matrix domain must agree. URL attribution is declared, not authenticated.')
        else:
            indices=[[lookup[k][0] for k in unit] for unit in units]
            pairs=[]
            for i in range(len(indices)):
                for j in range(i+1,len(indices)):
                    forward=max(matrix[a][b] for a in indices[i] for b in indices[j])
                    reverse=max(matrix[b][a] for a in indices[i] for b in indices[j])
                    pairs.append({'units':[i+1,j+1],'forwardMax':forward,'reverseMax':reverse})
            worst=max(max(p['forwardMax'],p['reverseMax']) for p in pairs)
            ok=worst<=pae_max and len(selected_plddt)==len(requested) and min(selected_plddt)>=plddt_min
            check('interunit-pae','pass' if ok else 'fail',{'maximum':worst,'pairs':pairs,**confidence_summary}, {'angstromMax':pae_max,'plddtMin':plddt_min,'reducer':'max of both directed cross-unit blocks'},'Engineering thresholds declared before inspection; not universal or validated sensitivity/specificity.')
    terminal=[]
    names=[r['name'] for r in rows]
    for start in (0, max(0,len(rows)-12)):
        run=[]
        for i in range(start,min(start+12,len(rows))):
            run=run+[i] if names[i]=='HIS' else []
            if len(run)>=6: terminal.extend(run)
    selected_tags=[rows[i]['auth'] for i in sorted(set(terminal)) if rows[i] in mapping]
    signals={'selectedTerminalPolyHis':selected_tags,'syntheticSource':snap['synthetic'],'sequenceDifferences':snap['differences']}
    check('construct-tags','fail' if selected_tags else 'not_evaluable',signals,{'selectedTerminalPolyHis':0},'Poly-His is a review signal, not proof of an engineered tag. No automatic trimming. Other construct metadata require sequence/source interpretation; absence of a motif does not prove a native construct.')
    check('assembly-annotation','not_evaluable',None,{'needed':['genomic assembly','reads','independent gene annotation']},'No assembly or annotation diagnosis can be made from this coordinate file alone.')
    reference=options.get('reference')
    if reference is None:
        check('unit-boundaries','not_evaluable',None,{'needed':'independently reviewed units in the same frame'},'Supplied units are not their own validation reference.')
    else:
        same=reference.get('structureSha256')==sha(text) and reference.get('chain')==options['chain'] and reference.get('frame')==options['frame'] and reference.get('model')==options['model'] and bool(reference.get('source'))
        tolerance=reference.get('tolerance',0)
        other=reference.get('units',[])
        valid=finite(tolerance) and tolerance>=0 and isinstance(other,list) and all(integer(r.get('start')) and integer(r.get('end')) and r['start']<=r['end'] for r in other)
        deltas=[max(abs(a['start']-b['start']),abs(a['end']-b['end'])) for a,b in zip(ranges,other)] if same and valid and len(other)==len(ranges) else []
        ok=bool(deltas) and max(deltas)<=tolerance
        check('unit-boundaries','pass' if ok else 'fail',{'identityAndFrameMatch':same,'referenceValid':valid,'units':len(other),'endpointDeltas':deltas,'source':reference.get('source')}, {'toleranceResidues':tolerance if finite(tolerance) else None,'expectedUnits':len(ranges)},'Comparison does not authenticate review status or silently choose one annotation.')
    check('fold-plausibility','not_evaluable',None,{'needed':'independent physical or experimental evidence'},'Pratt et al. report confident but implausible repeat models. Passing pLDDT/PAE does not establish a physically plausible fold; these controls do not detect all published failures.')
    failed=[c['id'] for c in checks if c['status']=='fail']
    unknown=[c['id'] for c in checks if c['status']=='not_evaluable']
    blocking=failed+[c['id'] for c in checks if c['status']=='not_evaluable' and c['id'] in ('confidence-scale','filter-direction','interunit-pae')]
    return {'version':VERSION,'provenance':{'structureSha256':sha(text),'parser':snap['parser'],'python':platform.python_version(),'entry':snap['entry'],'model':snap['model'],'authorChain':options['chain'],'frame':options['frame'],'confidenceScale':scale,'software':snap['software'],'modelGroups':snap['groups'],'confidenceBinding':binding},
            'checks':checks,'mapping':rows,'summary':{'failed':failed,'notEvaluable':unknown,'mechanicalAdmission':not blocking,'blocking':blocking,'biologicalValidity':'not_established'},
            'limitations':['Mechanical screening; a complete R3.8 evaluation needs independent labels and pertinent controls.','No physical fold classifier, genomic assembly validator, SIFTS/UniProt alignment or repeat detector.','Integrity and declared sources do not authenticate scientific provenance.']}

if __name__=='__main__':
    try:
        raw=sys.stdin.buffer.read(40_000_001)
        if len(raw)>40_000_000: raise ValueError('request-size')
        result=inspect(json.loads(raw, parse_constant=lambda s: (_ for _ in ()).throw(ValueError('nonfinite-json'))))
        print(json.dumps(result,sort_keys=True,separators=(',',':'),allow_nan=False))
    except Exception as error:
        print(json.dumps({'version':VERSION,'error':type(error).__name__,'detail':str(error)}),file=sys.stderr)
        sys.exit(2)
