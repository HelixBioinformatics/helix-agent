# Documento entregado

El archivo editable principal es `/home/webiwabou/Projects/Tesis.docx` y su
exportación es `/home/webiwabou/Projects/Tesis.pdf`. `installation.json`
registra sus hashes efectivos, la copia del original y las comprobaciones
previas a la instalación. La entrega tiene 155 páginas y 21 filas con los
identificadores actuales de resultados. No declara la tesis científicamente
terminada.

Se incorporaron las mediciones técnicas, sus fallos y límites, tres figuras
propias, conclusiones ajustadas y el anexo A.25. El texto de los capítulos 1
a 3, las referencias originales y las cuatro imágenes originales se
conservaron. Las diez notas nuevas son rojas y cursivas y no contienen
em dashes.

## Comprobaciones

- `checks.json`: generación del candidato y protección del XML previo al
  capítulo 4, relaciones e imágenes originales, 21 resultados y hashes de
  fuentes experimentales.
- `final-rendered-audit.json`: 261 controles sobre el Word renderizado y
  su PDF, bibliografía, imágenes, identificadores, índice, notas y paginación.
- `final-peer-review-20261013.json`: revisión visual independiente por otro
  agente de figuras, tabla y paginación. La versión anterior se conserva;
  el segundo render mantiene el texto y corrige un pie de figura dividido.
  Esta revisión de presentación no es anotación bioinformática humana.
- `installation.json`: copia de bytes ya comprobados sobre el original,
  con guardia SHA y copia exacta anterior.
- `private-files.json`: copia externa verificada de tres archivos, entrada
  exacta del autor, Word entregado y PDF. Conserva el insumo de regeneración
  fuera de Git y enlaza cada archivo por hash. No vuelve a renderizar ni
  modifica los originales.

## Regenerar en un destino nuevo

El generador no es una herramienta para sobreescribir futuras ediciones del
autor. Parte de la copia exacta anterior y valida las fuentes de esta campaña.
Se requiere restaurar los artefactos completos cuando el checkout no conserva
los archivos crudos omitidos de Git; consulte `../checks/delivery-20261013/`.

Desde la raíz de este checkout, con las dependencias declaradas:

```bash
uv run --with lxml --with gemmi==0.7.5 \
  python script/tesis/update_academy_campaign_docx.py \
  --source /home/webiwabou/Projects/Tesis-before-AWS-20261013.docx \
  --target /tmp/helix-thesis-reproduction.docx \
  --checks /tmp/helix-thesis-reproduction-checks.json \
  --require-structural-summary --require-workflow-summary \
  --require-aggregate-observed
/usr/bin/python3 script/tesis/render_docx.py \
  /tmp/helix-thesis-reproduction.docx /tmp/helix-thesis-reproduction-render
python3 script/tesis/audit_academy_docx.py \
  --source /home/webiwabou/Projects/Tesis-before-AWS-20261013.docx \
  --source-sha256 0b5e1e0c7a74f4dd3468656b6f9abef945bfeaf19b791c033bdc0c8cc573b28d \
  --rendered /tmp/helix-thesis-reproduction-render/helix-thesis-reproduction.docx \
  --pdf /tmp/helix-thesis-reproduction-render/helix-thesis-reproduction.pdf \
  --output /tmp/helix-thesis-reproduction-audit.json
```

Use destinos nuevos y conserve el Word que entregue el autor posteriormente.
La renderización requiere LibreOffice y el Python del sistema con UNO.
No se promete igualdad binaria entre renderizaciones distintas: se comprueban
contenido, fuentes, imágenes y paginación de cada entrega.
