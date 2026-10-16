# Herramientas de evidencia de la tesis

## Campaña de AWS Academy, octubre de 2026

La [campaña actual](../../evaluation/trp/campaign-20261012/README.md) conserva
congelaciones, intentos fallidos y verificaciones posteriores. Los ejemplos
históricos de edición de Word que siguen reproducen sus revisiones originales.

- `aws_academy_cluster.py`: opera sólo sobre recursos registrados y etiquetados
  del laboratorio seleccionado; mantiene separados ambos estados y credenciales.
- `aws_academy_prepare_remote.py`: prepara la configuración privada de Helix,
  verifica imagen/entorno y liga el plazo a Academia y a los tres guardas de
  apagado por arranque. Las claves permanecen fuera del repositorio.
- `record_academy_state.py`: obtiene una respuesta EC2 nueva y registra los
  estados de los nodos; `--require-stopped` falla si todavía queda cómputo activo.
- `provision_r24_workspace.py`: crea una única imagen XFS aislada para contrastes
  de ingeniería, sin nuevas instancias o volúmenes. Se niega a reformatear rutas
  existentes. `resume_r24_workspace.py` remonta esa misma imagen tras reiniciar,
  sin recrearla ni restablecer cuotas, y verifica los mounts NFS.
- `summarize_remote_workflows.py`: audita paquetes con sus propias referencias
  numéricas, separa primeros intentos y reintentos y cuenta IDs únicos.
- `audit_remote_campaign.py`: comprueba los paquetes, trabajos Slurm, límites
  observados, eventos y métodos. El oráculo de eventos puede suministrarse desde
  las acciones del corredor, independientemente del registro producido.
- `verify_structural_campaign.py --inputs`: verifica evidencia estérica primaria,
  coordenadas privadas y recursos químicos instalados, sin repetir mediciones.
  `structural_runtime_contrast.py verify` necesita el Python CCTBX fijado en su
  congelación, pues comprueba también los módulos instalados bajo `sys.prefix`.
  `verify_sasa_campaign.py` comprueba áreas, residuos, ausencias y denominadores.
- `update_academy_campaign_docx.py`: genera una copia desde el Word actual con
  resultados observados. `audit_academy_docx.py` contrasta la copia renderizada
  y su PDF con el original antes de instalarla.

Las cuotas del workspace experimental del head no acreditan la cuota agregada
de cliente y clúster. Las variantes de desarrollo, aprobaciones del corredor y
diagnósticos continuos tampoco sustituyen las referencias humanas reservadas.

## Comprobación independiente de instantáneas

`verify_snapshot.py` requiere Python 3.9 o posterior y únicamente su biblioteca estándar. Se puede copiar junto a un corpus a otra máquina. No importa código de Helix Agent, no ejecuta el modelo, no escribe archivos y no usa la red.

```bash
python3 script/tesis/verify_snapshot.py /ruta/corpus/repeatsdb.manifest.json
```

Lee el contrato de `packages/helix/src/bio/snapshot.ts`: `data` es relativo al manifiesto; `rows`, `bytes` y `sha256` deben coincidir con el NDJSON. Calcula el hash de los bytes originales, cuenta y analiza cada registro JSON. Rechaza archivos ausentes, rutas fuera del paquete, claves JSON duplicadas, JSON inválido, filas vacías y metadatos incompatibles. Un corpus vacío explícito (`rows=0`, `bytes=0`, hash del archivo vacío) es válido. Omitir todos los manifiestos es un error.

La salida es JSON; código 0 significa que todas las instantáneas indicadas coinciden, 1 que alguna falla y 2 que la invocación es inválida. No descubre manifiestos automáticamente ni verifica manifiestos de **ejecución**: ese contrato se completa en F4. Tampoco acredita autenticidad, corrección biológica ni integridad frente a quien altera a la vez los datos y el manifiesto. Para autenticidad hace falta un hash de referencia conservado por un tercero.

Las pruebas diferenciales usan la serialización y el hash reales del productor TypeScript y ejecutan Python como proceso independiente:

```bash
cd packages/helix
bun test test/bio/independent-verify.test.ts
```

Incluyen un traslado del paquete, alteraciones de datos y contadores, JSON inválido con hash coincidente y escapes de ruta. No son una evaluación de los indicadores biológicos de la tesis.

## Edición y revisión del documento de la primera fase

`update_phase1_docx.py` aplica `docs/tesis/fase1-documento.json` a la revisión original de la tesis cuyo SHA-256 se declara en el script. Requiere Python estándar, escribe una copia nueva y rechaza un origen distinto o un destino existente. Conserva los saltos de sección, las partes de figuras y anotaciones; modifica el cuerpo, los estilos de encabezado y la actualización de campos. Para reproducir esa edición se necesita el respaldo original con el hash indicado.

```bash
python3 script/tesis/update_phase1_docx.py /ruta/respaldo-original.docx /tmp/revision/Tesis.docx
/usr/bin/python3 script/tesis/render_docx.py /tmp/revision/Tesis.docx /tmp/renderizado
```

`render_docx.py` requiere LibreOffice y su módulo Python UNO. Abre una instancia aislada sin interfaz, con macros desactivadas, recalcula el índice y exporta DOCX/PDF a un directorio nuevo. El renderizado reserializa el Word; por ello se comparan el texto de referencias y las ilustraciones activas, y se revisan visualmente las páginas afectadas antes de reemplazar el original. No usa una sesión de Word o LibreOffice que el usuario tenga abierta.

Estos scripts registran la transformación de F1. Para fases posteriores se edita la revisión actual: no se cambia el hash esperado para forzar la reaplicación de F1 sobre un Word ya modificado.

## Fase 2: catálogo, protocolo y Word

- `bun script/tesis/check_trp_catalog.ts`: comprueba sin red los archivos de referencia de las operaciones admitidas. Los contratos están en `packages/helix/src/trp/`; el alcance y la reproducción se documentan en `evaluation/trp/README.md`.
- `run_geometre_reference.py` y `geometre.Dockerfile`: ejecutan el ejemplo real de GeomeTRe con versión, imagen y dependencias registradas. El catálogo enlaza la ejecución con todas las dependencias fijadas; el ejemplo requiere unidades suministradas.
- `update_phase2_docx.py`: aplica `docs/tesis/fase2-documento.json` sobre el Word final de F1, identificado por hash. Corrige R2.1, añade A.16 con los 21 criterios, actualiza avance y conserva secciones, imágenes y referencias. Es una migración entre revisiones conocidas, no un generador que se deba aplicar otra vez al Word actual.

Ejemplo de edición sobre una copia conservada de la revisión F1:

```bash
python3 script/tesis/update_phase2_docx.py /ruta/copia-fase1.docx /tmp/nueva-fase2/Tesis.docx
/usr/bin/python3 script/tesis/render_docx.py /tmp/nueva-fase2/Tesis.docx /tmp/revision-fase2
```

El renderizador usa una sola fuente de encabezados para evitar duplicados en el índice, actualiza campos y conserva las páginas automáticas entre secciones. `FilterData` se pasa a UNO como una secuencia tipada de propiedades; de otro modo Writer ignora la opción de páginas vacías y el PDF puede tener menos páginas que el campo `NUMPAGES`.

**Corrección del registro de F1:** su script insertaba un `w:r` directamente en celdas vacías, y LibreOffice descartaba ese texto inválido. F2 coloca el texto dentro de `w:p`, corrige también el script histórico y comprueba las dos celdas de R2.1 en el DOCX ya renderizado. El registro de F1 que las daba por llenas no constituye evidencia de que hubieran sobrevivido a aquella exportación.

## F4: admisión y evidencia portable

- `update_phase4_docx.py` exige el hash del Word instalado de F3 y aplica `docs/tesis/fase4-documento.json` a un archivo nuevo.
- `render_docx.py` exporta, reabre el Word y actualiza de nuevo índices/campos antes de la entrega final. F4 conserva páginas automáticas de separación y comprueba que NUMPAGES coincide con el PDF físico.
- `audit_phase4_docx.py` audita la revisión renderizada contra el F3 todavía instalado. Tras instalar F4, este guardia histórico deja de ser aplicable a `Tesis.docx`; la evidencia final conserva ambos hashes. Es intencional: no se debe volver a aplicar la fase ni alterar su hash esperado para forzar una nueva revisión.
- `audit_trp_bundle.py BUNDLE OUTPUT.json` verifica una copia con el verificador independiente del repositorio y prueba la ausencia/alteración de cada archivo, rutas inseguras y otras discrepancias. El contenido binario científico se comprueba por bytes; no se deserializa.
- `packages/helix/src/trp/verify_bundle.py.txt` es la fuente del verificador que se publica como `verify.py` en cada paquete. Se puede ejecutar directamente con Python 3.

La referencia de F4, sus limitaciones y el pseudocódigo se documentan en `docs/tesis/F4-ADMISION.md`. R3.2 conserva pendientes la cuota agregada y las reservas efectivas; la fórmula de almacenamiento es una estimación declarada.

## Identificadores vigentes y generadores históricos

Desde el 23/09/2026 se usan R1.1–R1.9, R2.1–R2.4 y R3.1–R3.8. Consulte [las equivalencias](../../docs/tesis/renumeracion-20260923/README.md). Los programas `update_*_docx.py`, `audit_phase*_docx.py`, `audit_r32_docx.py` y sus JSON de contenido reproducen versiones históricas: no ejecutarlos sobre el Word vigente sin adaptar sus selectores, numeración y contenido. Los códigos de resultado dentro de archivos de referencia son históricos. El auditor de trazabilidad utiliza la numeración actual.

`update_identifier_docx.py` aplica exclusivamente la migración editorial de septiembre de 2026 al hash del Word fuente registrado: preserva formato por tramo de texto, comprueba tablas y elimina solo la duplicación exacta detectada. Su salida usa un marcador explícito para reconstruir el índice con `render_docx.py --rebuild-index`; no admite reejecutar la renumeración sobre el documento ya migrado.
