# Corpus de solicitudes para revisión experta

Preparación del 30/09/2026. Estado: **entregado como material, pendiente de referencia humana y congelación**. No se ejecutó inferencia del agente sobre estos casos.

## Qué contiene

- 70 solicitudes mezcladas: 50 propuestas de planes factibles y 20 peticiones fuera de alcance o científicamente inválidas. La categoría prevista es metadato de diseño, no etiqueta humana.
- 50 accesiones distintas: 10 estructuras PDB para detección, 15 modelos AFDB para detección y 25 modelos AFDB para geometría condicional. Se suministran tres intervalos Repeat de UniProt por tarea geométrica, con su evidencia original. No son verdad estructural independiente.
- 50 componentes de familia Pfam en la selección, sin intersección con Pfam de Q9MCI8 (2xqh), P19148 (1a0c) ni P69905 (piloto de hemoglobina). `assignments.json` reserva también los miembros no seleccionados de esas familias. No usarlos después para ajustar el agente.
- Todos los casos con datos son humanos. La consulta devolvió una primera página de 500 entradas revisadas, de longitud 150–600, con anotación Repeat; no es un censo ni un muestreo representativo de todos los organismos o clases estructurales. Esta limitación se declara en el Excel.

## Selección e integridad

`selection-plan.json` conserva consulta, universo de esa página, requisitos y orden. La selección agrupa por componentes conectados de Pfam y recorre grupos en orden hash; se exige identificación de familia conocida. La disponibilidad de fuente y las restricciones de entrada deciden las exclusiones técnicas antes de inferencia. `pdb-preflight-selection.json` conserva los primeros diez PDB aceptados y las exclusiones del sondeo preliminar. No se repiten descargas fallidas para alterar su orden. `retrieval-attempts.json` corresponde a la obtención final.

Las restricciones estrictas del adaptador experimental excluyen modelos múltiples, residuos no canónicos, conformaciones alternativas, inserciones de autor y discontinuidades. Se ejecutó únicamente la comprobación de entrada `prepare_inner`, sin STRPsearch, sin GeomeTRe y sin un modelo de lenguaje. En AFDB se comprobó longitud y secuencia completa contra UniProt, cobertura CA 1..L, cadena única y dimensiones PAE L×L. Los umbrales pLDDT/PAE **no se usaron para escoger modelos que diesen un resultado favorable**. Una negativa por no cumplirlos puede ser correcta para el plan condicional.

Los originales entregados y sus SHA-256 están en `docs/tesis/evaluacion-experta-20260930/para-asesora/datos/fuentes.json`. UniProt y RCSB JSON por caso se extraen y serializan de las respuestas públicas; la página original del inventario y las exclusiones de desarrollo se archivan en `sources/`. El resto de `sources/` es caché local ignorada por Git; los archivos seleccionados sí quedan en el paquete entregable.

No se afirma que el detector desconozca estas proteínas: su base incorporada podría contenerlas. Esta entrega mide interpretación de solicitudes y no sensibilidad biológica ni generalización fuera de su base. Tampoco reemplaza T-GRAPH, T-RESOURCE, T-STRUCT o los turnos reales de T-TURNS.

## Trabajo de la experta y siguiente etapa

1. Revisar o corregir cada solicitud antes de ejecución; establecer su referencia sin observar respuestas de Helix.
2. Redactar dos paráfrasis humanas para cada intención factible, revisar equivalencia y registrar dudas. Las propuestas originales son asistidas por IA; las paráfrasis y etiquetas todavía están vacías.
3. Devolver el Excel, incluso por bloques. Conservar la primera entrega con fecha y hash. Resolver elegibilidad y fuentes antes de congelar. Si no quedan 50 intenciones factibles, completar nuevos casos antes de la inferencia reservada; no relabelar negativos para cumplir un cupo.
4. Generar `cases.jsonl` definitivo únicamente desde textos revisados. Las solicitudes de ejecución no deben incluir referencias esperadas ni etiquetas de la experta.
5. Confirmar configuración efectiva y límites de llamadas/tokens usando solo desarrollo. `decisions.json` registra modelo y presupuesto autorizados, no una verificación remota.
6. Congelar solicitudes, paráfrasis, referencias, datos, catálogo, código y entorno; luego hacer las tres repeticiones. Las correcciones posteriores se versionan y no se ocultan.
7. Recoger conversaciones reales con un operador humano. Seleccionar sesiones completas antes de la clasificación automática y entregar al menos 100 turnos con contexto, sin etiquetas del sistema. La asesora anotará sus clases en una segunda entrega. No hay conversaciones sintéticas en este paquete.

## Reproducción de la preparación

Instalar las dependencias de `requirements.txt` en un entorno aislado y ejecutar desde la raíz:

```sh
python script/tesis/download_expert_corpus.py
python script/tesis/build_expert_corpus_workbook.py
```

Conservar los datos archivados para no cambiar de versión de fuentes. El generador del Excel se niega a sobrescribir respuestas humanas existentes. El ZIP contiene solo Excel y datos seleccionados. Ningún script llama a OpenAI ni inicia servicios AWS.

`validation.json` registra conteos e integridad; la revisión visual se realizó abriendo el Excel con LibreOffice y revisando la exportación. Los 70 casos están completos en la representación y todos los campos de respuesta permanecen vacíos.
