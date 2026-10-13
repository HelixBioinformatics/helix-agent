# Estado del cierre

## Estado vigente, 12 de octubre de 2026

La campaña técnica ya probó Helix mediante SSH, Slurm, Nextflow y Docker en dos clústeres AWS Academy independientes de tres nodos. La implementación y la tesis completas siguen abiertas: pasar pruebas de ingeniería no demuestra los 21 indicadores científicos. Los capítulos 1 a 3 permanecen cerrados por el autor.

- **Flujos:** 52 intentos sobre 50 grafos únicos de una proteína de desarrollo; 48 primeros éxitos, dos fallos iniciales conservados y dos reintentos reparados. Los 50 casos finalmente verificados no constituyen la tasa científica de R1.5.
- **SIFTS y trazabilidad:** referencia remota de 12 unidades, CSV gold idéntico, paquete automático de 156 archivos verificado fuera del checkout y 320/320 alteraciones offline detectadas. Cancelación limpia de trabajo nativo 128 con RUNNING, señal real, CANCELLED y paquete automático de 143 archivos. Contraste público: 30 cadenas, 11751/11751 label/autor, parser SIFTS 30/30; 28 preparaciones con 11215 residuos y dos rechazos correctos sin CA. Gemmi léxico compartido; cero inserciones observadas no acredita ese dominio. Desarrollo sin referencia humana ni evaluación reservada. [Verificación final independiente](../../evaluation/trp/campaign-20261012/checks/root-review-20261013/public-mapping.json).
- **Recursos:** límites efectivos por tarea Docker de 2 CPU, 2 GiB y cero swap. No se demuestra límite agregado cliente/controlador/remoto, pico de disco ni cuota remota dura; una solicitud estricta se rechaza honestamente. R2.4 del head terminó: 26 factibles y 14 inviables de 40; 6/26 falsos rechazos (23,08%) y 34/40 aciertos (85%), sin alcanzar la meta de 5%. La extensión posterior de seis inviables se informa separada; no es tasa científica ni prueba agregada del cliente real. Lab1 está detenido según comprobación registrada. La revisión a951d73 vincula la ventana a la mínima fecha Academy/temporizadores observados de los tres huéspedes.
- **R3.2 negativas:** cuatro sesiones locales y 13/13 registros con causas y orden verificados (admisión 4/4, protocolo 3/3, permisos 4/4, aprobación 2/2). Callbacks sintéticos; dos paquetes fallidos de 25 archivos verifican en frío. [Segunda revisión](../../evaluation/trp/campaign-20261012/trace/event-negative-second-review.json).
- **Experta:** asesora Layla Hirsh seleccionada; independencia respecto del desarrollo declarada por el autor. Entrega real de 70 solicitudes preparada. Referencias, paráfrasis y turnos reales anotados no recibidos; kappa pendiente.
- **Modelo:** cuatro casos piloto reales de desarrollo con `openai/gpt-6-sol`, razonamiento `medium` y OAuth existente. Sin ciencia ni reserva humana ejecutada en el piloto. El cap solicitado de 8192 tokens no es duro bajo este adaptador; factura efectiva y revisión interna del proveedor desconocidas.
- **Estructuras:** 78 originales Pratt disponibles. CCTBX principal produjo observables en 105/108 casos y conservó tres timeouts de 180 s; el contraste 600 s recuperó 3/3. FreeSASA descriptivo evaluó 108/108. C9 continúa no evaluable como veredicto amplio: no hay clasificador validado, sensibilidad ni especificidad física.

[Informe y hashes](RESULTADOS-AWS-20261012.md), [21 resultados vigentes](trazabilidad.md), [checkpoint](checkpoint.json). Las fuentes y criterios figuran también en los campos `vigente` y `current` de los JSON. La documentación inicial queda a cargo del autor y no se registra como tarea pendiente del agente.

**Nota de supersesión:** las entradas fechadas siguientes conservan historia. Las afirmaciones antiguas de anotador/clúster/modelo pendientes, originales Pratt ausentes, adaptador remoto inexistente o ingeniería R2.2 completa fuera de su scope local se leen con sus fechas y quedan sustituidas por esta actualización. No se reescriben sus resultados ni se borran fallos.

## Actualización de originales Pratt, 1 de octubre de 2026

Se recuperaron del envío de los autores 78 modelos AF2 de rango 1, sus puntuaciones y sus PAE, correspondientes a toda la Tabla S1. Helix incorporó el contrato local ColabFold y ejecutó dos perfiles fijados antes de sus veredictos. El principal produce 78/78 alarmas mecánicas y marca los cinco ejemplos explícitamente problemáticos de las figuras 3, 6 y 7; esto no valida discriminación ni plausibilidad física. El control físico sigue no evaluable, con cobertura 0%, sensibilidad física y especificidad sin calcular. Faltan un control físico validado y al menos 30 negativos pertinentes revisados. Los originales de la Tabla S1 dejan de ser dependencia pendiente; los de las figuras 1/S1 y 14 no están en este envío. No se usó el modelo ni AWS. [Informe y evidencia](../../evaluation/trp/reference/pratt-author-20261001/README.md).

## Preparación de anotación — 28 de septiembre de 2026

La asesora bioinformática fue propuesta por el tesista para revisar la guía y/o coordinar un investigador externo. Aceptación, independencia respecto del desarrollo y disponibilidad por confirmar. Se prepararon [materiales para la reunión](reunion-asesora-20260928/README.md), PDF, Excel y piloto de 12 solicitudes/12 turnos sin etiquetas humanas. La reserva sigue pendiente; decisiones de modelo/presupuesto y Pratt aplazadas por el autor. AWS se analizó como opción de clúster; no hay acceso, gasto ni provisión autorizados en esta entrega. El adaptador TRP de ejecución local necesita ampliación para un planificador remoto.

## Verificación de Helix — 23 de septiembre de 2026

Nombre actual: **Helix Agent**, comando `helix`. Segunda estación: versión publicada 0.3.0, instalación idempotente, 139 archivos verificados y dos alteraciones rechazadas (corpus CLI y paquete portable); geometría de 12 unidades idéntica. Nueva referencia local SIFTS por herramientas del agente también satisfactoria. Cero llamadas LLM.

Ruta predicha integrada mediante `trp_predicted_geometry` y aprobación del servicio de preguntas; mantiene alcance de desarrollo y almacenamiento sin cuota dura. El código incorpora `helix upgrade`; el binario publicado 0.3.0 todavía se actualiza repitiendo el instalador oficial, sin desinstalar. [Plan y límites](VERIFICACION-HELIX-20260923.md), [evidencia](../../evaluation/trp/verification-20260923/README.md).

La regresión inicial detectó el hash de catálogo obsoleto del caso activo tras el cambio de branding. Se actualizó solo la referencia de desarrollo y se ejecutó con `HELIX_TRP_PYTHON` apuntando al entorno Gemmi existente. Las evidencias históricas permanecen intactas.

Identificadores actualizados al 23/09/2026: tres objetivos y 21 resultados. Las evidencias fechadas conservan su numeración original; consulte [equivalencias](renumeracion-20260923/README.md).

Revisión editorial del 23 de septiembre de 2026: causas agrupadas en tres pares y cinco objetivos reorganizados en tres. Se conservan los 21 resultados y sus métricas. [Correspondencia y cambios](agrupacion-20260923/CAMBIOS.md).

Renumeración posterior del 23/09/2026: los códigos vigentes se toman de las tablas 1.2.4 del Word. El [mapa de equivalencias](renumeracion-20260923/README.md) sustituye la decisión anterior de conservar los prefijos R1–R5.

Word sincronizado con las tres causas, los tres objetivos y la numeración vigente: métodos, resultados, conclusiones y anexos. Tabla accidental duplicada retirada e índice reconstruido; véase [auditoría documental](renumeracion-20260923/document-checks.json).

## Cierre técnico — 21 de septiembre de 2026 (registro histórico; supersedido el 12/10/2026)

Se ejecutó [el plan CT1–CT5](PLAN-CIERRE-TECNICO.md) con tres agentes y revisión integrada.
Los apartados siguientes conservan la historia de fases; sus pendientes se actualizan aquí.

- Motor 1.4.0: correspondencias label/autor y SIFTS/UniProt integradas en preparación y aprobación. Referencia real: 206 residuos, 12 unidades, geometría idéntica y copia portable verificada de 139 archivos.
- Catálogo 1.2.0: tres herramientas admitidas de seis auditadas. STRPsearch tiene ejecución protegida y herramienta `trp_detect`; referencias reales CIF, PDB y núcleo de la herramienta producen siete unidades candidatas. La aprobación del ensayo es sintética; no constituye anotación humana.
- Modelos predichos: CLI verificable con identidad AFDB, pLDDT y PAE; tres segmentos artificiales ejecutados correctamente. Se conserva el fallo inicial con dos segmentos. Falta integrar esta ruta en `trp_prepare`/`trp_run`; no prueba exactitud biológica.
- Regresión: 500 pruebas aprobadas, una omitida; 78 pruebas Python aprobadas y chequeo de tipos correcto. [Evidencia](evidencia/cierre-tecnico-20260921.json).
- F6 en preparación: siete artefactos técnicos con hashes y verificador por campaña. El borrador no está congelado: faltan corpus reservado, particiones, revisión independiente y las dependencias aplicables de anotación/modelo/presupuesto.
- ReUPred sigue sin entorno compatible validado. RepeatsDB declara CC BY 4.0 en su web actual, pero faltan correspondencias inequívocas de loci y confirmar aplicabilidad a la API. Los nuevos suplementos recuperados para Pratt resultaron ajenos al artículo y fueron rechazados; siguen faltando coordenadas/PAE originales.
- Word actualizado solo en resultados, conclusiones y anexo A.22. Los 21 resultados tienen [mapa legible](trazabilidad.md) y [mapa JSON](trazabilidad.json); presencia de evidencia no equivale a cumplimiento empírico.

F5 mantiene abierta su cobertura completa; F6 no ha iniciado mediciones reservadas. R2.2 conserva su verificación de ingeniería en la segunda PC. La detección y la CLI predicha todavía no tienen cuota dura de almacenamiento, por lo que no heredan esa garantía de recursos.

## Reanudación — 21 de septiembre de 2026

El autor declara cerrados problemática, marco conceptual y estado del arte.
Confirmó sustituir las tres secciones «Cadenas de búsqueda», «Documentos
encontrados» y «Criterios de inclusión/exclusión» por una nota roja. La copia
revisada actualiza resultados de R1.6 y añade A.21; no reabre la revisión de fuentes.

- Adaptador explícito offline `script/tesis/map_residue_units.py`: verifica cada
  residuo label/autor contra ambos archivos, identidad, coordenadas CA y B-factor.
  Ocho pruebas satisfactorias, incluidas ausencias, duplicados, marco equivocado,
  cambio de identidad/coordenadas y numeración no contigua.
- Ejecución real con los intervalos convertidos: **12 unidades, 206 residuos**,
  CSV idéntico a la referencia de GeomeTRe. [Evidencia](../../evaluation/trp/reference/coordinate-20260921/execution.json).
- Regresión: **482 aprobadas, una omitida por defecto, cero fallos**. Referencia
  real Nextflow ejecutada aparte: aprobada; **35 controles Python aprobados**.
  La copia portable verifica **127 archivos**. [Registros](evidencia/reanudacion-20260921).

Es evidencia de desarrollo sobre 2xqh, no evaluación reservada. R1.6 continúa
parcial: el preprocesamiento todavía no se integra automáticamente al flujo;
SIFTS/UniProt, detección y ejecución predicha siguen pendientes. F6 puede
prepararse, pero sus mediciones dependientes requieren resolver esas rutas,
referencias independientes, anotador y modelo/presupuesto.

## Cierre de R2.2 — 15 de septiembre de 2026

Motor actual `trp-nextflow/1.3.0`; contador `trp-resources/1.2.0`. Implementación, ensayos y Word actualizados. [Informe](R3.2-RECURSOS.md), [auditoría](evidencia/r32.json) y [decisiones pendientes](DECISIONES-PENDIENTES.md). No se usó API de modelos ni nube. Regresión: 482 pruebas correctas y una referencia externa omitida por defecto; referencia real ejecutada por separado. Auditoría portable: 266/266 alteraciones detectadas. Word: 135 páginas, anexo A.20 y 33 notas rojas en cursiva.

Actualizado: 15 de septiembre de 2026.

## Fase 5: controles implementados en el alcance inicial

- Catálogo versionado de **nueve controles**, lector mmCIF con Gemmi 0.7.5 y herramienta `trp_inspect`. Cada control conserva valor, umbral y motivo; diferencia fallos, no evaluables y no aplicables. [Método, algoritmo y límites](F5-CONTROLES.md).
- En F5, el motor `trp-nextflow/1.2.0` incorporó automáticamente reporte, catálogo y programa al digest aprobado de la ruta PDB experimental, y a los métodos/manifiesto. La inspección de modelos predichos no los admite a GeomeTRe ni certifica su plausibilidad.
- Referencias reales 2xqh/mmCIF y AF-P69905-F1 v6 con API y PAE. P69905 prueba confianza y ejes mediante intervalos artificiales; no es anotación de repeticiones. Ambos casos y sus perturbaciones son desarrollo excluido de T-STRUCT.
- **478 pruebas de regresión correctas, una referencia omitida por defecto, cero fallos; 35 pruebas estructurales Python correctas.** La referencia real de Nextflow pasó por separado y conserva el CSV de 12 unidades. Su copia contiene **127 archivos; 262/262 fallos de integridad detectados**. [Evidencia F5](evidencia/fase5.json).
- Auditoría de Pratt: 78 filas de predicciones publicadas en los suplementos; **cero archivos de coordenadas/PAE originales encontrados en el paquete descargado, cero modelos originales ejecutados**. Las filas no son etiquetas de fallo verificadas. Sensibilidad y especificidad permanecen sin calcular. [Auditoría de recuperación](../../evaluation/trp/reference/structural-f5/pratt/recoverability.json).
- Word: R3.5–R3.8, conclusiones y anexo A.19 actualizados; se conservan los cinco capítulos, cuatro ilustraciones y bibliografía. Notas nuevas en rojo y cursiva. [Auditoría documental](evidencia/documento-fase5.json).

**F5 no cierra la cobertura del dominio completo ni habilita todavía F6.** Persisten la ejecución admitida sobre modelos predichos, SIFTS/UniProt, detección, interpretación completa de constructos y evaluación independiente de fallos físicos. Los modos de ensamblaje y plausibilidad son explícitamente no evaluables con esta batería. La falta de archivos originales de Pratt es una dependencia de recuperación, no una tasa de acierto.

**R2.2 tiene la implementación y verificación de ingeniería completas.** La segunda PC ejecutó siete contrastes finales con cuota XFS y límites cgroup v2 de controlador/tareas: cero sobrepasos y subestimaciones observadas, margen mediano 13,54%. Se conservan dos subestimaciones de la primera serie y la corrección previa a la segunda. La evaluación reservada T-RESOURCE sigue pendiente. [Evidencia y ámbito](R3.2-RECURSOS.md).

## Fase 4: implementación de ingeniería completa; evaluación reservada pendiente

- Inventario fechado, presupuesto explícito para revisión y negativas por recurso integrados en `trp_prepare`/`trp_run`. Se reobservan recursos después de aprobar y antes del análisis real. El estado y las restricciones del protocolo forman parte del contenido protegido. [Diseño y límites](F4-ADMISION.md).
- Copia portable de todos los archivos de ejecución, verificador Python independiente, eventos con causas y métodos por plantilla. Referencia final: **121 archivos; 250/250 fallos inyectados detectados**. [Auditoría](evidencia/portable-audit-fase4.json).
- Referencia real: dos tareas simuladas y dos reales; CSV de 12 unidades idéntico a F2/F3. Aprobación sintética identificada, inventario local observado y presupuesto de ingeniería. **472 pruebas correctas, una omitida por defecto y cero fallos**; referencia real correcta por separado. Tipos y lint sin errores. [Evidencia](evidencia/fase4.json).
- Reglas de intervención en español e inglés, con texto y señales conservados. El acuerdo externo sigue sin medir; los ejemplos de desarrollo no son etiquetas independientes.
- Word: capítulos 4 y 5 actualizados, anexo A.18, 29 notas rojas en cursiva y cinco capítulos conservados. [Auditoría documental](evidencia/documento-fase4.json).

**Se satisface la compuerta de ingeniería de F4 para la ruta local.** Una solicitud estricta requiere una asignación XFS/cgroup verificada; fuera de ella se rechaza. El protocolo F2 permanece intacto. La cobertura pendiente de F5, R1.1/R1.6, anotador, datos originales y modelo/presupuesto siguen condicionando las mediciones dependientes de F6. La segunda PC no acredita ejecución en clúster. Se mantienen julio de 2027 y el borrador objetivo al 4 de junio. [Requisitos y opciones](DECISIONES-PENDIENTES.md).

## Fase 3: núcleo completado sobre el catálogo admitido inicial

- Integradas `trp_catalog`, `trp_prepare` y `trp_run` en el agente, con esquema, fuentes declaradas, aprobación por el servicio de preguntas y digest del paquete. Una revisión o entrada alterada invalida la propuesta; una aprobación consumida no puede reutilizarse.
- Emisor Nextflow DSL2 y validación de grafo, identidad, cadena, formato, numeración, inserciones y escalas. La ruta acepta geometría sobre unidades suministradas en PDB de autor; rechaza conversiones todavía no implementadas. [Algoritmo y límites](F3-ALGORITMO.md).
- Referencia real con Nextflow 25.10.4: configuración resuelta, dos tareas simuladas y dos reales completadas; CSV idéntico al de GeomeTRe en F2. La respuesta de aprobación de esta prueba se identifica como sintética. [Evidencia](../../evaluation/trp/reference/nextflow-f3/engineering-reference.json).
- **432 pruebas aprobadas, cero fallos**, más la referencia externa aprobada por separado. Un test externo se omite en la suite ordinaria porque requiere Docker; se ejecutó expresamente. Tipos sin errores y código nuevo sin advertencias de lint. [Registro](evidencia/fase3.json).
- Corpus técnico de **33 composiciones inválidas: 0 aceptadas y 33 motivos esperados detectados**. No sustituye la reserva T-GRAPH ni mide comprensión del lenguaje.
- STRPsearch reconstruido: la entrada completa produjo errores científicos con salida de proceso cero; una copia sin ligandos/agua produjo una región candidata con siete unidades. Se conservan ambas ejecuciones. Continúa candidato hasta cerrar reconstrucción, contratos y propagación de fallos. [Sondeo](../../evaluation/trp/F3.md).
- Word actualizado en capítulos 4 y 5 y Anexo A.17: esquema, algoritmo y evidencia. Mantiene cinco capítulos, bibliografía y cuatro ilustraciones; PDF de 123 páginas, con 27 notas rojas en cursiva. Se corrigió la exportación mediante reapertura del Word para evitar texto próximo al pie. [Auditoría](evidencia/documento-fase3.json).

**Pendientes de alcance:** R1.1 y R1.6 siguen parciales. F4 puede avanzar con inventario, admisión y manifiestos sobre esta ruta mientras la ampliación del instrumental y los mapeos se resuelve antes de F6. Los controles de modelos predichos se coordinan con F5. Anotador y clúster siguen sin confirmación; se mantienen julio de 2027 y el borrador objetivo al 4 de junio. No se ejecutaron inferencias de evaluación ni se enviaron mensajes a terceros.

## Fase 2 completada en su alcance inicial

- Catálogo TRP 1.0.0 implementado con seis recursos auditados: **dos operaciones admitidas**, tres candidatas y un comparador web. Conserva contratos de identificadores, numeración y escalas, con términos EDAM y anclas de bio.tools comprobados. [Catálogo y alcance](../../evaluation/trp/README.md).
- Referencias ejecutadas: recuperación PDB y GeomeTRe 1.0 sobre 2xqh/A con 12 unidades suministradas. Se guardan revisión, digest de imagen local, entorno, comando, archivos y hashes. El catálogo rechaza candidatos y comprueba los bytes antes de resolver una operación. La ejecución de referencia no mide detección de repeticiones.
- **R1.1 permanece parcial.** Falta integrar el catálogo y admitir detección/mapeos; las exclusiones y el traslado de esas tareas a F3 se declaran en el plan. No se presenta 2/2 como cobertura de todos los recursos TRP.
- R1.4 implementado como diseño: [protocolo 1.0.0](../../evaluation/trp/PROTOCOL.md), 21 indicadores, criterios, corpus, denominadores, tres repeticiones de lenguaje, incertidumbre y enmiendas. [Guía externa](../../evaluation/trp/ANNOTATION.md) y plantillas preparadas; no existe anotador confirmado ni evaluación empírica ejecutada.
- Se instaló el Word revisado en `~/Projects/Tesis.docx` y el PDF en `~/Projects/Tesis-fase2.pdf`: **121 páginas**, incluidas dos páginas automáticas de separación. Se actualizan capítulos 4 y 5, viabilidad y calendario; A.16 contiene el protocolo completo. Índice sin duplicados, 25 notas rojas en cursiva y cuatro ilustraciones conservadas. [Hashes y comprobaciones](evidencia/documento-fase2.json).
- Se corrigió un defecto de F1: el texto de R1.4 se había colocado fuera de los párrafos de las celdas y Writer lo descartaba. F2 corrige el escritor y verifica las celdas ya renderizadas. El texto bibliográfico completo se conservó; contar y depurar entradas partidas queda para F7.

| Comprobación F2                   | Resultado                                             | Evidencia                                                 |
| --------------------------------- | ----------------------------------------------------- | --------------------------------------------------------- |
| Suite conjunta nf-core, bio y TRP | 350 aprobadas, 0 fallidas, 32 archivos                | [Log](evidencia/dominio-fase2.log)                        |
| Pruebas específicas del catálogo  | 16 aprobadas, 0 fallidas                              | [Log](evidencia/catalogo-pruebas-fase2.log)               |
| Tipos y lint                      | Tipos sin errores; lint sin errores ni advertencias   | [Registro](evidencia/fase2.json)                          |
| Referencias guardadas             | 2/2 entradas admitidas verificables sin red ni Docker | [Verificación](evidencia/catalogo-verificacion-fase2.log) |

La sustentación se mantiene en julio de 2027 y el borrador completo tiene fecha objetivo 4 de junio. Anotador y clúster siguen pendientes por confirmación expresa del usuario. No se realizaron inferencias de evaluación ni se enviaron encargos a terceros. El cambio previo del SDK queda fuera del commit.

## Fase 1 completada

- Plan de siete fases con hitos, dependencias, criterios de aceptación y calendario propuesto: [PLAN.md](PLAN.md).
- Los tres objetivos y 21 resultados del Word vigente están mapeados contra código, pruebas y brechas: [trazabilidad.json](trazabilidad.json). Ningún indicador experimental completo se declara alcanzado por pasar pruebas de componentes.
- Se reemplazó `~/Projects/Tesis.docx` por la versión revisada y se guardó `~/Projects/Tesis-fase1.pdf`. El documento tiene 110 páginas renderizadas. Se completaron las 15 secciones del Anexo A como plan estimado; se redactó un resumen de 245 palabras y conclusiones de avance; se presentó el estado de los 21 resultados en el capítulo 4.
- Se corrigió el nivel de “Presentación de los resultados esperados”: ahora es el capítulo 4 y las conclusiones son el 5. Se recalcularon el índice y la paginación de preliminares, cuerpo y anexo; se uniformaron los encabezados. Se corrigieron las dos erratas señaladas y se completaron las celdas de R1.4 en la tabla de verificación.
- Se conservaron las cuatro ilustraciones en uso y el texto de la bibliografía. El conteo de 100 entradas comunicado en F1 no se reutiliza: F2 cotejó 99 párrafos bibliográficos y dos notas, con entradas partidas pendientes de depurar en F7. La pasada de LibreOffice descartó una imagen no utilizada y el comentario asociado a material de plantilla retirado; se conservaron las anotaciones vinculadas al texto que permanece. La revisión de contenido de esas referencias se hará en F7.
- Se incorporaron notas con el formato existente: `NOTA PARA EL AUTOR.`, cursiva y rojo. Las estimaciones no se presentan como gastos realizados, y las conclusiones de avance no se presentan como resultados finales.
- Se implementó una comprobación de corpus con Python estándar, independiente del productor TypeScript y sin modelo ni red: [verificador](../../script/tesis/verify_snapshot.py). También verificó correctamente la instantánea histórica de 156 entradas de nf-core conservada en la bitácora; ese corpus no sustituye el de evaluación TRP.

## Comprobaciones realizadas

| Comprobación                        | Resultado                                                                                                                                                       | Evidencia                                           |
| ----------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------- |
| Suite de dominio antes de cambios   | 322 aprobadas, 0 fallidas; 30 archivos                                                                                                                          | [Log](evidencia/dominio-antes.log)                  |
| Pruebas nuevas del verificador      | 12 aprobadas, 0 fallidas                                                                                                                                        | [Log](evidencia/verificador.log)                    |
| Suite de dominio después de cambios | 334 aprobadas, 0 fallidas; 31 archivos                                                                                                                          | [Log](evidencia/dominio-despues.log)                |
| Tipos del paquete                   | `bun typecheck`, salida 0                                                                                                                                       | [Log](evidencia/tipos.log)                          |
| Lint del archivo de prueba nuevo    | 0 errores y 0 advertencias                                                                                                                                      | [Registro](evidencia/fase1.json)                    |
| Word/PDF                            | Sin instrucciones pendientes de la plantilla; 21 resultados y 15 apartados del anexo presentes; índice actualizado; imágenes activas y bibliografía preservadas | [Registro y hashes](evidencia/documento-fase1.json) |

Las pruebas de ingeniería no acreditan los indicadores biológicos o de elicitación. El verificador nuevo cubre **instantáneas de corpus**; la cobertura de todas las ejecuciones se completa en F4. La revisión visual se concentró en portada, resumen, índice, capítulos nuevos y tablas del anexo; la auditoría completa de contenido y presentación de los capítulos 1–3 está planificada en F7.

## Dependencias que siguen abiertas

**Conexión resuelta por confirmación del usuario:** el agente ya está conectado con OpenAI. No es necesario solicitar esa conexión otra vez. F1 no ejecutó llamadas al modelo; la identidad exacta del modelo y su configuración se verificarán al preparar el protocolo.

**Plazo confirmado por el usuario:** sustentación en julio de 2027, con un borrador completo previo. El plan mantiene el 4 de junio como fecha objetivo del borrador y reserva el resto de junio para revisión y correcciones. No se necesita volver a preguntar por el mes de sustentación.

1. Copia auténtica del Tema FCI y denominación oficial del título. La sección se llenó con el alcance y una nota roja de pendiente administrativo; no se fabricó una aprobación institucional.
2. Confirmación de dedicación y presupuesto; programación institucional del día exacto de sustentación dentro de julio de 2027. Las 640 horas y S/23 204,50 siguen siendo supuestos de planificación detallados en el anexo; la confirmación del plazo no confirma esos recursos.
3. Anotador externo para R1.3 y R3.3 y acceso a clúster: el usuario confirmó que ninguno está asegurado y pidió registrarlos como dependencias pendientes. Preparar los instrumentos sin atribuirles participación ni disponibilidad.
4. Instrumentos TRP ejecutables y con condiciones verificadas; datos originales de los fallos publicados; modelo, configuración y límite de costo de la evaluación.

## Siguiente fase: F3, especificación y composición

1. Partir del Word y catálogo de F2. R1.1 sigue parcial: reconstruir los entornos de ReUPred/STRPsearch y conseguir referencias de detección antes de prometer tareas de descubrimiento. Verificar condiciones y marco de la API actual de RepeatsDB. El ensayo GeomeTRe no sustituye esos recursos.
2. Construir el esquema de especificación con procedencia de parámetros y aprobación ligada a su hash. Integrar la resolución del catálogo que verifica sus archivos.
3. Emitir Nextflow, comprobar todo el grafo, los identificadores concretos, formatos, cadenas, numeración y controles exigibles; emitir informe de comprobaciones realizadas y omitidas.
4. Construir el corpus adversarial y los ejemplos de desarrollo. Mantener las familias/intenciones de depuración fuera de la reserva de F6.
5. Completar la guía y asignación externa cuando exista participante, sin atribuir a terceros etiquetas del investigador. El modelo, presupuesto, clúster y congelación de la campaña siguen pendientes donde correspondan.

## Reanudación y archivos

El Word actualizado es el documento editable principal. [fase1-documento.json](fase1-documento.json) conserva el contenido aplicado en esta fase; no es un generador permanente que deba sobreescribir posteriores ediciones. El script de edición exige el hash del documento de entrada original para evitar aplicar los mismos cambios a una revisión distinta. [Las instrucciones de edición y renderizado](../../script/tesis/README.md) documentan ese límite.

El commit del verificador es `267afbd` (`feat(thesis): add independent snapshot verification`). La planificación, el contenido documental y los registros se guardan en el commit de documentación que contiene este archivo. El cambio previo en `packages/sdk/js/src/v2/client.ts` se conserva fuera de ambos commits; su hash antes y después es `99fa8d8e31a4b95c5b7ad2814319f94b8d96a27e22331e78b05d179e232311ba`.
