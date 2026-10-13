# Revisión de contenido y entregabilidad

La revisión corregida corresponde a **06:05:21–06:07:54 UTC del 13 de octubre de 2026**. Es un snapshot de la campaña en ese intervalo; el lote actual puede incorporar nuevas salidas y requiere repetir el scan antes de versionar la entrega final.

- **26 875 archivos**, 2 088 140 212 bytes; 78 387 entidades al incluir contenidos de archivos comprimidos y payloads JSON.
- **Cero** coincidencias con valores privados identificados de AWS/OAuth/SSH/Munge y **cero** archivos idénticos por SHA256 a las 78 coordenadas originales Pratt. No hay candidatos de credenciales sin resolver en este snapshot.
- **42 marcadores PEM vacíos** son falsos positivos: no contienen payload privado y el literal escapado coincide con un ejemplo de la dependencia pública `@npmcli/config`. Se registraron hashes de fuente y caché, sin copiar valores.
- **89 archivos contenedores** y **26 inspecciones SQLite**, incluyendo duplicados en archives. Se leyeron 1016 filas de 522 tablas; cuatro copias aplicaron WAL comprometido y validado por checksums exclusivamente en RAM. No hubo errores de lectura ni gaps pendientes del helper.
- Ningún archivo del inventario supera **100 MiB**. Hay **834 pyc**, 22 080 482 bytes, y 18 361 miembros con contenido idéntico al de archivos extraídos. Estos conteos no autorizan eliminar evidencia.

[Resumen corregido](snapshot-20261013T060521Z/summary.json), [hallazgos y offsets sin valores](snapshot-20261013T060521Z/findings.json), [inventario por hash](snapshot-20261013T060521Z/snapshot.json), [SQLite](snapshot-20261013T060521Z/sqlite.json), [archives](snapshot-20261013T060521Z/archives.json), [origen del placeholder público](public-placeholder-origin.json), [análisis de entrega Git](git-delivery-analysis.json) y [verificación](verification.json).

El primer snapshot de 05:55–05:57 UTC se conserva completo. Tenía dos gaps del helper: gzip XML tratado como tar y deserialize de SQLite con cabecera WAL. Su scanner original permanece junto al protocolo. El segundo los corrige; también conserva su copia exacta del scanner. Los archivos originales no se extrajeron ni modificaron.

El informe derivado de duplicación se normalizó a grupos por SHA256 para evitar repetir miles de rutas de archivos vacíos. Conserva cada miembro, cada ruta correspondiente y los hashes/tamaños de su codificación anterior. [Registro de normalización](derived-report-normalization.json). No se cambió ningún archivo de la campaña original ni una evidencia medida.

## Método y límites

Los valores privados se cargan en memoria sólo desde archivos privados existentes. Se buscan valores exactos y sus formas JSON, URL y base64; también patrones AWS, GitHub, proveedores y claves privadas. No se escriben valores, cuerpos de claves, huellas de contraseñas ni coordenadas privadas. No había archivos persistidos adicionales de contraseñas Canvas/SSH o token GitHub conocidos por el operador: este método no promete detectar contraseñas arbitrarias ni todas las formas posibles de ofuscación.

Los archivos se inventarían por ruta, tamaño, mtime e inode antes de leer; el hash corresponde a los bytes leídos. Se comparan los estados al terminar y se informa cualquier crecimiento. La segunda lectura no observó adiciones, eliminaciones ni cambios en ese intervalo; esto no congela salidas futuras. Se excluye únicamente esta carpeta de revisión del conjunto de entrada.

Se leen tar/tgz/ZIP sin extraer a disco, gzip XML y payloads base64 de JSON. Para SQLite se verifica y aplica en memoria el WAL hasta el último commit válido. Las cabeceras 18 y 19 se ajustan sólo en esa copia a modo rollback, según la documentación local de `sqlite3_deserialize` en `/usr/include/sqlite3.h`; los originales y sus hashes permanecen intactos. Las autopruebas utilizan fixtures artificiales, un SQLite independiente con WAL y filas overflow, y verifican que los informes omitan los valores encontrados.

## Entrega y repetición

`actual-allocation-and-supervisor.tar` conserva la captura primaria de asignaciones y supervisores. Las cachés y pyc medidos forman parte de ese alcance; quitarlos cambiaría la evidencia y puede invalidar manifiestos. Las versiones de fuentes y smokes fallidos también se conservan. La extracción duplicada puede reconstruirse posteriormente desde un archive canónico, pero root debe revisar antes todas sus referencias, hashes y auditores. Este trabajo no seleccionó un conjunto Git, no descartó archivos ni cambió manifiestos.

Desde la raíz del repositorio:

```bash
python3 script/tesis/review_campaign_content.py --self-test
python3 script/tesis/review_campaign_content.py
```

Cada ejecución crea un nuevo directorio fechado y conserva los anteriores. La segunda orden debe repetirse tras terminar el lote y antes de staging/commit. [Helper reproducible](../../../../../script/tesis/review_campaign_content.py).
