# Encargo de anotación externa — instrumento preparado

Identificadores actualizados al 23/09/2026: tres objetivos y 21 resultados. Las evidencias fechadas conservan su numeración original; consulte [equivalencias](../../docs/tesis/renumeracion-20260923/README.md).

**Actualización operativa del 30/09/2026.** El tesista designa a su asesora como experta responsable. Informa que no participó en el desarrollo y que solo revisó parte del informe; la relación académica y exposición previa se declararán. La asesora consideró comprensible el piloto, según el tesista. La primera entrega de evaluación real está en [evaluacion.xlsx](../../docs/tesis/evaluacion-experta-20260930/para-asesora/evaluacion.xlsx), acompañada de datos públicos. Contiene borradores de solicitudes asistidos por IA y campos vacíos para referencias y paráfrasis humanas. Todavía no hay etiquetas externas recibidas ni consentimiento firmado atribuido a la participante. No se repite la búsqueda de otra persona como condición de inicio; se conserva el registro de su participación.

## Perfil y material

Se requiere una persona ajena al desarrollo, con experiencia en estructuras de proteínas y lectura de procedimientos bioinformáticos. Registrar seudónimo, experiencia relevante, relación con el proyecto, versión de guía, fecha y conflictos declarados. El objetivo es evaluar especificaciones y turnos con contexto, no favorecer una variante del sistema.

Entregar: solicitudes, datos necesarios para resolverlas, catálogo congelado, definiciones de marcos y escalas, especificaciones en orden aleatorio y sesiones con contexto hasta el turno anotado. Ocultar predicciones automáticas, variante del sistema y resultados de otras personas. No entregar credenciales ni mensajes personales ajenos al estudio.

## A. Admisibilidad y equivalencia de especificaciones (R1.3)

Evaluar cada original y paráfrasis de forma independiente. Una especificación es admisible si conserva el objetivo, identifica entradas y proteína/cadena, declara marco de residuos y confianza cuando corresponden, usa operaciones disponibles, fija parámetros requeridos con procedencia y puede ejecutarse dentro del alcance. Una aprobación del usuario no corrige un error biológico.

Registrar `admissible`, `inadmissible` o `not_evaluable`, campos que sustentan el juicio y una explicación breve. La ausencia de un dato necesario no se resuelve adivinando. Para equivalencia comparar objetivo, entradas, operaciones, parámetros, marcos y producto previsto después de evaluar ambas especificaciones; variaciones de redacción u orden sin efecto no las hacen distintas. Dos especificaciones incompletas no forman un par estable.

## B. Intervenciones humanas (R3.3)

Unidad: un turno humano completo, junto a los mensajes previos necesarios. No partir un turno en varias observaciones. Aplicar una clase principal y conservar posibles clases secundarias en la explicación:

| Clase              | Criterio                                                       | Ejemplo de desarrollo, redactado por el investigador |
| ------------------ | -------------------------------------------------------------- | ---------------------------------------------------- |
| factual-correction | Corrige un hecho, valor o afirmación errónea del sistema       | «La cadena es B; A pertenece a otra proteína.»       |
| rejection          | Niega o detiene una acción propuesta                           | «No ejecutes esa descarga.»                          |
| redirection        | Cambia el objetivo o método deseado                            | «Ahora compara las unidades con otra métrica.»       |
| disambiguation     | Resuelve una ambigüedad sin corregir un error previo           | «Me refiero al segundo dominio.»                     |
| approval           | Autoriza una propuesta concreta con suficiente contexto        | «Apruebo esa especificación y sus parámetros.»       |
| other              | No hay una intervención de las clases anteriores identificable | «Gracias.»                                           |

Precedencia cuando coexisten clases: corrección factual, rechazo, redirección, desambiguación, aprobación. `other` no significa ausencia absoluta de intervención; significa que la guía no identifica una de sus categorías. «Continúa» solo es aprobación si el contexto identifica inequívocamente la propuesta autorizada; el anotador puede disentir de las reglas automáticas basadas en palabras.

## Flujo y control de independencia

1. Revisar guía y ejemplos D-LANG/D-TURNS; discutir ambigüedades antes de congelar la guía. Los ejemplos son del investigador y no entran en el kappa final.
2. Confirmar disponibilidad y acuerdo de uso de las etiquetas; registrar la asignación del conjunto reservado antes de clasificarlo automáticamente.
3. Anotar de forma independiente y guardar la primera entrega inmutable con fecha y hash. No mostrar etiquetas del clasificador durante esta tarea.
4. Calcular acuerdo con la primera entrega. Conservar desacuerdos; cualquier adjudicación posterior tiene otro archivo y no reemplaza retroactivamente el kappa.
5. Reportar tiempo, omisiones, casos no evaluables y distribución de clases. Si no se cuenta con participante externo, R1.3 y R3.3 siguen pendientes de validación externa.

La plantilla JSONL contiene un esquema de fila, no una anotación: todos los campos de participante, fecha y juicio están vacíos. Para intercambio tabular se puede exportar la misma estructura conservando identificadores y hashes.
