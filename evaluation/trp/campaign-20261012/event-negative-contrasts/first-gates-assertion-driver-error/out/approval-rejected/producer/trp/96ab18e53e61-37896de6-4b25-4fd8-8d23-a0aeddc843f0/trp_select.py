import hashlib, json, pathlib
s = json.loads(pathlib.Path('settings.json').read_text())
for name, expected in [('source.pdb', s['inputHash']), ('selection.pdb', s['selectionHash'])]:
    if hashlib.sha256(pathlib.Path(name).read_bytes()).hexdigest() != expected:
        raise ValueError('Approved input changed: ' + name)
pathlib.Path(s['pdb'] + '.pdb').write_bytes(pathlib.Path('selection.pdb').read_bytes())
