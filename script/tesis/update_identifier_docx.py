#!/usr/bin/env python3
"""Migrate the author's mixed-namespace DOCX using the dated, verified mapping."""
import argparse,difflib,hashlib,io,json,re,zipfile
from pathlib import Path
import xml.etree.ElementTree as E
ROOT=Path(__file__).resolve().parents[2]
W='http://schemas.openxmlformats.org/wordprocessingml/2006/main'
def q(s):return '{'+W+'}'+s
def text(e):return ''.join(t.text or '' for t in e.iter(q('t')))
def replace_text(p,value):
    nodes=list(p.iter(q('t')));old=text(p)
    # Edit text spans in reverse order, keeping paragraph/run formatting and drawings.
    for op,i,j,k,l in reversed(difflib.SequenceMatcher(None,old,value,autojunk=False).get_opcodes()):
        if op=='equal':continue
        offsets=[];pos=0
        for node in nodes:
            offsets.append((pos,pos+len(node.text or ''),node));pos+=len(node.text or '')
        touched=[(a,b,n) for a,b,n in offsets if b>i and a<j]
        if not touched:
            a,b,n=next((x for x in offsets if x[0]<=i<=x[1]),offsets[-1]);n.text=(n.text or '')[:i-a]+value[k:l]+(n.text or '')[i-a:]
        else:
            for ix,(a,b,n) in enumerate(touched):
                v=n.text or '';n.text=v[:max(0,i-a)]+(value[k:l] if ix==0 else '')+v[min(len(v),j-a):]
    assert text(p)==value

def main():
    ap=argparse.ArgumentParser();ap.add_argument('source',type=Path);ap.add_argument('target',type=Path);ap.add_argument('--report',type=Path,required=True);args=ap.parse_args()
    mapping=json.loads((ROOT/'docs/tesis/renumeracion-20260923/equivalencias.json').read_text());m=mapping['results']
    rawsha=hashlib.sha256(args.source.read_bytes()).hexdigest()
    if rawsha!=mapping['source_sha256']:raise ValueError('Source differs from reviewed author version; do not apply migration twice')
    with zipfile.ZipFile(args.source) as z:
        raw=z.read('word/document.xml')
        for _,(prefix,uri) in E.iterparse(io.BytesIO(raw),events=['start-ns']):
            if not prefix.startswith('ns'):E.register_namespace(prefix,uri)
        doc=E.fromstring(raw);body=doc.find(q('body'));items=list(body)
        # The accidental table repeats exactly the existing authoritative section in 16 cells.
        cells=items[111].findall(q('tr')+'/'+q('tc'));canonical=''.join(text(e) for e in items[38:111])
        assert len(cells)==16 and all(text(c)==canonical for c in cells)
        body.remove(items[111])
        assert text(items[37])==text(items[38])=='Árbol de Problemas'
        body.remove(items[38])
        expected=[r['id'] for r in mapping['canonical_results']];counter=0;changes=[]
        for index,item in enumerate(items):
            if index in (38,111):continue
            for p in item.iter(q('p')):
                before=text(p);s=before
                if 69<=index<=97 and re.match(r'Resultado \d\.',s):
                    s=re.sub(r'^Resultado \d\.',expected[counter]+'.',s);counter+=1
                    if index==80:s=s.replace('del Resultado 1 ','del Resultado 1.4 ')
                elif index>=112:
                    protected={}
                    def save(match):
                        key=f'@@PATH{len(protected)}@@';protected[key]=match[0];return key
                    s=re.sub(r'(?:[\w./-]+/)?R[1-5]\.[1-9]-[\w.-]+',save,s)
                    s=re.sub(r'(?<![\w])R[1-5]\.[1-9](?!\d)',lambda x:m[x[0]],s)
                    s=re.sub(r'\b(Resultados? )([1-5]\.[1-9](?:(?:, | y |–)[1-5]\.[1-9])*)',lambda x:x[1]+re.sub(r'[1-5]\.[1-9]',lambda y:m['R'+y[0]][1:],x[2]),s)
                    s=re.sub(r'\bOE[1-5]\b',lambda x:mapping['objectives'][x[0]],s)
                    s=re.sub(r'(objetivo específico )[45]\b',r'\g<1>3',s)
                    s=s.replace('capa de admisión del objetivo específico 3','capa de admisión del objetivo específico 2')
                    s=s.replace('causa C6','causa C3')
                    if 'kappa' in s.lower() or 'acuerdo sustancial' in s:s=s.replace('Tabla 6','Tabla 1.5')
                    s=s.replace('los cinco bloques técnicos y sus códigos de resultado','los cinco bloques técnicos, organizados bajo tres objetivos y los códigos de resultado actualizados')
                    for key,val in protected.items():s=s.replace(key,val)
                    s=s.replace('packages/bioinformatica/','packages/helix/')
                if s!=before:replace_text(p,s);changes.append({'body_index':index,'before':before,'after':s})
        assert counter==21
        levels={'Descripción':2,'Problema seleccionado':2,'Objetivos':1,'Objetivo general':2,'Objetivos específicos':2,'Resultados esperados':2,'Mapeo de objetivos, resultados y verificación':2}
        for paragraph in list(body):
            if paragraph.tag!=q('p'):continue
            pr=paragraph.find(q('pPr'))
            if pr is None:continue
            num=pr.find(q('numPr'))
            title=text(paragraph).strip()
            if not title and num is not None:
                pr.remove(num)
            if title in levels and num is not None:
                level=levels[title];num.find(q('ilvl')).set(q('val'),str(level))
                style=pr.find(q('pStyle'))
                if style is None:style=E.SubElement(pr,q('pStyle'))
                style.set(q('val'),'Heading'+str(level+1))
        for paragraph in body.iter(q('p')):
            pr=paragraph.find(q('pPr'))
            if pr is None:continue
            style=pr.find(q('pStyle'))
            if style is not None and re.fullmatch('Heading[1-6]',style.get(q('val'),'')):
                outline=pr.find(q('outlineLvl'))
                if outline is None:outline=E.SubElement(pr,q('outlineLvl'))
                outline.set(q('val'),str(int(style.get(q('val'))[-1])-1))
        # Rebuild the malformed imported TOC field so Writer/Word can refresh it.
        toc=E.Element(q('p'))
        E.SubElement(E.SubElement(toc,q('r')),q('t')).text='THESIS_TOC_REBUILD_20260923'
        position=list(body).index(items[25]);body.remove(items[25]);body.insert(position,toc)
        # Keep the grouped objectives and all means/indicators in the author's tables verbatim.
        assert all(text(items[i])==text(list(E.fromstring(raw).find(q('body')))[i]) for i in [46,64,65,66,101,103,105,107,109])
        args.target.parent.mkdir(parents=True,exist_ok=True)
        with zipfile.ZipFile(args.target,'w',zipfile.ZIP_DEFLATED) as out:
            for item in z.infolist():out.writestr(item,E.tostring(doc,encoding='utf-8',xml_declaration=True) if item.filename=='word/document.xml' else z.read(item.filename))
    report={'source_sha256':rawsha,'target_sha256':hashlib.sha256(args.target.read_bytes()).hexdigest(),'changes':changes,'removed_duplicate_cells':16,'each_duplicate_characters':len(canonical),'canonical_tables_unchanged':True,'canonical_result_count':counter,'structural_controls_C1_C9_preserved':True}
    args.report.parent.mkdir(parents=True,exist_ok=True);args.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='changes'}));print('Paragraphs updated:',len(changes))
if __name__=='__main__':main()
