# Qué falta para completar la tesis

## Actualización de originales Pratt, 1 de octubre de 2026

Se recuperaron del envío de los autores 78 modelos AF2 de rango 1, sus puntuaciones y sus PAE, correspondientes a toda la Tabla S1. Helix incorporó el contrato local ColabFold y ejecutó dos perfiles fijados antes de sus veredictos. El principal produce 78/78 alarmas mecánicas y marca los cinco ejemplos explícitamente problemáticos de las figuras 3, 6 y 7; esto no valida discriminación ni plausibilidad física. El control físico sigue no evaluable, con cobertura 0%, sensibilidad física y especificidad sin calcular. Faltan un control físico validado y al menos 30 negativos pertinentes revisados. Los originales de la Tabla S1 dejan de ser dependencia pendiente; los de las figuras 1/S1 y 14 no están en este envío. No se usó el modelo ni AWS. [Informe y evidencia](../../evaluation/trp/reference/pratt-author-20261001/README.md).

Identificadores actualizados al 23/09/2026: tres objetivos y 21 resultados. Las evidencias fechadas conservan su numeración original; consulte [equivalencias](renumeracion-20260923/README.md).

Estado vigente: 21 de septiembre de 2026. Sustentación: julio de 2027; borrador objetivo: 4 de junio de 2027. Problemática, marco conceptual y estado del arte cerrados por el autor.

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
