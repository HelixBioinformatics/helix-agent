# Cierre de la campaña AWS de Helix

Se completó la campaña técnica viable con las dos cuentas disponibles. No se
necesitan más laboratorios ahora. Las mediciones científicas obligatorias
siguen pendientes y no se declara terminada la tesis ni validados sus 21
resultados. [Registro completo y hashes](ENTREGA-AWS-20261013.json).

## Resultado entregado

- Correcciones de backend, verificación de métodos/eventos y seguimiento
  persistente de trabajos Slurm: `9ada336`. Preparación Academy: `0dcb38a`.
- Regresión local: 543 pruebas aprobadas, 63 opcionales omitidas y cero fallos;
  tipos correctos. Integración posterior: 89 comprobaciones independientes,
  un paquete satisfactorio de 152 archivos y uno de fallo de 151 archivos.
  La tarea propia 384 quedó CANCELLED con ExitCode 0:9 y el registro terminal
  persistió tras salir de la cola. Se conservan los errores previos.
- Word y PDF instalados: 155 páginas, 261 comprobaciones de render y revisión
  visual. Se preservan los capítulos 1 a 3, las referencias e imágenes
  originales. Resultados, conclusiones, figuras y anexo A.25 actualizados.
  [Instalación](../../evaluation/trp/campaign-20261012/document/installation.json).
- Seis instancias detenidas por comprobación SDK. Cada cuenta conserva
  90 GiB en tres discos; detener las instancias no elimina ese almacenamiento.
- Datos completos preservados y extraídos en un destino nuevo para verificar
  cada hash: 43.979 archivos de campaña, más un artefacto científico de 299
  fuentes y una copia externa del Word de entrada y los documentos entregados.
  Son artefactos privados locales, fuera de Git. Las rutas y anclas están
  en el registro JSON.

La selección de Git contiene 32.147 archivos de evidencia legible: 32.139
revisados y ocho archivos de cierre comprobados por separado. Cada blob del
índice coincide con la fuente y el archivo privado verificado. Los 76 JSON
con coordenadas derivadas privadas siguen intactos fuera de Git. La revisión
cubre los patrones y linajes declarados; no afirma detectar cualquier secreto
o transformación arbitraria de coordenadas.

## Resultado que no alcanza la meta

R2.4 conserva **tres falsos rechazos entre seis casos factibles de frontera**,
50%, frente al máximo de 5%. Los cuarenta casos originales tienen 18 factibles,
18 inviables y cuatro desconocidos. El suplemento separado permite alcanzar
veinte por clase sólo en la unión de 44 casos. No se rebajaron umbrales ni se
reescribieron las decisiones para dar por cumplido ese resultado.

## Continuación

1. Mejorar el estimador con un protocolo nuevo y congelado antes de ejecutar;
   conservar esta campaña y su incumplimiento.
2. Recibir las referencias de la asesora y sus paráfrasis, congelar la reserva
   y evaluar solicitudes lingüísticas.
3. Registrar sesiones humanas reales y recibir al menos cien primeras
   etiquetas ciegas de turnos antes de calcular kappa.
4. Validar una regla física y etiquetas pertinentes antes de sensibilidad y
   especificidad. Las estructuras experimentales repetitivas no son negativos
   físicos certificados.

El perfil geométrico co-localizado es el que tiene cuota conjunta verificada.
Las rutas dedicadas de detección y modelos predichos, y los contratos
ReUPred/RepeatsDB restantes, mantienen los límites documentados. No existe una
exigencia P95 en las 21 métricas actuales ni un P95 medido.

## Restauración

El archivo de campaña por sí solo no contiene los 108 insumos originales del
estudio estructural. Se requiere además el artefacto científico. La guía
externa `RESTORE.md`, anclada en el registro JSON, describe extracción en un
directorio nuevo y comprobación de cada miembro. Los lotes estructurales leen
rutas absolutas congeladas; `score-one` permite una entrada reubicada y una
salida nueva con el entorno declarado.

El primer empaquetado se conserva como fallo: 57 rutas compartían enlaces
físicos y la biblioteca tar intentaba representarlos como enlaces. La fuente
corregida y validada está en
[package_private_delivery.py](../../script/tesis/package_private_delivery.py).
Conserva los bytes completos de cada ruta como archivo regular; no conserva
la unión entre inodos. La campaña congelada no se modificó y el segundo
archivo pasó extracción, hashes y permisos. Esta reparación de transporte
no alteró mediciones, software experimental ni Word.
