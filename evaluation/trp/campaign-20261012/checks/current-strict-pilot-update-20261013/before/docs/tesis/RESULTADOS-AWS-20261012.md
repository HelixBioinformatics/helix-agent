# Resultados técnicos de la campaña del 12 de octubre de 2026

Actualización de estado y trazabilidad. Conserva los 21 resultados y los umbrales de la tesis. Las ejecuciones en nube son desarrollo técnico; las estructuras y pilotos de modelo tienen los scopes propios descritos aquí. Los capítulos 1 a 3 no se reabren.

## Flujos remotos e infraestructura

Dos cuentas AWS Academy independientes permitieron probar dos clústeres Slurm de tres nodos, con SSH, Nextflow y Docker. El inventario comprueba controlador y trabajadores por separado, sin sumar memoria entre nodos ni combinar créditos de cuentas. La imagen fija es `sha256:1dd91e70acb153a0bd9a51346fc001dd5025f851c9598697cdd37f07d9490b0a`; el perfil numérico registrado es `haswell-single-thread` sobre x86_64.

La revisión `a951d73` incorpora los ejecutores y verificadores de esta campaña. La preparación del operador observa el temporizador de parada de los tres huéspedes y escribe en la configuración privada la menor fecha entre esos límites y el fin de la sesión Academy. Renovar Academy no amplía por sí solo el temporizador de arranque de una VM. [Política y comprobación](../../evaluation/trp/campaign-20261012/cloud/lab2/prepare-window/prepare-status.json).

El corpus contiene 50 variantes de grafos de una proteína de desarrollo, 2XQH/A. Hubo 52 intentos: 48 primeros éxitos, dos fallos iniciales conservados y dos reintentos reparados. Los 50 casos finalmente verificados no se presentan como 50 intenciones humanas ni como una tasa científica de R1.5. El adaptador conserva errores de seguimiento SSH, consulta el mismo controlador un máximo de tres veces ante errores transitorios reconocidos y no vuelve a enviar ciencia automáticamente.

La referencia mapeada SIFTS conserva mmCIF, XML, residuos y transformación UniProt/autor para 12 unidades. El CSV coincide con el gold fijo. Su paquete automático tiene 156 archivos, ancla `b400c54428684c5d1f767324154388f906f466c849736bf28394241fabed80aa`, y verifica fuera del checkout. La auditoría detectó 320/320 alteraciones introducidas sobre copias.

La cancelación limpia observó el trabajo nativo 128 como RUNNING y solicitó Tool.Context.abort 68 ms después; Slurm terminó CANCELLED, código 143:0. El controlador terminó, no quedaron trabajos propios ni contenedores en el trabajador, y el paquete automático de 143 archivos conservó el evento final real. Su ancla es `62cf9fba9e9a2e23cb4e4e55f30bd50a36000976c438b8d4387d7468a7b735e6`. Los intentos previos deficientes siguen conservados. Lab1 consta detenido. El contraste del head de Lab2 terminó y tuvo una parada verificada el 13/10/2026 a las 03:52 UTC; la nueva evaluación agregada se administra separadamente.

## Correspondencias públicas de numeración, R1.6

Se mantuvieron las 30 cadenas PDB públicas del conjunto experimental anterior, sin 2XQH ni modelos privados. Selección, fuentes, expectativas y comparador se congelaron antes de ejecutar el módulo real de Helix. Las expectativas provienen de filas mmCIF, columnas PDB y referencias por residuo del XML SIFTS oficial; no del mapeo producido ni de interpolar extremos. Gemmi 0.7.5 se comparte como lector léxico CIF; las uniones, identidad y comparación de coordenadas se implementaron aparte. Esta independencia no cubre errores comunes del lector.

Se contrastaron **11751/11751** posiciones label/autor con CA. El parser SIFTS coincidió en **30/30** cadenas. La preparación completa admitió **28/30** cadenas y convirtió **11215** residuos; las otras **2/30** se rechazaron correctamente. GLY182 de 2bm4-A y LYS353 de 1o8i-A, UniProt375, sólo tienen N en el mmCIF, sin CA, aunque SIFTS los considera observados. Se conservaron ambos rechazos, 265 residuos no observados de SIFTS y cuatro CA sin referencia observada a la accesión seleccionada. Los denominadores corresponden a operaciones distintas.

No aparecieron inserciones ni ubicaciones alternativas; no se valida ese dominio real. Los intervalos son sondas de numeración, no unidades de repetición anotadas por una experta. Una cadena admitida y ambos rechazos se reprodujeron con informes idénticos byte a byte. Es cobertura adicional de desarrollo de R1.6, sin referencia humana, reserva ni validación biológica. Los archivos originales y los fallos se conservan.

[Resumen y alcance](../../evaluation/trp/campaign-20261012/mapping-public-contrasts/README.md), [auditoría por cadena y residuo](../../evaluation/trp/campaign-20261012/mapping-public-contrasts/audit.json) y [verificación final de root](../../evaluation/trp/campaign-20261012/checks/root-review-20261013/public-mapping.json). Esta última conserva comando, salida exitosa, fecha y hashes del verificador y resumen. El protocolo limitó cada URL a una petición de 30 segundos y 20 MB; la alternativa XML oficial sólo se admitió después de HTTP404 del XML remediado. El fixture tipado heredado se identifica como dependencia capturada retrospectivamente, sin atribuirle congelación prospectiva.

## Recursos: observación y límite de inferencia

Las salidas de las tareas científicas muestran límites efectivos Docker de 2 CPU, 2 GiB y cero swap. No verifican un límite duro global de controlador/cliente/remoto ni una cuota global de almacenamiento. Una petición estricta de cuota remota se rechaza honestamente. La ingeniería local XFS/cgroup anterior conserva su propio scope; no demuestra por transferencia R2.2 agregado en nube.

En SIFTS, Nextflow informó peak RSS de 11.7 MB y 188.6 MB para SELECT y GEOMETRY, con tiempos de comando 173 ms y 2.6 s. Su wrapper agrega VmRSS/VmHWM del árbol de procesos muestreado; no es una medición independiente de memoria física única ni un pico del clúster. Slurm registró duraciones nativas de cero y tres segundos, con resolución de segundos.

La carpeta final archivada del cliente tiene 7882950 bytes regulares y 8417280 bytes asignados, incluida la copia portable; la carpeta final del flujo en el head tiene 4331885 bytes regulares y 4792320 bytes asignados. Se excluyen cachés y otras ejecuciones. Estos tamaños son finales, no picos ni cuotas. El contraste del head R2.4 original quedó cerrado: 40 escenarios, 26 factibles y 14 inviables, seis falsos rechazos (6/26, 23,08%) y 34/40 aciertos (85%). Conserva 42 intentos enviados y dos desconocidos históricos; no quedan casos únicos sin resolver. La meta de falso rechazo de 5% no se alcanza. Una extensión decidida tras observar los originales añade seis inviables y se informa por separado, sin sustituir el denominador original. El oráculo acotado no comprende preparación/exportación del cliente real: estas tasas no son el indicador científico ni R2.2 agregado. [Fuentes verificadas](../../evaluation/trp/campaign-20261012/trace/r24-canonical-source-review.json).

## Sesiones negativas de R3.2

Cuatro sesiones locales reales de preparación/ejecución, con inventario del host y Protocol/Question.Service, comprobaron 13/13 registros exigibles con causas, tipos y orden: admisión 4/4, protocolo 3/3, permisos 4/4 y aprobación 2/2. Dos negativas que llegaron a trp_run conservaron paquetes automáticos fallidos de 25 archivos, verificados en frío. Los rechazos de preparación tienen registros JSON y del protocolo; no se fabrican eventos de ejecución. Las expectativas se fijaron antes del productor; las acciones se observaron en vivo antes de leer sus registros, intercaladas con los eventos. Los callbacks son sintéticos, sin modelo, ciencia, AWS ni anotaciones humanas. [Segunda revisión](../../evaluation/trp/campaign-20261012/trace/event-negative-second-review.json).

## Experta y modelo

El autor seleccionó a su asesora, Layla Hirsh, como experta independiente del desarrollo. El material real preparado contiene 70 solicitudes: 50 propuestas factibles y 20 peticiones de límites. Factibilidad definitiva, referencias humanas y dos paráfrasis por intención no se han recibido. La anotación de turnos reales para kappa se realiza después de ejecutar y capturar las sesiones pertinentes; no la sustituye una respuesta de aprobación sintética.

Cuatro pilotos reales de desarrollo usaron `openai/gpt-6-sol`, razonamiento `medium`, mediante OAuth existente. Probaron preparación/alcance con hechos suministrados y no ejecutaron ciencia ni reserva humana. El adaptador elimina maximumOutputTokens del parámetro de chat: 8192 es un límite solicitado, no un cap duro demostrado. La factura efectiva, el nivel efectivo y la revisión interna del proveedor no están observados. La estimación tarifaria del auditor no se presenta como gasto efectivo.

## Originales Pratt y observables físicos locales

Los 78 originales de rango 1 de la Tabla S1, con coordenadas y PAE, están disponibles. El perfil principal CCTBX Reduce2/Probe2 produjo observables estéricos en 105/108 casos, con tres timeouts al límite 180 s. El contraste secundario 600 s recuperó 3/3 sin borrar los fallos principales. Las 30 referencias experimentales revisadas como proteínas repetitivas no son negativos físicos certificados.

FreeSASA calculó observables descriptivos en 108/108 casos. Su área superficial o identidad de residuos cargados no define por sí sola protonación ni fallo. Las envolturas opcionales se integraron en Helix y se archivan/ligan al digest cuando se activan. C9 mantiene el veredicto amplio not_evaluable: no hay clasificador/umbral validado, sensibilidad ni especificidad física. Esos experimentos son locales y no se atribuyen a AWS ni al modelo.

## Criterios de actualización

- Implementado describe software o diseño verificado en un alcance, no la satisfacción de un indicador científico.
- Las 50 variantes de grafos proceden de una proteína de desarrollo, 2XQH/A; no son 50 proteínas ni 50 intenciones humanas reservadas.
- Los dos fallos iniciales y sus reintentos se cuentan como 52 intentos, sin borrar fallos ni convertir 50 éxitos finales en la tasa científica de R1.5.
- Aprobaciones sintéticas y permisos automáticos no son intervenciones anotadas por una experta.
- Observables estéricos y de superficie no constituyen un clasificador de plausibilidad física; sensibilidad, especificidad y kappa permanecen ausentes.
- Los límites efectivos de tareas Docker, tamaños finales por carpeta y telemetría de procesos no demuestran un límite agregado cliente/controlador/clúster ni un pico de almacenamiento.
- El contraste head R2.4 original 40 y la extensión posterior 6 se informan por separado; falso rechazo 6/26 y acierto 34/40 sólo describen ese alcance. No son tasa científica ni prueba agregada del cliente real.
- Las 30 cadenas públicas contrastan numeración: 11751 correspondencias label/autor y 11215 residuos preparados en 28 cadenas, con dos rechazos correctos conservados. Gemmi léxico compartido y cero inserciones observadas limitan la independencia y cobertura; no es evaluación reservada ni anotación biológica.
- Se conservan los 21 identificadores y el cierre autoral de los capítulos 1 a 3.

## Índice de fuentes y hashes

Los hashes siguientes fijan las fuentes concretas de esta actualización. El índice original conserva observaciones de avance fechadas. Las nuevas fuentes finales del contraste del head y las negativas R3.2 se añaden al final de este índice; ninguna tasa head se transforma en indicador científico o agregado.

| Fuente | SHA-256 |
|---|---|
| [workflows](../../evaluation/trp/campaign-20261012/cloud/workflow-summary.json) | `ae68aac93c5d9b7809804bf0f40c44e462e0e19005df0e9e73661913dc7310ae` |
| [pilot](../../evaluation/trp/campaign-20261012/model-pilot/audit.json) | `e778d2350f295051bb01b1c3efe40de079b112a84b8dafaab6893ff424b00c9c` |
| [pilot_settings](../../evaluation/trp/campaign-20261012/model-pilot/settings-probe-request/audit.json) | `075eaa90a92bae795e8dd0051d80bdd683c546d4f2727edc79cd3a31ce00340c` |
| [steric_primary](../../evaluation/trp/campaign-20261012/structural/summary.json) | `a019bdf4e65abb960735df52907ec25e8105eebfffe313be35c9abc4933e622b` |
| [steric_secondary](../../evaluation/trp/campaign-20261012/structural/runtime-600/summary.json) | `48c315caededc16f411133782baca20f0838f7e2e831baa5871b29f68c8da04f` |
| [surface](../../evaluation/trp/campaign-20261012/structural/freesasa/summary.json) | `2b05c768cac199c8177e4f974846b1f6fe0eef84c98097a12cef0384951e3397` |
| [surface_integration](../../evaluation/trp/campaign-20261012/structural/freesasa/integration/agent-reference.json) | `1db0ac3dbf1c09a3dc4e0f5304ae4e82b6668261f638744813627623e3741b99` |
| [mapped](../../evaluation/trp/campaign-20261012/cloud/lab1/mapped-reference-protocol/driver-terminal.json) | `0e88b189344616302cbf89a028f3689f9ba6a03f88dd12b0b49fb76dfe19490a` |
| [mapped_audit](../../evaluation/trp/campaign-20261012/trace/mapped-reference.json) | `38ff44a16ad47bfa35cfa7d6c0c5098ba1ef8182e76aad691ec086a7d582e1bd` |
| [mapped_copy](../../evaluation/trp/campaign-20261012/trace/mapped-reference-copy.json) | `81f3d3fa9dde72c2eeb0e729c52bebf066aaa73723ffe7e353716ca1a6f19315` |
| [cancel](../../evaluation/trp/campaign-20261012/cloud/lab1/cancellation/next-ctx-abort/driver-terminal.json) | `a8771640649d57c46b63f6c97f59368b96c2c6b1b921a73118cb44d6cff2a37f` |
| [cancel_audit](../../evaluation/trp/campaign-20261012/trace/running-cancellation-clean.json) | `002f23614d2333ecc510127e9afcd68c5cc8d73e2668c767b1b7d01a7d5ee08b` |
| [lab1_stop](../../evaluation/trp/campaign-20261012/cloud/lab1/stop-state.json) | `5071d46182badb1be98833bf884241b96cb4922d03bc87a727477cab5ebb043e` |
| [regression](../../evaluation/trp/campaign-20261012/checks/final-regression/summary.json) | `a3cddb172872b1f63c6fb172998ef4a09ff414dab69391a3df9e17476978715a` |
| [r24_observation](../../evaluation/trp/campaign-20261012/trace/r24-initial-checkpoint-independent-audit.json) | `b077d7bd28de3d62b6ba4a9ca48c853eac27cdd6478fbf47546d57176824de5d` |
| [annotation](../../docs/tesis/evaluacion-experta-20260930/README.md) | `378e70e07016a8e8c8f5d3545ab6b2774d05b77481ef9d3deb5c8a6468a85738` |
| [annotation_workbook](../../docs/tesis/evaluacion-experta-20260930/para-asesora/evaluacion.xlsx) | `d0e61be48192abea4f3b6cef6f8561fc42b0aeb2132dfac6c9eb1e71a69ef91a` |
| [graph_corpus](../../evaluation/trp/campaign-20261012/contract-corpus/graphs.json) | `3d20eda715833d882a7ff8e0e5b10180c3fecec4f20012eb74f266062bfc9e7d` |
| [steric_integration](../../evaluation/trp/campaign-20261012/structural/agent-reference.json) | `d88bab81f38e786288cd42d47548a81afd68a304a73910a4e7391e36a966d0c5` |
| [operator_window](../../evaluation/trp/campaign-20261012/cloud/lab2/prepare-window/prepare-status.json) | `b12e8b71517939d663af4816dc9027b9040d2b6380d8ffe30be3bdfd1911ad5e` |
| [operator_window_helper](../../script/tesis/aws_academy_prepare_remote.py) | `af16699cf13f285dfb53e8fbc9cab8ce7c95e0e43ff35748922870bdd51f9739` |
| [public_mapping_summary](../../evaluation/trp/campaign-20261012/mapping-public-contrasts/summary.json) | `7388b1eb7f776d7a092a6c4f7f3641b586db428fb63eb471b79a93909846591c` |
| [public_mapping_audit](../../evaluation/trp/campaign-20261012/mapping-public-contrasts/audit.json) | `b9c5b98fcac3464eb2bbe4d1e93ce112d272c93ce000bd6a856f0c7a3c61da6c` |
| [public_mapping_manifest](../../evaluation/trp/campaign-20261012/mapping-public-contrasts/manifest.json) | `baedd3702e605efb04eabe803294b7368771bd0f2c07ac7427f2f2b2b4474ac6` |
| [public_mapping_protocol](../../evaluation/trp/campaign-20261012/mapping-public-contrasts/protocol.json) | `81bf8e5bf0a151c63df779b8036490e04ba18c2e4c1d5baf6b1defdbd425b6b1` |
| [public_mapping_freeze](../../evaluation/trp/campaign-20261012/mapping-public-contrasts/oracle-freeze.json) | `86e81898e53fed7208323e4609d8aa7fb155718a675da3e00f4d5fdf99cd314d` |
| [public_mapping_root_review](../../evaluation/trp/campaign-20261012/checks/root-review-20261013/public-mapping.json) | `7ad1eac7a9fb0545e1caf6e1139363f56f5045d0bf5b5cfee2269897eb93b021` |
| [r24_head_final](../../evaluation/trp/campaign-20261012/cloud/lab2/r24-summary.json) | `a36bee8d3bd32538550d16eda6d5e3392d3e8061b3148c62248815faee9a687b` |
| [r24_head_source_review](../../evaluation/trp/campaign-20261012/trace/r24-canonical-source-review.json) | `d159b1b7cb63c195d55856aa479430a2f81d29569b37250853e547ffbc8316a7` |
| [event_negative](../../evaluation/trp/campaign-20261012/event-negative-contrasts/audit.json) | `f25e63cfcd6f6f92e091aeaf687641ed3ff479c59e078be174076cc555cd7c24` |
| [event_negative_second_review](../../evaluation/trp/campaign-20261012/trace/event-negative-second-review.json) | `e47908f6f5c18661c4054005330f78e3d78872745c7358aa67b63baeaed514c5` |
