# Plan de cierre técnico y evaluación

## Actualización de originales Pratt, 1 de octubre de 2026

Se recuperaron del envío de los autores 78 modelos AF2 de rango 1, sus puntuaciones y sus PAE, correspondientes a toda la Tabla S1. Helix incorporó el contrato local ColabFold y ejecutó dos perfiles fijados antes de sus veredictos. El principal produce 78/78 alarmas mecánicas y marca los cinco ejemplos explícitamente problemáticos de las figuras 3, 6 y 7; esto no valida discriminación ni plausibilidad física. El control físico sigue no evaluable, con cobertura 0%, sensibilidad física y especificidad sin calcular. Faltan un control físico validado y al menos 30 negativos pertinentes revisados. Los originales de la Tabla S1 dejan de ser dependencia pendiente; los de las figuras 1/S1 y 14 no están en este envío. No se usó el modelo ni AWS. [Informe y evidencia](../../evaluation/trp/reference/pratt-author-20261001/README.md).

Identificadores actualizados al 23/09/2026: tres objetivos y 21 resultados. Las evidencias fechadas conservan su numeración original; consulte [equivalencias](renumeracion-20260923/README.md).

Fecha de inicio: 21 de septiembre de 2026. Continuación del plan F1–F7,
sin modificar los 21 resultados ni los umbrales fijados en F2.

El autor da por cerrados problemática, marco conceptual y estado del arte.
El trabajo documental se concentra en resultados, conclusiones de avance,
anexos y trazabilidad de la evidencia. No se reabre el corpus bibliográfico.

| Hito | Resultados | Trabajo y archivos | Criterio de cierre |
|---|---|---|---|
| CT1. Correspondencias integradas | R1.6, R1.7, R3.6 | Incorporar el adaptador a `src/trp/` y a preparación; conservar entradas, conversiones, hashes y aprobación; verificar SIFTS por residuo | Referencia real, rechazos por ambigüedad y alteración, ruta antigua conservada, copia portable verificable |
| CT2. Detector ejecutable | R1.1, R1.5 | Fijar entorno STRPsearch, preparación de entrada y contrato de salida; capturar fallos científicos aunque la CLI devuelva cero | Una referencia real y casos negativos; límites explícitos de licencia, datos y marcos; admisión solo con evidencia completa |
| CT3. Modelos predichos | R1.6, R3.6–R3.7 | Verificar identidad, productor, cadena, pLDDT y PAE; transportar geometría sin presentar confianza como B-factor experimental | Ejecución delimitada y trazable, rechazo de datos incompatibles; distinguir geometría de validez física |
| CT4. Preparación de F6 | R1.3, R1.9, R2.4, R3.3, R3.8 | Verificador de congelación y dependencias; localizar originales estructurales públicos; preparar medición sin inventar etiquetas externas | Informe computable de qué campaña puede comenzar, denominadores y valores ausentes explícitos |
| CT5. Integración y resultados | Los 21 | Regresión pertinente, ejecuciones científicas, verificación independiente; `trazabilidad.json`, `checkpoint.json`, Word y anexos | Cada afirmación nueva enlaza evidencia; ninguna prueba de desarrollo se presenta como evaluación reservada |

## Dependencias y ejecución paralela

CT1 y CT2 pueden implementarse en paralelo; CT3 se integra después de disponer
de contratos inequívocos y se coordina con CT1. CT4 puede avanzar desde el
protocolo vigente. CT5 depende de los cambios efectivamente verificados.

Un agente trabaja en correspondencias e integración; otro en detectores y sus
referencias; otro en preparación de evaluación y recuperación de datos. El
agente principal integra, revisa, ejecuta la regresión y actualiza el documento.
Se asignan archivos distintos para evitar sobrescrituras. Los commits se crean
tras revisar las contribuciones, con título en inglés y sin coautor.

## Decisiones externas y límites de la campaña

- Anotador independiente: necesario para referencia humana y acuerdo. Se puede
  preparar guía/corpus; no atribuir etiquetas independientes al investigador o LLM.
- Modelo y presupuesto: conexión OpenAI confirmada; identificador y tope de
  gasto de la campaña pendientes. El trabajo técnico no requiere llamadas pagadas.
- Originales de Pratt: buscar depósitos públicos; no enviar mensajes a autores.
  Ausencia de archivos es dato faltante, no acierto ni error del detector.
- Clúster: la segunda PC está autorizada como estación adicional. No equivale
  a un clúster con planificador. Se conserva esta dependencia donde aplique.
- Sustentación: julio de 2027; borrador completo objetivo 4 de junio de 2027.

## Validación

Pruebas unitarias adversariales de contratos, integración de preparación y
aprobación, ejecución real de herramientas con límites, regresión TRP/bio/nfcore,
y verificador Python de la copia de evidencia. Preservar casos fallidos.
La documentación distingue implementación, evidencia de desarrollo y campaña
reservada. El Word se edita desde su versión actual y se compara para conservar
el contenido de los capítulos que el autor cerró.

## Estado de ejecución

- CT1 completado en el alcance definido: integración y referencia SIFTS real, 206 residuos/12 unidades y verificación portable.
- CT2 completado para STRPsearch: guardia, herramienta interactiva, pruebas negativas y referencias reales; ReUPred y RepeatsDB siguen fuera del catálogo admitido.
- CT3 completado como CLI de desarrollo verificable; integración al agente completada mediante `trp_predicted_geometry` el 23/09/2026; gobernanza estricta conjunta pendiente. Los segmentos artificiales no son anotaciones de repeticiones.
- CT4 completado como preparación: verificador y siete artefactos con hashes. Congelación y evaluación reservada pendientes; originales Pratt no recuperados.
- CT5 completado para esta entrega: regresión 500 pruebas, 78 Python, tipos, trazabilidad de 21 resultados y actualización de Word/anexo A.22.

El cierre de estos hitos delimitados no declara completadas la tesis ni la cobertura total de F5. Próximo trabajo técnico: unificar la gobernanza estricta de recursos en las rutas nuevas y resolver contratos restantes del dominio; después congelar cada campaña con sus referencias y dependencias.
