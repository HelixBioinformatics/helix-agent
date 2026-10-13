# Contraste prospectivo de admisión y ejecución limitada

Este procedimiento no inicia instancias ni trabajos al preparar el plan. El
operador lo ejecuta después de terminar el lote positivo de Lab2. No modifica
el montaje ni los datos de `/shared/helix`.

## Alcance y decisión

Se toman los primeros veinte grafos válidos del corpus congelado, sin escoger
los que mejor funcionaron. Cada uno tiene dos escenarios nuevos: 64 MiB y un
límite escalonado de 64 KiB a 16 MiB. Todos conservan tres CPU de presupuesto,
4 GiB de memoria, 1080 segundos, imagen exacta y perfil Haswell con una hebra.
Los nombres de cohorte expresan una expectativa de diseño, no una etiqueta.
Las cuarenta etiquetas físicas empiezan como `null`.

El admisor real de producción emite su decisión con un inventario nuevo. El
oráculo independiente ejecuta aun los casos rechazados, con un controlador
limitado a una CPU y 2 GiB y tareas Docker de dos CPU y 2 GiB sobre Slurm. Una
cuota XFS de proyecto limita entradas, trabajo, logs y una copia materializada
del recorrido. El CSV debe coincidir con su comparador de las mismas unidades.

**Adaptación explícita:** se mide un proyecto de trabajo en el controlador,
incluida una copia portable allí materializada. El presupuesto de Helix también
considera copias de preparación y exportación del cliente real, ubicadas en
otra máquina en la ruta habitual. Esta prueba no limita esos bytes del cliente
real y no completa la cota agregada de R2.2 ni la evaluación integral reservada
de R2.4. Se publica como matriz de desarrollo para ese alcance de trabajo. Un
falso rechazo puede reflejar, además del estimador conservador, esa diferencia
de alcance; debe conservarse y explicarse, no presentarse como un error puro
del estimador sobre una unidad idéntica de extremo a extremo.

Una falta de espacio observada durante el copiado es inviabilidad concreta de
transferencia al proyecto, no una excepción del validador. Un fallo desconocido,
un error de operador o falta de evidencia cgroup mantiene etiqueta `null`.
La presencia de veinte casos por cohorte no demuestra veinte factibles y veinte
inviables: los tamaños mínimos se contrastan después de observar los cuarenta.

## Preparación local sin trabajos AWS

Con el mismo archivo privado de destino verificado para Lab2, después de fijar
la revisión de producción y sus fechas de apagado:

```bash
HELIX_TRP_REMOTE=/ruta/privada/lab2-remote.json bun evaluation/trp/campaign-20261012/trace/prepare_r24_resource_cases.ts /ruta/nueva/r24-inputs
```

El generador obtiene veinte comparadores Docker locales, fija cuarenta paquetes,
sus hashes y las fuentes, y escribe `freeze.json` antes de medir la factibilidad.
Los comentarios Slurm son diferentes por caso. No se reasignan casos tras
observar resultados. Transferir después el paquete y este runner al controlador.

## Montaje aislado, solo después del lote positivo

El operador verifica previamente cero trabajos propios activos en Lab2. Los
siguientes comandos se adaptan a sus dos IP privadas observadas; no se sustituye
el export existente. `/shared/helix-r24` tiene que estar libre en los tres nodos.
Los comandos son una instrucción de preparación, no evidencia de instalación.

Controlador:

```bash
sudo apt-get install -y xfsprogs
sudo install -d -m 0755 /srv/helix-r24-store /shared/helix-r24
sudo fallocate -l 2G /srv/helix-r24-store/disk.img
sudo chmod 0600 /srv/helix-r24-store/disk.img
sudo mkfs.xfs -f -q /srv/helix-r24-store/disk.img
sudo mount -o loop,prjquota,allocsize=4k /srv/helix-r24-store/disk.img /shared/helix-r24
sudo exportfs -o rw,sync,no_subtree_check,root_squash WORKER1_PRIVATE_IP:/shared/helix-r24
sudo exportfs -o rw,sync,no_subtree_check,root_squash WORKER2_PRIVATE_IP:/shared/helix-r24
sudo xfs_quota -x -c 'state -p' /shared/helix-r24
```

Cada trabajador:

```bash
sudo install -d -m 0755 /shared/helix-r24
sudo mount -t nfs4 HEAD_PRIVATE_IP:/shared/helix-r24 /shared/helix-r24
findmnt -n -T /shared/helix-r24
```

El operador comprueba escritura de Ubuntu en un subdirectorio nuevo y el mismo
archivo/hash en los tres nodos, `root_squash` activo, Nextflow 25.10.4 disponible,
la imagen exacta en ambos trabajadores y los temporizadores de los tres nodos.
Se mantiene el disco dentro del volumen existente; no requiere otra EC2 ni EBS.

## Una decisión y una ejecución por escenario

Antes de cada caso se obtiene la observación real mediante el observador remoto
de producción. Se archiva fuera de la cuota junto con el plan y la decisión:

```bash
bun evaluation/trp/campaign-20261012/trace/decide_r24_resource_case.ts /ruta/r24-inputs/freeze.json R24-1-generous /ruta/observacion-nueva.json > /ruta/decision-R24-1-generous.json
```

En el controlador:

```bash
sudo python3 /ruta/run_r24_independent.py --package /ruta/r24-inputs --case R24-1-generous --mount /shared/helix-r24 --output /ruta/nueva/salidas/R24-1-generous --decision /ruta/decision-R24-1-generous.json
```

El supervisor observa límites, quota y nativos, conserva logs y limpia solamente
el servicio y trabajos del comentario de ese caso. No vuelve a enviarlos.
Todos los resultados, incluso los desconocidos, se conservan con el ID inicial.
El checkpoint global es 02:59 UTC del 13 de octubre, con veinte minutos antes
del límite de huésped observado. Al llegar al checkpoint se limpia el caso
actual y se registran los casos sin iniciar; no se etiqueta su factibilidad.
Una continuación necesita una enmienda prospectiva y renovación/reinicio por
mecanismos oficiales, conservando el lote inicial y sin duplicar casos únicos.

## Reporte

Calcular la matriz solo sobre etiquetas empíricas `true`/`false`; informar también
cuarenta casos previstos, iniciados, terminados, desconocidos y sin iniciar.
Falso rechazo = rechazos del admisor entre todos los factibles observados. Acierto
= decisiones que concuerdan con la etiqueta de ese alcance / casos evaluables.
Se mantienen 5% y cero excedencias como metas del protocolo, sin bajar el umbral
si aparecen falsos rechazos. Comparar bloques XFS con bloques XFS, nunca sumar
bytes lógicos del manifiesto como si fuesen el máximo físico observado.

Estimación operativa: 45 a 90 minutos en el clúster existente, 2,25 a 4,5 horas
de VM sumadas, cero llamadas pagadas al modelo y cero instancias nuevas. Es una
previsión, no un tiempo o consumo de créditos ya medido.

La cuota por árbol se apoya en la [documentación de XFS de Red Hat](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/7/html/storage_administration_guide/xfsquota).
Los límites del controlador usan propiedades de systemd que el supervisor
contrasta de nuevo en cgroup v2; la mera existencia del comando no se reporta
como un límite efectivo ya comprobado.
