# Contraste independiente de recursos de los flujos

## Resultados observados

La cohorte original contiene 40 escenarios de presupuesto sobre 20 variantes de grafo del mismo caso de desarrollo 2XQH. La etiqueta de factibilidad se obtuvo ejecutando el grafo aun cuando Helix lo había rechazado. Ninguna etiqueta se asignó a partir del estimador o del nombre de la cohorte.

- Original de 40: 26 factibles y 14 inviables; 34/40 decisiones coinciden con la referencia del workspace del head,85 %.
- Seis de 26 casos factibles fueron rechazados,23,08 % para este alcance adaptado. Son los presupuestos de 8, 12 y 16 MiB de las parejas 8 a 10 y 18 a 20. El umbral de 5 % no se cumple en esta comparación.
- Los 40 escenarios requirieron 42 intentos: se conservaron dos intentos desconocidos del checkpoint inicial, sin convertirlos en fallos físicos.
- Extensión separada: seis escenarios de 64 KiB de las primeras variantes del corpus aún no utilizadas; los seis resultaron inviables por un error real de cuota durante la copia. Su número y presupuesto se eligieron después de observar los 14 inviables originales; esta adaptación se informa explícitamente.
- Conjunto adaptado de 46: 26 factibles y 20 inviables; 40/46 decisiones coinciden,86,96 %. El falso rechazo permanece 6/26, 23,08 %. La extensión no cambia el denominador ni el resultado original de 40.

Los 26 casos factibles terminaron con 7163904 a 7172096 bytes de bloques asignados en su proyecto XFS. El máximo observado de memoria del controlador fue 213086208 bytes; los tiempos del supervisor fueron 109,999 a 131,945 s. Estos valores se exportan en original de 40.csv. El máximo de almacenamiento registrado incluye la observación final posterior a la duplicación portátil; las muestras intermedias por sí solas omiten esa copia.

## Alcance de la referencia

La unidad es el bloque asignado por XFS dentro del workspace del head, incluyendo los archivos preparados, trabajos, registros y la copia materializada del resultado portátil. Se excluyen la preparación y exportación del cliente real, el supervisor independiente y las cachés ya existentes de Nextflow y Docker. La demanda de Helix se cuenta en el ámbito agregado del paquete y de sus copias. Por ello, 23,08 % es el rechazo contra esta referencia adaptada del head; no establece el error de estimación o la tasa del protocolo contra un consumo agregado idéntico. El resultado científico R2.4 permanece pendiente, y no se declara cumplida una cota de extremo a extremo de R2.2.

Cada ejecución factible exigió cuatro IDs nativos distintos y completados: dos tareas stub y dos científicas. El auditor comprobó la asignación real al trabajador correspondiente, 2 CPU/2 GiB por tarea, los límites efectivos del contenedor, ausencia de swap, OpenBLAS Haswell con un hilo y el CSV exacto de su propio conjunto de unidades. El controlador independiente estuvo limitado a 1 CPU/2 GiB. Las negativas requieren un errno 28/122 o un error de cuota conservado en el archivo anclado. Los datos son de ingeniería sobre una proteína; no reemplazan las referencias biológicas ni las anotaciones externas.

## Checkpoint y procedencia

La primera ventana terminó con un controlador detenido por su watchdog de 71,087 s y un supervisor que se negó a comenzar a menos de 90 s del checkpoint. Ambas observaciones se conservaron como desconocidas. Se verificó que no quedaban trabajos, servicios o contenedores propios, se detuvieron y arrancaron las mismas tres instancias y se remontó la imagen XFS existente sin formatear ni borrar cuotas. La continuación conservó IDs, entradas científicas, presupuestos y CSV de referencia. Únicamente cambió el destino observado, el comentario único del trabajo y el espacio de nombres operativo.

Los límites de la ventana nueva se derivaron del mínimo entre el cierre de Academy a las 04:18:18 UTC y las guardas verificadas de 180 minutos desde el arranque de los tres huéspedes. El checkpoint de las 03:58 UTC reservó veinte minutos para recuperar datos. La extensión terminó a las 03:44:34 UTC. La prueba final independiente encontró cero trabajos propios, cero controladores activos y cero contenedores en ambos trabajadores, e inspeccionó 48 supervisores.

## Archivos

- ../r24-campaign/inputs/freeze.json: plan original de 40, etiquetas desconocidas antes de ejecutar.
- ../r24-campaign/all-original-attempts.json: matriz original final y todos los intentos, incluidos los dos desconocidos.
- ../r24-continuation/inputs/freeze.json: enmienda operativa prospectiva y hashes del destino renovado.
- ../r24-extension/inputs/freeze.json: extensión separada elegida después de observar la grilla original.
- ../r24-summary.json: resumen auditado con denominadores separados y R2.4 científico sin valor.
- original de 40.csv y extension.csv: filas reproducibles para las tablas del informe.
- ../r24-final-quiescence.json: evidencia de limpieza antes de detener el laboratorio.

Los resultados crudos, archivos de transporte y verificadores se conservan en las tres carpetas originales. El manifiesto externo enlaza hashes y tamaños; verifica integridad, que es distinta de la validez biológica.
