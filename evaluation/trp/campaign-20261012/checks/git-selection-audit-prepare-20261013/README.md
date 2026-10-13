# Auditoría semántica de la selección de Git

Preparación realizada sin escanear la selección ni modificar artefactos históricos.
El scanner anterior conserva su hash y cubre credenciales/bytes exactos de originales.
El auditor adicional examina coordenadas derivadas y no presenta la ausencia de un
PDB completo como prueba de que no hay coordenadas privadas.

Después del cierre de datos y Word, ejecutar desde la raíz del repositorio:

    python3 script/tesis/audit_selected_campaign_content.py --selected-nul /ruta/seleccion-final.nul --output evaluation/trp/campaign-20261012/checks/git-selection-semantic-final-20261013

La selección debe contener rutas relativas únicas terminadas por NUL. El destino
debe ser nuevo. La salida sólo contiene rutas, categorías, conteos y hashes; no
registra coordenadas ni cadenas secretas. Exit0 requiere que no haya hallazgos
privados, orígenes no resueltos, huecos de inspección ni archivos que cambien.
Exit2 exige revisión o exclusión de la selección, conservando la evidencia privada.

Cubre campos numéricos xyz/atomXYZ/coordinates/positions y triples x/y/z vinculados
a los78 SHA privados. Inspecciona PDBATOM real en texto/strings, JSON/base64,
SQLite/WAL y contenedores tar/gzip/zip sin extracción a disco. Las coordenadas de
30 estructuras públicas y2XQH se permiten cuando su fuente pública está respaldada.
Un vector con origen no establecido queda no resuelto; no se permite automáticamente.
Las fuentes privadas sólo se leen para hashes o matching de credenciales en memoria.
No se afirma detectar toda contraseña arbitraria ni toda transformación/renombrado.

La auditoría cubre únicamente la selección declarada. Un índice Git distinto necesita
su propia selección y nueva verificación. La campaña completa puede conservar datos
privados y debe archivarse por separado en una entrega privada, sin borrar originales.
