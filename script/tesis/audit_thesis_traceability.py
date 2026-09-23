#!/usr/bin/env python3
"""Check the 21-result index and produce a readable map without inferring success."""
import argparse
from collections import Counter
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
EXPECTED=[f'R{oe}.{r}' for oe,n in ((1,9),(2,4),(3,8)) for r in range(1,n+1)]

def audit(data):
    rows=data['resultados']; errors=[]
    counts=Counter(row['id'] for row in rows)
    if set(counts)!=set(EXPECTED) or any(count!=1 for count in counts.values()):
        errors.append('Expected exactly the 21 unique results R1.1–R3.8')
    for row in rows:
        if row.get('objetivo') != 'OE'+row['id'][1]:
            errors.append(row['id']+': objective does not match current numbering')
        if not row.get('pendiente'): errors.append(row['id']+': missing scope/remaining-work statement')
        for key in ('codigo','pruebas','evidencia'):
            for path in row.get(key,[]):
                target=ROOT/path
                if not target.is_file():errors.append(f'{row["id"]}: missing {key} file {path}')
        measurement=row.get('medicion')
        if isinstance(measurement,dict) and measurement.get('evidencia'):
            if not (ROOT/measurement['evidencia']).is_file():errors.append(row['id']+': missing measurement evidence')
    mapping=json.loads((ROOT/'docs/tesis/renumeracion-20260923/equivalencias.json').read_text())
    if set(mapping['results'].values())!=set(EXPECTED) or len(set(mapping['results'].values()))!=21:
        errors.append('Identifier mapping is not a bijection of 21 results')
    for row in rows:
        if mapping['results'].get(row.get('id_anterior'))!=row['id']:
            errors.append(row['id']+': incorrect historical correspondence')
    protocol=json.loads((ROOT/'evaluation/trp/protocol.json').read_text())
    previous=json.loads((ROOT/'docs/tesis/renumeracion-20260923/protocol-1.0.0.json').read_text())
    import re
    expected=json.loads(re.sub(r'(?<![\w])R[1-5]\.[1-9](?!\d)',lambda m:mapping['results'].get(m[0],m[0]),json.dumps(previous)))
    for key,value in expected.items():
        if key not in ('version','date') and protocol.get(key)!=value:
            errors.append('Protocol changed beyond identifier migration: '+key)
    return {'ok':not errors,'results':len(rows),'errors':errors,
            'scope':'Completeness and file existence only; not empirical achievement.'}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--markdown',type=Path)
    args=parser.parse_args()
    data=json.loads((ROOT/'docs/tesis/trazabilidad.json').read_text())
    result=audit(data)
    if args.markdown:
        lines=['# Mapa de los 21 resultados esperados','',
               'Numeración del 23/09/2026, tres objetivos. [Equivalencias e históricos](renumeracion-20260923/README.md). Generado desde `trazabilidad.json`. «Implementado» describe software o diseño; no acredita la medición reservada de F6.','',
               '| Resultado | Anterior | Objetivo | Entregable | Estado | Código / pruebas | Alcance y pendiente |',
               '|---|---|---|---|---|---|---|']
        for row in data['resultados']:
            links=[f'[{Path(p).name}](../../{p})' for p in row['codigo']+row['pruebas']]
            lines.append('| '+' | '.join((row['id'],row['id_anterior'],row['objetivo'],row['titulo'],row['estado'],'; '.join(links),row['pendiente'].replace('|','/')))+' |')
        args.markdown.write_text('\n'.join(lines)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 0 if result['ok'] else 1

if __name__=='__main__':raise SystemExit(main())
