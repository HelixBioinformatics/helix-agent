# Originales de Pratt incorporados el 01/10/2026

Se incorporaron los archivos que el tesista recibió de Daniel Rigden, recuperados por Dr Price. El envío contiene **78 PDB de rango 1, 78 JSON de puntuaciones y 78 JSON PAE**. Las 78 secuencias coinciden exactamente con los motivos de la Tabla S1 repetidos diez veces. Se conservan los bytes originales y sus SHA-256 en [manifest.json](manifest.json). El directorio `originals/` permanece local; las condiciones de redistribución del envío separado no se especificaron en el correo compartido. El artículo y sus suplementos públicos conservan su licencia propia.

Los nombres `model_1` a `model_5` identifican conjuntos de parámetros AF2. El paquete contiene únicamente `rank_001`, con `seed_000`; no contiene los rangos 2 a 5 ni los registros originales de configuración. La versión local 1.5.2 aparece en el artículo, pero no se presenta como una versión comprobada mediante un log del envío.

## Vinculación y controles

Helix incorpora el contrato `colabfold-local/1.0.0` en `trp_inspect`, con motor `trp-structural/1.1.0`. Comprueba identidad de archivos, SHA-256, secuencia completa, cadena única, numeración continua, modelo único, pLDDT del JSON frente a la columna B y matrices PAE idénticas en los dos JSON. Los **78/78** pares superan estas comprobaciones. La procedencia es declarada por el operador; estas comprobaciones no autentican al remitente ni certifican validez biológica.

Se detectó una particularidad del formato: la matriz PAE se redondea a dos decimales, mientras `max_pae` conserva más precisión. El [código oficial de ColabFold 1.5.2](https://github.com/sokrypton/ColabFold/blob/v1.5.2/colabfold/batch.py#L460-L472) confirma esa serialización. El adaptador permite exclusivamente la media unidad del último decimal, 0,005 Å, al contrastar la matriz con ese máximo. **El umbral de evaluación de 5 Å no cambia.**

En nueve casos, la media del JSON difiere del valor publicado más de la tolerancia de redondeo adoptada, 0,056 puntos; la mayor diferencia absoluta es 0,0797 puntos. Se registran ambos valores en [cases.json](cases.json). No se reemplazó la tabla publicada ni se alteraron las puntuaciones originales. Los cinco ejemplos positivos explícitos no presentan esa discrepancia.

## Referencias de problema publicado

Los cinco ejemplos siguientes se vincularon por secuencia exacta a las descripciones de las figuras de [Pratt et al. (2025)](https://doi.org/10.1016/j.csbj.2025.01.016). Sus etiquetas indican un problema físico o de validación descrito por los autores; no son cinco determinaciones experimentales nuevas.

| Identificador | Figura | Evidencia publicada | pLDDT medio publicado | pLDDT mínimo, diez motivos | PAE máximo entre motivos, Å |
|---|---|---|---:|---:|---:|
| 8b | 3A | Hidrofobicidad expuesta y choques entre residuos | 83,5 | 73,12 | 17,25 |
| 12ab | 7A | Ejemplo problemático según Verify3D | 82,4 | 50,56 | 30,02 |
| 19r | 7B | Ejemplo problemático según Verify3D | 82,7 | 60,31 | 25,58 |
| 21r | 6 | Carga interna y choques de lisinas con histidinas | 82,0 | 54,81 | 29,27 |
| 22r | 3B | Aspartatos internos apilados sin compensación | 82,4 | 46,31 | 30,38 |

Las otras **73 predicciones quedan sin etiqueta de fallo/corrección**. La clasificación de 32 modelos como β-solenoides no los convierte en 32 fallos demostrados. Tampoco se usan los otros tipos de pliegue como controles correctos.

No están los dos modelos preliminares sometidos a dinámica molecular en la figura 14, de motivos `TVCWCMIWQCEEKFVIVEVM` y `GDDPIYTKDNINPIGPYMGN`, ni el ejemplo de mucina de la figura 1/S1, `QTSTVIGTIASTETSSSTGI`. Se registran como no recuperados en este envío. Su ausencia no impidió inspeccionar los 78 modelos de la Tabla S1.

## Resultado del diagnóstico

El perfil principal conservó los umbrales anteriores: pLDDT mínimo de 70 y máximo de ambos bloques dirigidos PAE de 5 Å entre cada par de motivos. Se analizaron diez motivos por secuencia, sin recortar residuos. **Los 78 modelos generan alarma PAE; 68 presentan además algún residuo con pLDDT inferior a 70.** La media alta no implica que todos los residuos alcancen el mínimo ni que todas las orientaciones relativas sean confiables.

Los cinco ejemplos problemáticos generan alarma: 5/5, con intervalo Wilson de 95% de 56,6% a 100%. Esta es una tasa descriptiva de alarma mecánica en cinco ejemplos ilustrados. **No es una sensibilidad física validada**, porque el control no identifica hidrofobicidad expuesta, cargas internas o choques. Además, marcar también todas las predicciones sin etiqueta no acredita capacidad de discriminación.

Antes de ejecutar se fijó un diagnóstico adicional que usa los ocho motivos centrales, con los mismos umbrales y las matrices originales completas. Marca 77/78 modelos y conserva las cinco alarmas; `10ab` recibe admisión mecánica en esa selección. Es un análisis de la influencia de los extremos, no una elección retrospectiva del perfil que debe aprobar el benchmark. Los motivos de secuencia suministrados tampoco son anotaciones independientes de límites estructurales.

El control `fold-plausibility` permanece **no evaluable en 78/78**, incluso cuando existe una alarma de otro control. La cobertura física es 0%; sensibilidad física y especificidad quedan `null`. La tasa conservadora de detección física es 0/5 en los ejemplos etiquetados. No se declara cumplimiento de R3.8 ni se modifican las metas de 80%, 90% y 90%.

## Qué quedó resuelto y qué sigue abierto

Quedó resuelta la falta de coordenadas y PAE para todos los rangos 1 de la Tabla S1. Se completaron su vinculación, la ejecución de la batería, los reportes por instancia y un contraste del adaptador real del agente sobre los cinco ejemplos, con verificación portable y resultados iguales al motor offline. No hubo llamadas a un modelo ni uso de AWS.

Para cerrar la evaluación física de R3.8 hacen falta un control físico ejecutable y validado, y al menos 30 controles negativos pertinentes con anotación revisada de RepeatsDB, según el protocolo. Si se utiliza este diagnóstico para diseñar o calibrar un control nuevo, deberá conservarse como desarrollo y evaluarse ese cambio con referencias independientes; no reutilizar las mismas salidas como una reserva intacta. Los datos originales de las figuras ausentes aportarían ejemplos adicionales, pero la recuperación de la Tabla S1 ya no es el bloqueo.

## Reproducción y archivos

Con los originales locales en `originals/`:

```sh
python3 script/tesis/evaluate_pratt_originals.py verify
python3 script/tesis/evaluate_pratt_originals.py run
HELIX_TRP_PYTHON=python3 bun script/tesis/run_pratt_inspection.ts
```

El motor PDB de este diagnóstico usa la biblioteca estándar de Python. El comando `prepare` se ejecutó una vez, antes de observar los veredictos; rechaza sobrescribir la congelación. El registro [freeze.json](freeze.json) conserva los hashes de datos, etiquetas, fuentes y dos perfiles. Es una fijación de este diagnóstico acotado; no se presenta como congelación completa de F6 ni como un checkout global limpio.

- [outcomes.csv](outcomes.csv): 156 filas, correspondientes a 78 modelos en dos perfiles, con valores, veredictos y motivos.
- [summary.json](summary.json): conteos calculados, indicadores ausentes, incertidumbre y hashes de los 156 reportes.
- [cases.json](cases.json): tabla de correspondencia y evidencia de las cinco etiquetas.
- `metadata/`: 78 contratos de procedencia y emparejamiento.
- `reports/`: nueve controles por modelo y perfil, con productor, marco, hashes y umbrales.
- [agent-adapter.json](agent-adapter.json): cinco inspecciones realizadas mediante el adaptador de archivos de Helix y verificadas desde su copia portable local.
- `validation/`: regresión de contratos, dominio y tipos. Los ensayos sintéticos se usan únicamente para verificar software.

Se conservó intacta la auditoría pública anterior en `../structural-f5/pratt/recoverability.json`: su resultado de cero modelos recuperados describe el paquete público de septiembre, no este envío posterior de los autores.
