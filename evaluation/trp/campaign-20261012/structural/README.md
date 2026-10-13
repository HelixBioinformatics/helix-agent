# Diagnóstico físico exploratorio de Helix, 12/10/2026

Se añadió una medida física ejecutable a la inspección de Helix: el recuento de choques atómicos graves y su normalización por 1000 átomos mediante CCTBX Reduce2/Probe2. La integración es opcional, se configura por el operador y conserva el veredicto general de plausibilidad del pliegue como **no evaluable**. Una medida de choques no demuestra por sí sola que un pliegue sea plausible o implausible.

La extensión se fijó en [protocol.json](protocol.json) antes de medir los choques. Conserva los 78 originales AF2 de Pratt sin modificarlos y añade 30 cadenas experimentales de beta-solenoides con anotación revisada de RepeatsDB. Es una fase de desarrollo y exploración; no se presenta como evaluación reservada de un clasificador.

## Método y referencias independientes

Se usa CCTBX 2025.11, con incorporación de hidrógenos, `keep_hydrogens=False`, `do_flips=False`, `nuclear=False`, sin filtro por columna B y sin relajación de las coordenadas originales. El método considera graves los solapamientos desfavorables de al menos 0,4 Å y calcula el clashscore como su número por 1000 átomos. Es el criterio atómico de [MolProbity, Williams et al. (2018)](https://doi.org/10.1002/pro.3330), aplicado mediante la [implementación oficial de CCTBX](https://github.com/cctbx/cctbx_project/blob/master/mmtbx/programs/clashscore2.py). **No se fijó ni se ajustó un umbral de decisión para el modelo completo.**

La [API oficial de RepeatsDB](https://repeatsdb.org/api/) se consultó por fuente PDB y clase 3.1, beta-solenoides. Se inspeccionaron 121 candidatos en el orden archivado de la API: se seleccionaron 30 y se descartaron 91. Las razones de descarte fueron 73 duplicados por PDB o identidad UniProt, 13 casos con observaciones alternativas u ocupación parcial, tres con elementos ajenos al alcance de proteína y dos con múltiples modelos. Los resultados de choques no se utilizaron para seleccionar o reemplazar casos.

Las 30 referencias tienen `reviewed=true`, fuente experimental RCSB/PDB y distintos identificadores PDB y UniProt. La revisión de la anotación está respaldada por el recurso externo; no se atribuye al agente una revisión experta nueva. Sus etiquetas indican **estructura repetitiva experimental de referencia** y no certifican ausencia de todo error físico o atómico. Los 73 modelos de Pratt sin evidencia explícita de problema conservan su etiqueta desconocida.

Se examina la cadena polimérica completa seleccionada, no una conversión inferida de los loci de RepeatsDB. Se excluyen otras cadenas, ligandos y aguas del cálculo. Este alcance permite una comparación de contactos internos reproducible, pero no evalúa el entorno molecular completo. Los archivos de coordenadas, los originales de los autores y la evidencia portable que los contiene permanecen locales fuera de este paquete versionable. [cases.json](cases.json) registra sus procedencias y hashes.

## Resultados observados

| Cohorte | Casos fijados | Evaluables | Cobertura de la medida estérica | Clashscore mediano | Rango observado |
|---|---:|---:|---:|---:|---:|
| Originales AF2 de Pratt | 78 | 77 | 98,7% | 54,51 | 0,00 a 241,28 |
| Referencias experimentales revisadas | 30 | 28 | 93,3% | 10,09 | 0,97 a 29,45 |

Los casos `23ab`, `1ea0-A` y `1llw-A` excedieron el límite previamente registrado de 180 segundos por instancia. Se conservan como no evaluables, sin valor numérico y sin reemplazarlos por otros ejemplos. Los cinco problemas ilustrados en el artículo de Pratt fueron evaluables:

| Caso | Choques graves | Clashscore |
|---|---:|---:|
| 8b | 77 | 64,17 |
| 12ab | 277 | 131,16 |
| 19r | 155 | 53,41 |
| 21r | 160 | 49,38 |
| 22r | 172 | 50,74 |

Los 28 casos experimentales evaluables también contienen al menos un choque grave. Por tanto, la existencia de un choque no puede tratarse automáticamente como evidencia de pliegue incorrecto. El contraste entre las distribuciones es descriptivo. Todos los modelos de los autores son AF2 **sin relajación**, mientras las referencias experimentales fueron refinadas; esta diferencia de preparación impide atribuir el contraste exclusivamente a la validez del pliegue.

La figura [steric-distribution.png](steric-distribution.png), también en PDF y SVG, conserva los denominadores evaluables y los cinco identificadores publicados. No muestra un umbral ni una frontera de clasificación. Los valores por caso están en [outcomes.csv](outcomes.csv) y los conteos derivados en [summary.json](summary.json).

## Integración en la implementación

La variable de operador `HELIX_TRP_STERIC_PYTHON` habilita el validador mantenido mediante un programa incluido en Helix. El modelo de lenguaje no elige un ejecutable ni envía código. Se verifica la identidad exacta de la estructura, el modelo seleccionado y la cadena de autor; se registran versiones, hashes de módulos y extensiones, 54 hashes de recursos químicos y el hash del programa incluido. Se devuelve una medida determinista y se conserva `foldVerdict=not_established`, sin un umbral para el modelo completo.

Los fallos del validador quedan explícitos y no se convierten en un resultado físico positivo ni negativo. La cancelación del usuario se propaga. Los reportes no incorporan tiempos variables o rutas temporales: la relectura antes de ejecutar puede compararse con el reporte que se aprobó. Cambiar el programa o sus recursos modifica el contenido sujeto a aprobación.

[agent-reference.json](agent-reference.json) prueba el adaptador real de archivos de Helix sobre `8b`, con coordenadas y PAE originales emparejadas. Reproduce los 77 choques y clashscore 64,17 del cálculo externo, conserva incertidumbre biológica y supera la verificación portable. Los ensayos comprueban dos reportes deterministas, el adaptador, rechazo de modificaciones del programa archivado y comportamiento ante un entorno inexistente: nueve pruebas correctas y 45 aserciones con el entorno real. La campaña de 108 casos usa el motor externo; no se presenta como 108 sesiones del agente.

## Qué aporta y qué falta para R3.8

Quedan disponibles un observable físico mantenido e integrado, 30 referencias experimentales con anotación revisada, errores de ejecución conservados y evidencia reproducible. Este trabajo no mide hidrofobicidad expuesta, cargas internas sin compensación ni estabilidad termodinámica. Tampoco introduce una verdad física para los casos sin etiqueta.

La sensibilidad y especificidad generales de plausibilidad permanecen `null`. Falta justificar y evaluar una regla de decisión para el fallo físico concreto, con una referencia pertinente y datos independientes de su diseño. Si estas distribuciones se emplean para elegir un umbral o diseñar esa regla, pasarán a ser datos de desarrollo y no podrán presentarse después como una reserva intacta. Se conservan las metas previas de la tesis; no se declaran satisfechas mediante esta medida auxiliar.

## Reproducción

```sh
python3 script/tesis/setup_steric_validator.py
~/.local/state/helix/structural-20261012/venv/bin/python script/tesis/structural_campaign.py verify
HELIX_TRP_STERIC_PYTHON="$HOME/.local/state/helix/structural-20261012/venv/bin/python" bun script/tesis/run_steric_production_reference.ts
python3 script/tesis/verify_structural_campaign.py --inputs
```

El instalador usa versiones fijadas y verifica los hashes de los recursos oficiales geostd y CCD. Los cambios de configuración necesarios para resolver dependencias faltantes se registraron antes del primer resultado físico válido en los archivos `runtime-amendment*.json`; no cambiaron coordenadas, etiquetas ni umbrales. El intento interrumpido por diccionarios faltantes se conserva en `failed-runtime-attempt-1/`.

Para volver a ejecutar los 108 casos, con los originales locales y las referencias conservadas, se usa `structural_campaign.py run`. No se sobrescribe la fijación prospectiva mediante `prepare`. El verificador independiente usa la biblioteca estándar y comprueba hashes, identidad de las referencias, conteos, valores, denominadores y ausencia de métricas de clasificación injustificadas. La verificación sin `--inputs` comprueba el paquete derivado; con esa opción contrasta además los originales y recursos locales. No certifica autoría ni verdad biológica.

Esta extensión no empleó llamadas a modelos ni instancias AWS; sus cálculos se realizaron en la estación local.
