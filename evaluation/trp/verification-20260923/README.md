# Helix: segunda estación, 23 de septiembre de 2026

`output/summary.json` registra nueve comprobaciones: siete salidas correctas y dos rechazos esperados (alteración de corpus y de paquete portable). El CSV de GeomeTRe conserva exactamente los bytes de la referencia 2xqh/A de doce unidades. El verificador independiente acepta los 139 archivos íntegros contra el hash registrado fuera del paquete. Esta transferencia y repetición son desarrollo, no corpus reservado.

Binario remoto: Helix 0.3.0, instalado en `~/.helix/bin/helix`. Nextflow 26.04.4 estaba en `~/.local/bin/nextflow`; ambas carpetas deben añadirse al PATH de sesiones SSH no interactivas. El ensayo utiliza rutas explícitas y no cambia el perfil de inicio del usuario.

El instalador oficial conservó la misma versión sin reinstalar ni desinstalar. Esto verifica idempotencia, no una actualización entre versiones distintas. La nueva orden `helix upgrade` se valida en el código fuente de esta entrega; no pertenece todavía al binario publicado 0.3.0.

El contenedor científico, con SHA fijado, tuvo dos CPU y 2 GiB, sin red. Esta ejecución no tiene cuota dura de almacenamiento y no acredita recursos de clúster. El corpus mínimo del ensayo CLI es sintético y solo prueba integridad. No se ejecutaron llamadas a LLM.
