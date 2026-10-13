# Contraste secundario del límite de ejecución

Se conservaron sin cambios los 105 resultados evaluables y los tres límites de 180 segundos del protocolo principal. Antes de repetir esos tres casos se fijaron las coordenadas, las etiquetas, las versiones del método, sus módulos y recursos químicos y los hashes del paquete principal en [freeze.json](freeze.json).

Se permitió una sola tentativa por caso, de hasta 600 segundos, con un trabajador local. No se cambiaron parámetros químicos, umbrales biológicos ni entradas. Este contraste amplía un límite técnico y no reemplaza retrospectivamente los fallos del primario.

| Caso | Tiempo de la tentativa secundaria | Choques graves | Clashscore |
|---|---:|---:|---:|
| 23ab | 240,77 s | 358 | 87,08 |
| 1ea0-A | 190,44 s | 1605 | 71,55 |
| 1llw-A | 188,55 s | 961 | 42,51 |

Las tres tentativas finalizaron correctamente. El perfil ampliado contiene medidas para 78/78 modelos de Pratt y 30/30 referencias experimentales: medianas 55,09 y 11,84, respectivamente. El primario sigue reportando 77/78 y 28/30, con medianas 54,51 y 10,09. Los dos perfiles se mantienen separados.

Cada tiempo secundario fue superior a 180 segundos. El perfil también cambia de dos trabajadores a uno, por lo que las diferencias de tiempo no se atribuyen exclusivamente al límite. La configuración de producción de Helix conserva su límite de 180 segundos y no se cambió durante la campaña remota.

El experimental `1ea0-A` presenta clashscore 71,55, superior al de cuatro de los cinco problemas ilustrados de Pratt. La [figura ampliada](steric-distribution.png) muestra ese solapamiento; existe también en PDF y SVG. Esto refuerza la necesidad de separar el observable estérico de un clasificador de plausibilidad. No se seleccionó un umbral después de observar estos valores. Sensibilidad y especificidad física permanecen sin establecer.

[outcomes.csv](outcomes.csv) conserva las tres tentativas y [expanded-outcomes.csv](expanded-outcomes.csv) combina las 105 medidas del primario con las tres recuperadas exclusivamente para describir el perfil ampliado. [summary.json](summary.json) reporta ambos denominadores. El manifiesto del cálculo secundario y el manifiesto separado del análisis conservan sus hashes; el paquete principal sigue intacto.

```sh
~/.local/state/helix/structural-20261012/venv/bin/python script/tesis/structural_runtime_contrast.py verify
python3 script/tesis/verify_structural_campaign.py --inputs
```

La auditoría de fuentes y etiquetas está en [source-label-audit.json](source-label-audit.json). Las cinco etiquetas originales siguen vinculadas por secuencia exacta a las figuras de los autores. La Tabla S1 no contiene una columna Verify3D que permita identificar honestamente todos los casos problemáticos mencionados en el texto. La anotación revisada de RepeatsDB tampoco certifica ausencia de toda anomalía atómica.
