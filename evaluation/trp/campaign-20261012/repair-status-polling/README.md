# Corrección del seguimiento SSH

La corrección se comprobó primero en una copia aislada y se aplicó después de terminar ambos lotes positivos. La aplicación superó 60 pruebas y la revisión de tipos; los intentos y las fuentes anteriores permanecen conservados.

## Diagnóstico

Los registros reales de laboratorio 2 muestran fallos en G-valid-011 y G-valid-014, con ejecuciones correctas entre ambos. Antes de cada fallo hubo una consulta SSH que terminó con código `255`. El código intentó registrar un estado terminal que todavía no había observado mediante `{ terminal: undefined }`. La serialización estricta rechazó ese valor y ocultó el error de seguimiento original.

El registro original solo conserva el tamaño de stderr, 61 bytes; no permite recuperar su texto exacto. No se atribuye una causa de red más específica a esos intentos.

Los dos paquetes fallidos superaron la auditoría independiente de integridad, métodos, configuración, aprobación, eventos y limpieza. Sus informes están en `../trace/intermittent-status-failures/`. Ningún intento fallido se convirtió en una ejecución correcta ni se volvió a enviar para este diagnóstico.

## Cambio propuesto

`status-repair.patch` introduce tres cambios en el cliente:

1. Representa un estado terminal no observado como `null`, un valor JSON válido.
2. Conserva el diagnóstico de un fallo SSH en eventos verificables.
3. Repite exclusivamente la consulta de estado del mismo controlador, con un máximo de tres intentos y una espera de un segundo, cuando el error identifica una interrupción transitoria del transporte.

Los errores de autenticación, clave de host o diagnóstico desconocido no se repiten. Una cancelación explícita tampoco activa reintentos. No se repiten el envío, el controlador ni las tareas científicas.

El script Python remoto, el flujo científico, la imagen, los límites de las tareas y el diseño de los casos permanecen iguales.

## Verificación aislada

La versión original falla tres de cinco pruebas nuevas; reproduce el ocultamiento del error. La versión corregida supera las cinco pruebas, con 30 comprobaciones, y la revisión de tipos. Los registros originales y corregidos acompañan el parche. `git apply --check` confirma que el parche puede aplicarse sobre la fuente actual.

## Aplicación

La opción con menor riesgo es terminar los procesos activos, conservar sus revisiones y aplicar el parche antes de ejecutar los casos aún pendientes o repetir únicamente los intentos fallidos, guardando las nuevas ejecuciones por separado.

Si queda una campaña activa, se puede ejecutar la revisión corregida desde una copia aislada que conserve íntegramente la revisión original. Los resultados deben identificar qué revisión utilizó cada intento. No se deben reiniciar ni volver a enviar las ejecuciones ya correctas.

## Aplicación realizada

El parche se aplicó el 13 de octubre de 2026 a las 02:06:35 UTC, después de la confirmación de que ambos lotes positivos terminaron. La implementación formateada superó 60 pruebas, 269 comprobaciones y la revisión de tipos. `application-record.json` conserva los hashes de las fuentes y de los registros de comprobación. La propuesta y los intentos originales permanecen conservados.
