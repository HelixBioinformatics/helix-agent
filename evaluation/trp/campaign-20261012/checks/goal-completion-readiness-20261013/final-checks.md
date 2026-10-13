# Comprobaciones finales y herramientas reutilizables

Esta lista localiza interfaces existentes. No repite pruebas de dominio, llama
al modelo ni inicia AWS. Los informes nuevos deben tener destinos nuevos; no
se usan los comandos como autorización para sustituir evidencia congelada.

## Requisitos y artefactos

```sh
python3 script/tesis/audit_thesis_traceability.py
python3 script/tesis/verify_public_mapping_evidence.py
python3 script/tesis/verify_structural_campaign.py
python3 script/tesis/verify_sasa_campaign.py
```

- El primero verifica los 21 IDs, equivalencias y existencia de enlaces. No
  usar `--markdown` durante la revisión: esa opción escribe la tabla.
- El verificador de mapeos comprueba datos, correspondencias y reproducción
  conservada de tres casos; no genera ciencia ni etiquetas.
- El verificador estérico puede recibir `--inputs` para añadir comprobación
  de originales privados y química instalada, cuando estén disponibles.
- FreeSASA necesita sus entradas y originales autorizados. Ninguno de estos
  verificadores certifica sensibilidad/especificidad física.

`script/tesis/check_f6_readiness.py` es una comprobación de una congelación por
scope. Sus dependencias de anotación científica no deben convertirse en
impedimento artificial de revisar integridad técnica. Seguir su interfaz real
después de que existan los artefactos de una campaña reservada.

`script/tesis/verify_snapshot.py MANIFEST...` sirve sólo para snapshots NDJSON
con source, endpoint, fetchedAt, data, rows, bytes y sha256. No sirve para un
manifiesto general de miles de archivos ni para un paquete TRP portable.

Para paquetes TRP usar el verificador de confianza del checkout, con el ancla
conservada fuera del paquete. Para SSH ordinario, el auditor adicional admite
exactamente `--sha256`, `--expected-outcome`, `--reference-run`,
`--require-reference`, `--event-oracle`, `--fault-injection` y `--output`:

```sh
python3 script/tesis/audit_remote_campaign.py /ruta/copia/portable \
  --sha256 HASH_EXTERNO --expected-outcome succeeded \
  --reference-run /ruta/referencia_de_las_mismas_entradas \
  --require-reference --output /tmp/revision-remota-nueva.json
```

No aplicar automáticamente las suposiciones SSH de ese auditor al backend
co-localizado. Para el perfil estricto usar `aggregate-resource-contrasts/
audit_cases.py` sobre una copia nueva como explica `strict-reproduction.md`.
El cierre debe verificar también las puertas esperadas, causas y campos de
métodos de la nueva campaña, con sus 24 campos actuales y fuentes; no asumir
que una auditoría histórica de 20 campos sobre otra ruta ya la cubre.

## Word y anexo

`script/tesis/audit_academy_docx.py` comprueba preservación, 21 identificadores,
bibliografía, notas nuevas, índice y totales de páginas sobre un render nuevo.
Necesita el Word base anterior a instalación y su hash real:

```sh
python3 script/tesis/audit_academy_docx.py \
  --source /ruta/base-previa.docx --source-sha256 HASH_BASE \
  --rendered /ruta/final-rendered.docx --pdf /ruta/final.pdf \
  --output /tmp/auditoria-final-word-nueva.json
```

El render intermedio de 143 páginas anterior a los contrastes estrictos no
certifica las modificaciones posteriores. Hace falta render/revisión visual
final, instalación del resultado autorizado en `Tesis.docx` y hash posterior,
manteniendo intactos los capítulos 1 a 3. El script no realiza esos pasos.

## Escaneo y cierre de versiones

Los informes históricos `checks/versioning-content-scan.json` y
`checks/versioning-archive-scan.json` no tienen un programa productor persistido
localizable en el checkout. Cubrían 13.420 archivos y 22 comprimidos en aquella
instantánea. No se presentan como escaneo de los nuevos resultados.

El coordinador encargó una revisión actual de 21.519 archivos y 75 comprimidos,
aproximadamente 1,54 GB. Conservar su salida y hashes cuando termine. El alcance
final incluye fuentes/artefactos a versionar, tar/zip sin extracción peligrosa,
DB/WAL/SHM y coordenadas originales privadas: reportar rutas/categorías, sin
imprimir cadenas secretas. La búsqueda por patrones o igualdad de hashes no
certifica detectar todos los secretos ni todas las transformaciones de datos.

Los nuevos programas de código que cambiaron el perfil tienen regresión
pertinente y chequeos focales conservados en `checks/strict-profile-integration/`.
Hay 541 pruebas aprobadas en el entorno fijado y 65 focales posteriores a la
calibración. No repetir una regresión amplia sin cambios/fallos que lo motiven.
Verificar los hashes de las fuentes realmente desplegadas y conservar los
fallos del entorno anterior.

Antes de los commits finales: `git diff --check`, revisión del diff propio,
fuentes/manifest anclados y del escaneo final. Los commits autorizados llevan
título en inglés y sin firma de coautor. Mantener los cambios del usuario.

Tras recopilar todo, el coordinador verifica trabajos, procesos y contenedores
propios vacíos y estado EC2 detenido de ambos laboratorios. La parada antigua
de R24 no vale como estado final tras una renovación que los encendió. Documentar
volúmenes residuales, ventana y saldo informado con su retraso; no afirmar
facturación exacta ni gastar más cuentas cuando no exista déficit comprobado.
