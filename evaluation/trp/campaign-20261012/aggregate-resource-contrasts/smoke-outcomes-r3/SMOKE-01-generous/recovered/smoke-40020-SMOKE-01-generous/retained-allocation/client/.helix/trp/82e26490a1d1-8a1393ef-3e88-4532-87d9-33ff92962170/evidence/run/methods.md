# Métodos de la ejecución registrada

Se procesó 2xqh, cadena autora A, modelo 1, con 3 unidades suministradas. La entrada se identifica mediante SHA-256 f674267d0ef4752a3d4da00497947bfc09f441a5c36d39593b72bc2ba390df0b.

El adaptador trp-nextflow/1.4.0 generó la orden ["nextflow","-C","nextflow.config","run","main.nf","-ansi-log","false","-with-trace","trace.tsv"] y fijó la imagen sha256:1dd91e70acb153a0bd9a51346fc001dd5025f851c9598697cdd37f07d9490b0a. La revisión de GeomeTRe es 8bb0c50bb0bf73c16cc22e7bd4e3991a326841c9; su contrato de parámetros es ["chain","units","insertions (optional)","window=6 (upstream default; no CLI override)"]. Se planificaron dos tareas simuladas y dos reales, sin reintentos; tareas científicas en infraestructura remota: 2. Estado registrado: failed.

No se dispone de una consulta de versión de Nextflow completada correctamente.

La reserva estimada de almacenamiento fue 21295104 bytes. Los campos y sus fuentes se encuentran en methods.json; el inventario, el presupuesto, las decisiones y los eventos se conservan en archivos separados.

- Author-PDB numbering; supplied units, not repeat detection; experimental B-factor is not pLDDT.
- The real Helix client runs on the verified head. Local Python transport invokes the controller; Slurm executes worker jobs. This is not an SSH transport experiment.
- Root-owned policy and kernel receipts bind one XFS project quota covering declared client work/temp/state/cache/export and NFS remote work. Real Helix and Python/Nextflow share 1 CPU/2 GiB/swap-zero controller cgroup; sequential worker containers use 2 CPU/2 GiB. Root sampler records current usage separately from total-run entitlement. Preloaded read-only software/image caches and external root-supervisor records are infrastructure outside workBytes.
- Offline verification checks bytes and declared links, not scientific truth or an authenticated human identity.
- Agent provider/model/cost are not observed by this workflow; task software is identified by the pinned catalogue reference and image.
