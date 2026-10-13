# Campaña de evaluación de Helix, 12 de octubre de 2026

Este directorio separa la evaluación técnica que puede ejecutarse ahora de las
mediciones científicas que requieren referencias independientes. El plan cubre
los 21 resultados actuales: R1.1 a R1.9, R2.1 a R2.4 y R3.1 a R3.8. No declara
terminada la tesis.

## Resultados comprobados durante la campaña

Los artefactos iniciales de planificación conservan lo observado al inicio.
Los resúmenes siguientes incorporan ejecuciones posteriores sin sustituir
los intentos fallidos ni atribuir etiquetas humanas a las respuestas del corredor.

- `cloud/workflow-summary.json`: 52 intentos, 50 variantes distintas verificadas.
  Los primeros intentos fueron 48 satisfactorios y dos fallidos; ambos fallos
  permanecen en sus carpetas originales y sus dos reintentos están separados.
  Cada CSV se compara con una referencia local de sus propias entradas, imagen
  y perfil numérico. Todas las variantes son subconjuntos de 2XQH/A.
- `cloud/lab1/mapped-reference-protocol/driver-terminal.json`: ruta real
  SIFTS/UniProt de 12 unidades y 206 residuos, cuatro tareas Slurm, paquete
  de 156 archivos y 320/320 alteraciones detectadas por auditoría independiente.
- `cloud/lab1/cancellation/next-ctx-abort/driver-terminal.json`: aborto de Helix
  posterior a observar una tarea nativa en ejecución. Slurm registró CANCELLED,
  el controlador terminó y el paquete automático conserva el evento de fallo.
  Los ensayos anteriores de cancelación fallidos y la recuperación manual se
  conservan con sus propias limitaciones.
- `structural/summary.json`: observables estéricos medidos en 105/108 casos
  con el límite primario de 180 segundos. `structural/runtime-600/summary.json`
  conserva un contraste prospectivo separado de los tres tiempos agotados,
  recuperados con 600 segundos; no cambia el denominador ni el resultado primario.
- `structural/freesasa/summary.json`: exposición al solvente medida en 108/108
  estructuras, con ausencia de átomos y casos sin residuos cargados explícitos.
  Los módulos opcionales de Helix reproducen observables externos fijados;
  estos valores no constituyen un clasificador de plausibilidad física validado.
- `model-pilot/audit.json`: cuatro casos de desarrollo con el modelo acordado.
  El equivalente de precio API de los pasos observados es US$0,1200792;
  no se observó una factura OAuth ni un límite de salida de 8192 tokens aplicado
  por el proveedor. Los guardias de pasos y tiempo se informan por separado.
- `checks/final-regression/summary.json`: 532 pruebas aprobadas, 59 pruebas
  opcionales omitidas y ningún fallo; las pruebas remotas y los motores externos
  tienen además sus invocaciones y evidencias específicas.

El contraste de decisiones de recursos está en
`cloud/lab2/r24-campaign/`. Su oráculo independiente impone cuotas XFS y límites
de controlador/tareas, incluyendo ejecuciones rechazadas por Helix.
El alcance fijado es el workspace del head, con una copia portable materializada;
excluye el almacenamiento del cliente real y del supervisor. Por eso no demuestra
la cuota agregada de la ruta remota ni la evaluación reservada R2.4.

La matriz conjunta de recursos ya terminó: `aggregate-resource-contrasts/summary.json`
conserva los cuarenta IDs originales, seis de frontera y cuatro suplementarios
por separado. La frontera observó tres falsos rechazos entre seis casos
factibles y no cumple la meta del 5%. Los cuatro desconocidos originales
y las primeras interpretaciones permanecen conservados.

`cloud/lab1/final-stopped-post-corrections-20261013.json` y el registro homónimo
de lab2 confirman mediante nuevas consultas EC2 los seis nodos detenidos. Los registros de parada
anteriores son históricos. La versión corregida se valida por separado en
`checks/post-campaign-production-20261013/`; las nuevas pruebas no cambian
las tasas de los cincuenta casos de recursos. Detener cómputo conserva sus
discos y no elimina su coste. `final-storage-post-corrections-20261013.json`
en cada laboratorio comprueba tres volúmenes con 90 GiB retenidos por cuenta.
El saldo del portal no representa una factura final.

## Plan y auditoría

- `campaign-plan.json`: ocho hitos, requisitos por resultado, dependencias,
  condiciones de presupuesto y pruebas que demostrarían cada cierre.
  Los estados operativos M4/M8 se actualizaron después de observar los casos,
  instalar el documento y detener el cómputo. La versión anterior exacta está
  en `checks/final-goal-plan-before-delivery-20261013.json`; casos, umbrales y
  diseño no cambiaron. `progress.json` identifica sus campos históricos.
- `audit.json`: instantánea del Word, protocolo, respuestas actuales de la
  experta, decisiones de modelo y cinco verificaciones de evidencia existente.
- `audit_campaign.py`: reconstruye esa instantánea mediante lectura de Word y
  Excel, sin modificar esos documentos, llamar al modelo ni iniciar AWS.
- `cloud/`: campañas e infraestructura de las dos cuentas, gestionadas por el
  coordinador. Cada cuenta conserva presupuesto y capacidades propios.
- `structural/`: preparación de controles estructurales, gestionada por el
  agente responsable. Un candidato descargado no constituye una etiqueta
  independiente de estructura físicamente correcta.

La auditoría detecta 70 solicitudes en el Excel de la experta. Sus campos de
solicitud definitiva, objetivo esperado, factibilidad y ambas paráfrasis siguen
vacíos. Son campos reales leídos del archivo, no solo un estado histórico del
plan. El libro recibido posteriormente debe preservarse y congelarse antes de
la inferencia reservada.

`evaluation/trp/protocol.json` es el diseño fechado de septiembre de 2026.
Sus dependencias operativas históricas se interpretan con las decisiones y
congelaciones de esta campaña: acceso al modelo y a Slurm ya comprobados,
referencias humanas y validación física aún pendientes. Sus 21 métricas y
umbrales permanecen iguales. No contiene una exigencia de latencia P95.

El modelo acordado sigue siendo OpenAI `gpt-6-sol`, razonamiento medio,
US$100 de presupuesto total, con hasta US$10 para el piloto incluidos en ese
total. `model-access.json` conserva la observación inicial: la estación de
oficina no respondió por SSH y un filtro del complemento excluía el modelo
en la lista local. Tras corregir ese filtro, `model-access-probe.json` registra
una respuesta real del modelo solicitado mediante el OAuth existente: 3707
tokens de entrada, 12 de salida y 125 de razonamiento. Fue una comprobación
de acceso, sin casos reservados ni evaluación humana. El coste cero registrado
por el complemento no demuestra gratuidad de API; no se observó facturación.

## Contratos y evidencia comprobados

`contract-corpus/freeze.json` fija los casos antes de consultar sus resultados.
El generador se niega a sobrescribir una congelación existente.

- 50 grafos válidos: subconjuntos distintos de las unidades publicadas de
  2XQH/A, con 3, 4, 6, 8 o 10 unidades.
- 30 grafos inválidos: tres variantes de cada uno de los diez modos fijados en
  el protocolo. Sus etiquetas derivan de alteraciones explícitas del contrato.
- 40 presupuestos sintéticos: veinte admisibles y veinte insuficientes según
  el contrato aritmético. Su factibilidad física permanece sin etiqueta.

La ejecución estática obtuvo 50/50 válidos aceptados y 0/30 inválidos aceptados,
con los treinta motivos esperados detectados y ninguna excepción del control.
Esto comprueba contratos en una sola proteína de desarrollo. No representa
50 proteínas independientes, desempeño del lenguaje, recorrido Nextflow en
seco ni ejecución satisfactoria de 50 solicitudes revisadas por la experta.

La inyección de fallos en una copia del paquete SIFTS de 139 archivos detectó
286/286 alteraciones, ausencias y otros fallos de integridad. Se verificó también
la copia restaurada. El paquete original no se modificó. La prueba se repetirá
con los nuevos paquetes remotos para comprobar su alcance específico.

Las verificaciones actuales también confirman las siete ejecuciones finales de
recursos locales, los originales y 156 informes de Pratt, y la evidencia previa
de dos tareas Nextflow sobre dos trabajadores AWS. Cada prueba conserva su
alcance de ingeniería; no sustituye una campaña reservada.

## Reproducción sin nube ni modelo

Desde la raíz del repositorio:

```sh
python evaluation/trp/campaign-20261012/audit_campaign.py
bun evaluation/trp/campaign-20261012/run_contract_graphs.ts
python script/tesis/audit_trp_bundle.py evaluation/trp/reference/coordinate-integrated-20260921/evidence evaluation/trp/campaign-20261012/checks/portable-fault-injection.json
```

Los resultados se escriben solo en este directorio. El corredor de grafos
comprueba hashes de casos y del código que ejecuta contra su congelación.
La integración remota modificó posteriormente `resources.ts`, que este
corredor estático no importa. Sus bytes originales se conservan en
`contract-corpus/frozen-sources/` con el hash original, y el informe declara
cuando consulta ese archivo de procedencia. La congelación y las etiquetas
originales permanecen intactas. Si cambian los módulos que sí ejecuta el
corredor, evaluar la revisión congelada o registrar otra revisión; no
reemplazar silenciosamente sus hashes.

## Límites científicos pendientes

R1.3 requiere las referencias y paráfrasis humanas, configuración efectiva y
congelación de T-LANG. R1.5 requiere sus 50 especificaciones factibles aprobadas
para calcular la tasa científica prevista. R3.3 requiere al menos 100 turnos
humanos reales y primeras etiquetas independientes para calcular kappa.

R3.8 conserva sensibilidad física y especificidad sin calcular. Los 78
originales de Pratt están disponibles y verificados. Sus alarmas mecánicas no
demuestran discriminación de fallos físicos. Se necesita un control físico
validado y al menos 30 controles negativos pertinentes revisados; sus familias
y su uso en desarrollo o reserva deben quedar registrados.

La campaña de presión de AWS y las decisiones sintéticas de presupuesto deben
informarse por separado. Un rechazo que coincide con el propio estimador no
demuestra que una tarea fuese físicamente inviable. El contraste exige una
observación independiente de ejecución limitada o de capacidad del planificador.

## Correcciones posteriores a las campañas

El código probado está en el commit `9ada336`. Corrige el backend de
proveniencia, los métodos y eventos obligatorios del verificador estricto y
el seguimiento de trabajos propios tras salir de la cola. El historial
experimental conserva sus fuentes exactas y resultados originales.

La validación local posterior obtuvo 543 pruebas aprobadas, 63 opcionales
omitidas y cero fallos; la comprobación de tipos pasó. El seguimiento tiene
20 contratos nuevos y 12 existentes aprobados. El verificador conserva
compatibilidad histórica explícita con ancla externa; los paquetes fallidos
reales se siguen informando como `failed`. Comandos, alcances y registros:
[README de validación](checks/post-campaign-production-20261013/README.md).

La integración posterior en Slurm aprobó 89 comprobaciones independientes:
un recorrido satisfactorio produjo un paquete coherente de 152 archivos y
cuatro tareas nativas completadas; una cancelación deliberada de la tarea
propia 384 conservó `CANCELLED`, `ExitCode 0:9` y un paquete automático
de fallo de 151 archivos. Ambos verificaron por defecto, sin compatibilidad
histórica. Las dos fallas previas del conductor se conservan y la entrada
sintética de ingeniería no aporta etiquetas biológicas ni una tasa R2.4.
[Prueba remota posterior](checks/post-campaign-production-20261013/cloud/README.md).
