"""Verify exported predicted geometry evidence without executing scientific payloads."""
import argparse,hashlib,json
from pathlib import Path

def sha(data):return hashlib.sha256(data).hexdigest()
def verify(root,expected=None):
    root=Path(root).resolve(strict=True)
    raw=(root/'manifest.json').read_bytes()
    if expected and sha(raw)!=expected:raise ValueError('manifest-anchor-mismatch')
    m=json.loads(raw)
    if m['version']!='helix-predicted-evidence/1.0.0':raise ValueError('version')
    actual=set()
    for file in root.rglob('*'):
        if file.is_symlink():raise ValueError('symlink')
        if file.is_file():actual.add(file.relative_to(root).as_posix())
    if actual!=set(m['files'])|{'manifest.json'}:raise ValueError('unlisted-or-missing-file')
    for name,info in m['files'].items():
        if Path(name).is_absolute() or '..' in Path(name).parts:raise ValueError('unsafe-path')
        data=(root/name).read_bytes()
        if len(data)!=info['bytes'] or sha(data)!=info['sha256']:raise ValueError('artifact-changed:'+name)
    proposal=json.loads((root/'work/proposal.json').read_bytes())
    if set(proposal['files'])!={'request.json','inspection.json','afdb.pdb','inspect_structure.py','predicted_geometry.py'}:raise ValueError('proposal-files')
    if sha((root/'work/proposal.json').read_bytes())!=m['digest']:raise ValueError('proposal-binding')
    for name,h in proposal['files'].items():
        if sha((root/'work'/name).read_bytes())!=h:raise ValueError('proposal-input:'+name)
    admission=json.loads((root/'admission.json').read_bytes())
    if set(admission['sources'])!={'structure','pae','api'}:raise ValueError('source-files')
    for name,source in admission['sources'].items():
        if sha((root/f'original-{name}.txt').read_bytes())!=source['sha256']:raise ValueError('original-source:'+name)
    execution=json.loads((root/'work/execution.json').read_bytes())
    if execution['status']!='succeeded' or execution['proposalDigest']!=m['digest'] or execution['sourceEntry']!=m['entry']:raise ValueError('execution-binding')
    if sha((root/'work/geometry.csv').read_bytes())!=execution['geometrySha256']:raise ValueError('geometry-binding')
    events=json.loads((root/'approval-events.json').read_bytes())
    if not any(e.get('channel')=='Question.Service' and e.get('sessionID')==m['sessionID'] and e.get('digest')==m['digest'] and e.get('approvalDigest')==m['approvalDigest'] for e in events):raise ValueError('approval-binding')
    return {'ok':True,'files':len(m['files']),'manifestSha256':sha(raw),'externallyAnchored':bool(expected),'scope':'Integrity and declared links, not authorship or biological accuracy'}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('root');p.add_argument('--sha256');a=p.parse_args()
    print(json.dumps(verify(a.root,a.sha256),indent=2))
