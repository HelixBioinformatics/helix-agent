import os, json, pathlib, socket, numpy
from threadpoolctl import threadpool_info
def _limit(name):
    return pathlib.Path('/sys/fs/cgroup/' + name).read_text().strip()
print('HELIX_RUNTIME:' + json.dumps({'hostname': socket.gethostname(), 'cpuMax': _limit('cpu.max'), 'memoryMax': _limit('memory.max'), 'swapMax': _limit('memory.swap.max'), 'numericalProfile': os.environ.get('OPENBLAS_CORETYPE', 'native'), 'threads': os.environ.get('OPENBLAS_NUM_THREADS'), 'blas': threadpool_info()}), flush=True)
import hashlib, json, pathlib
s = json.loads(pathlib.Path('settings.json').read_text())
for name, expected in [('source.pdb', s['inputHash']), ('selection.pdb', s['selectionHash'])]:
    if hashlib.sha256(pathlib.Path(name).read_bytes()).hexdigest() != expected:
        raise ValueError('Approved input changed: ' + name)
pathlib.Path(s['pdb'] + '.pdb').write_bytes(pathlib.Path('selection.pdb').read_bytes())
