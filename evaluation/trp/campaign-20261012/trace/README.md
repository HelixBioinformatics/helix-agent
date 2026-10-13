# Verificación independiente de ejecuciones remotas

`script/tesis/audit_remote_campaign.py` lee la evidencia real exportada por
Helix. No conecta a AWS, no ejecuta scripts incluidos en el paquete y no llama
al modelo. Usa el verificador de confianza del repositorio para comprobar el
manifiesto contra un hash conservado fuera del paquete.

Para una ejecución con las unidades completas de la referencia de desarrollo:

```sh
python script/tesis/audit_remote_campaign.py RUTA_AL_PAQUETE --sha256 HASH_EXTERNO --reference-run evaluation/trp/reference/nextflow-f5/evidence/run --require-reference --fault-injection --output evaluation/trp/campaign-20261012/trace/caso.json
```

El hash debe proceder del registro del conductor de la campaña. Leerlo del
propio manifiesto únicamente demostraría consistencia interna.

## Qué comprueba

- Digest de propuesta, respuesta por `Question.Service`, destino remoto,
  configuración, presupuesto, copia aprobada y transferencia verificada.
- Dos trabajos simulados y dos científicos, con cuatro IDs nativos distintos.
- Correspondencia de ID, estado, comentario de propiedad, código de salida y
  nodo entre las trazas y el texto original de `scontrol show job`.
- Asignación al trabajador aprobado para cada operación.
- Límites CPU, memoria y swap y perfil numérico desde los mensajes reales
  capturados dentro de los contenedores. El hostname del contenedor no se
  interpreta como nombre del trabajador.
- Decisión de admisión anterior a las tareas científicas y reconocimiento de
  esa misma decisión por el controlador remoto.
- Eventos de permisos, aprobación, protocolo, admisión y ejecución en su
  secuencia. Se puede proporcionar además un inventario independiente de
  acciones esperadas mediante `--event-oracle`.
- Cada valor de métodos enlazado a su fuente y reproducción exacta de la
  plantilla de Markdown y sus limitaciones explícitas.
- Esquema, identidad, límites de unidades y valores finitos del CSV.
- Inyección de alteraciones y ausencias en cada artefacto de una copia,
  conservando intacto el paquete recibido.

## Referencia numérica por caso

`--reference-run` debe contener `specification.json`, `source.pdb` y
`results/geometry.csv`. El comparador exige la misma proteína, cadena, modelo,
unidades, inserciones y hash de coordenadas antes de comparar el CSV byte a
byte. Para un subconjunto de unidades debe generarse su propia referencia
manual con las mismas versiones y parámetros. No se compara contra el CSV de
las doce unidades originales.

`verifier-reference-guards.json` registra tres comprobaciones del propio
comparador: reconoce la referencia correcta y rechaza referencias de otro
subconjunto o de otras coordenadas. Son comprobaciones locales del verificador,
no evidencia de una ejecución remota.

## Ejecuciones interrumpidas y rechazos

`--expected-outcome` admite `failed`, `cancelled` y `rejected`. No exige cuatro
trabajos terminados en una ejecución parcial. Una cancelación remota debe
conservar el terminal y la observación nativa de cancelación confirmada, sin
trabajos pendientes. La ausencia de un controlador o de una respuesta de SSH
no permite afirmar que el planificador haya cancelado el trabajo.

Una mutación que invalida la integridad del paquete produce un fallo de esta
auditoría. No se transforma ese fallo en una verificación satisfactoria de los
resultados; se conserva como una inyección detectada por el verificador.

La cobertura de eventos se limita a las puertas obligatorias del camino
observado y al inventario de acciones externo cuando existe. No demuestra
por sí sola cobertura de una sesión humana completa, kappa, sensibilidad
física ni especificidad biológica.

## Evidencia ya auditada

`lab1-helix-reference.json` verifica la ejecución real de Helix con los cuatro
trabajos 16 a 19: dos simulados y dos científicos, repartidos en los dos
trabajadores aprobados. El CSV de catorce filas coincide byte a byte con la
referencia de esas mismas doce unidades. Se comprobaron diez eventos de
puertas obligatorias y veinte campos de métodos. La inyección detectó
296/296 fallos sobre un paquete de 144 archivos, incluida la copia restaurada.

`first-remote-failure-diagnostics.json` conserva el intento anterior: SELECT 15
falló con código 126 al montar una ruta sin permiso de tránsito para Docker.
No terminó ninguna tarea científica. `first-remote-failure.json` comprueba la
integridad de ese paquete fallido y detecta 190/190 inyecciones. La petición
de cancelación encontró cero trabajos activos; no demuestra cancelación de
un trabajo que estuviese ejecutándose.

El error posterior del conductor de archivo, que esperaba los nombres de
logs locales, se registra aparte de la ejecución científica satisfactoria.
Recuperar sus archivos desde la copia portable completa no requiere repetir
la ejecución en AWS.

`audit_pressure.py` reconstruye los cuarenta contrastes de la segunda cuenta
desde las salidas crudas y la capacidad de cada nodo. Confirmó veinte pruebas
de presión o contención y veinte solicitudes que exceden CPU o RAM por nodo.
Una prueba de contención de memoria tiene éxito cuando el núcleo mata al
proceso hijo que rebasa su límite; esto no se cuenta como éxito de una tarea
científica. Estas pruebas no contienen predicciones de admisión de Helix y
no producen una tasa de falso rechazo de flujos bioinformáticos.

`lab1-monitor-cleanup.json` conserva una auditoría con `verified=false`.
El paquete recuperado de 145 archivos pasa integridad, estado cancelado,
enlaces de aprobación, métodos y cancelación nativa. El ledger recuperado no
contiene el evento automático de fallo que exige el oráculo del camino:
su último evento es `interruption-recovered`, documentado durante recuperación.
No se relaja esa exigencia para obtener una auditoría satisfactoria.

La solicitud original conserva fallo de monitor SSH con salida 255 después
del límite de 180 segundos del conductor. La limpieza de Helix canceló el
trabajo GEOMETRY 24 en estado ejecutándose, con estado nativo `CANCELLED`,
salida `143:0` y 51 segundos de ejecución, y dejó cero trabajos propios y
contenedor terminado. Se utilizó una estructura sintética de 1000 unidades
para mantener una tarea activa; no tiene verdad biológica. El ensayo y su
empaquetado automático no pasaron. Estos hechos prueban limpieza ante el
fallo de transporte observado, sin afirmar cancelación explícita del usuario,
interrupción verificada de una fibra ni éxito de la prueba en vivo.
