# Contrastes negativos de registro de decisiones, R3.2

Se ejecutaron cuatro sesiones deterministas mediante las herramientas reales
`trp_prepare` y `trp_run`, el inventario real de esta estación, `Protocol.Service`
y `Question.Service`. Los permisos y la respuesta de aprobación proceden de
callbacks sintéticos autorizados del conductor. No hubo llamadas al modelo,
personas anotando, tareas científicas ni operaciones AWS.

El protocolo fija las causas, tipos, cantidades y orden esperados antes de cada
ejecución. El conductor registra por separado las invocaciones de permisos,
las respuestas de la UI y los resultados de las guardias de protocolo. La
auditoría lee después los eventos y registros del productor. No obtiene las
expectativas del mismo ledger que está comprobando.

| Caso | Resultado observado | Registro comprobado |
|---|---|---|
| Permiso denegado | El análisis no se envía | Solicitud, denegación con causa y terminal automático fallido |
| Aprobación rechazada | La opción «Rechazar» consume la propuesta | Permiso, pregunta/respuesta real de Question.Service y terminal fallido |
| Protocolo rechazado | La restricción comprometida prohíbe GeomeTRe | Rechazo de preparación y negativa fechada del ledger de protocolo |
| Presupuesto insuficiente | Se ofrecen 1 CPU frente a la demanda de 3 | Decisión tipificada, recurso, demanda, disponibilidad y fecha |

La auditoría independiente encontró **13/13 registros exigibles**:
admisión 4/4, protocolo 3/3, permisos 4/4 y aprobación 2/2. Las dos sesiones
que alcanzaron `trp_run` produjeron paquetes automáticos fallidos de 25 archivos,
verificados en frío con el verificador de confianza. Los rechazos anteriores a
la preparación no tienen un ledger de ejecución: se comprobaron sus registros
JSON y, cuando aplica, el ledger de negativas del protocolo. No se fabricaron
eventos de ejecución para esos casos.

La ejecución principal pasó 4 pruebas y 16 aserciones en 3.99 s. El chequeo de
tipos pasó. El primer intento del conductor falló antes de invocar las guardias
porque no exponía el servicio de inventario; está en
`initial-layer-construction-failure/`. El siguiente ejecutó correctamente las
cuatro negativas, pero tres aserciones buscaban el código tipificado dentro de
`Cause.pretty`, que sólo imprime el mensaje. Sus datos y la verificación
independiente de las cuatro guardias se mantienen en
`first-gates-assertion-driver-error/`. El conductor reparado registra y comprueba
`WorkflowError.code`. Son cuatro casos únicos con dos observaciones posteriores
de las guardias, no ocho casos independientes.

## Archivos y verificación

- `protocol.json`: expectativas prospectivas y hashes de diez fuentes directas.
- `source-snapshot.json` y `source-snapshot/`: fuentes conservadas, iguales al
  freeze después de la ejecución.
- `primary/`: acciones externas, estado del conductor y artefactos originales
  de cada sesión, copiados antes de eliminar su instancia temporal.
- `audit.py` y `audit.json`: comparación independiente de orden, tipos, conteos,
  causas, cadena de hashes y paquetes automáticos.
- `driver-terminal.json`: resultados reales de pruebas/tipos y errores previos.
- `completion-review-supplement.json`: supersesión acotada de este pendiente
  técnico; no declara completado el objetivo.
- `cancellation-interpretation-review.json`: nota fuente sobre la cancelación
  real anterior, sin alterar su evidencia ni repetir ciencia.

```sh
python3 evaluation/trp/campaign-20261012/event-negative-contrasts/audit.py \
  --protocol evaluation/trp/campaign-20261012/event-negative-contrasts/protocol.json \
  --cases evaluation/trp/campaign-20261012/event-negative-contrasts/primary \
  --output /tmp/helix-negative-audit.json
```

El harness nuevo es opt-in y omite estos casos en una regresión normal. Una
nueva ejecución necesita una carpeta nueva y un freeze de las fuentes efectivas;
no se sobrescriben los resultados conservados. La prueba no depende de SSH.

## Alcance

Es cobertura adicional de desarrollo de R3.2 sobre estas cuatro fuentes y
sesiones. No valida una sesión humana universal, kappa, intención biológica ni
los próximos experimentos agregados de recursos. Las aprobaciones automáticas
son diferentes de una respuesta real anotada por la asesora.

El campo genérico `running_job_cancellation_demonstrated=false` del auditor
anterior sólo usa las trazas exportadas. La revisión externa de aquella misma
cancelación sí conserva trabajo nativo 128 RUNNING, `Tool.Context.abort`,
CANCELLED con 143:0, cero trabajos propios y controlador terminado. La nota
nueva enlaza ambos documentos, deja intacto el informe original y no interpreta
los tiempos nativos con resolución de segundos como latencia subsegundo.
