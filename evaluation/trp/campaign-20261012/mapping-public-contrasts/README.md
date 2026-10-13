# Contraste público del mapeo de residuos de Helix

## Resultado y alcance

Se conservaron las 30 cadenas públicas del conjunto experimental previamente seleccionado. No se usaron coordenadas privadas de Pratt, 2XQH, modelos de lenguaje ni AWS. El módulo real de Helix coincidió con las expectativas obtenidas de las fuentes públicas en todas las comparaciones realizadas. Esta evidencia de desarrollo amplía la cobertura de R1.6; no sustituye una referencia independiente de una experta ni una evaluación reservada de anotaciones biológicas.

Los denominadores corresponden a operaciones diferentes:

- **11 751/11 751** posiciones con CA en mmCIF: mapeo individual real de `label_seq_id` a numeración de autor, con igualdad de identidad, coordenadas y factor B frente al PDB oficial.
- **30/30** cadenas: las filas del parser SIFTS real coincidieron exactamente con las extraídas por separado del XML oficial. El XML contiene **11 749** residuos observados con referencia a la accesión seleccionada y **265** no observados, que se conservaron en las expectativas.
- **28/30** solicitudes completas de preparación fueron admitidas y mapearon **11 215** residuos UniProt. Las otras **2/30** fueron rechazadas correctamente por falta de CA. Ambos rechazos permanecen en el denominador.

El contraste no mide identificación de repeticiones, exactitud de límites biológicos, validez física ni rendimiento de lenguaje natural. Los intervalos son sondas de numeración construidas por continuidad de los identificadores públicos. Un único intervalo se dividió en dos para cumplir el contrato existente del adaptador; no se interpretó como dos unidades biológicas.

## Fuentes y protocolo previo

`protocol.json` fijó las 30 identidades PDB/cadena/accesión, las versiones y hashes del productor y los límites de ejecución antes de descargar las fuentes. `audit-method.json` fijó el auditor separado; `oracle-freeze.json` selló fuentes y expectativas antes de ejecutar Helix. Se descargaron CIF y PDB oficiales de RCSB y XML SIFTS oficial de EBI. [Descargas oficiales de RCSB](https://www.rcsb.org/docs/programmatic-access/file-download-services), [distribución de SIFTS](https://www.ebi.ac.uk/pdbe/docs/sifts/quick.html).

Se intentó primero `xml_remediated`; únicamente un HTTP 404 habilitó la alternativa oficial `xml`. Ocurrió en las 30 cadenas y está registrado como `availabilityFallback: true`, junto con URL efectiva, fecha, `Last-Modified`, bytes y SHA256. El código de adquisición congelado admite esta alternativa sólo después de 404. Los archivos se conservaron completos, incluyendo XML comprimido y descomprimido. Los límites fueron una petición por URL, 30 segundos de transporte y 20 MB por archivo y XML descomprimido; tres trabajadores de adquisición y un trabajador científico, con una ejecución primaria por cadena y límite de 180 segundos.

Las expectativas se construyeron a partir de filas `_atom_site` del mmCIF, columnas fijas del PDB y referencias por residuo del XML con sus espacios de nombres. No se interpolaron extremos de segmentos ni se usó el mapeo producido por Helix como referencia. SIFTS distingue las referencias por residuo y la numeración del autor; los extremos de segmentos no bastan para representar inserciones o numeración discontinua. [Documentación del XML SIFTS](https://www.ebi.ac.uk/pdbe/docs/sifts/efamily.html).

Gemmi 0.7.5 se compartió exclusivamente como lector léxico de CIF entre productor y expectativa. La selección de filas, unión con PDB/XML, identidad y comprobación de coordenadas se implementaron aparte. Por ello la independencia cubre esas operaciones y no valida posibles fallos comunes del lector CIF. El SHA del fixture heredado de especificación tipada se registró al cerrar la evidencia, después de ejecutar, y se identifica expresamente como dependencia capturada retrospectivamente; no se presenta como parte de la congelación prospectiva.

## Rechazos y posiciones conservadas

`2bm4-A` tiene GLY de autor **182**, UniProt **182**; `1o8i-A` tiene LYS de autor **353**, UniProt **375**. SIFTS los marca observados, pero las filas oficiales de átomos contienen sólo **N**, sin CA. Por eso la preparación completa produce `sifts-identity`. La falta se comprobó en la fuente, antes de aceptar el rechazo del productor. No se eliminaron estos residuos para forzar una preparación exitosa.

Cuatro posiciones con CA carecen de referencia observada a la accesión seleccionada: `1k28-A` SER576, HIS583, HIS584 y `1k4z-A` MET1368 (`label_seq_id` 1). Conservan su resultado válido para mapeo label/autor y quedan fuera de la solicitud UniProt porque no existe esa correspondencia seleccionada en la fuente. Estas cuatro posiciones y los dos residuos sin CA explican la diferencia entre 11 751 y 11 749.

En este conjunto no se observaron códigos de inserción ni ubicaciones alternativas. Este resultado **no demuestra cobertura del dominio de inserciones o ambigüedades reales**. La selección experimental anterior ya favorecía cadenas aptas para los análisis estructurales.

## Auditoría y reproducción

`audit.json`, `chain-outcomes.csv` y `residue-outcomes.csv` conservan las comparaciones por cadena y residuo. El auditor compara los resultados reales con las expectativas congeladas. El verificador final comprueba además el conjunto exacto de etiquetas, duplicados, SHA de fuentes y código, ausencia de cambios en las expectativas y manifestación de todos los archivos.

Tras terminar los 30 casos, un plan secundario fijó una reproducción para `1bhe-A` y ambos rechazos, con los mismos archivos, versiones y parámetros, una sola vez por caso. Los tres informes fueron idénticos byte por byte a los primarios. `reproduction/plan.json` y `reproduction/verification.json` conservan esta comprobación; no añaden casos científicos ni convierten rechazos en éxitos.

Desde la raíz del repositorio:

```bash
/home/webiwabou/.local/state/helix/freesasa-20261012/venv/bin/python script/tesis/public_mapping_contrasts.py verify-sources
/home/webiwabou/.local/state/helix/freesasa-20261012/venv/bin/python script/tesis/audit_public_mapping_contrasts.py
/home/webiwabou/.local/state/helix/freesasa-20261012/venv/bin/python script/tesis/verify_public_mapping_evidence.py
```

El segundo comando regenera determinísticamente las tablas de auditoría; el primero y el tercero sólo leen. `manifest.json` contiene SHA y tamaño de cada archivo de evidencia y de los helpers. Para reproducir las ejecuciones se usa `run_public_mapping_contrasts.ts` con cada ID del protocolo y el Python congelado, sin habilitar validadores físicos opcionales. Los informes originales ya están sellados y deben conservarse al reproducir en otra carpeta o checkout.
