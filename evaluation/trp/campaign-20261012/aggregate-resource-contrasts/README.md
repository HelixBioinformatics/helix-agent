# Contrastes de recursos con el cliente completo de Helix

Esta campaña compara la decisión real de admisión de Helix con la ejecución física de su cliente, preparación, SQLite persistente, controlador y exportación. Todos los casos proceden de una proteína de desarrollo. Las variantes prueban el contrato de ingeniería; no constituyen una muestra biológica independiente ni reemplazan las solicitudes reservadas de la anotadora.

## Alcance y unidades

Una cuota XFS de proyecto contabiliza los bloques asignados de las siete rutas declaradas: raíz de la asignación, espacio del cliente, estado, caché, temporales, espacio remoto y exportación. El cliente y el controlador local de Python/Nextflow comparten un grupo de control del núcleo con un CPU, 2 GiB de RAM y sin swap. Cada tarea de Slurm usa dos CPU y 2 GiB de RAM en su contenedor; las tareas son secuenciales. Se comprueban cuatro trabajos reales: dos de ejecución de prueba y dos de cálculo.

El perfil usa transporte local entre cliente y controlador y NFS hacia dos trabajadores. No se atribuye SSH a ese transporte ni se agrupa la RAM de varios nodos para un único trabajo. El software instalado, las imágenes y cachés compartidas de infraestructura y la telemetría del observador experimental quedan fuera del almacenamiento de trabajo. La cuota abarca las rutas declaradas, no todos los discos físicos de las máquinas.

El pico de bloques asignados se muestrea cada 0,5 segundos. La memoria máxima procede del contador del núcleo. Un pico de almacenamiento de un intento bloqueado corresponde a trabajo incompleto y no se interpreta como el espacio total que necesitaría un flujo exitoso.

## Conjuntos preservados

- `campaign-inputs/freeze.json`: cuarenta contrastes originales, veinte entradas con dos presupuestos cada una. Se congelaron fuentes, entradas, resultados de referencia, umbrales y reglas antes de observar los resultados de esos casos.
- `boundary-inputs/freeze.json`: seis contrastes adicionales de tres entradas diferentes con cuotas de 39 y 41 MiB. Se conservan separados del conjunto original. Los campos genéricos de mínimo veinte por clase copiados en ese archivo no cambian su denominador de seis; ese mínimo corresponde al conjunto original.
- `extension-inputs/freeze.json`: suplemento de cuatro entradas nuevas, dos con 128 MiB y dos con 64 o 128 KiB. Se planificó después de conocer los resultados originales y se congeló antes de sus propias salidas. Aporta dos factibles y dos inviables adicionales para alcanzar veinte observaciones de cada clase; no reemplaza ni modifica los cuarenta originales ni los seis de frontera. El primer comando local de congelación falló por la desaparición de un entorno temporal de Python; se preserva en `extension-freeze-first-command.json`, sin envíos a la nube.
- `smoke-outcomes*`: intentos de desarrollo conservados, incluidos fallos de arranque, observación y del estimador anterior. No se cuentan como casos nuevos de la campaña.
- `copy-causal-controls`: control independiente del mecanismo ENOSPC bajo cuota. La primera interpretación queda intacta y su revisión de salud global está en `mechanism-review.json`.
- `checkpoint-1`: interrupción programada sólo del conductor local, recuperación del mismo trabajo y prueba de reposo antes de una eventual continuación legítima de las máquinas. Un error de transporte no autoriza reenviar un trabajo.

La calibración del perfil de almacenamiento se realizó en un piloto de desarrollo previo. El perfil estricto reserva 32 MiB de sobrecarga; el perfil ordinario de Helix conserva 12 MiB. La predicción es una estimación declarada y no una garantía universal de pico.

## Decisión real y oráculo físico

Antes de preparar o ejecutar, se registra la decisión del módulo original de Helix sobre el mismo paquete ligado a la política y el presupuesto del caso. Para un rechazo exclusivamente debido a la estimación de almacenamiento, el arnés experimental puede ejecutar el contrafactual, con la decisión original archivada. La excepción está aislada en el arnés; no se ofrece al modelo y no evita las cuotas, permisos, propiedad, plazo, RAM, CPU o aprobaciones del sistema.

Se etiqueta un caso como físicamente factible sólo cuando el cliente real completa el flujo, cuatro trabajos nativos finalizan correctamente, el CSV coincide con la referencia de su propia entrada, SQLite es persistente y la exportación existe e íntegra dentro de la cuota. Los casos ordinariamente admitidos deben superar además el verificador portátil habitual. En un contrafactual, un rechazo del verificador debido sólo a la estimación original se conserva y no se utiliza de manera circular como prueba de imposibilidad física.

Una etiqueta de inviabilidad requiere un fallo terminal causal del núcleo bajo la misma cuota o grupo de control. Un error genérico, un fallo de observación o un fallo de escritura de una caché opcional que el programa ignora quedan sin etiqueta. En particular, los fallos de directorio no capturados por el filtro de syscalls original permanecen desconocidos.

## Auditorías y correcciones de observación

`audit_cases.py` conserva exactamente su SHA congelado y tiene una copia adicional en `source-snapshots/audit_cases-frozen.py`. La edición temporal del auditor y su restauración están reconocidas en `auditor-source-overlay.json`; no se alteraron el productor, las entradas, los presupuestos ni los resultados originales.

Las correcciones posteriores a la observación tienen archivos separados:

- `audit_cases_resolution.py` y `auditor-amendment.json`: resolución de un milisegundo de `Date.now()` frente a microsegundos de `strace`, con la misma ventana causal de cinco segundos; relación de un fallo fatal de apertura de SQLite con la syscall de su archivo específico.
- `audit_cases_fd.py` y `auditor-fd-amendment.json`: relación entre el descriptor explícito de un error fatal de escritura y el archivo expuesto por `strace -yy`, en el árbol de procesos propio.
- `independent-audit.json`: interpretación del auditor congelado.
- `review-resolution.json` y `review-fd.json`: revisiones separadas. Los informes históricos siguen en `audit-history` y `review-history`.

El resumen conserva las rutas y SHA de todas las interpretaciones y declara cuál se seleccionó. Las correcciones del auditor no se presentan como reglas prospectivas de clasificación biológica.

## Resultados y reproducción

`summary.json` y `cases.csv` son las fuentes de resultados. Incluyen todos los identificadores planificados, los casos sin observación, los desconocidos observados, las cuotas, los picos, las predicciones, los excesos y las tasas de falso rechazo. Los cuarenta originales y los seis de frontera tienen denominadores separados. Los umbrales permanecen: falso rechazo máximo de 5 %, ningún admitido sobre presupuesto, diferencia de conteos de cero y mediana de sobreestimación máxima de 25 %. Su evaluación sólo corresponde a los contrastes técnicos observados; `scientificR24Rate` permanece nulo.

### Resultado final observado

| Conjunto | Observados | Factibles | Inviables | Desconocidos | Falsos rechazos | Mediana de sobreestimación |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Original | 40/40 | 18 | 18 | 4 | 0/18 | 13,90 % |
| Frontera | 6/6 | 6 | 0 | 0 | 3/6 (50 %) | 11,20 % |
| Suplemento posterior | 4/4 | 2 | 2 | 0 | 0/2 | 12,64 % |

En la frontera, los tres presupuestos de 39 MiB permiten completar el cliente, sus cuatro trabajos y la exportación. Helix los rechaza porque estima 42 266 624 bytes, alrededor de 40,31 MiB. El contraste de frontera incumple el umbral de falso rechazo de 5 %. No se cambió el umbral ni se corrigió el estimador después de observar estos casos.

El conjunto original más su suplemento aporta veinte casos factibles y veinte inviables, con cuatro desconocidos conservados. La unión descriptiva de los tres conjuntos tiene 26 factibles, 20 inviables, cuatro desconocidos y tres falsos rechazos entre 26 factibles (11,54 %). No es una estimación poblacional ni un resultado independiente de tres proteínas: todas las entradas derivan de la misma proteína de desarrollo y los conjuntos tienen selecciones de presupuesto distintas.

En los cincuenta casos observados no hubo exceso de cuota muestreado ni exceso de la predicción en un caso admitido. Los 26 flujos completos exportaron evidencia íntegra, reprodujeron sus conteos sin diferencias y conservaron SQLite verificable en frío. El muestreo de bloques no garantiza que se haya observado todo pico transitorio. La memoria máxima se informa separadamente, sin equiparar bytes de RAM con almacenamiento.

El auditor congelado clasifica inicialmente los cuarenta originales como 18 factibles, 10 inviables y 12 desconocidos. Las revisiones de resolución temporal y descriptores de archivo aportan ocho inviables demostrados adicionales, sin borrar las primeras interpretaciones. Los cuatro desconocidos finales son `AGG-08-small`, `AGG-18-small`, `AGG-13-generous` y `AGG-14-generous`. En los dos pequeños falta la syscall de creación de directorio necesaria para demostrar la causalidad. En los dos generosos ocurrió un fallo de infraestructura, sin prueba de imposibilidad por presupuesto.

### Continuación y reparación operativa

El primer bloque se detuvo a las 06:36 UTC únicamente en su conductor local. Se recuperó el mismo intento en curso, se probó reposo de las tres máquinas y se realizó un ciclo legítimo de parada y arranque de las mismas instancias. La continuación despachó sólo trece casos que no habían sido enviados. Los dos generosos ya fallidos no se reintentaron.

En el fallo original de `AGG-13-generous`, el daemon de Slurm del trabajador 2 registró `Stale file handle` al abrir `.command.log`, fallo de preparación de E/S y señal 53 antes de ejecutar la tarea. La condición transitoria `InvalidAccount` también se observó en trabajos exitosos y no se interpreta como causa definitiva. Al reiniciar se restauró el archivo XFS existente y el UUID `cd26a20b-f8e0-480a-9640-38e1b93e7fff`, sin formatear ni reiniciar cuotas. Se añadió `fsid=43` estable a la exportación NFS conservando `root_squash` y se montó directamente en ambos trabajadores.

Los preflights operativos preservan un error de sintaxis del observador antes de modificar el huésped y un error del comando de prueba de Docker, que no anulaba el entrypoint `geometre`. El tercer preflight completó los trabajos nativos 316 y 317 con E/S real de NFS y la imagen fijada. Son comprobaciones de infraestructura, no casos de la campaña. Las fuentes productoras congeladas permanecieron en `ecfab67`. La prueba final en `final-quiescence.json` confirma los cincuenta intentos terminales, su limpieza y ausencia de trabajos, contenedores y procesos propios activos.

Para verificar el paquete congelado sin mutar interpretaciones ni lanzar trabajos en nube:

```bash
python3 evaluation/trp/campaign-20261012/aggregate-resource-contrasts/verify_final_package.py
```

Para reproducir las auditorías originales en una copia aislada del checkout de fuentes `ecfab67`, sin nuevos trabajos en nube:

```bash
python3 evaluation/trp/campaign-20261012/aggregate-resource-contrasts/audit_cases.py --inputs evaluation/trp/campaign-20261012/aggregate-resource-contrasts/campaign-inputs --outcomes evaluation/trp/campaign-20261012/aggregate-resource-contrasts/campaign-outcomes
python3 evaluation/trp/campaign-20261012/aggregate-resource-contrasts/audit_cases_resolution.py --inputs evaluation/trp/campaign-20261012/aggregate-resource-contrasts/campaign-inputs --outcomes evaluation/trp/campaign-20261012/aggregate-resource-contrasts/campaign-outcomes
python3 evaluation/trp/campaign-20261012/aggregate-resource-contrasts/audit_cases_fd.py --inputs evaluation/trp/campaign-20261012/aggregate-resource-contrasts/campaign-inputs --outcomes evaluation/trp/campaign-20261012/aggregate-resource-contrasts/campaign-outcomes
python3 evaluation/trp/campaign-20261012/aggregate-resource-contrasts/summarize_campaign.py
uv run --with matplotlib python evaluation/trp/campaign-20261012/aggregate-resource-contrasts/plot_campaign.py
```

Para la frontera, las mismas auditorías reciben `boundary-inputs` y `boundary-outcomes`. Cada caso conserva el archivo tar original, SHA externo, enlaces simbólicos registrados, política, inventario, observación del núcleo, entrada, decisión real, salida del cliente, limpieza y exportación. La extracción de revisión sólo materializa archivos ordinarios y conserva los enlaces del archivo original por separado.
