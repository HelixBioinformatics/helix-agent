# Integración remota después de las correcciones de producción

## Resultado y alcance

`summary.json` y `audit_integration.py` contienen 89 comprobaciones independientes. Se verificaron dos nuevas sesiones con el cliente real de Helix, SQLite persistente, aprobación sintética por Question.Service, controles efectivos del perfil estricto y tareas Slurm reales. El verificador frío por defecto se ejecutó sin la opción de compatibilidad histórica.

El positivo POST-01 usa G-valid-048. Sus cuatro tareas nativas 377, 378, 379 y 380 terminaron COMPLETED; el CSV coincide con el gold congelado de esa entrada. El paquete exportado contiene 152 archivos. La declaración de backend es consistente entre ejecución, registro de Run y evento de finalización.

El negativo POST-04 usa un fixture de ingeniería previamente validado: 1000 transformaciones de seis coordenadas CA, 6000 átomos CA. No representa una estructura experimental ni tiene gold biológico. Después de preparación, aprobación y admisión científica reales, el observador corroboró RUNNING del GEOMETRY 384 y envió un único scancel sobre ese ID y comentario exacto. Una observación independiente posterior confirmó CANCELLED, ExitCode 0:9. El ledger de producción retuvo el estado terminal cuando el trabajo dejó de estar en la cola. Helix generó automáticamente el paquete de fallo con 151 archivos; ese paquete pasa el verificador frío por defecto.

El observador rápido tuvo 80 consultas y sólo alcanzó COMPLETING. Sus datos originales se conservaron. La confirmación CANCELLED procede de `native-terminal-live-observation.json` y del ledger de producción, sin reescribir el observador. La diferencia entre el timestamp del pedido y el de la primera observación terminal de producción fue 30418,009 ms. Es un intervalo observado de este caso, no una latencia interna del scheduler, un máximo ni un P95.

`post-quiescence.json`, observado el 13 de octubre de 2026 a las 17:43:06 UTC, confirma lectura independiente de los tres nodos: cola vacía, contenedores vacíos, procesos propios terminados y cgroups de controlador sin procesos. No se ejecutaron acciones de ciclo de vida AWS desde este harness; el agente principal es responsable de detener las instancias.

## Intentos de harness preservados

1. POST-02 falló antes de lanzar el cliente. El observador creó el directorio que el supervisor requería crear de forma exclusiva. Se preservaron el FileExistsError, la ausencia de entrada del cliente y la cola vacía. No se sometieron tareas nativas ni se evaluó una cancelación.
2. POST-03 completó la preparación, pero el harness intentó interpretar como JSON la salida visual truncada de Prepare. Se preservaron la excepción, los artefactos durables y la ausencia de Run, aprobación y tareas nativas.
3. Antes de POST-04, `offline-large-prepare.json` verificó el retorno metadata y la lectura de artefactos durables en una preparación real de las 1000 unidades. No invocó Run, AWS ni un modelo. Una instalación de dependencia en segundo plano produjo posteriormente un 404 de NPM; no se afirma ausencia total de tráfico de red.
4. POST-04 tiene una congelación y namespace nuevos. El frontend valida id/digest y lee admission.json, budget.json y run.json de la carpeta durable correspondiente. Conserva los servicios reales y la aprobación normal; no cambia Truncate, el productor, el presupuesto ni el conjunto científico.

Cada lanzamiento tiene un intento escrito antes de despachar. No hubo reenvío por timeout de transporte. El conductor inicial se cerró localmente sólo después de comprobar ausencia de trabajo del huésped; los intentos terminales no se reutilizaron.

## Recursos y procedencia

El cliente y controlador co-localizados comparten un cgroup de 1 CPU y 2 GiB, swap cero. Cada tarea de trabajador dispone de 2 CPU y 2 GiB, swap cero, sin sumar memoria entre nodos para una tarea. Las rutas declaradas de cliente, SQLite, estado, cache, temporales, exportación y ejecución remota heredan una misma cuota XFS por proyecto de 128 MiB. La imagen, las dependencias públicas instaladas y los caches comunes de infraestructura quedan fuera de ese presupuesto, tal como declara el perfil.

Se restauró el mismo filesystem XFS, UUID cd26a20b-f8e0-480a-9640-38e1b93e7fff, con fsid NFS 43 estable y root_squash. No se formateó, reinició la cuota ni alteró la campaña original. El preflight operativo verificó NFS y el Docker fijado en ambos trabajadores mediante tareas 375 y 376, sin integrarlas en las métricas de evaluación.

Las congelaciones y overlays guardan las fuentes y hashes. El runtime nuevo contiene las correcciones aprobadas de backend, semántica del verificador y ledger nativo. No se copiaron credenciales del modelo ni de AWS; el archivo SDK modificado por el usuario no se tocó ni se incluyó como fuente nueva.

## Límites

Estos contrastes demuestran integración y manejo de un fallo inducido sobre un trabajo propio. No añaden observaciones al conjunto original de 50 contrastes de recursos, no modifican la calibración ni los umbrales, y no completan las métricas científicas reservadas, kappa o validez física. Las 70 solicitudes reservadas siguen requiriendo la anotación independiente.

## Reproducción y revisión

Desde la raíz del repositorio:

```bash
python evaluation/trp/campaign-20261012/checks/post-campaign-production-20261013/cloud/audit_integration.py
```

Esta auditoría opera sobre los artefactos recuperados y la fuente confiable fijada del verificador, sin llamadas AWS. `observe_quiescence.py` realizó la observación independiente en vivo; su resultado se revisa desde el archivo conservado, sin repetir esa consulta después de detener las instancias.
