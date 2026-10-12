# Coordinación de la reunión y decisión de infraestructura

## Estado al 28/09/2026

El tesista identifica a su asesora, bioinformática con contactos de investigadores, como posible participante o coordinadora. No hay aceptación, fechas ni etiquetas recibidas todavía. Modelo/presupuesto y decisión sobre Pratt siguen pendientes por decisión explícita del autor. No se enviaron mensajes a terceros ni se crearon recursos AWS.

## Agenda propuesta (30 minutos, ajustable)

- 0–5: explicar el problema y los dos juicios humanos que se necesitan.
- 5–12: revisar una solicitud y un turno; escuchar qué información necesita para decidir.
- 12–20: revisar independencia, disponibilidad y posible especialista referido.
- 20–27: acordar piloto y fecha; revisar volumen reservado y cómo estimar esfuerzo.
- 27–30: registrar acuerdos. No dar por confirmados anotador ni horas en ausencia de aceptación.

Separar los papeles: revisar guía, elaborar referencia, juzgar salidas y adjudicar. Si la misma persona cumple varios, registrar qué vio y en qué orden. Para piloto usar el paquete para-asesora. Para la reserva preparar paquetes nuevos y cegados; no reutilizar 2xqh, P69905 ni sus familias. Una asesora puede aportar evaluación humana, pero la relación académica debe declararse y su participación en diseño puede limitar la independencia. Un especialista referido ajeno al desarrollo es la opción preferible.

## Entrega posterior que debe preparar el coordinador

1. Catálogo/operaciones y condiciones congelados, insumos y datos suficientes para cada caso, trazabilidad de familias.
2. 50 intenciones factibles, sus 100 paráfrasis revisadas y 20 negativos; referencia humana preparada antes de producir/ver salidas del agente.
3. Ejecutar solo tras confirmar modelo, presupuesto, corpus y guía. Cegar modelo, variante y salidas/etiquetas ajenas. Los IDs internos retienen la correspondencia entre original, paráfrasis y réplica.
4. T-TURNS: seleccionar sesiones completas antes de ejecutar clasificador; entregar al menos 100 turnos elegibles con contexto y sin predicciones. No seleccionar por palabras/clase que favorezcan la métrica.
5. Primera entrega externa inmutable; preservar fecha y hash. Adjudicación posterior en otro archivo. No sustituir el kappa de primeras etiquetas por consenso.
6. Juicios/Equivalencia contienen solo cabeceras hasta que existan salidas asignadas; eso es deliberado. Campos anotados del piloto están vacíos. No calcular métricas a partir de plantillas.

## AWS: sí permite cumplir el alcance, con implementación y medición

El Word exige ejecución “en entorno local y en agrupación de cómputo”; no exige que el clúster sea propiedad de la universidad. Una cuenta AWS permite aprovisionar infraestructura adecuada. Tener cuenta o una VM EC2 por SSH no constituye por sí mismo evidencia de ejecución en clúster.

**Opción más directa para conservar la afirmación literal:** AWS ParallelCluster con Slurm. Propuesta de ensayo: nodo de cabecera y hasta dos nodos de cómputo, cola y límites definidos, Nextflow enviando trabajos mediante Slurm, runtime de contenedores compatible y almacenamiento accesible a los trabajadores. Esa topología es una propuesta de validación, no un requisito numérico ya fijado por la tesis.

**Alternativa:** Nextflow con AWS Batch, cola y entorno de cómputo administrado, imágenes accesibles y S3. Es evidencia de ejecución por lotes distribuida en nube; acordar con la asesora si esa arquitectura satisface lo que se entiende por “agrupación de cómputo” en el documento y describirla así. No equiparar todas las arquitecturas sin registrar la decisión.

**Trabajo mío todavía necesario:** la ruta TRP en packages/helix/src/trp/nextflow.ts fija process.executor = 'local' (línea 164 al revisar). Sus verificaciones de Docker local y cuotas no se trasladan automáticamente a AWS. Debo implementar un adaptador/configuración revisada, disponibilidad de imágenes por digest, transferencia de datos, identidad y correspondencias, admisión de recursos, proveniencia y errores/cancelación; luego contrastar productos con la referencia local. El soporte de Nextflow no equivale a soporte ya verificado de Helix.

**Qué habría que aportar después:** cuenta con facturación o créditos habilitados, acceso delegado con permisos adecuados (SSO/rol), región y cuotas de cómputo disponibles, presupuesto de infraestructura y autorización para consumirlo. Un presupuesto de nube es distinto del presupuesto API de modelos. No hacen falta credenciales ahora y no se solicita la cuenta raíz.

**Qué medir para sostener la afirmación:** envío real a la cola, IDs y estados del planificador, asignación a nodos, límites y consumo observado, ejecución de una tarea del alcance con insumos fijados, comparación de producto local/remoto, fallos/cancelación, manifiesto portable y coste/recursos eliminados al terminar. No se exige una mejora de velocidad si no forma parte del indicador.

No se promete coste fijo ni apagado instantáneo por una alerta de gasto. Se presupuestarán por separado cómputo, discos, almacenamiento y red; se establecerá tamaño máximo y duración de la prueba y se comprobará eliminación de recursos. No se aprovisionó nada en esta entrega.

Fuentes oficiales consultadas el 28/09/2026:
- AWS ParallelCluster y planificadores: https://docs.aws.amazon.com/parallelcluster/latest/ug/
- Requisitos de cuenta/permisos/región: https://docs.aws.amazon.com/parallelcluster/latest/ug/install-v3-configuring.html
- Nextflow y AWS Batch (cola, entorno, S3 e imágenes): https://docs.seqera.io/nextflow/aws
- Ejecutores de Nextflow: https://docs.seqera.io/nextflow/executor

## Actualización del 12/10/2026: infraestructura preparada

Se obtuvo acceso a dos Learner Labs con presupuesto de US$50 por entorno. En el primero se desplegaron un controlador y dos trabajadores EC2 con Slurm, Docker y NFS. Se verificaron ejecución en ambos nodos, renovación de la sesión de cuatro horas, apagado/reanudación, persistencia, cancelación y límites efectivos de contenedores. Se dejó el cómputo detenido; los discos se conservan y mantienen coste de almacenamiento.

El flujo fijo de GeomeTRe produjo resultados idénticos a la referencia local al fijar el perfil numérico de OpenBLAS. La primera ejecución con selección automática del perfil numérico presentó una discrepancia que se conserva en la evidencia. El informe está en `evaluation/trp/aws-academy-cluster-20261012/README.md` y `report.json`.

Queda pendiente implementar y validar la integración de Helix con Slurm y ejecutar la campaña prevista. Esta prueba de infraestructura y de un caso fijo no marca como completa la evaluación del resultado esperado de ejecución local y en agrupación de cómputo.
