"""Read archived SIFTS residue XML. No segment endpoint interpolation or network."""
import json,sys,hashlib,xml.etree.ElementTree as ET

def parse(request):
    text=request['xml']
    if len(text.encode())>20_000_000 or '<!DOCTYPE' in text.upper() or '<!ENTITY' in text.upper():
        raise ValueError('unsupported XML declaration or size')
    root=ET.fromstring(text)
    local=lambda node:node.tag.rsplit('}',1)[-1]
    if local(root)!='entry' or root.attrib.get('dbAccessionId','').lower()!=request['pdb'].lower():
        raise ValueError('sifts-entry-mismatch')
    rows=[]
    for residue in root.iter():
        if local(residue)!='residue': continue
        refs=[n.attrib for n in residue if local(n)=='crossRefDb']
        pdb=[r for r in refs if r.get('dbSource')=='PDB' and r.get('dbAccessionId','').lower()==request['pdb'].lower() and r.get('dbChainId')==request['chain']]
        uni=[r for r in refs if r.get('dbSource')=='UniProt' and r.get('dbAccessionId')==request['accession']]
        if not pdb or not uni: continue
        if len(pdb)!=1 or len(uni)!=1: raise ValueError('ambiguous-sifts-residue')
        if any(local(n)=='residueDetail' and n.text and n.text.strip()=='Not_Observed' for n in residue): continue
        p,u=pdb[0],uni[0]
        if not p.get('dbResNum','').isdigit() or not u.get('dbResNum','').isdigit(): raise ValueError('unsupported-sifts-numbering')
        rows.append({'author':int(p['dbResNum']),'uniprot':int(u['dbResNum']),'residue':p.get('dbResName'),'uniprotResidue':u.get('dbResName')})
    if not rows: raise ValueError('no-observed-sifts-residues')
    if len({r['author'] for r in rows})!=len(rows) or len({r['uniprot'] for r in rows})!=len(rows): raise ValueError('nonbijective-sifts-mapping')
    releases={n.attrib['dbSource']:n.attrib['dbVersion'] for n in root.iter() if local(n)=='db' and 'dbSource' in n.attrib and 'dbVersion' in n.attrib}
    return {'version':'trp-sifts-residues/1.0.0','sha256':hashlib.sha256(text.encode()).hexdigest(),'pdb':request['pdb'],'chain':request['chain'],'accession':request['accession'],'release':root.attrib.get('date'),'databaseReleases':releases,'rows':rows}

if __name__=='__main__':
    try:
        raw=sys.stdin.buffer.read(40_000_001)
        if len(raw)>40_000_000: raise ValueError('request-size')
        print(json.dumps(parse(json.loads(raw)),allow_nan=False))
    except Exception as exc:
        print(str(exc),file=sys.stderr)
        sys.exit(2)
