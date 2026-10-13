# Resultados técnicos de la campaña del 12 de octubre de 2026

Actualización final de la campaña, 13 de octubre de 2026. Los cincuenta contrastes del cliente completo están observados; las reparaciones posteriores están aplicadas y verificadas; Word/PDF ya están instalados con sus hashes verificados. Conserva los 21 resultados y los umbrales de la tesis. Las ejecuciones en nube son desarrollo técnico; las estructuras y pilotos de modelo tienen sus alcances propios descritos aquí. Los capítulos 1 a 3 no se reabren.

## Flujos remotos e infraestructura

Dos cuentas AWS Academy independientes permitieron probar dos clústeres Slurm de tres nodos, con SSH, Nextflow y Docker. El inventario comprueba controlador y trabajadores por separado, sin sumar memoria entre nodos ni combinar créditos de cuentas. La imagen fija es `sha256:1dd91e70acb153a0bd9a51346fc001dd5025f851c9598697cdd37f07d9490b0a`; el perfil numérico registrado es `haswell-single-thread` sobre x86_64.

La matriz agregada conserva sus fuentes congeladas `ecfab67` y los ejecutores de desarrollo fechados. Las correcciones posteriores de producción están en `9ada336`; la preparación operativa, en `0dcb38a`. Las nuevas fuentes no cambian retrospectivamente los paquetes originales. La preparación del operador observa el temporizador de parada de los tres huéspedes y escribe en la configuración privada la menor fecha entre esos límites y el fin de la sesión Academy. Renovar Academy no amplía por sí solo el temporizador de arranque de una VM. [Política y comprobación](../../evaluation/trp/campaign-20261012/cloud/lab2/prepare-window/prepare-status.json).

El corpus contiene 50 variantes de grafos de una proteína de desarrollo, 2XQH/A. Hubo 52 intentos: 48 primeros éxitos, dos fallos iniciales conservados y dos reintentos reparados. Los 50 casos finalmente verificados no se presentan como 50 intenciones humanas ni como una tasa científica de R1.5. El adaptador conserva errores de seguimiento SSH, consulta el mismo controlador un máximo de tres veces ante errores transitorios reconocidos y no vuelve a enviar ciencia automáticamente.

La referencia mapeada SIFTS conserva mmCIF, XML, residuos y transformación UniProt/autor para 12 unidades. El CSV coincide con el gold fijo. Su paquete automático tiene 156 archivos, ancla `b400c54428684c5d1f767324154388f906f466c849736bf28394241fabed80aa`, y verifica fuera del checkout. La auditoría detectó 320/320 alteraciones introducidas sobre copias.

La cancelación limpia observó el trabajo nativo 128 como RUNNING y solicitó Tool.Context.abort 68 ms después; Slurm terminó CANCELLED, código 143:0. El controlador terminó, no quedaron trabajos propios ni contenedores en el trabajador, y el paquete automático de 143 archivos conservó el evento final real. Su ancla es `62cf9fba9e9a2e23cb4e4e55f30bd50a36000976c438b8d4387d7468a7b735e6`. Los intentos previos deficientes siguen conservados. La parada anterior de Lab1 y la del contraste del head de Lab2, verificada el 13/10/2026 a las 03:52 UTC, se conservan como observaciones históricas. La campaña agregada posterior terminó y tiene una quiescencia independiente final; no se afirma un estado EC2 actual sólo con esas pruebas anteriores.

## Correspondencias públicas de numeración, R1.6

Se mantuvieron las 30 cadenas PDB públicas del conjunto experimental anterior, sin 2XQH ni modelos privados. Selección, fuentes, expectativas y comparador se congelaron antes de ejecutar el módulo real de Helix. Las expectativas provienen de filas mmCIF, columnas PDB y referencias por residuo del XML SIFTS oficial; no del mapeo producido ni de interpolar extremos. Gemmi 0.7.5 se comparte como lector léxico CIF; las uniones, identidad y comparación de coordenadas se implementaron aparte. Esta independencia no cubre errores comunes del lector.

Se contrastaron **11751/11751** posiciones label/autor con CA. El parser SIFTS coincidió en **30/30** cadenas. La preparación completa admitió **28/30** cadenas y convirtió **11215** residuos; las otras **2/30** se rechazaron correctamente. GLY182 de 2bm4-A y LYS353 de 1o8i-A, UniProt375, sólo tienen N en el mmCIF, sin CA, aunque SIFTS los considera observados. Se conservaron ambos rechazos, 265 residuos no observados de SIFTS y cuatro CA sin referencia observada a la accesión seleccionada. Los denominadores corresponden a operaciones distintas.

No aparecieron inserciones ni ubicaciones alternativas; no se valida ese dominio real. Los intervalos son sondas de numeración, no unidades de repetición anotadas por una experta. Una cadena admitida y ambos rechazos se reprodujeron con informes idénticos byte a byte. Es cobertura adicional de desarrollo de R1.6, sin referencia humana, reserva ni validación biológica. Los archivos originales y los fallos se conservan.

[Resumen y alcance](../../evaluation/trp/campaign-20261012/mapping-public-contrasts/README.md), [auditoría por cadena y residuo](../../evaluation/trp/campaign-20261012/mapping-public-contrasts/audit.json) y [verificación final de root](../../evaluation/trp/campaign-20261012/checks/root-review-20261013/public-mapping.json). Esta última conserva comando, salida exitosa, fecha y hashes del verificador y resumen. El protocolo limitó cada URL a una petición de 30 segundos y 20 MB; la alternativa XML oficial sólo se admitió después de HTTP404 del XML remediado. El fixture tipado heredado se identifica como dependencia capturada retrospectivamente, sin atribuirle congelación prospectiva.

## Recursos: observación y límite de inferencia

Las salidas de las tareas científicas muestran límites efectivos Docker de 2 CPU, 2 GiB y cero swap. En la ruta SSH ordinaria no verifican un límite duro conjunto de controlador/cliente/remoto ni una cuota común de almacenamiento; una petición estricta se rechaza sin el perfil opcional verificado. El perfil co-localizado descrito después aporta una garantía de ingeniería distinta y delimitada. La ingeniería local XFS/cgroup anterior conserva su propio scope; no demuestra por transferencia R2.2 agregado en nube.

En SIFTS, Nextflow informó peak RSS de 11.7 MB y 188.6 MB para SELECT y GEOMETRY, con tiempos de comando 173 ms y 2.6 s. Su wrapper agrega VmRSS/VmHWM del árbol de procesos muestreado; no es una medición independiente de memoria física única ni un pico del clúster. Slurm registró duraciones nativas de cero y tres segundos, con resolución de segundos.

La carpeta final archivada del cliente tiene 7882950 bytes regulares y 8417280 bytes asignados, incluida la copia portable; la carpeta final del flujo en el head tiene 4331885 bytes regulares y 4792320 bytes asignados. Se excluyen cachés y otras ejecuciones. Estos tamaños son finales, no picos ni cuotas. El contraste del head R2.4 original quedó cerrado: 40 escenarios, 26 factibles y 14 inviables, seis falsos rechazos (6/26, 23,08%) y 34/40 aciertos (85%). Conserva 42 intentos enviados y dos desconocidos históricos; no quedan casos únicos sin resolver. La meta de falso rechazo de 5% no se alcanza. Una extensión decidida tras observar los originales añade seis inviables y se informa por separado, sin sustituir el denominador original. El oráculo acotado no comprende preparación/exportación del cliente real: estas tasas no son el indicador científico ni R2.2 agregado. [Fuentes verificadas](../../evaluation/trp/campaign-20261012/trace/r24-canonical-source-review.json).

## Perfil estricto con el cliente completo, resultado final

La revisión congelada `ecfab67` ofrece un perfil opcional co-localizado. El cliente real de Helix, bootstrap, SQLite persistente, copia inicial, temporales, cachés propias, trabajo NFS y exportación portátil se miden dentro de un proyecto XFS. Cliente, Python y Nextflow comparten un cgroup de 1 CPU, 2 GiB y swap cero; las tareas Slurm usan asignaciones separadas de 2 CPU y 2 GiB. Se materializan las entradas en los trabajadores con `stageInMode=copy`. Se excluyen software preinstalado, cachés compartidas Docker/Nextflow y telemetría externa. No se suman memorias entre nodos ni se extienden estas garantías a la ruta SSH ordinaria o todas las herramientas del dominio.

El primer piloto completo observó 37 380 096 bytes frente a 21 295 104 estimados: subestimación de 16 084 992 bytes conservada, sin exceder el presupuesto de 128 MiB. Antes de congelar la campaña se calibró una reserva de 32 MiB a partir del residuo sobre las copias deterministas; el perfil ordinario conserva 12 MiB. El nuevo piloto observó 36 831 232 bytes frente a 42 266 624 estimados, sobreestimación de 14,76 %, con cuatro trabajos nativos, CSV propio, SQLite y exportación verificados. Los intentos de desarrollo fallidos permanecen separados.

Un control causal independiente copió la misma fuente de 359 397 bytes con Bun: fallo terminal ENOSPC bajo 64 KiB y copia idéntica bajo 128 MiB, con espacio e inodos libres en la raíz XFS. La primera lectura de `statvfs` dentro del proyecto estaba recortada por la cuota y su revisión queda conservada. La regla exige un fallo terminal enlazado por ruta, tiempo y proceso a la syscall causal; un error opcional de caché ignorado no demuestra inviabilidad.

| Conjunto | Observados | Factibles | Inviables | Desconocidos | Falsos rechazos | Aciertos comprobados / observados | Mediana de sobreestimación |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Original | 40/40 | 18 | 18 | 4 | 0/18 | 36/40 | 13,90 % |
| Frontera separada | 6/6 | 6 | 0 | 0 | 3/6, 50 % | 3/6 | 11,20 % |
| Suplemento posterior | 4/4 | 2 | 2 | 0 | 0/2 | 4/4 | 12,64 % |

Los cuarenta originales y seis de frontera se congelaron antes de sus salidas. El suplemento se decidió tras observar el original y se congeló antes de sus propias salidas, con nuevas entradas e IDs. Sólo la unión de originales y suplemento, 44 observados con cuatro desconocidos, alcanza veinte factibles y veinte inviables; los cuarenta originales no cumplen ese mínimo. La unión descriptiva de los tres conjuntos conserva 26 factibles, 20 inviables y cuatro desconocidos, con 3/26 falsos rechazos, 11,54 %. No es una estimación poblacional: todas las variantes derivan de una proteína de desarrollo y los presupuestos se eligieron con diseños distintos.

La frontera demuestra tres falsos rechazos: con 39 MiB los flujos completaron el cliente, sus cuatro trabajos, el CSV propio, SQLite y la exportación, pese al rechazo real de Helix por una predicción de 42 266 624 bytes. **El 50 % de falso rechazo de la frontera incumple el umbral de 5 %.** No se cambió el umbral ni se ajustó el estimador después de observar esos resultados. El contrafactual conserva la decisión real y sólo permite ejecutar rechazos exclusivos de estimación `workBytes`; no salta cuotas, cgroups, permisos, propiedad ni plazo. Sus eventos de ejecución no se presentan como admisión original.

No se observaron excesos de cuota ni excesos de predicción en casos admitidos. Los 26 flujos completos reprodujeron sus conteos sin diferencias. Los picos de bloques asignados se muestrearon cada 0,5 s; no equivalen a todos los discos ni garantizan capturar todo pico transitorio. RAM y duración se informan separadamente. No hay un P95 de latencia medido; los temporizadores de 1080 segundos y las duraciones de tareas no constituyen ese percentil.

El auditor congelado conservó 18 factibles, diez inviables y doce desconocidos originales. Las revisiones separadas de resolución temporal y descriptores aportaron ocho inviables causales adicionales, sin borrar las primeras interpretaciones. Los desconocidos finales son `AGG-08-small` y `AGG-18-small`, por falta de la syscall de creación de directorio, y `AGG-13-generous` y `AGG-14-generous`, por fallos de infraestructura sin prueba de inviabilidad por presupuesto.

La continuación detuvo sólo el conductor local, recuperó el mismo intento y despachó únicamente los trece casos aún no enviados después de un ciclo legítimo de las mismas máquinas. No reintentó los fallos terminales. Se documentó `Stale file handle` en la preparación de E/S de Slurm, se restauró el XFS existente sin formatear ni reiniciar cuotas y se fijó `fsid=43` de NFS con `root_squash`. Los errores de los dos primeros preflights se conservaron; el tercero completó los trabajos nativos 316 y 317 antes de continuar.

La revisión final reprodujo cincuenta interpretaciones con las fuentes congeladas y aprobó 1766 controles. El manifiesto verifica 21 059 archivos, 2 770 277 634 bytes; los datos grandes originales siguen fuera de un commit de código. La quiescencia final de campaña se comprobó a las 08:21 UTC: sin trabajos propios, contenedores ni procesos de cliente/tracer activos.

[Resumen y denominadores](../../evaluation/trp/campaign-20261012/aggregate-resource-contrasts/summary.json), [reproducción en frío](../../evaluation/trp/campaign-20261012/aggregate-resource-contrasts/final-package-verification.json), [quiescencia](../../evaluation/trp/campaign-20261012/aggregate-resource-contrasts/final-quiescence.json) y [figura final](../../evaluation/trp/campaign-20261012/aggregate-resource-contrasts/figures/aggregate-storage.png). El SHA del resumen es `a53095ee21ad8a1a4ba2efcfb7245e3e082cf5d1b1a33419685150f7026970e4`. R2.4 científico permanece sin medir.

## Sesiones negativas de R3.2

Cuatro sesiones locales reales de preparación/ejecución, con inventario del host y Protocol/Question.Service, comprobaron 13/13 registros exigibles con causas, tipos y orden: admisión 4/4, protocolo 3/3, permisos 4/4 y aprobación 2/2. Dos negativas que llegaron a trp_run conservaron paquetes automáticos fallidos de 25 archivos, verificados en frío. Los rechazos de preparación tienen registros JSON y del protocolo; no se fabrican eventos de ejecución. Las expectativas se fijaron antes del productor; las acciones se observaron en vivo antes de leer sus registros, intercaladas con los eventos. Los callbacks son sintéticos, sin modelo, ciencia, AWS ni anotaciones humanas. [Segunda revisión](../../evaluation/trp/campaign-20261012/trace/event-negative-second-review.json). Una [revisión de otro agente](../../evaluation/trp/campaign-20261012/trace/event-negative-independent-agent-review.json) añadió 31 controles, comprobó causas específicas y el enlace de la respuesta «Rechazar» con Question.Service y volvió a verificar ambos paquetes fallidos sin mutar los originales.

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
- Los límites y tamaños de la ruta SSH ordinaria no demuestran las garantías agregadas del perfil opcional. La cuota co-localizada cubre sólo sus rutas declaradas; sus bloques muestreados no abarcan todos los discos físicos.
- El contraste head R2.4 original 40 y la extensión posterior 6 se informan por separado; falso rechazo 6/26 y acierto 34/40 sólo describen ese alcance. No son tasa científica ni prueba agregada del cliente real.
- Las 30 cadenas públicas contrastan numeración: 11751 correspondencias label/autor y 11215 residuos preparados en 28 cadenas, con dos rechazos correctos conservados. Gemmi léxico compartido y cero inserciones observadas limitan la independencia y cobertura; no es evaluación reservada ni anotación biológica.
- Se conservan los 21 identificadores y el cierre autoral de los capítulos 1 a 3.

## Reparaciones posteriores y estado operativo

Las reparaciones de backend, verificación semántica y seguimiento de IDs nativos están aplicadas en `9ada336`, con helper operativo `0dcb38a`. La regresión local aprobó 543 pruebas, omitió 63 opt-in y no tuvo fallos; 1601 aserciones, 57 archivos y tipos correctos. Las pruebas locales y sus fronteras simuladas no se presentan como ejecuciones científicas de nube.

La nueva [integración final](../../evaluation/trp/campaign-20261012/checks/post-campaign-production-20261013/cloud/summary.json) aprobó 89 controles independientes. POST-01 ejecutó cuatro tareas nativas, IDs 377 a 380 COMPLETED, CSV idéntico al gold propio, SQLite persistente y exportación de 152 archivos. El backend coincide entre ejecución, Run y evento de finalización. POST-04 usó un fixture de ingeniería de 1000 unidades sintéticas, sin gold biológico inventado: tras aprobación y admisión científicas reales se canceló una sola vez el trabajo propio 384 observado RUNNING. Terminó CANCELLED, ExitCode 0:9; el ledger retuvo el estado al desaparecer de la cola y Helix produjo el paquete automático de fallo de 151 archivos. Ambos paquetes pasan el verificador frío por defecto sin legacy.

El observador rápido alcanzó sólo COMPLETING en sus 80 consultas; se conserva. Una lectura independiente posterior y el ledger confirman CANCELLED. El intervalo observado hasta la primera lectura terminal de producción fue 30418,009 ms; no es latencia interna, límite máximo ni P95. Se conservaron dos errores de harness anteriores: colisión de carpeta antes de lanzar el cliente y lectura incorrecta de una salida visual truncada después de Prepare, antes de Run. La enmienda validó offline metadata y artefactos durables antes del nuevo intento, sin cambiar productor ni aprobación.

Las respuestas frescas de EC2 DescribeInstances confirman las tres instancias propias de Lab1 detenidas a las 17:06:16 UTC y las tres de Lab2 a las 17:50:26 UTC. En Lab2, la parada siguió a la recuperación de la integración y la comprobación de quiescencia de las 17:43:06 UTC. Los volúmenes permanecen; la parada de cómputo no significa coste de almacenamiento cero ni factura final. Los USD 48,6 restantes de Lab2 fueron un reporte del portal, con demora de facturación. [Lab1](../../evaluation/trp/campaign-20261012/cloud/lab1/final-stopped-post-corrections-20261013.json), [Lab2](../../evaluation/trp/campaign-20261012/cloud/lab2/final-stopped-post-corrections-20261013.json).

No queda un caso de la matriz ni de esta integración por enviar y no se requieren más cuentas. Los siguientes resultados científicos necesitan referencias independientes: R1.5 lingüístico, R3.3 con turnos y kappa, y R3.8 físico. Las rutas dedicadas y contratos restantes conservan sus límites. El OAuth elegido funciona y sus límites declarados no implican pedir otra API para este cierre técnico. La documentación inicial sigue a cargo del autor. El Word/PDF ya están instalados con hashes comprobados; la entrega final y archivos locales corresponden al agente principal.

## Índice de fuentes y hashes

Los hashes siguientes fijan las fuentes concretas de esta actualización. El índice original conserva observaciones de avance fechadas. Las fuentes finales del cliente completo y la revisión negativa adicional se añaden al índice; las observaciones históricas conservan sus hashes y ninguna tasa del head se transforma en indicador científico o agregado.

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
| [strict_pilot_old](../../evaluation/trp/campaign-20261012/aggregate-resource-contrasts/smoke-outcomes-r4/summary.json) | `b70b92ac12501054b84c68dc5f7b0e4d0b2d3cb0c56d732a4977a8142a3cfd8a` |
| [strict_pilot_new](../../evaluation/trp/campaign-20261012/aggregate-resource-contrasts/smoke-outcomes-r5/summary.json) | `11956c8dd067a2e9ef2802c6f1a2ccc05f170723a145409baf256f91357eb241` |
| [strict_calibration](../../evaluation/trp/campaign-20261012/aggregate-resource-contrasts/calibration-before-final-campaign.json) | `db8454721db409c014ab96320d4e9b34bcdf1015bbbab177ca4768a9c8b2f6a4` |
| [strict_copy_causal](../../evaluation/trp/campaign-20261012/aggregate-resource-contrasts/copy-causal-controls/mechanism-review.json) | `f3eb0d1f7f1e12b9c5c6a98d4ff7cf17ed19f883d751b6bc10d1af467d23dd1d` |
| [strict_frozen_original40](../../evaluation/trp/campaign-20261012/aggregate-resource-contrasts/campaign-inputs/freeze.json) | `c33fb8b69e6361fb90bac025ccbf62fb590122b93b5f78d8da754b3886d28f20` |
| [strict_frozen_boundary6](../../evaluation/trp/campaign-20261012/aggregate-resource-contrasts/boundary-inputs/freeze.json) | `6ef89e2db501a307ad1034ab41f9ad7c5dd01029848c2115a23d97c3ac0a518e` |
| [lab1_fresh_stop](../../evaluation/trp/campaign-20261012/cloud/lab1/final-stopped-20261013.json) | `1ef4b53f0f0e78fe9db4349fed3592cc581a478528093dcf641e5b4e92683364` |
| [strict_regression](../../evaluation/trp/campaign-20261012/checks/strict-profile-integration/root-regression-pinned-environment/summary.json) | `f927e1a7d90ff53360e91e7b030602d40b590e1dd868e40f3dc97bbefddac5dc` |
| [strict_storage_focused](../../evaluation/trp/campaign-20261012/checks/strict-profile-integration/calibrated-client-storage/summary.json) | `f31cb2718ed3b2c1f35516f6114d2710ccad7fdc695393571d8d3491cd9efb02` |
| [strict_typecheck](../../evaluation/trp/campaign-20261012/checks/strict-profile-integration/calibrated-typecheck/summary.json) | `de42608c7699892be5d45c0562e581c538653b05dbbb0bf6c19d88b6457b360f` |
| [strict_final_summary](../../evaluation/trp/campaign-20261012/aggregate-resource-contrasts/summary.json) | `a53095ee21ad8a1a4ba2efcfb7245e3e082cf5d1b1a33419685150f7026970e4` |
| [strict_final_cases](../../evaluation/trp/campaign-20261012/aggregate-resource-contrasts/cases.csv) | `6de287549d175b9402b511bcbb9298a91383b3b4a7a331b1ee05387e474e329a` |
| [strict_final_cold_audit](../../evaluation/trp/campaign-20261012/aggregate-resource-contrasts/final-package-verification.json) | `99bf437f36f6c5d7c7cfd1ca1541b7fda143adec4b7486fef82caa6958bd1ed7` |
| [strict_final_quiescence](../../evaluation/trp/campaign-20261012/aggregate-resource-contrasts/final-quiescence.json) | `3aac5f5c80421d416f61e489d9c0095d00d1059458cf96b33072a38198cab24a` |
| [strict_final_manifest](../../evaluation/trp/campaign-20261012/aggregate-resource-contrasts/analysis-manifest.json) | `f15ca302f6159e54997ec0e2ea85c37470cae26cd8967aee6612ad19f46eaf16` |
| [strict_final_manifest_verification](../../evaluation/trp/campaign-20261012/aggregate-resource-contrasts/manifest-verification.json) | `a8b0e115e34e8f099d9897e3ad59cdc524be9342859ec4a35f70a54f4e71525d` |
| [strict_frozen_supplement4](../../evaluation/trp/campaign-20261012/aggregate-resource-contrasts/extension-inputs/freeze.json) | `2947a9d34ab84687e16e848620b3221ad4add9642ee8710827b311c14fd691b3` |
| [strict_final_figure](../../evaluation/trp/campaign-20261012/aggregate-resource-contrasts/figures/figure-manifest.json) | `27f9a0fdefcde94568118df07a247f5eefa3bb5b6333b0d1a622972a2e4352a8` |
| [event_negative_agent_review](../../evaluation/trp/campaign-20261012/trace/event-negative-independent-agent-review.json) | `ca0b8d07f60b66cd5dba64a0b30c3d9cf6dd6d857725f183480e9d4a3f700a38` |
| [cloud_status_20261013T1634](../../evaluation/trp/campaign-20261012/checks/user-status-20261013T1634.json) | `5edb967947644800948dc1c7ce6f1d23bf16425829f02b516ea757626a0cab3e` |

### Comprobaciones posteriores y estado final

| Fuente | SHA-256 |
| --- | --- |
| [post_campaign_local](../../evaluation/trp/campaign-20261012/checks/post-campaign-production-20261013/summary.json) | `fa5d578fb5e9983087a7042204f85fdc4761ef12e90a3b12ef407d2e460b9324` |
| [post_campaign_regression](../../evaluation/trp/campaign-20261012/checks/post-campaign-production-20261013/broad-summary.json) | `145ad9de75f48a69db680c9f8e5515947a6f6e9dcf22ee2af4570137bd4ca08f` |
| [post_campaign_typecheck](../../evaluation/trp/campaign-20261012/checks/post-campaign-production-20261013/typecheck-summary.json) | `1267514fc51af9115c22485c3c4c2b2c9a3dd8428959f138104241e97f436bc5` |
| [post_campaign_native](../../evaluation/trp/campaign-20261012/checks/post-campaign-production-20261013/native/summary.json) | `5793f61c7e8c7828b4f573701930609db96946d400acefb2683edb1763a41d0f` |
| [post_campaign_cloud](../../evaluation/trp/campaign-20261012/checks/post-campaign-production-20261013/cloud/summary.json) | `79d058fee282b559e7133ce43d602b3633484d6f5829a4d5e1bd4dae0df6530f` |
| [post_campaign_cloud_quiescence](../../evaluation/trp/campaign-20261012/checks/post-campaign-production-20261013/cloud/post-quiescence.json) | `3511e2ef52679a46d77c508eb939c142f761b3b07b3783d46ce4e93c64403856` |
| [lab1_post_corrections_stop](../../evaluation/trp/campaign-20261012/cloud/lab1/final-stopped-post-corrections-20261013.json) | `9175710c5605bdaa353e89a49feb59ef05f6faf40a6d4a848cb4b470161f9fb7` |
| [lab2_post_corrections_stop](../../evaluation/trp/campaign-20261012/cloud/lab2/final-stopped-post-corrections-20261013.json) | `20feafae4b138f28fb6e23c3ccb4587f681407293154ae8c5b091fd95848ff17` |

## Documento instalado

Word y PDF instalados el 13 de octubre a las 18:02 UTC: **155 páginas, 261 comprobaciones de render y diez notas rojas nuevas**. Los capítulos 1 a 3, bibliografía, imágenes originales y 21 IDs se conservaron. La revisión visual aceptó el candidato; los hashes instalados y el backup exacto del archivo del autor se verificaron. [Instalación y hashes](../../evaluation/trp/campaign-20261012/document/installation.json). La tesis sigue incompleta en sus validaciones científicas obligatorias.

| Artefacto | SHA-256 |
| --- | --- |
| Word instalado | `c545774dadf8e4910c8ae620cb3e4f3f8830fa38aa02e40accd03dcde0c118ac` |
| PDF instalado | `9f0fa60a320a12049a15d34ff69e14a997970afdc5a4874b804b16f74f427438` |
| Backup exacto del autor | `0b5e1e0c7a74f4dd3468656b6f9abef945bfeaf19b791c033bdc0c8cc573b28d` |
| [installed_document](../../evaluation/trp/campaign-20261012/document/installation.json) | `9c85c3ac0b2ce658801c087dcb195a31c076b968ffd5781b4faf56229d53e828` |
| [final_rendered_document](../../evaluation/trp/campaign-20261012/document/final-rendered-audit.json) | `f51b5edc4b39916de9c463edfe390d3c4587cb387ad2aad1d038ee41be7a68d1` |
| [final_document_peer_review](../../evaluation/trp/campaign-20261012/document/final-peer-review-20261013.json) | `f848a99aa772e9b4bfbf4020ba9d345609557a0951cbef0b991b601ceb9e77a7` |
