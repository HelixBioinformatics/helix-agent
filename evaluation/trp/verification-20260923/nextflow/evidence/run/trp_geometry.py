import hashlib, json, pathlib, subprocess
s = json.loads(pathlib.Path('settings.json').read_text())
name = s['pdb'] + '.pdb'
if hashlib.sha256(pathlib.Path(name).read_bytes()).hexdigest() != s['selectionHash']:
    raise ValueError('Selected structure changed')
intervals = lambda values: ','.join(str(r['start']) + '_' + str(r['end']) for r in values)
args = ['geometre', 'single', name, s['chain'], 'geometry.csv', intervals(s['units'])]
if s['insertions']:
    args.extend(['-ins_def', intervals(s['insertions'])])
subprocess.run(args, check=True, timeout=120)
if not pathlib.Path('geometry.csv').is_file():
    raise ValueError('GeomeTRe exited without a CSV')
