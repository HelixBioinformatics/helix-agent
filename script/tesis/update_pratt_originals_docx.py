#!/usr/bin/env python3
"""Update measured Pratt results from the current Word; preserve Chapters 1–3."""
import argparse
import hashlib
import io
import json
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import xml.etree.ElementTree as ET
from update_identifier_docx import q, text, replace_text

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'evaluation/trp/reference/pratt-author-20261001'

def paragraph(value, heading=False, note=False):
    p=ET.Element(q('p'))
    if heading:
        pr=ET.SubElement(p,q('pPr'))
        ET.SubElement(pr,q('pStyle'),{q('val'):'Heading2'})
        ET.SubElement(pr,q('outlineLvl'),{q('val'):'1'})
        ET.SubElement(ET.SubElement(pr,q('numPr')),q('numId'),{q('val'):'0'})
    r=ET.SubElement(p,q('r'))
    if note:
        pr=ET.SubElement(r,q('rPr'));ET.SubElement(pr,q('i'));ET.SubElement(pr,q('color'),{q('val'):'FF0000'})
    ET.SubElement(r,q('t')).text=value
    return p

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path);parser.add_argument('target',type=Path);args=parser.parse_args()
    summary=json.loads((BASE/'summary.json').read_text())
    assert summary['originalModelsRecovered']==78 and summary['originalFiles']==234
    primary=summary['profiles']['all-ten-repeats'];central=summary['profiles']['central-eight-repeats']
    assert primary['mechanicallyFlagged']==78 and primary['publishedProblemsMechanicallyFlagged']==5
    assert central['mechanicallyFlagged']==77 and primary['physicalSensitivity'] is None and primary['specificity'] is None
    source_sha=hashlib.sha256(args.source.read_bytes()).hexdigest()
    replacements={
      'La escala se establece desde el método experimental o desde el productor AlphaFold Monomer':
      'La escala se establece desde el método experimental o desde el productor AlphaFold Monomer y las métricas locales de mmCIF, con contraste entre pLDDT y el campo B. Para AFDB se exige correspondencia de entrada, versión, cadena, secuencia completa, dimensiones y URLs declaradas con la respuesta API archivada. Desde el 1 de octubre de 2026 se admite también el contrato local ColabFold para PDB monoméricos: identidad de rango y semilla, hashes de coordenadas y archivos originales de puntuación y PAE, secuencia completa y numeración continua, acuerdo de pLDDT y matrices PAE idénticas. No se atribuyen esos archivos a AFDB. Se evalúan ambos bloques dirigidos entre cada par de unidades, porque PAE puede ser asimétrica.',
      'Cada inspección conserva estructura, opciones, API y PAE cuando existen':
      'Cada inspección conserva estructura, opciones, API y PAE cuando existen o los metadatos y archivos originales de puntuación y PAE de ColabFold, catálogo, programa y reporte, con tamaños y SHA-256 en un manifiesto verificable sin red. El reporte identifica parser y versión de Python, estructura, modelo, productor, marco, escala, correspondencias y veredicto por control. La procedencia declarada y la verificación de integridad no autentican a los autores ni establecen validez biológica. El adaptador real de Helix reprodujo los reportes offline de los cinco ejemplos problemáticos de Pratt y sus copias portables superaron la verificación independiente.',
      'La auditoría de recuperación del artículo de Pratt et al. (2025) y de sus suplementos públicos':
      'El 1 de octubre de 2026 se incorporó un envío de los autores de Pratt et al. (2025), remitido por Daniel Rigden y recuperado por Dr Price. Contiene 78 modelos AF2 de rango 1, 78 archivos JSON de puntuación y 78 matrices PAE. Las secuencias coinciden exactamente con los 78 motivos de la Tabla S1 repetidos diez veces; todos los modelos superaron las comprobaciones de emparejamiento, confianza y ejes. Se conservaron los archivos originales y sus hashes. Los nombres model_1 a model_5 indican conjuntos de parámetros, no rangos adicionales: el envío solo incluye rank_001 y seed_000. No se sustituyeron originales por predicciones regeneradas.',
      'Se evaluaron cero modelos originales de ese estudio con la batería implementada':
      'Se vincularon cinco ejemplos problemáticos por coincidencia exacta de secuencia con las figuras 3, 6 y 7: 8b, 12ab, 19r, 21r y 22r. La referencia publicada describe hidrofobicidad expuesta, cargas internas apiladas, choques entre residuos o problemas identificados por Verify3D. Las otras 73 predicciones permanecen sin etiqueta de fallo o corrección; la clasificación de 32 modelos como β-solenoides no constituye por sí sola una etiqueta de fallo. No están en este envío los dos modelos preliminares sometidos a dinámica molecular en la figura 14 ni el ejemplo de mucina de la figura 1/S1.',
      'El protocolo F2 mantiene sensibilidad ≥80%, especificidad ≥90% y cobertura evaluable ≥90%':
      'El perfil principal, fijado antes de obtener los veredictos, conservó pLDDT mínimo de 70 y PAE máximo dirigido entre motivos de 5 Å sobre los diez motivos completos. Produjo 78 alarmas en 78 modelos: todos excedieron el límite PAE y 68 presentaron además algún residuo con pLDDT inferior a 70. Los cinco ejemplos problemáticos generaron alarma, 5/5, con intervalo Wilson de 95% de 56,6% a 100%. Esta tasa describe alarmas mecánicas sobre ejemplos ilustrados; no es una sensibilidad física validada ni prueba discriminación, porque también se marcaron todas las predicciones sin etiqueta. No se ajustaron retrospectivamente los umbrales.',
      'NOTA PARA EL AUTOR. Conservar explícita la diferencia entre confianza y plausibilidad. Pratt':
      'NOTA PARA EL AUTOR. Los originales de la Tabla S1 ya fueron recuperados y ejecutados. El resultado observado exige mantener la diferencia entre alarma mecánica y detección física: marcar 78/78 no demuestra discriminación. Para cerrar R3.8 se requiere un control físico validado y al menos 30 controles negativos pertinentes revisados, con evaluación independiente. Si estos resultados se emplean para diseñar o calibrar ese control, deben conservarse como desarrollo y no reutilizarse como una reserva intacta.',
      'El cierre elimina la deuda de implementación de cuota y controlador.':
      'El cierre elimina la deuda de implementación de cuota y controlador. No sustituye la evaluación reservada, las referencias externas ni los contratos pendientes de F5. Los originales de rango 1 de la Tabla S1 de Pratt fueron recuperados e inspeccionados posteriormente, el 1 de octubre de 2026; su validación física y los controles negativos siguen pendientes. La segunda estación es un anfitrión local accesible por SSH; no se declara como clúster.',
      'La recuperación pública de Pratt no proporcionó coordenadas ni PAE originales.':
      'La recuperación pública de Pratt no proporcionó coordenadas ni PAE originales. Una descarga de suplementos desde BioStudies presentó contenidos ajenos al artículo pese al identificador del registro; se descartó y se conservó evidencia de la discrepancia. Esa auditoría histórica no describe el envío posterior de los autores, incorporado el 1 de octubre de 2026: se inspeccionaron los 78 modelos originales de rango 1 de la Tabla S1. Sensibilidad física y especificidad permanecen sin calcular por falta de un control físico validado y de controles negativos pertinentes.',
      'La continuación técnica amplía el alcance verificable: incorpora detección STRPsearch':
      'La continuación técnica amplía el alcance verificable: incorpora detección STRPsearch, mapeo SIFTS por residuo integrado a Nextflow, geometría acotada sobre modelos predichos y lectura verificada de los originales locales de ColabFold proporcionados por los autores de Pratt et al. (2025). El diagnóstico de 78 modelos conserva procedencia, valores y veredictos. Que todos generen alarma bajo el perfil inicial muestra su límite para discriminar fallos físicos; no demuestra cumplimiento de R3.8. La comparación reservada, el acuerdo humano y la validación física permanecen pendientes.',
      'C9. Plausibilidad física. Pratt et al. (2025) muestran modelos repetitivos':
      'C9. Plausibilidad física. Pratt et al. (2025) muestran modelos repetitivos de confianza alta y conformación poco plausible. La batería no implementa un clasificador físico validado: el control permanece no evaluable en los 78 originales inspeccionados. Las alarmas PAE y pLDDT no identifican cargas internas, hidrofobicidad expuesta ni choques. Aprobar C1–C3 tampoco certificaría plausibilidad. El diagnóstico conserva esa cobertura física de 0% y separa las cinco referencias de problema publicadas de las predicciones sin etiqueta.',
      'Se conserva el artículo y los suplementos de Pratt bajo CC BY 4.0.':
      'Se conserva el artículo y los suplementos públicos de Pratt bajo su licencia CC BY 4.0 y la auditoría histórica de septiembre. El envío posterior de los autores proporciona las coordenadas y PAE de los 78 modelos AF2 de rango 1 de la Tabla S1. Se archivó localmente sin modificar sus bytes, con un manifiesto de hashes; no se supone que la licencia del artículo cubra automáticamente este envío separado. Las condiciones de redistribución no se especificaron en el correo compartido. No se generaron predicciones sustitutas.',
      'La evaluación reservada de F6 conserva el protocolo, las particiones y las referencias independientes exigidas.':
      'La evaluación reservada de F6 conserva el protocolo, las particiones y las referencias independientes exigidas. La asesora ha sido designada para la anotación y el modelo y presupuesto fueron elegidos por el autor; estas decisiones no equivalen a anotaciones terminadas ni a una configuración efectiva verificada. Los originales de rango 1 de la Tabla S1 de Pratt se recuperaron el 1 de octubre de 2026 y se inspeccionaron; faltan la validación física y los controles negativos pertinentes para R3.8. Los casos 2xqh y P69905 continúan excluidos de la reserva.',
    }
    with ZipFile(args.source) as archive:
        raw=archive.read('word/document.xml')
        for _,(prefix,uri) in ET.iterparse(io.BytesIO(raw),events=['start-ns']):
            if not prefix.startswith('ns'):ET.register_namespace(prefix,uri)
        doc=ET.fromstring(raw);body=doc.find(q('body'));items=list(body)
        boundary=next(i for i,p in enumerate(items) if text(p)=='Presentación de los resultados esperados')
        closed=[ET.tostring(p) for p in items[:boundary]]
        if any(text(p)=='A.24. Modelos originales de Pratt y diagnóstico de la batería' for p in body):raise ValueError('already updated')
        changed=[];used=set()
        for item in items[boundary:]:
            for p in item.iter(q('p')):
                old=text(p)
                for prefix,value in replacements.items():
                    if old.startswith(prefix):
                        replace_text(p,value);used.add(prefix);changed.append({'before':old,'after':value})
                        # A historical paragraph explicitly selected Gungsuh.
                        # Newly written prose uses the template's Times New Roman.
                        for pr in p.findall(q('r')+'/'+q('rPr')):
                            fonts=pr.find(q('rFonts'))
                            if fonts is not None and fonts.get(q('ascii'))=='Gungsuh':pr.remove(fonts)
                        break
        if used!=set(replacements):raise ValueError('missing expected paragraphs: '+repr(set(replacements)-used))
        note=next(p for p in body if text(p).startswith('NOTA PARA EL AUTOR. Los originales de la Tabla S1'))
        index=list(body).index(note)
        additions=[
          'Un segundo perfil diagnóstico, también fijado antes de la ejecución, seleccionó los ocho motivos centrales sin cambiar los umbrales ni las matrices completas. Marcó 77/78 modelos y conservó las cinco alarmas; solo 10ab obtuvo admisión mecánica en esa selección. El perfil es un diagnóstico de los extremos y no reemplaza al principal. Los intervalos son motivos conocidos de la construcción de las secuencias, no una anotación independiente de unidades estructurales.',
          'El control de plausibilidad física permaneció no evaluable en 78/78 modelos, por lo que la cobertura física es 0%. Sensibilidad física y especificidad permanecen sin calcular; la tasa conservadora de detección física sobre los cinco ejemplos etiquetados es 0/5. No se dispone todavía de los al menos 30 controles negativos pertinentes con anotación revisada de RepeatsDB previstos en T-STRUCT. Se conservan las metas F2 de sensibilidad ≥80%, especificidad ≥90% y cobertura ≥90%, sin declarar su cumplimiento. La ausencia de coordenadas y PAE de la Tabla S1 deja de ser el bloqueo.',
          'La evidencia de esta incorporación se conserva en evaluation/trp/reference/pratt-author-20261001/: manifiesto de 234 originales, correspondencias, perfiles y etiquetas fijados, 156 reportes de control y CSV de resultados. Nueve medias de pLDDT difieren del redondeo esperado de la tabla, con diferencia máxima de 0,0797 puntos; se conservaron ambos valores y los cinco ejemplos problemáticos no presentan esa discrepancia. No hubo llamadas al modelo ni consumo de AWS.',
        ]
        for value in additions:body.insert(index,paragraph(value));index+=1
        section=body.find(q('sectPr'));index=list(body).index(section) if section is not None else len(body)
        annex=[paragraph('A.24. Modelos originales de Pratt y diagnóstico de la batería',heading=True),
          paragraph('El envío de los autores incorporado el 1 de octubre de 2026 contiene 78 conjuntos de tres archivos: PDB AF2 no relajado de rango 1, puntuaciones JSON y PAE JSON. El adaptador ColabFold exige hashes coincidentes, identidad de rango/semilla y nombres, una cadena completa y sin ambigüedad, secuencia idéntica al motivo de Tabla S1 repetido diez veces, pLDDT consistente con la columna B y matrices PAE idénticas. El código oficial de ColabFold 1.5.2 explica que las celdas PAE se redondean a dos decimales y max_pae no; el contraste admite únicamente 0,005 Å por serialización, sin cambiar el umbral de 5 Å.'),
          paragraph('El archivo freeze.json fija fuentes, hashes, cinco referencias problemáticas y los dos perfiles antes de sus veredictos. Es un diagnóstico acotado, no una congelación completa de F6 ni una afirmación de checkout global limpio. Se reproducen las inspecciones con script/tesis/evaluate_pratt_originals.py; la opción verify contrasta los 234 originales y los 156 reportes con sus hashes. script/tesis/run_pratt_inspection.ts ejecuta el adaptador real del agente para los cinco ejemplos, verifica sus copias portables y comprueba igualdad con los reportes offline.'),
          paragraph('Los resultados se conservan con valor, umbral y estado: 78/78 alarmas en el perfil principal y 77/78 en el central. Cinco ejemplos publicados generan alarma en ambos; el control físico sigue no evaluable en todos. Los otros 73 modelos no se etiquetan retrospectivamente como correctos o fallidos. Faltan los modelos preliminares de las figuras 1/S1 y 14 y los rangos 2 a 5. La sensibilidad física y la especificidad no se completan sin un control físico validado y negativos independientes pertinentes.'),
          paragraph('NOTA PARA EL AUTOR. La conclusión defendible de esta entrega es la recuperación íntegra de la Tabla S1 y la limitación observada de los controles mecánicos para discriminar problemas físicos. No presentar 5/5 alarmas como validación completa de R3.8 ni 32 β-solenoides como 32 fallos demostrados.',note=True)]
        for p in annex:body.insert(index,p);index+=1
        assert [ET.tostring(p) for p in list(body)[:boundary]]==closed
        args.target.parent.mkdir(parents=True,exist_ok=True)
        with ZipFile(args.target,'w',ZIP_DEFLATED) as out:
            for entry in archive.infolist():
                out.writestr(entry,ET.tostring(doc,encoding='utf-8',xml_declaration=True) if entry.filename=='word/document.xml' else archive.read(entry.filename))
    save={'sourceSha256':source_sha,'targetSha256':hashlib.sha256(args.target.read_bytes()).hexdigest(),
          'closedBodyElementsPreserved':boundary,'changedParagraphs':changed,'addedResultParagraphs':len(additions),
          'addedAnnexParagraphs':len(annex),'summarySha256':hashlib.sha256((BASE/'summary.json').read_bytes()).hexdigest(),
          'chapters1to3Unchanged':True,'originalFilesReplaced':False}
    (BASE/'document-checks.json').write_text(json.dumps(save,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps({'changedParagraphs':len(changed),'chapters1to3Unchanged':True,'sourceSha256':source_sha,'targetSha256':save['targetSha256']}))

if __name__=='__main__':main()
