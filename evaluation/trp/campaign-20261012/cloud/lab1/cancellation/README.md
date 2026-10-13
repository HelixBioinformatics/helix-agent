# Cancelación y fallos de configuración en el clúster real

La prueba limpia de cancelación pasó: se observó el trabajo científico `128` como `RUNNING` en `helix-worker2`, se solicitó `Tool.Context.abort` 68 milisegundos después y Slurm lo registró como `CANCELLED`, con código `143:0`. El controlador terminó, no quedaron trabajos propios en la cola y una consulta independiente a Docker devolvió cero contenedores en ese trabajador.

El paquete se generó automáticamente y conserva el evento real `execution.failed-or-rejected`. Superó las seis comprobaciones de auditoría independiente, sin reconstruir eventos ni recuperar manualmente el paquete. El conductor terminó con una prueba aprobada y seis comprobaciones. Este caso es sintético y sus aprobaciones son respuestas de un conductor de ingeniería autorizado, sin anotación experta independiente.

## Intentos anteriores conservados

Antes de la prueba limpia, la limpieza de un trabajo nativo activo quedó observada: Slurm registró el trabajo `24`, operación `GEOMETRY`, como `RUNNING` y después como `CANCELLED`, con código `143:0`. La solicitud de cancelación de Helix identifica el fallo de una consulta SSH de seguimiento, código `255`. El controlador terminó como `cancelled`, no quedaron trabajos de esa ejecución en la cola y una consulta posterior a Docker en el trabajador devolvió cero contenedores.

Esta evidencia prueba la limpieza del trabajo ante la pérdida de seguimiento. El conductor de la prueba tuvo problemas de temporización y no terminó como una prueba automatizada aprobada. Las respuestas de aprobación fueron entradas de un conductor de ingeniería autorizado, sin anotación humana independiente.

## Evidencias conservadas

| Carpeta | Observación | Interpretación |
| --- | --- | --- |
| `next-ctx-abort/` | Tarea científica `128` observada como `RUNNING`; señal real `Tool.Context.abort`; estado nativo `CANCELLED`; empaquetado automático y auditoría completos. | Prueba automatizada aprobada, con limpieza confirmada y sin evidencia biológica. |
| `invalid-partition/` | Una consulta SSH real a una partición Slurm inexistente produjo una negativa tipada durante la preparación. | No se solicitó aprobación ni se enviaron tareas científicas. |
| `driver-error-no-submit/` | El primer conductor no exponía directamente el servicio de procesos que necesitaba. | Error del conductor después de preparar la propuesta, antes de enviar trabajos. |
| `fast-stub-timing-race/` | Se observó el trabajo `20` como `RUNNING`; la señal `Tool.Context.abort` interrumpió el flujo y el controlador. El trabajo corto ya había terminado como `COMPLETED` cuando se consultó de nuevo. | No demuestra que ese trabajo nativo fuera cancelado. La prueba mantuvo una comprobación estricta y falló ante ese resultado. |
| `running-job/` | Un trabajo científico más largo terminó como `CANCELLED` después del fallo de seguimiento SSH. Se recuperaron los artefactos de esa misma ejecución detenida. | Demuestra limpieza nativa real. El observador de 60 segundos expiró antes de comenzar la tarea científica y el límite de 180 segundos terminó el conductor. No se afirma que el conductor pasara. |

## Alcance del caso más largo

`running-job/synthetic-source.pdb` contiene un caso de ingeniería determinista con 1000 unidades de seis posiciones C-alfa. Sus coordenadas se obtuvieron mediante transformaciones de las primeras seis posiciones de 2XQH/A. El identificador `0syn` no representa una entrada real del PDB. Los campos experimentales del archivo emulan el contrato de desplazamiento atómico que admite esta ruta; los comentarios del propio archivo declaran que no se trata de una estructura experimental.

El caso amplía el intervalo de ejecución para observar la cancelación. No constituye un ejemplo biológico independiente, una referencia de exactitud estructural ni un control para estimar sensibilidad o especificidad. La implementación, la imagen y los límites de recursos de las tareas permanecieron iguales a los del flujo aprobado.

## Recuperación y verificación

El conductor terminó antes de completar el empaquetado local. La recuperación conservó los archivos aprobados, la cadena de eventos ya registrada, las entradas, las consultas y los archivos del controlador remoto. `run/recovery.json` distingue esa recuperación del empaquetado automático. No se volvió a enviar el trabajo para obtener un resultado más favorable.

```bash
python3 running-job/evidence/verify.py running-job/evidence \
  --sha256 82ba85307d7efdae574be1506c7e7a7ef380714b8c5cb5b5ec68b4643741961c
```

El paquete verifica 145 archivos y registra estado `failed`, sin resultado científico completado. Las consultas nativas y la solicitud de cancelación están dentro del paquete; las observaciones y limitaciones del conductor están junto a él. La reconstrucción de una consulta SSH independiente está declarada expresamente en `independent-running-observation.json` y no atribuye una hora UTC que la consulta original no imprimió.

El conductor actualizado en `packages/helix/test/trp/remote-cancellation.live.test.ts` dispone de más tiempo para observar la fase científica. La prueba limpia posterior está conservada en `next-ctx-abort/`, con el fixture prospectivo y el snapshot de fuentes previos a la ejecución.

## Paquete de la prueba limpia

`next-ctx-abort/driver-terminal.json` enlaza por hash el snapshot de fuentes, el fixture, las observaciones nativas antes y después, la solicitud de interrupción, el registro del conductor y la lectura de contenedores. El manifiesto automático contiene 143 archivos y tiene SHA-256 `62cf9fba9e9a2e23cb4e4e55f30bd50a36000976c438b8d4387d7468a7b735e6`. La auditoría está en `../../../trace/running-cancellation-clean.json`.

El flujo interrumpido registra estado `failed`; el resultado aprobado corresponde al ensayo de cancelación y limpieza, no a un análisis científico completado. El trabajo nativo duró tres segundos antes de terminar.
