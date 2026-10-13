# Referencia remota con mapeo SIFTS

La ejecución real de desarrollo con 2XQH, su mmCIF archivado y el XML SIFTS para Q9MCI8 pasó por las herramientas `trp_prepare` y `trp_run`. El CSV coincide byte por byte con la referencia fija de GeomeTRe para las 12 unidades. No es un conjunto reservado ni una evaluación de anotación humana.

El ensayo terminó con una prueba aprobada y tres comprobaciones. Las cuatro tareas nativas Slurm, dos stub y dos científicas, fueron 137, 138, 139 y 140 en los dos trabajadores. La imagen exacta y el perfil numérico Haswell constan dentro del paquete aprobado.

## Evidencia y portabilidad

El paquete automático contiene 156 archivos y 5748810 bytes declarados. Su manifiesto tiene SHA-256 `b400c54428684c5d1f767324154388f906f466c849736bf28394241fabed80aa`. La auditoría superó nueve comprobaciones y detectó las 320 alteraciones de ingeniería introducidas sobre copias locales. Una copia fuera del repositorio también se verificó desde un directorio externo, con el verificador copiado previamente comprobado contra la fuente de confianza. No se volvió a ejecutar ciencia para esas comprobaciones.

`driver-terminal.json` enlaza por hash la congelación de 36 fuentes y entradas, los registros, las auditorías y los tamaños finales. El protocolo prospectivo permanece conservado; el resumen aclara las observaciones de memoria por tarea disponibles después de la ejecución.

## Alcance de las observaciones de recursos

Los registros capturan límites efectivos Docker de 2 CPU, 2 GiB y cero swap por tarea científica. No prueban una reserva exclusiva de núcleos, un límite duro del controlador ni una cuota global de disco.

Nextflow reportó 11.7 MB de peak RSS para SELECT y 188.6 MB para GEOMETRY. Son métricas instrumentadas de un árbol de procesos, cuyo wrapper suma VmRSS y VmHWM muestreados en `/proc`; no representan un pico independiente de RAM física única ni del cliente, controlador o clúster completos. El tiempo del comando fue 173 ms y 2.6 s, respectivamente; Slurm registró cero y tres segundos de duración nativa, con resolución de segundos.

La carpeta archivada en el cliente contiene 7882950 bytes regulares, incluida su copia portable, y ocupa 8417280 bytes asignados. La carpeta final del flujo en el head contiene 4331885 bytes regulares y ocupa 4792320 bytes asignados. Esos tamaños finales excluyen cachés compartidas y otras ejecuciones; no son picos de almacenamiento ni cuotas.
