# Equivalencias de identificadores — 23 de septiembre de 2026

Fuente: tablas de la sección 1.2.4 del Word actualizado. Se conservan los 21 compromisos y sus criterios; cambia la agrupación a tres objetivos.

| Anterior | Vigente | Resultado |
|---|---|---|
| R1.1 | R1.1 | Catálogo declarativo del dominio |
| R1.2 | R1.2 | Módulo de elicitación |
| R1.3 | R1.3 | Corpus de enunciados con patrón de referencia externo |
| R2.1 | R1.4 | Protocolo de evaluación |
| R2.2 | R1.5 | Motor de composición |
| R2.3 | R1.6 | Recurso de correspondencia entre identificadores y numeración de residuos |
| R2.4 | R1.7 | Validador estático y recorrido sin datos |
| R2.5 | R1.8 | Informe de validación |
| R2.6 | R1.9 | Corpus de composiciones inválidas y tasa de aceptación indebida |
| R3.1 | R2.1 | Declaración de los recursos disponibles del entorno |
| R3.2 | R2.2 | Contador de demanda |
| R3.3 | R2.3 | Rechazo tipificado |
| R3.4 | R2.4 | Medición del acierto del rechazo |
| R4.1 | R3.1 | Manifiesto verificable en frío |
| R4.2 | R3.2 | Registro de decisiones y rechazos |
| R4.3 | R3.3 | Conteo de intervenciones humanas |
| R4.4 | R3.4 | Documentación de métodos con versiones fijadas |
| R5.1 | R3.5 | Catálogo de modos de fallo |
| R5.2 | R3.6 | Batería de controles |
| R5.3 | R3.7 | Artefacto de controles legible por máquina |
| R5.4 | R3.8 | Sensibilidad y especificidad |

Causas: C1/C2 anteriores → C1; C3/C4 → C2; C5/C6 → C3. Objetivos: OE1/OE2 anteriores → OE1; OE3 → OE2; OE4/OE5 → OE3.

## Archivos históricos

Las referencias de ejecución, hashes, catálogos ligados a ejecuciones, informes fechados, borradores F6, `fase*-documento.json`, `r32-documento.json` y generadores/auditores de versiones anteriores del Word conservan la numeración anterior. Sus rutas también se conservan (por ejemplo `R3.2-RECURSOS.md`, cuyo contenido vigente trata R2.2). No aplicar sustituciones a sus bytes: usar esta equivalencia al interpretarlos. Los informes de ejecución emitidos por versiones anteriores pueden mencionar R5.4; equivale a R3.8.

La nota `agrupacion-20260923/CAMBIOS.md` registra una etapa editorial anterior que conservaba R1–R5; esta renumeración la sucede.

## Inconsistencias internas del Word fuente

Las tablas 1.2.4 ya tienen los códigos nuevos. Los métodos, tabla de métodos, capítulos posteriores e índice todavía contienen códigos anteriores, y algunos párrafos conservan referencias a causas C4–C6 y objetivos 4–5. Este trabajo propaga los códigos al repositorio y no sobrescribe el Word actualizado por el autor. Los párrafos «Resultado 1», etc., reinician numeración por bloque; las tablas 1.2.4 resuelven su identidad inequívoca.

## Verificación

`python3 script/tesis/audit_thesis_traceability.py --markdown docs/tesis/trazabilidad.md` comprueba los 21 códigos, objetivos, enlaces y correspondencia editorial del protocolo. La equivalencia es fechada: R3.2 sin versión resulta ambiguo (antes contador de demanda; ahora registro de decisiones).
