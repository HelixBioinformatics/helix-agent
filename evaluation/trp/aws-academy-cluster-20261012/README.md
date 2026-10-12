# Clúster pequeño de AWS Academy

Fecha de preparación y verificación: 12 de octubre de 2026.

El primer Learner Lab contiene un clúster de Slurm con un controlador y dos trabajadores. Los tres nodos se dejaron **detenidos** al finalizar. En el segundo laboratorio se eliminó la instancia `t3.small` autorizada por el usuario y su disco raíz. No se crearon recursos de cómputo adicionales allí.

## Configuración

| Nodo | Instancia | vCPU | RAM | Disco raíz |
| --- | --- | ---: | ---: | ---: |
| helix-head | t3.medium | 2 | 4 GiB | 50 GiB |
| helix-worker1 | m5.large | 2 | 8 GiB | 20 GiB |
| helix-worker2 | m5.large | 2 | 8 GiB | 20 GiB |

Ubuntu 24.04, Slurm 23.11.4, Nextflow 25.10.4 y Docker. `/shared/helix` es una carpeta NFS compartida desde el disco del controlador. Los 50 GiB incluyen el sistema operativo y las cachés. Slurm admite hasta 7400 MiB por trabajador y la partición `helix` limita los trabajos a 20 minutos. La instancia del controlador usa créditos de CPU en modo `standard`.

El acceso SSH permite únicamente la dirección del operador; los nodos se comunican por su grupo de seguridad privado. Se reutiliza `LabInstanceProfile`. Las credenciales, la clave SSH y la clave de MUNGE están fuera del repositorio, en archivos exclusivos del usuario.

## Cuatro horas y reanudación

La documentación del laboratorio indica sesiones de cuatro horas, con renovación mediante **Start Lab**. Se comprobó la renovación: el tiempo restante pasó de `03:23:42` a `03:59:58`; la fecha de fin también se extendió. La evidencia está en [session-renewal.json](session-renewal.json).

Cada nodo tiene un temporizador de apagado a las tres horas desde su arranque. El apagado del sistema operativo está configurado para detener la instancia. Los discos y el estado de Slurm permanecen al detenerla. Academy también detiene EC2 al terminar la sesión y puede volver a encender las instancias al iniciar otra sesión.

La reanudación de los tres nodos se probó: Slurm y Docker volvieron a funcionar, ambos trabajadores ejecutaron un trabajo y el archivo de comprobación persistió. Nextflow reutilizó `SELECT` y volvió a ejecutar `GEOMETRY`; no se afirma que todas las tareas se recuperen de caché. Una tarea interrumpida necesita reejecución, aunque sus insumos y resultados completos se conserven.

Los discos EBS siguen teniendo coste mientras las instancias están detenidas. El indicador de gasto de Academy se actualiza con retraso de 8 a 12 horas, por lo que esta entrega no declara un gasto exacto.

## Uso desde esta computadora

Renovar el acceso temporal, introduciendo la contraseña del portal cuando se solicite:

```bash
UV_NO_PROGRESS=1 uv run --with selenium python script/tesis/aws_academy_access.py --username TU_CORREO_ACADEMY --lab 183928 --renew
```

El script usa la página de Canvas y el botón normal de renovación. No almacena la contraseña. Las credenciales temporales se guardan en `~/.aws/helix-academy-1.credentials` con permisos `0600`. El controlador requiere al menos 30 minutos de sesión restante antes de iniciar nodos.

```bash
UV_NO_PROGRESS=1 uv run --with boto3 python script/tesis/aws_academy_cluster.py start
UV_NO_PROGRESS=1 uv run --with boto3 python script/tesis/aws_academy_cluster.py status
UV_NO_PROGRESS=1 uv run --with boto3 python script/tesis/aws_academy_cluster.py exec 'sinfo -N'
UV_NO_PROGRESS=1 uv run --with boto3 python script/tesis/aws_academy_cluster.py stop
```

Después de `start`, esperar a que los servicios terminen de arrancar antes de enviar trabajos. El operador verifica la cuenta y las etiquetas de propiedad; actualiza las direcciones públicas después de un nuevo arranque. El estado privado está en `~/.local/state/helix/aws-academy/cluster/state.json`.

Antes de detener el clúster, terminar o cancelar los trabajos propios y guardar sus resultados. `stop` detiene las instancias; un trabajo que todavía esté ejecutándose se interrumpe.

El flujo validado permanece en `/shared/helix/helix-controlled-workflow`. Sus archivos y la configuración se conservan también en `controlled-run/`. Para una nueva prueba se debe utilizar una carpeta de resultados nueva; para recuperar la existente se puede usar `-resume`.

## Prueba científica y perfil numérico

Se ejecutaron las dos etapas reales del flujo de GeomeTRe para el caso congelado **2XQH, cadena A**. `SELECT` se ejecutó en el primer trabajador y `GEOMETRY` en el segundo. Se mantuvieron los insumos, las fronteras de unidades y la imagen Docker de la referencia local.

La primera ejecución detectó diferencias en dos unidades y sus agregados. OpenBLAS seleccionaba `Haswell` en la computadora local y `SkylakeX` en AWS. Con `OPENBLAS_CORETYPE=Haswell` y un hilo, la prueba controlada produjo un CSV **idéntico byte por byte** a la referencia local. La variable controla la selección del código numérico de OpenBLAS. [Documentación de OpenBLAS](https://www.openmathlib.org/OpenBLAS/docs/runtime_variables/).

El perfil controlado está en [controlled-run/nextflow.config](controlled-run/nextflow.config), junto con límites explícitos de Docker de 2 vCPU y 2 GiB sin memoria adicional de intercambio. Los valores efectivos se observaron dentro del contenedor en ambos trabajadores. Una cuota de CPU no implica núcleos exclusivos. La prueba cubre el hardware x86_64 evaluado; no demuestra equivalencia de cualquier herramienta o arquitectura.

El CSV tiene 14 filas: 12 filas de unidades, incluida la primera fila de ceros de GeomeTRe, y dos filas de agregados. Su SHA-256 es `7e8393ba3d8cd1035b2e7b8a790fd896f3e8748038c52233e3ae4fc7aff41e0f`. La primera ejecución discrepante permanece en `initial-run/`; no se sustituyó ni se amplió una tolerancia para aceptarla.

Verificar los archivos guardados sin usar AWS:

```bash
python3 script/tesis/verify_aws_academy_evidence.py
```

## Alcance de esta entrega

Se verificaron el clúster, un trabajo en ambos nodos, la persistencia entre arranques, la cancelación de un trabajo en ejecución, los límites de contenedores y un flujo científico fijo.

La integración de la ruta TRP de Helix con la cola de Slurm sigue pendiente: `packages/helix/src/trp/nextflow.ts` genera un ejecutor local. Esta preparación no cierra por sí sola la evaluación completa de ejecución local y en clúster ni la campaña con solicitudes anotadas. Los detalles y las limitaciones están en [report.json](report.json).

Durante el primer arranque se corrigieron la creación del directorio de exportaciones NFS, el nombre del archivo de distribución de Nextflow y la topología de CPU de los trabajadores. Las plantillas del repositorio contienen esas correcciones. La marca de preparación y las comprobaciones reales de servicios se usan para verificar el entorno; el diagnóstico histórico de cloud-init del primer intento no se considera evidencia de un despliegue limpio.
