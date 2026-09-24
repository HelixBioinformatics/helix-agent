# Continuación de verificaciones de Helix — 23 de septiembre de 2026

Se continúa CT3–CT5 del plan vigente. El producto se llama **Helix Agent** y su comando es `helix`. Se conservan rutas históricas de evidencia e identificadores internos cuando cambiarlos alteraría contratos o hashes. Numeración de tesis: tres causas, tres objetivos, 21 resultados.

## Secuencia y criterios de cierre

1. **Despliegue en segunda estación:** identificar binario publicado, versión y SHA; verificar entorno con PATH explícito, idempotencia del instalador, rechazo de evidencia alterada y geometría real idéntica. Cero llamadas al modelo.
2. **Actualización explícita:** incorporar y probar `helix upgrade` sin desinstalación y evitando gestores que distribuyen un homónimo. No publicar release durante esta entrega; distinguir fuente modificada de binario publicado.
3. **CT3:** integrar al agente la ruta de geometría AFDB con fuentes, PAE, confianza, propuesta ligada a hash y aprobación. Verificar referencia y rechazos; no presentar los segmentos artificiales de desarrollo como anotación biológica.
4. **Integración y documento:** pruebas pertinentes, evidencias fechadas, branding y resultados de desarrollo en Word/anexo. Conservar indicadores y corpus reservado de F6.

## Límites

La conexión SSH es una segunda estación, no un clúster. Los contrastes de despliegue no miden comprensión del lenguaje ni exactitud biológica. Las pruebas de detección/geometría independientes no heredan cuotas duras XFS si no se ejecutan bajo esa asignación. Anotador, corpus independiente, originales estructurales y modelo/presupuesto siguen pendientes para las campañas que los requieran.

## Evidencias

Los registros se conservan en `evaluation/trp/verification-20260923/`. Los agentes trabajan sobre actualización CLI y ruta AFDB; el coordinador ejecuta la verificación remota y actualiza el documento. Las credenciales no forman parte de los registros.

## Resultado de esta entrega

Segunda estación: nueve comprobaciones con desenlaces esperados, incluyendo dos rechazos de archivos alterados. Referencia científica idéntica de 12 unidades y verificación de paquete portable de 139 archivos. La instalación existente es Helix 0.3.0; la repetición del instalador no cambió su binario.

Ruta AFDB integrada mediante `trp_predicted_geometry`: aprobación por el servicio de preguntas, tres segmentos suministrados/21 residuos, CSV idéntico y verificador portable. Se verificó la ejecución real del agente con respuesta sintética de prueba. No se convierte en anotación biológica.

Pruebas: 471 de dominio y 48 de herramientas/actualización, 78 Python, ayuda/snapshot y tipos correctos; referencias reales Nextflow y AFDB ejecutadas aparte. Tres pruebas dependientes de entorno se omiten por defecto en los grupos ordinarios. Se conservan los fallos iniciales del hash de catálogo obsoleto y su corrección en el caso activo de desarrollo.

`helix upgrade` implementado y consulta real `--check` satisfactoria desde fuente; publicación pendiente. Siguiente hito técnico: unificar la gobernanza estricta de recursos de las rutas dedicadas y cerrar contratos restantes de ReUPred/RepeatsDB; las dependencias de evaluación reservada permanecen explícitas.
