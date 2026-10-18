# Helix: propuesta de identidad para la TUI

Fecha: 17 de octubre de 2026. Documento de propuesta original. La instalación de skills, implementación y validación posteriores están registradas en [el sistema visual y entrega](./tui-identity.md); los diagnósticos y futuros de este documento corresponden al estado previo.

## Objetivo y recomendación

Rediseñar la presentación de Helix como un **cuaderno molecular**: una herramienta científica sobria, de lectura precisa, con una firma biológica breve. Traducir la landing reciente a celdas de terminal y hacer reconocible una sesión activa, además de la portada. Conservar la funcionalidad y los contratos que sustentan la tesis.

La propuesta se apoya en inspección de código local, la imagen de portada del video existente y fuentes públicas de 15 soluciones. No se ejecutaron sus aplicaciones. La imagen del video es una referencia histórica, no una captura del estado actual. No se pudo hacer inspección en navegador en esta sesión porque no había navegador conectado. Los bocetos son conceptuales, con contenido ilustrativo; no son capturas ni prueba de compatibilidad con OpenTUI.

## Diagnóstico del proyecto

- La landing declara cromo oscuro, verde bosque y salvia: [www/README.md](../www/README.md), [styles.css](../www/styles.css).
- La marca web combina hélice, `helix.` y Georgia. La terminal debe traducir su jerarquía sin exigir una fuente específica: [index.html](../www/index.html).
- La landing ya dibuja k-mers de 3–9 caracteres y ondas ocasionales: [glyphs.js](../www/glyphs.js). Sus letras de fondo son decorativas; las etiquetas de la hélice 3D tienen otra procedencia. No mezclar esos dos usos.
- La TUI ya tiene hélice `●/◦`, paleta salvia y un indicador propio de seis puntos: [logo.ts](../packages/tui/src/logo.ts), [helix.json](../packages/tui/src/theme/assets/helix.json), [spinner.tsx](../packages/tui/src/component/spinner.tsx).
- Su fondo oscuro actual es verde `#14251e`; la landing usa carbón `#0a0c10`. Hay alineamiento parcial de marca, no equivalencia de sistema visual.
- La composición activa conserva chat, indentaciones variables, prompt inferior y sidebar de 42 columnas, automática por encima de 120 columnas. La semejanza restante con OpenCode es estructural.
- Existen `PAGE`, `Entry`, `Hairline` y numeración, pero esas primitivas no están integradas en las pantallas activas. El anillo de actividad coexiste con un barrido de 40 ms en el prompt. Hay decisiones visuales propias a medio conectar.

### Antecedente que debe reconciliarse

[docs/tui.md](./tui.md), «El Registro», es una propuesta anterior. Conserva dos decisiones explícitas: interfaz en inglés y marca `●/◦`. Su paleta turquesa quedó atrás respecto de la landing reciente. Sus ideas de firma con `f`, Enter inerte, eliminación de «Allow always» y persistencia en `amendments.jsonl` cambian funcionalidad y **no pertenecen a este trabajo**. No implementar el documento íntegramente ni tratar sus comentarios como evidencia de comportamiento actual.

## Dirección visual

### Cuaderno molecular — recomendada

Una rejilla común para prosa, herramientas, metadatos y prompt. Roles claramente visibles, bloques separados por espacio, filetes finos donde agrupan información, pocas superficies rellenas. La sidebar se presenta como ficha con alineación y ritmo propios, conservando sus datos, acciones, orden y comportamiento.

La identidad debe reconocerse al recortar el logo y retirar el color: alineación, ritmo, foco y proporciones han de diferenciar a Helix. El término «cuaderno» es una dirección gráfica; no añade promesas de inmutabilidad, firma legal, validación científica ni nuevas capacidades de auditoría.

### Bancada instrumental — alternativa de contraste

Cabeceras compactas y delimitación más visible de zonas de trabajo; prompt y contexto con superficie tenue. Permite comparar densidad y foco contra la dirección editorial. Tiene mayor riesgo de conservar la silueta OpenCode, por lo que no es la recomendación principal. Ambas opciones mantienen los mismos controles y contenido.

Los bocetos de comparación viven en [boceto de direcciones](design/tui-identity-directions.html). Permiten explorar sesión/bienvenida y claro/oscuro. Sus proporciones son ilustrativas; los breakpoints reales se decidirán con renderizado en terminal.

## Traducción de la landing

| Papel | Base propuesta | Regla |
|---|---|---|
| Fondo oscuro | `#0a0c10` | Plano principal, sin tinte verde dominante |
| Superficie secundaria | `#11141a` | Reservada para agrupaciones que lo necesiten |
| Texto principal | `#eceeed` | Respuestas, acciones y datos esenciales |
| Texto secundario | `#b3babd` | Contexto y metadatos legibles |
| Texto atenuado | `#858c92` | Información secundaria; comprobar contra cada superficie |
| Acento salvia | `#b9e27f` | Foco y firma de marca, con redundancia textual |
| Salvia suave | `#dcebb5` | Complemento restringido; no segundo código de estados |
| Acento claro | `#244d3e` | Bosque sobre superficies claras |

El cromo se traduce a dos o tres intensidades discretas, no a efectos de brillo permanentes. Georgia no se puede imponer en una TUI general: usar caja, peso, espacio y composición. Conservar la geometría de la hélice; reservar celdas para sus glifos en vez de asumir que todos tienen el mismo ancho.

El tema claro requiere contraste propio. La salvia luminosa sobre fondo claro no es un acento legible. `#5f666e` de la landing se reservaría a decoración oscura, no texto pequeño esencial. Mantener estados de error, advertencia, éxito operativo y selección como roles distintos; un proceso completado no equivale a una conclusión científica validada.

La marca seguirá funcionando con tema de usuario, pocos colores y animación desactivada. El tema Helix recomendado no debe imponerse a quien eligió otro tema.

## Detalles propios

1. **Hebra complementaria.** En un área fija junto al logo, un fragmento sintético corto aparece en gris y revela brevemente su complemento en salvia. Ejemplo: `ACGTCA` / `TGCAGT`, alineados posición a posición. Evitar coordenadas, identificadores biológicos y porcentajes que puedan parecer datos del usuario.
2. **Cadencia molecular contenida.** Un único episodio decorativo a la vez, con largos periodos de quietud; punto de partida para prototipo: cada 10–16 segundos, tres pasos de intensidad. Sólo en bienvenida o su región de marca. Pausar mientras se escribe, ante permisos/preguntas y cuando las animaciones están desactivadas. Sin tráfico, lectura de datos biológicos, persistencia ni telemetría.
3. **Firma cotidiana.** Marca pequeña y punto salvia en cabecera o pie usando espacio reservado. La firma grande cede espacio en terminal pequeño; no hacer que una animación cambie el alto de la portada.
4. **Ritmo editorial de sesión.** Mismo origen horizontal para texto y herramientas, etiquetas cortas y estados en posición estable. No introducir números de evento, relojes o métricas nuevos por motivos estéticos. Si un dato no existe de forma fiable, no se muestra.
5. **Actividad con personalidad.** Consolidar la presentación del indicador existente de seis puntos, revisando la convivencia actual con el barrido del prompt. El estado operativo y la decoración tienen señales distinguibles. Conservar cuándo empieza/termina la actividad y los controles de interrupción.

Evitar lluvia de letras, secuencias detrás de respuestas, paneles científicos ficticios, imágenes obligatorias, Nerd Fonts y nuevos modos de navegación. Copiar texto, seleccionar resultados y leer sesiones largas deben seguir siendo tareas tranquilas.

## Referencias verificadas

Fuentes primarias consultadas el 17 de octubre de 2026. «Aplicación» es una recomendación de diseño, no una afirmación de que Helix ya lo haga. No se copiaron implementaciones.

| Solución | Evidencia y naturaleza | Qué estudiar para Helix |
|---|---|---|
| Seqera | [Repositorio de distribución](https://github.com/seqeralabs/seqera-cli), [CLI interactiva](https://docs.seqera.io/platform-enterprise/co-scientist/reference/cli). No se verificó fuente de la TUI. | Relación ciencia–marca. El efecto genómico es referencia aportada por el usuario, no verificado independientemente. |
| Claude Code | [Repositorio](https://github.com/anthropics/claude-code) de documentación/plugins; [modo interactivo](https://code.claude.com/docs/en/interactive-mode). | Jerarquía entre conversación, actividad y detalles; aplicar a superficies existentes sin añadir visores o flujos. |
| Gemini CLI | [Repositorio](https://github.com/google-gemini/gemini-cli), [Header.tsx](https://raw.githubusercontent.com/google-gemini/gemini-cli/main/packages/cli/src/ui/components/Header.tsx). Logos long/short/tiny por ancho. | Firma que cede espacio según columnas; conservar geometría estable. |
| Crush | [Repositorio y temas](https://github.com/charmbracelet/crush#themes). | Personalidad sostenida por una paleta semántica; sin copiar la estética Charm. |
| Pi | [Repositorio actual](https://github.com/earendil-works/pi), [uso](https://raw.githubusercontent.com/earendil-works/pi/main/packages/coding-agent/docs/usage.md), [temas](https://raw.githubusercontent.com/earendil-works/pi/main/packages/coding-agent/docs/themes.md). | Metadatos compactos y estado del editor; usar únicamente estados existentes en Helix. |
| Codex | [Repositorio](https://github.com/openai/codex), [indicador de actividad](https://raw.githubusercontent.com/openai/codex/main/codex-rs/tui/src/status_indicator_widget.rs). | Tiempo, interrupción, truncamiento y movimiento en ubicación predecible. |
| Aider | [Repositorio](https://github.com/Aider-AI/aider), [opciones](https://aider.chat/docs/config/options.html). | Separar roles de texto, advertencias y errores; legibilidad en presentación simple. |
| Goose | [Repositorio actual](https://github.com/aaif-goose/goose), [temas CLI](https://goose-docs.ai/docs/guides/goose-cli-commands/#themes). | Markdown y código como parte del sistema; sus temas documentados no cubren toda la interfaz. |
| Amp | [Documentación de interacción](https://ampcode.com/docs/cli/keybindings); no se verificó fuente TUI. | Descubrimiento en paleta de comandos y jerarquía de bloques existentes. |
| OpenCode | [Repositorio](https://github.com/anomalyco/opencode), [temas](https://opencode.ai/docs/themes/). | Referencia explícita de diferenciación: composición, prompt, sidebar, densidad y overlays. |
| Yazi | [Repositorio](https://github.com/sxyazi/yazi), [configuración visual](https://yazi-rs.github.io/docs/configuration/theme/). | Marcadores coherentes de selección y foco, sin añadir modos o paneles. |
| Lazygit | [Repositorio](https://github.com/jesseduffield/lazygit), [configuración](https://raw.githubusercontent.com/jesseduffield/lazygit/master/docs/Config.md). | Una región enfocada destaca; las regiones inactivas retroceden. |
| Atuin | [Repositorio](https://github.com/atuinsh/atuin). | Filas legibles para sesiones y actividad con datos existentes. |
| btop | [Repositorio](https://github.com/aristocratos/btop#prerequisites). | Degradación truecolor/256/16 colores y cobertura de glifos. |
| K9s | [Repositorio y skins](https://github.com/derailed/k9s#skins). Logo en región fija de 26×6. | Presupuesto fijo de espacio para la marca; cero desplazamiento de vistas por decoración. |

Prioridad de estudio profundo: Gemini, Codex, Pi, Lazygit y K9s. Crush aporta personalidad; OpenCode sirve para contraste. El objetivo no es reunir todas sus funciones ni todas sus convenciones visuales.

## Skills propuestas

| Prioridad | Skill | Procedencia y uso |
|---|---|---|
| Alta | `opentui` oficial | [OpenTUI](https://github.com/anomalyco/opentui#ai-agent-skill). Conocer celdas, layout, Solid, ciclo de render, input y snapshots. La documentación actual ofrece `npx skills add https://opentui.com --skill opentui`; el repo instala documentación de main. Verificar ejemplos contra la versión **0.4.3** fijada en Helix. Instalar una skill no autoriza actualizar el runtime. |
| Alta | `frontend-design` | [Anthropic](https://github.com/anthropics/skills/tree/main/skills/frontend-design). Dirección artística, composición y crítica. Aplicarla subordinada a las restricciones de terminal y a la marca existente; sus reglas web no determinan fuente, hover ni estructura del renderer. |
| Alta, por crear | `helix-tui-art-direction` | Skill propia usando `skill-creator`, ya disponible. Guardaría paleta, rejilla, glifos, movimiento, tamaños, referencias, perímetro de tesis y checklist de equivalencia visual/funcional. Es una propuesta de skill nueva, no una instalación disponible. |
| Opcional | `impeccable` | [Repositorio](https://github.com/pbakaus/impeccable), [skill](https://github.com/pbakaus/impeccable/blob/main/.agent/skills/impeccable/SKILL.md). Útil para `critique`, `distill` y `polish`. Sus herramientas web/nativas no prueban una TUI; no aplicar detectores CSS como autoridad sobre OpenTUI. Considerarlo alternativa o segunda revisión, no requisito junto a otra skill de diseño. |

Ya están disponibles `skill-installer`, `skill-creator` y `visualize`; no requieren otra instalación. `imagegen` no es necesario para un sistema que debe renderizarse con celdas. No instalar habilidades de React/Ink, Bubble Tea o Ratatui para forzar una migración de stack. Las skills de diseño ayudan al proceso; la comprobación final sigue siendo en terminal.

## Perímetro de implementación futura

**Cambios permitidos:** colores, estilos, espaciado, alineaciones, glifos en celdas, composición, truncamiento con acceso al contenido completo, decoración local, estados visuales derivados de datos existentes. Se pueden extraer componentes presentacionales conservando props, callbacks y slots.

**Contratos congelados:** herramientas bioinformáticas, Nextflow/nf-core, agentes, prompts internos, SDK/API, eventos, persistencia, esquemas, permisos y respuestas, atajos, selección/pegado/IME, rutas, artefactos y datos de tesis. Tampoco añadir métricas, reorganizar aprobaciones ni cambiar defaults de sidebar/tema sin una razón dentro del alcance autorizado.

| Zona | Tratamiento |
|---|---|
| `packages/tui/src/theme/assets/helix.json` | Paleta y roles, manteniendo compatibilidad de tokens y temas |
| `src/logo.ts`, `src/component/logo.tsx`, nuevas primitivas `src/ui/` | Composición de marca y render puro; conservar `●/◦` |
| `src/routes/home.tsx` | Sólo presentación: contiene autoenvío de `--prompt`, que se conserva |
| `src/routes/session/index.tsx` | Archivo mixto: separar presentación cuidadosamente; no reescribir undo/redo, exportación, compaction ni SDK |
| `src/component/prompt/index.tsx` | Archivo mixto: conservar handlers, IME, adjuntos, historial, autocompletado y envío |
| `src/routes/session/sidebar.tsx`, pies y slots | Reorganización visual conservando información, orden y acciones |
| `src/routes/session/permission.tsx`, `question.tsx` | Estilo; mismas opciones, selección, orden, teclas y payloads |
| `packages/helix/src/{nfcore,bio,session}`, SDK, server, herramientas | Fuera del cambio visual |
| `docs/tesis`, `script/tesis`, `evaluation` | Fuera del cambio; no regenerar ni modificar evidencia |

La pertenencia a `packages/tui` no basta para considerar un cambio puramente visual. Cada diff debe comprobarse por comportamiento. Reutilizar slots disponibles y el control de animaciones existente; no introducir otro scheduler permanente.

## Plan de ejecución

1. **Baseline y contratos.** Capturar la TUI actual con fixtures, inventariar superficies y registrar por pantalla `dato existente → presentación nueva → acción idéntica`. Separar `docs/tui.md` en ideas aprovechables y cambios fuera de alcance.
2. **Sistema y variantes.** Preparar Cuaderno/Bancada en 80×24 y formato ancho; comparar también sin logo, en monocromo y con tema claro. Resolver tokens, glifos, celdas, foco y densidad. Elegir Cuaderno como base si no hay otra preferencia del usuario.
3. **Portada y marca.** Adaptar marca conservando geometría, añadir hebra complementaria decorativa y definir variantes compactas. Verificar que nada desplaza el prompt ni entra en copia/transcripción.
4. **Sesión cotidiana.** Integrar rejilla, estilo de herramientas, prompt, contexto, menús y diálogos. Conservar accesos, funciones y campos existentes. Priorizar diferencias de composición frente a ajustes de color.
5. **Estados y robustez.** Actividad, herramientas pendientes/resueltas, permisos, preguntas, errores, desconexión, autocompletado, diffs largos, subagentes, sesión larga, resize, tema de usuario y animación desactivada.
6. **Cierre verificable.** Revisar el diff para detectar cambios funcionales, ejecutar pruebas pertinentes, capturar antes/después y documentar límites. Entregar un cambio acotado a presentación con evidencia de validación, no sólo una portada atractiva.

## Criterios de aceptación

- Helix se distingue en una sesión activa, también sin logo y en escala de grises; evaluación visual comparativa explícita, no puntuación inventada.
- Base 80×24; validación adicional 120×40 y 160×48, degradación a 60×20. En pequeño desaparece antes el ornamento que el contenido o una acción.
- Foco, selección, advertencias y errores se entienden sin depender sólo del color. Variantes dark/light/system y temas de usuario conservan legibilidad.
- Probar truecolor, 256 y 16 colores/ASCII según capacidades reales; documentar límites si falta soporte. No requerir emojis, fuente especial, ligaduras ni imagen en terminal.
- Cadenas largas, rutas, Unicode, IME y resize no provocan solapamientos ni cambios de columna al resolver una herramienta.
- Con animación desactivada no quedan timers decorativos activos. Medir CPU/despertares/render frente al baseline; la decoración no justifica render continuo.
- Fixtures idénticos producen el mismo contenido significativo y las mismas acciones/payloads antes y después. Aprobaciones, rechazo, interrupción, submit, historial, plugins, selección y copia se conservan.
- Ornamentación sintética separada de datos del análisis, sin coordenadas falsas, porcentajes inventados o afirmaciones científicas nuevas.
- Sin cambios en lógica, artefactos ni evidencia de tesis. No basta con que el cambio compile.

Harness existente: `testRender`, `captureCharFrame()`, snapshots de herramientas, SDK/eventos simulados y pruebas de tema, teclas, lifecycle, IME y carreras de envío en `packages/tui/test`. Añadir cobertura visual representativa de home/logo y sesión integrada; evitar snapshots masivos que sólo ratifiquen el cambio sin comprobar un requisito.

Comandos de validación futura: `bun run --cwd packages/tui typecheck` y `bun run --cwd packages/tui test`, más comprobaciones pertinentes de lint y revisión real en terminal. El script de pruebas raíz indica que no se deben ejecutar tests desde la raíz. Este trabajo de planificación no ejecutó las pruebas del producto.

## /goal propuesto

```text
/goal Rediseñar exclusivamente la capa visual de la TUI de Helix Agent para darle una identidad propia, reconocible durante una sesión activa y alineada con la landing actual de www/. Usar docs/tui-identity-plan.md como propuesta inicial y contrastar cada decisión con el código vigente. Trabajar con criterio de dirección de arte y las restricciones de OpenTUI/Solid fijadas en el repositorio.

Primero capturar el estado actual y definir una matriz por pantalla de datos existentes, presentación nueva y acciones idénticas. Reconciliar el antecedente docs/tui.md sin implementar sus cambios de permisos, firma ni persistencia. Comparar las direcciones Cuaderno molecular y Bancada instrumental; usar Cuaderno molecular como recomendación inicial. Aprovechar las referencias verificadas de Gemini, Codex, Pi, Crush, Lazygit, K9s y otras TUIs sin copiar su identidad ni incorporar sus funcionalidades.

Traducir cromo, carbón, bosque y salvia de la landing a un sistema de celdas. Conservar la hélice de Helix y la interfaz en inglés. Añadir una firma genómica discreta con fragmentos sintéticos complementarios junto al logo, quietud durante escritura y aprobaciones, y respeto al control existente de animaciones. Dar identidad también a transcripción, prompt, herramientas, contexto, menús, estados y diálogos mediante composición, jerarquía, foco y espaciado.

Conservar herramientas, agentes, prompts internos, Nextflow/nf-core, contratos SDK/API, eventos, persistencia, permisos, opciones, atajos, plugins y artefactos de tesis. Usar únicamente datos y estados ya disponibles. No modificar docs/tesis, script/tesis ni evaluation, ni actualizar dependencias para acomodar el diseño.

Validar 80x24, 120x40 y 160x48, degradación estrecha, oscuro/claro/system, ASCII y color limitado según capacidades reales, Unicode/IME, selección/copia, resize y animación desactivada. Verificar con fixtures y pruebas pertinentes que las acciones y payloads son equivalentes; revisar capturas reales antes/después, también sin logo y en monocromo. Entregar sistema visual documentado, implementación acotada a presentación, capturas y comprobaciones, con límites pendientes explícitos. No dar por terminado el trabajo con un cambio de paleta o sólo una nueva portada.
```

Este texto propone un goal; no lo activa. Las skills se seleccionan e instalan por separado y su documentación debe ajustarse a la versión que usa Helix.
