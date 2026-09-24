#!/usr/bin/env python3
"""Apply Helix branding and verified development results without changing thesis metrics."""
import argparse,hashlib,io,json,zipfile
from pathlib import Path
import xml.etree.ElementTree as E
from update_identifier_docx import replace_text,q,text
ROOT=Path(__file__).resolve().parents[2]
def para(value,heading=False):
    p=E.Element(q('p'))
    if heading:
        pr=E.SubElement(p,q('pPr'));E.SubElement(pr,q('pStyle'),{q('val'):'Heading2'});E.SubElement(pr,q('outlineLvl'),{q('val'):'1'});E.SubElement(E.SubElement(pr,q('numPr')),q('numId'),{q('val'):'0'})
    E.SubElement(E.SubElement(p,q('r')),q('t')).text=value
    return p

def main():
    a=argparse.ArgumentParser();a.add_argument('source',type=Path);a.add_argument('target',type=Path);args=a.parse_args()
    evidence=json.loads((ROOT/'evaluation/trp/verification-20260923/output/summary.json').read_text());assert evidence['ok']
    final=json.loads((ROOT/'evaluation/trp/verification-20260923/integration.json').read_text());assert final['verified']
    source_sha=hashlib.sha256(args.source.read_bytes()).hexdigest()
    with zipfile.ZipFile(args.source) as z:
        raw=z.read('word/document.xml')
        for _,(prefix,uri) in E.iterparse(io.BytesIO(raw),events=['start-ns']):
            if not prefix.startswith('ns'):E.register_namespace(prefix,uri)
        doc=E.fromstring(raw);body=doc.find(q('body'));branding=0
        for p in doc.iter(q('p')):
            old=text(p);new=old.replace('Bioinformática.org','Helix Agent')
            if old.startswith('La geometría de modelos predichos se verificó en una ruta CLI separada'):
                new='La geometría de modelos predichos se verificó inicialmente mediante una CLI y luego se integró al agente mediante trp_predicted_geometry, con identidad AFDB y pLDDT conservados. La continuación de este capítulo documenta la ejecución. Es una ruta dedicada: todavía no comparte toda la admisión de trp_prepare/trp_run ni su cuota dura. Los casos multicadena y la ampliación completa del dominio conservan límites explícitos.'
            if new!=old:replace_text(p,new);branding+=1
        heading='Verificación de Helix en la segunda estación'
        assert not any(text(p)==heading for p in body)
        paragraphs=[
            'El nombre vigente de la implementación es Helix Agent y el comando de terminal es helix. Las rutas y nombres conservados en evidencias fechadas identifican versiones históricas del mismo proyecto.',
            'La estación de laboratorio ejecutó el binario publicado Helix 0.3.0. El diagnóstico detectó ocho CPU y Docker; Nextflow 26.04.4 se encontró al incorporar su directorio de usuario al PATH de la sesión SSH. El instalador reconoció la versión existente sin desinstalar ni alterar el hash del binario. Este contraste verifica idempotencia de instalación; no mide una actualización entre versiones distintas.',
            'La copia portable de la referencia SIFTS pasó la comprobación independiente de 139 archivos contra el hash externo previamente conservado; una alteración de la estructura produjo rechazo. La orden helix verify aceptó un corpus mínimo íntegro y rechazó su alteración. Ese corpus es sintético y solo prueba el mecanismo de integridad. Una nueva ejecución real de GeomeTRe en contenedor sin red produjo las mismas doce unidades y un CSV idéntico byte a byte a la referencia de desarrollo 2xqh/A.',
            'El contraste científico usó dos CPU y 2 GiB de memoria. No se aplicó cuota dura de almacenamiento en esta ejecución, por lo que no extiende la garantía estricta de R2.2 a todas las rutas. Las comprobaciones no efectuaron llamadas al modelo y no acreditan exactitud biológica, comprensión del lenguaje ni ejecución en un clúster.',
            final['document_paragraph'],
            'El código incorpora una orden explícita helix upgrade para el canal oficial. La versión publicada 0.3.0 verificada en el laboratorio todavía no contiene esa orden. La disponibilidad del cambio en el repositorio no equivale a una nueva publicación instalable. Los ensayos, aprobaciones sintéticas y límites se documentan en evaluation/trp/verification-20260923/.',
        ]
        chapter=next(p for p in body if text(p)=='Conclusiones y trabajos futuros');index=list(body).index(chapter)
        for p in [para(heading,True)]+[para(v) for v in paragraphs]:body.insert(index,p);index+=1
        section=body.find(q('sectPr'));index=list(body).index(section) if section is not None else len(body)
        for p in [para('A.23. Verificación de despliegue de Helix y continuidad técnica',True),para('El programa script/tesis/verify_helix_workstation.py registra versión y SHA del binario, entorno, decisiones de verificadores y ejecución científica. Los casos alterados deben producir salida no nula; el contraste positivo debe reproducir el CSV de referencia. Su resumen se conserva en evaluation/trp/verification-20260923/output/summary.json. El ensayo distingue binario publicado, código fuente en desarrollo y contenedor científico fijado.'),para(final['document_paragraph']),para('La evaluación reservada de F6 conserva el protocolo, las particiones y las referencias independientes exigidas. Siguen pendientes el anotador, el modelo y presupuesto de campaña y los originales estructurales o la enmienda prospectiva de su corpus. Los casos 2xqh y P69905 de esta entrega continúan excluidos de la reserva.')]:body.insert(index,p);index+=1
        args.target.parent.mkdir(parents=True,exist_ok=True)
        with zipfile.ZipFile(args.target,'w',zipfile.ZIP_DEFLATED) as out:
            for item in z.infolist():out.writestr(item,E.tostring(doc,encoding='utf-8',xml_declaration=True) if item.filename=='word/document.xml' else z.read(item.filename))
    print(json.dumps({'source_sha256':source_sha,'branding_paragraphs':branding,'evidence_verified':True}))
if __name__=='__main__':main()
