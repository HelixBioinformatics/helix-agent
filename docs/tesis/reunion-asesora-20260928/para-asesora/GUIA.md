# Guía de anotación — reunión y piloto
Versión de trabajo: piloto-2026-09-28. Instrumento auxiliar de ANNOTATION.md y protocolo TRP 1.0.1. Los criterios se discutirán antes de congelar la reserva. No sustituye una evaluación realizada.

## 1. Roles e independencia
La asesora ha sido propuesta por el tesista; aún no se presume aceptación ni fecha. Puede coordinar el reclutamiento, revisar la guía y participar en el piloto. Para la reserva se prefiere un especialista que no haya desarrollado el sistema ni visto sus respuestas o las etiquetas automáticas. Si anota la asesora, declarar su relación académica y su participación en diseño/criterios; describir independencia del desarrollo y cegamiento, sin afirmar independencia institucional. Una segunda persona puede resolver discrepancias después de conservar la primera entrega; no es requisito añadido de dos anotadores para el kappa sistema-humano de R3.3.

## 2. Lo que debe hacer en Referencia (R1.3)
Leer la solicitud y la ficha de alcance. Completar el objetivo esperado, entradas y cadena, operaciones admisibles, numeración de residuos, confianza, parámetros, salida esperada y datos que exigiría aclarar. En factibilidad elegir factible, requiere_aclaracion, fuera_de_alcance o no_evaluable. No escribir comandos ni JSON. Si falta algo, describirlo; no adivinar una cadena ni aceptar por omisión un cambio de proteína. Si varias soluciones son válidas, declararlas. Registrar motivo y minutos. Las referencias se elaboran sin ver salidas de Helix.

Los datos del piloto están en datos/. 2xqh/A y AF-P69905-F1 son casos de desarrollo previamente usados: NO integran la reserva. Las unidades suministradas son entradas de prueba, no etiquetas humanas de repetición; en el ejemplo AFDB son segmentos artificiales de hemoglobina. El objetivo es juzgar la interpretación y las condiciones de ejecución, no certificar plausibilidad física.

## 3. Lo que debe hacer en Turnos (R3.3)
Leer el contexto previo y el turno humano completo. Seleccionar una clase principal:
- factual-correction: corrige un hecho, dato o afirmación errónea previa.
- rejection: niega o detiene una acción propuesta.
- redirection: cambia el objetivo o método deseado.
- disambiguation: resuelve una ambigüedad sin corregir un error previo.
- approval: autoriza una propuesta concreta identificable en el contexto.
- other: no se identifica ninguna de las clases anteriores.
Si coexisten, precedencia: factual-correction, rejection, redirection, disambiguation, approval, other. Puede anotar clases secundarias en la justificación. Si no hay contexto suficiente, marcar evaluable=no y dejar clase vacía con el motivo; no forzar other. “Continúa” no es aprobación sin una propuesta inequívoca. Evaluar el turno, no la simpatía o extensión de la respuesta.

## 4. Etapa posterior: evaluar las salidas
Tras cerrar las referencias, el coordinador entregará las especificaciones con identificadores neutros, datos y contexto. Ocultará modelo, variante, predicciones automáticas y respuestas de otros anotadores. La planilla Juicios está vacía porque todavía no se han generado/asignado salidas reservadas.

Una especificación admisible conserva objetivo y entradas, identidad/cadena, operaciones disponibles, marcos, escala de confianza, parámetros y procedencia requerida. No exigir igualdad literal con una única solución. Etiquetas: admissible, inadmissible, not_evaluable. Registrar la dimensión que sustenta el juicio y su motivo. Haber recibido aprobación no sana un error científico. Los negativos de alcance se analizan por separado de la tasa de admisibilidad de los factibles.

En Equivalencia, primero juzgar ambas especificaciones y después comparar objetivo, entradas, operaciones, parámetros, marco y producto. Una reformulación sin efecto no rompe equivalencia. Dos errores iguales o dos especificaciones no admisibles no cuentan como estabilidad. Una pareja sin datos suficientes es no_evaluable.

## 5. Entrega y desacuerdos
Registrar seudónimo, guía, fecha, minutos y omisiones. Entregar el archivo sin reemplazar decisiones iniciales tras discutirlas. El coordinador conservará copia original, fecha y SHA-256; cualquier adjudicación irá en otro archivo. Calcular kappa con las primeras etiquetas independientes, no con las acordadas después. Los no evaluables, casos omitidos y cambios de guía se reportan; nunca inventar respuestas ni eliminarlos silenciosamente del denominador.

## 6. Volumen final: distinto del piloto
T-LANG: al menos 50 intenciones factibles, dos paráfrasis humanas revisadas por intención y 20 solicitudes fuera de alcance. Tres repeticiones de los 150 textos factibles producen 450 especificaciones; además 100 pares original/paráfrasis por repetición (300 comparaciones). Las referencias se preparan una vez por intención y sus paráfrasis se revisan. Los negativos y las aclaraciones añaden trabajo y se registran aparte. T-TURNS: al menos 100 turnos, de sesiones completas reservadas con contexto; no seleccionarlos por la clase predicha.

No se fija una promesa de horas: cronometrar el piloto y proyectar por tarea (referencias, juicios, pares, turnos), con tiempo adicional de coordinación y adjudicación. La selección final separa intención, sesión y familia; ni estos casos ni sus familias entran en la reserva. Las tareas estructurales de R3.8 se acordarán después de resolver fuentes, corpus y referencias científicas. No están incluidas en este encargo inicial.
