# Reproducción del perfil Slurm estricto de Helix

Esta receta describe la revisión congelada de la campaña del 13/10/2026.
No ejecuta ninguna operación por sí misma. Una auditoría en frío lee resultados;
una repetición experimental crea asignaciones, trabajos y archivos nuevos.
No se sobrescriben las congelaciones ni los resultados originales.

## Qué se ejecuta y qué se cuenta

El cliente real de Helix se ejecuta en el controlador del clúster. Sus archivos
de entrada, bootstrap, SQLite persistente, estado, caché del cliente, temporales,
trabajo Nextflow y exportación portable solicitada están bajo un único proyecto
XFS. La comparación entre demanda y consumo usa ese mismo conjunto de rutas.
Las tareas científicas siguen ejecutándose en dos trabajadores Slurm reales.

La ruta estricta usa un proceso Python local para controlar Slurm desde el head,
con política del operador. La ruta SSH desde una computadora distinta conserva
su prueba separada de transferencia y confianza SSH; no se le atribuye por
transferencia la cuota agregada de este perfil co-localizado.

El cliente, Python/Nextflow y el trazador comparten un cgroup v2 de 1 CPU,
2 GiB y cero swap. Cada tarea Docker usa 2 CPU, 2 GiB y cero swap; los dos
procesos científicos son secuenciales. Los 3 CPU/4 GiB del presupuesto expresan
controlador más una tarea, no memoria sumada entre trabajadores. Los límites
de ancho de banda de CPU no reservan núcleos exclusivos.

Quedan fuera de `workBytes` las dependencias y código inmutables preinstalados,
la distribución Nextflow y las imágenes/cachés de Docker de infraestructura,
y la telemetría experimental del supervisor root. Esta última conserva las
observaciones sin consumir el espacio de la aplicación que pretende medir.
La copia de conservación del supervisor se hace después de medir; no sustituye
la exportación portable real del cliente. Todas estas exclusiones deben quedar
declaradas en una nueva repetición.

## Fuentes, versiones y condiciones

La lista completa de fuentes y hashes está en
`aggregate-resource-contrasts/source-refresh-final/setup.json`. Los freezes de
`campaign-inputs/` y `boundary-inputs/` fijan módulos, programas, casos, datos,
presupuestos y referencias antes de sus resultados. Usar esa revisión o
registrar otra antes de producir datos nuevos.

| Componente | Perfil comprobado |
|---|---|
| Sistema | Ubuntu 24.04, Linux x86_64 y cgroup v2 |
| Clúster | Slurm 23.11.4, controlador y dos trabajadores |
| Nextflow | 25.10.4, distribución previamente disponible |
| Bun | 1.3.14; binario identificado por hash en setup.json |
| Parser estructural | Gemmi 0.7.5 en entorno Python del operador |
| GeomeTRe | Imagen exacta `sha256:1dd91e70acb153a0bd9a51346fc001dd5025f851c9598697cdd37f07d9490b0a` |
| Cálculo numérico | Haswell, una hebra BLAS, misma imagen y entradas del gold |
| Política | `trp-remote-strict/1.0.0`; backend `trp-slurm-colocated-strict/1.0.0` |
| Contador | `trp-colocated-client-storage/1.0.0`, sobrecarga 32 MiB más términos de copias |

El contador se calibró con un piloto de desarrollo del cliente real. La
subestimación del perfil anterior se conserva en
`calibration-before-final-campaign.json`; cambiar de 12 a 32 MiB no cambió los
umbrales 5%, cero excedencias y 25% de margen mediano. No es una garantía universal
de consumo ni una evaluación reservada de proteínas independientes.

Se requieren Docker y la imagen en ambos trabajadores, NFS del proyecto XFS,
UID no root compatible en los tres nodos, `root_squash`, cuota de proyecto
activa, herramientas XFS y `strace` 6.8. Las rutas del cliente deben tener
herencia del mismo project ID. El checker debe existir, pertenecer a root y
no ser modificable por el cliente. Su hash debe concordar con la fuente
`packages/helix/src/trp/remote_strict.py.txt`.

El operador observa cuenta, saldo informado con su retraso, capacidad por nodo
y ventana de los tres huéspedes antes de iniciar. El límite aplicable es el
mínimo entre Academy y sus temporizadores de arranque. Renovar Academy puede
encender instancias y no amplía por sí mismo un temporizador de huésped.

## Auditoría en frío, sin nube ni modelo

Ejecutar desde la raíz del checkout de la revisión correspondiente. Los comandos
siguen las interfaces realmente existentes; los verificadores anteriores de
evidencia general no certifican por sí solos este perfil.

Para un paquete portable ordinario exitoso, copiarlo a una carpeta nueva y usar
un hash conservado fuera del paquete, por ejemplo el registro del conductor:

```sh
HELIX_REVIEW_TMP=$(mktemp -d /tmp/helix-strict-review.XXXXXX)
cp -a /ruta/paquete/portable-evidence "$HELIX_REVIEW_TMP/portable"
python3 packages/helix/src/trp/verify_bundle.py.txt \
  "$HELIX_REVIEW_TMP/portable" --sha256 HASH_EXTERNO_DEL_MANIFIESTO
```

Este verificador procede del checkout confiable. No se ejecuta arbitrariamente
código de un archivo comprimido. Identificar su propia revisión/hash junto con
el resultado. Una comprobación de integridad no demuestra verdad biológica.

El auditor `audit_cases.py` tiene sólo `--inputs` y `--outcomes`. Escribe
`independent-audit.json` y `summary.json` dentro de outcomes, por lo que se usa
sobre una copia nueva para no sustituir informes conservados:

```sh
HELIX_REVIEW_TMP=$(mktemp -d /tmp/helix-strict-matrix-review.XXXXXX)
cp -a evaluation/trp/campaign-20261012/aggregate-resource-contrasts/campaign-outcomes \
  "$HELIX_REVIEW_TMP/outcomes"
python3 evaluation/trp/campaign-20261012/aggregate-resource-contrasts/audit_cases.py \
  --inputs evaluation/trp/campaign-20261012/aggregate-resource-contrasts/campaign-inputs \
  --outcomes "$HELIX_REVIEW_TMP/outcomes"
```

Repetir la lectura de la cohorte boundary con sus inputs y una copia distinta
de sus outcomes. No mezclar seis sondeos de 39/41 MiB con los cuarenta escenarios
primarios. No se inventa una opción `--output` que este auditor no soporta.

Los archivos tar originales conservan enlaces como metadata. El conductor los
registra y no los sigue al recuperar; su copia local no prueba bloques físicos
del huésped. Para consumo se usan las cuotas/cgroups observados en
`supervision.json`, no `du` de una extracción nueva. Mantener el manifiesto
general con ancla exterior y comprobar todos sus hashes.

No ejecutar `audit_campaign.py`, `run_contract_graphs.ts` o el auditor de matrices
sobre sus salidas originales para una comprobación final: generan archivos y
pueden reemplazar snapshots. Usar una copia/salida nueva, o los verificadores
de lectura mencionados en `final-checks.md`.

## Repetición experimental nueva

Esta sección requiere infraestructura y permisos del operador. No es una
comprobación offline. Conservar claves y credenciales fuera del repositorio.
Los helpers de despliegue actuales se dirigen a Lab2 `185395` y contienen rutas
de la estación del autor; otro entorno necesita una revisión explícita y
congelada de esos parámetros, no una supuesta opción CLI inexistente.

`deploy_runtime.py` prepara código público y puede desplegarlo con `--deploy`.
Antes de usarlo necesita los artefactos locales que realmente lee:

- `/tmp/helix-remote-strict-stage/packages/helix/src/trp/remote_strict.py.txt`,
  con el hash de checker aprobado;
- `/tmp/helix-strict-dependencies.tar.zst`, dependencias inmutables con rutas
  relativas al runtime, y su hash;
- `/home/webiwabou/.bun/bin/bun`, binario identificado por hash.

El archivo de dependencias es de infraestructura y no contiene credenciales.
Si esos archivos ya no existen, reconstruirlos desde la revisión y lockfile
congelados en un entorno limpio y registrar hashes nuevos. No asumir que los
temporales de la estación se distribuyen con Git.

En una infraestructura nueva y sin trabajos propios activos:

```sh
UV_NO_PROGRESS=1 uv run --with boto3 python \
  evaluation/trp/campaign-20261012/aggregate-resource-contrasts/deploy_runtime.py \
  --output /ruta/nueva/runtime-preparado --deploy
```

El helper instala un runtime root-owned y readonly en
`/opt/helix-strict-runtime`, un filesystem XFS separado y NFS para ambos
trabajadores. `guest-init --output RUTA` sólo acepta rutas de infraestructura
nuevas; se niega si el mount/store ya existen. No reformatear el disco de una
campaña conservada para repetirla.

Preparar inputs en una carpeta nueva con el Python Gemmi del operador:

```sh
HELIX_TRP_PYTHON=/ruta/venv-gemmi-0.7.5/bin/python bun \
  evaluation/trp/campaign-20261012/aggregate-resource-contrasts/prepare_cases.ts \
  /ruta/nueva/inputs campaign replica40
```

Los argumentos son posicionales: carpeta, modo y namespace del huésped. El modo
`campaign` usa veinte grafos con dos presupuestos; `smoke` usa uno; `boundary`
usa tres grafos adicionales con 39/41 MiB. El generador comprueba el freeze del
corpus y requiere los golds de las campañas head anteriores. No descarga ni
regenera un gold silenciosamente. Una repetición con otros datos requiere
referencias numéricas propias, mismas unidades e imagen/perfil, fijadas antes.

Verificar code/dependencias/checker desplegados y una ventana nueva antes de
congelar el checkpoint. El driver toma `--inputs`, `--output`, `--namespace` y
`--checkpoint`:

```sh
UV_NO_PROGRESS=1 uv run --with boto3 python \
  evaluation/trp/campaign-20261012/aggregate-resource-contrasts/drive_campaign.py \
  --inputs /ruta/nueva/inputs --output /ruta/nueva/outcomes \
  --namespace ID_DE_PROYECTO_NUEVO --checkpoint FECHA_ISO_UTC_VERIFICADA
```

El namespace numérico debe estar libre para todos los casos. Los outputs,
rutas y comentarios nativos también deben ser nuevos. El checkpoint debe
dejar recuperación antes del mínimo Academy/huéspedes; no copiar literalmente
el checkpoint histórico de 2026. Una respuesta SSH desconocida no autoriza
volver a enviar ciencia. El conductor conserva intención previa al envío,
export-ready, estado nativo y tar crudo; reanudar lectura de un mismo resultado
no equivale a un reenvío.

El supervisor instala el entorno real del cliente dentro de la asignación,
usa un modelo-fixture público para bootstrap sin llamadas al proveedor y
conserva SQLite, incluidos WAL/SHM cuando existan. Los imports iniciales
Global, FSUtil y InstanceBootstrap son secuenciales; después carga los servicios.
No se usa preload de tests, DB en memoria ni bootstrap vacío. La política,
checker, límites, código y datos generados participan en el digest de aprobación
y se comprueban de nuevo. `stageInMode=copy` en la ruta estricta mantiene las
entradas de cada tarea físicamente dentro del proyecto.

## Oráculo y causas, sin inventar etiquetas

Primero se registra la decisión de `R.count/admit` real e inalterada sobre
inventario/política/budget actuales. Sólo el ejecutor contrafactual autorizado
puede continuar tras rechazos exclusivamente de `workBytes` con códigos
`budget-insufficient` o `capacity-insufficient`. Usa `mock.module` en el
conductor de evaluación para omitir esa negativa; no cambia la política,
cuota, cgroup, datos, aprobación ni resultados de la decisión original.
Los casos quedan marcados `executionOracleForcedOnly` y no se presentan como
aceptaciones normales de Helix.

Un contrafactual no acredita que su paquete pasó el verificador ordinary de
admisión. Su comparación requiere el auditor independiente de ejecución y
conserva cualquier fallo del verificador por la negativa original. No se
relaja la comprobación ordinary de los casos realmente admitidos.

La factibilidad exige cuatro tareas nativas completas, CSV igual al gold propio,
cliente/bootstrap/SQLite reales, exportación real y límites observados. Una
etiqueta inviable requiere causa de terminal enlazada por ruta, tiempo y syscall
a EDQUOT, ENOSPC de cuota independientemente cualificado con disco/inodos
globales sanos, o OOM real del cgroup. Un error ignorado de caché, nombre
«small», decisión del admisor o fallo de operador no producen esa etiqueta.
Los desconocidos permanecen desconocidos.

Guardar separadamente primario40, boundary6, pilotos/calibración, fallos previos
y cualquier continuación. Informar denominadores, falsos rechazos, acierto,
excedencias, margen y límites aunque no alcancen la meta. Estas variantes de
una proteína de desarrollo no sustituyen T-LANG, kappa ni validación física.
Tras conservar y verificar evidencias, el operador confirma cero trabajos y
procesos propios, detiene el cómputo y registra almacenamiento residual y saldo
con su retraso. No se elimina la asignación anterior para ocultar un fallo.
