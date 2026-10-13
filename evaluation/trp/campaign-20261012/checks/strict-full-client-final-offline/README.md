# Verificación offline del cliente estricto completo

Se auditó una copia de `AGG-01-generous`, sin ejecutar ciencia, modelos, SSH ni operaciones AWS. La huella externa del manifiesto procede del terminal registrado por el supervisor, fuera del paquete: `a2fb5c236fbac84746aabaee6d44db4bd7844904764fe9aa2741a48f387c78c0`.

## Resultado vigente

`attempt-2/audit.json` pasó las cinco comprobaciones. `attempt-2/fault-injection.json` contiene 460/460 detecciones: ausencia, mutación y enlace simbólico en cada uno de los 150 archivos declarados; tres alteraciones del manifiesto; cinco rutas inseguras; un archivo adicional y un ancla incorrecta. Incluye los comprobadores, las políticas y los recibos estrictos, también sus copias del recorrido stub. Las 19 negativas semánticas se detectaron mediante el verificador confiable o el observador adicional. La copia terminó idéntica al original y verificó con el ancla externa inicial. La comparación de hashes confirmó que el paquete original permaneció intacto.

Los 24 campos de métodos tienen el nombre y puntero esperados, coinciden con sus fuentes y generan exactamente el texto de `methods.md`. Se cotejaron diez puertas de control, su orden, cadena y registros fuente. Los trabajos nativos 262 a 265 terminaron en los dos trabajadores previstos; las observaciones de CPU, RAM, swap y BLAS se cotejaron con `.command.out`. El CSV coincide byte a byte con el gold propio de este grafo, congelado antes de la ejecución.

La comprobación estricta examinó cinco recibos y las observaciones externas del supervisor: proyecto XFS 50000, cota 134217728 B, uso final 36573184 B, cliente y controlador en el cgroup compartido de 1 CPU/2 GiB/swap cero, tareas en contenedores de 2 CPU/2 GiB. La base SQLite persistente tiene 249856 B y 20 tablas. El uso final de disco no se presenta como pico. Software y cachés inmutables preinstalados, más telemetría experimental externa del supervisor, quedan fuera del presupuesto de trabajo declarado.

## Limitaciones y defectos semánticos encontrados

La aprobación fue una respuesta sintética a `Question.Service`. El éxito conserva diez puertas obligatorias, pero no un oráculo separado de acciones de callbacks: `gateRecords` está vacío. El contraste negativo de cuatro sesiones y 13 acciones observadas independientemente permanece en su campaña separada. Ninguna de estas pruebas mide kappa ni identifica una persona aprobadora.

Con el ancla original, cualquier mutación de los archivos falla. Al crear deliberadamente un manifiesto nuevo para probar consistencia semántica, el verificador congelado rechazó 16 de las 19 negativas; el observador adicional detectó las otras tres:

- Campo obligatorio de métodos `remote strict allocation` eliminado.
- Prosa adicional sin respaldo en `methods.md`.
- Evento `permission/requested` eliminado y cadena recalculada.

Las pruebas de endurecimiento encontraron además dos inconsistencias de aprobación que el verificador anterior aceptaba con un manifiesto nuevo: respuesta `Rechazar` o canal desconocido, manteniendo el digest. Esto es una brecha de consistencia del nuevo perfil, no un resultado de autenticación ni una ruptura del ancla original.

El detalle del evento de finalización aún usa el identificador genérico `trp-slurm-ssh/1.0.0`; `execution.json`, `software.json` y los métodos declaran correctamente `trp-slurm-colocated-strict/1.0.0` y transporte Python local. No se presenta esta campaña como prueba de SSH. El campo de alcance de observaciones del contenedor dice “no disk quota”: se refiere al contenedor; la cuota conjunta se demuestra por los recibos del proyecto XFS y el supervisor.

No se generaliza desde esta proteína de desarrollo a exactitud biológica, estructuras reservadas ni todos los presupuestos. Los archivos opcionales ausentes en esta ejecución, como SIFTS, CCTBX o FreeSASA, se cubren en sus campañas propias.

## Reproducción

Desde la raíz del repositorio, elija un destino nuevo:

```sh
python3 evaluation/trp/campaign-20261012/checks/strict-full-client-final-offline/review.py \
  --output /tmp/helix-strict-offline-nueva-revision
```

El script usa los bytes del verificador confiable fijados por la congelación, nunca ejecuta el código del paquete y rechaza un directorio de salida existente. No vuelve a ejecutar el flujo científico. Primero prueba el auditor SSH anterior; su incompatibilidad con el perfil co-localizado queda conservada. Reutiliza sus lectores de trabajos y observaciones, complementados por un observador del perfil estricto.

`attempt-1` se conserva: las 460 y 19 inyecciones se detectaron, pero el observador supuso erróneamente que el recibo de admisión científica era del cliente. Ese recibo procede del controlador. La corrección del observador produjo el segundo resultado verde; no hubo un nuevo intento científico.

El parche propuesto se mantiene fuera de producción en `/tmp/helix-strict-verifier-hardening-20261013/`. Modifica únicamente `verify_bundle.py.txt`. Sus siete pruebas y 56 casos verificaron seis paquetes intactos con sus anclas externas (estricto 150, SSH 144, SIFTS 156, cancelación 143 y dos negativos de 25), cada uno de los 24 campos y diez puertas, fuentes, duplicados, orden, aprobación, prosa y restauración. El primer intento de unittest tuvo un error de enlace de funciones del propio harness; su salida se conserva y no acredita detecciones. La producción congelada no se alteró durante esta auditoría.
