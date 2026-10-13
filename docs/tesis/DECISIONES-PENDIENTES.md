# Qué falta para completar la tesis

## Decisiones y dependencias vigentes, 13 de octubre de 2026

El modelo está elegido y probado, dos cuentas AWS Academy ya permitieron ejecutar los clústeres y los 78 originales principales de Pratt están recuperados. La matriz agregada de recursos terminó; no hay que pedir más cuentas para completar sus casos. Los capítulos 1 a 3 permanecen cerrados. [Evidencia final](RESULTADOS-AWS-20261012.md).

| Pendiente vigente | Qué se requiere | Cómo completarlo |
| --- | --- | --- |
| Referencia humana, R1.3 y R1.5 | Factibilidad definitiva, flujo esperado, campos de referencia y dos paráfrasis humanas por intención factible | La asesora completa el material real de 70 solicitudes; conservar sus primeras respuestas y congelar reserva/particiones antes de ejecutar el modelo |
| Turnos e intervenciones, R3.3 | Conversaciones reales y juicios independientes sin adjudicación previa | Capturar las sesiones pertinentes y entregar los turnos a la experta; calcular cobertura y kappa con esas etiquetas. Los callbacks sintéticos no sirven como anotación humana |
| Criterio físico, R3.8 | Definición externa, clasificador validado y controles físicos pertinentes | Usar Pratt y los observables como datos, sin convertir toda predicción en fallo ni toda estructura experimental en negativo físico certificado |

**Integración técnica ya verificada:** producción `9ada336`, helper `0dcb38a`, regresión 543/63/0 y tipos correctos. [integración final](../../evaluation/trp/campaign-20261012/checks/post-campaign-production-20261013/cloud/summary.json) con 89 controles, cuatro tareas y CSV correctos en el positivo de 152 archivos; trabajo propio 384 CANCELLED 0:9 y paquete automático de fallo de 151 archivos. Los dos usan el verificador por defecto sin legacy. No añade casos a las cohortes ni sustituye las referencias humanas.

**Recursos, resultado ya obtenido:** originales 40 con 18 factibles, 18 inviables y cuatro desconocidos; frontera seis factibles y tres falsos rechazos, 50 %, que incumple 5 %; suplemento posterior con dos factibles y dos inviables. Sólo la unión de 44 alcanza veinte por clase y mantiene cuatro desconocidos. No se precisa otra cuenta para observar esos resultados; tampoco corresponde sustituirlos por más casos hasta que el porcentaje parezca favorable. Las rutas del dominio que no usan el perfil estricto conservan sus límites.

**Qué debe aportar el autor:** las referencias y paráfrasis de la experta, y después sus etiquetas de turnos reales; coordinación de una referencia física válida cuando se defina el clasificador. La documentación inicial es responsabilidad del autor y queda fuera de los pendientes del agente. El modelo/API y AWS no se registran como nuevas dependencias para las tareas técnicas actuales.

Las respuestas frescas de EC2 DescribeInstances confirman las tres instancias propias de Lab1 detenidas a las 17:06:16 UTC y las tres de Lab2 a las 17:50:26 UTC. En Lab2, la parada siguió a la recuperación de la integración y la comprobación de quiescencia de las 17:43:06 UTC. Los volúmenes permanecen; la parada de cómputo no significa coste de almacenamiento cero ni factura final. Los USD 48,6 restantes de Lab2 fueron un reporte del portal, con demora de facturación. [Lab1](../../evaluation/trp/campaign-20261012/cloud/lab1/final-stopped-post-corrections-20261013.json), [Lab2](../../evaluation/trp/campaign-20261012/cloud/lab2/final-stopped-post-corrections-20261013.json).

El OAuth existente funciona. No se atribuye su estimación tarifaria a una factura efectiva ni se afirma un tope duro de 8192 tokens. Tampoco hay P95 de latencia medido. Son límites explícitos, no solicitudes de otra cuenta. Sustentación julio de 2027 y borrador objetivo 4 de junio de 2027 se mantienen.

**Nota de supersesión:** los escenarios siguientes son históricos. Se conservan sus fechas, métricas y decisiones; no representan el estado operativo actual ni acreditan R1.5 científico, kappa o sensibilidad/especificidad física.


Word y PDF instalados el 13 de octubre a las 18:02 UTC: **155 páginas, 261 comprobaciones de render y diez notas rojas nuevas**. Los capítulos 1 a 3, bibliografía, imágenes originales y 21 IDs se conservaron. La revisión visual aceptó el candidato; los hashes instalados y el backup exacto del archivo del autor se verificaron. [Instalación y hashes](../../evaluation/trp/campaign-20261012/document/installation.json). La tesis sigue incompleta en sus validaciones científicas obligatorias.

## Registro histórico conservado hasta el 1 de octubre de 2026

## Actualización de originales Pratt, 1 de octubre de 2026

Se recuperaron del envío de los autores 78 modelos AF2 de rango 1, sus puntuaciones y sus PAE, correspondientes a toda la Tabla S1. Helix incorporó el contrato local ColabFold y ejecutó dos perfiles fijados antes de sus veredictos. El principal produce 78/78 alarmas mecánicas y marca los cinco ejemplos explícitamente problemáticos de las figuras 3, 6 y 7; esto no valida discriminación ni plausibilidad física. El control físico sigue no evaluable, con cobertura 0%, sensibilidad física y especificidad sin calcular. Faltan un control físico validado y al menos 30 negativos pertinentes revisados. Los originales de la Tabla S1 dejan de ser dependencia pendiente; los de las figuras 1/S1 y 14 no están en este envío. No se usó el modelo ni AWS. [Informe y evidencia](../../evaluation/trp/reference/pratt-author-20261001/README.md).

Identificadores actualizados al 23/09/2026: tres objetivos y 21 resultados. Las evidencias fechadas conservan su numeración original; consulte [equivalencias](renumeracion-20260923/README.md).

Estado histórico: 21 de septiembre de 2026, supersedido por la actualización del 12 de octubre de 2026. Sustentación: julio de 2027; borrador objetivo: 4 de junio de 2027. Problemática, marco conceptual y estado del arte cerrados por el autor.

## Trabajo técnico pendiente tras CT1–CT5

| Pendiente | Qué se requiere | Opciones |
| --- | --- | --- |
| Ruta predicha y gobernanza conjunta | La herramienta del agente ya integra preparación, aprobación y evidencia; falta incorporar la cuota dura y el flujo común de admisión | Reutilizar la asignación estricta XFS/cgroup y conservar rechazos explícitos |
| ReUPred y RepeatsDB | Entorno ejecutable compatible del primero; contrato inequívoco de loci/API del segundo | Resolver contratos o excluir esas rutas del alcance evaluado con justificación previa |
| Gobernanza de nuevas rutas | Integrar detector y ruta predicha al control estricto de almacenamiento cuando se afirme esa garantía | Reutilizar el entorno XFS/cgroup validado; mientras tanto documentar límites de las rutas independientes |
| Corpus reservado de F6 | Casos, particiones, referencias independientes y revisión antes de congelar | Completar cada campaña por separado con el verificador; no reutilizar casos de desarrollo como reserva |

SIFTS/UniProt ya está integrado y STRPsearch está admitido: dejaron de ser bloqueos generales. La ruta predicha ya funciona desde una herramienta del agente; la gobernanza estricta conjunta sigue pendiente. [Plan y evidencia](PLAN-CIERRE-TECNICO.md).

## Dependencias y decisiones externas

| Dependencia | Qué se necesita | Opciones y efecto |
| --- | --- | --- |
| Anotador independiente | Persona con competencia en el dominio, disponibilidad, guía y etiquetas iniciales ciegas; referencia de admisibilidad/equivalencia y al menos 100 turnos para acuerdo. | Colaborador/asesora que pueda asumir el papel independiente, o anotador remunerado. Registrar experiencia y adjudicación separada. Otro modelo no sustituye esta referencia humana. |
| Archivos de Pratt | Coordenadas originales, PAE cuando proceda y etiquetas justificadas. El suplemento recuperado contiene 78 filas de metadatos, no los modelos. | Buscar otro depósito público; solicitar originales a los autores con autorización expresa para contactar; o aprobar un benchmark recuperable equivalente y documentar la enmienda antes de medir. Regenerar predicciones no reproduce los archivos publicados. |
| Modelo y gasto de evaluación | Identificador exacto del modelo, parámetros, límites de tokens/llamadas y tope monetario. La preferencia del autor es minimizar el coste; el nombre comunicado no se ha validado como identificador de API. | Piloto con un tope elegido por el autor para medir coste real; después fijar presupuesto de campaña. O fijar directamente un presupuesto total y detenerse al alcanzarlo, informando los casos no ejecutados. No se iniciaron llamadas pagadas para R2.2. |
| Infraestructura de clúster | Cuenta, planificador/ejecutor, cuota y ventana de acceso si se mantiene esa afirmación. | Conseguir clúster institucional; presupuestar uno en nube; o enmendar prospectivamente la afirmación a ejecución local en dos equipos. Una VM o SSH por sí solos no validan un clúster. |
| Requisitos administrativos | Documento auténtico de aprobación FCI, título oficial y fecha institucional cuando corresponda. | Incorporar los documentos aprobados; mantener las notas rojas mientras estén pendientes. No inventar aprobaciones. |

La batería prevista incluye 50 intenciones factibles y dos paráfrasis por
intención, tres repeticiones (450 solicitudes de ese bloque), casos fuera de
alcance, 50 grafos válidos, 30 inválidos, 40 contrastes de recursos y conjuntos
estructurales con referencias independientes. Los fallos y no evaluables se
conservan en los denominadores conforme al protocolo F2.

## Documento y entrada a F6

El documento ya contiene resultados de esta entrega y el anexo A.22. Para el cierre
faltan resultados reservados, sus intervalos y denominadores; discusión de los
límites observados, conclusiones ajustadas a esos resultados, comprobación final del template/anexos. Las notas de autor deben retirarse o
resolverse con evidencia, no convertir metas en resultados.

Se puede preparar el corpus, la guía de anotación y los comprobadores de F6.
La medición dependiente no empieza hasta congelar la implementación aplicable,
referencias, particiones, modelo y presupuesto. No es necesario que una
dependencia detenga tareas independientes, pero tampoco se declara satisfecha
la compuerta completa de F5 mientras falten los contratos del dominio.

**Continuidad propuesta:** unificar la gobernanza de la ruta predicha, resolver los contratos restantes y completar el corpus reservado con revisión independiente; decidir modelo/gasto antes de un piloto pagado. La
nube queda como alternativa de infraestructura, no como requisito de R2.2.
