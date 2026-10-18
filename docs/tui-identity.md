# Helix TUI: Cuaderno molecular

Implementación completada el 17 de octubre de 2026 sobre el brief del goal y [la propuesta inicial](./tui-identity-plan.md), con una [revisión posterior del campo genómico](design/tui-genome-field.md) según las capturas y preferencias del usuario. El cambio afecta a presentación, sin modificar contratos operativos ni evidencia de tesis. La validación usa el renderer nativo con datos simulados; sus límites de terminal físico se detallan abajo.

## Sistema visual

La landing aporta carbón `#0a0c10`, superficies `#11141a`, tinta `#eceeed`, contexto `#b3babd`, salvia luminosa `#b9e27f` y bosque `#244d3e` para claro. El cromo se expresa mediante valores de gris y contraste; la terminal conserva la fuente del usuario.

Se eligió **Cuaderno molecular** frente a **Bancada instrumental**: prioriza origen horizontal común, bloques de lectura tranquilos y contexto en forma de ficha. Bancada conserva más superficies rellenas y una silueta más cercana al donante. La comparación conceptual previa está en [boceto de direcciones](design/tui-identity-directions.html); las capturas nativas de la implementación son la evidencia final.

Reglas de composición: margen exterior de dos celdas; origen compartido de prosa, herramientas y prompt; separadores finos en chrome, no raíles de color por hablante; metadatos secundarios en líneas compactas; foco con contraste y marcador redundante. No se usa numeración de entradas ni nuevas métricas.

La hélice publicada mantiene `●` y `◦` en celdas reservadas. El par aislado junto a ella fue sustituido por un campo genómico casi negro en el fondo libre de la bienvenida. Fragmentos de ocho bases se iluminan suavemente en el mismo sitio; las filas complementarias son sintéticas. El campo se cancela durante escritura, modales, pérdida de foco y animaciones desactivadas. No se monta en el chat ni se copia a mensajes, resultados, eventos o prompts del modelo. El indicador de actividad conserva su significado y su control de interrupción.

El campo se omite en terminales de menos de 40 columnas o 22 filas y cuando no se declaran RGB ni 256 colores. En terminales bajos con borrador, la marca cede sus cinco filas a una firma de texto de una fila; a 60×20 se conservan seis líneas de entrada y los controles. El tema claro usa bosque, tintas oscuras y colores semánticos propios. Se respetan los temas elegidos por el usuario. `HELIX_ASCII=1` o `TERM=dumb` representan la identidad y los filetes nuevos con `*`, `o`, `-`, `|` y `+`; esto no convierte todos los glifos heredados del producto a ASCII.

## Matriz de contratos, registrada antes de editar

| Superficie | Dato existente | Presentación nueva | Acción que se conserva |
|---|---|---|---|
| Bienvenida | Marca, promesa, placeholders, `PromptRef` | Hélice en celdas, hebra sintética, ancho/alto adaptable | Binding del prompt, auto-submit de `--prompt`, destinos y slots |
| Sesión | `session.title`, mensajes/parts ordenados | Firma pequeña, título, etiquetas de rol y rejilla común | Navegación, orden, scroll, selección, exportación, undo/redo, compaction |
| Herramientas | Estado/input/output/error del mismo part | Columnas estables en pendiente/resuelto, bloque con filete | Expansión, errores, contenido, permisos, clicks existentes |
| Prompt | Modo/agente/modelo/variante/status/hints | Filete de foco, entrada y metadatos alineados, anillo existente | Submit/IME, historial, partes/adjuntos, pegado, autocompletado, editor, atajos, interrupción |
| Contexto | Sesión, tokens/coste, MCP, LSP, todo, files, directorio | Ficha de 42 columnas con secciones compactas | Slots, orden, campos, acciones, auto-visibilidad por encima de 120 columnas |
| Diálogos/listas | Títulos, filtros, opciones, current, hints/actions | Cabecera común y gutter estable de selección | Defaults, filtro, orden, teclas, focus, mouse y callbacks |
| Permisos | Request, opciones once/always/reject, diff/comando | Colores/filetes de la misma familia | Opciones y selección, confirmaciones, rechazo, teclas y payload SDK |
| Preguntas | Request, opciones/custom/multiple, respuestas | Colores/filetes de la misma familia | Orden, edición, selección, submit/reject y payload SDK |
| Error/actividad | Error y status recibidos | Error legible y señal de actividad quieta/animada | Contenido, tiempos operativos, reintento e interrupción |

Se excluyen `docs/tesis`, `script/tesis`, `evaluation`, agentes, herramientas, Nextflow/nf-core, contratos SDK/API, persistencia y dependencias. De `docs/tui.md` se conserva el idioma inglés, la marca y la disciplina gráfica; se excluyen sus propuestas de cambiar firma, Enter, «Allow always», enmiendas y nueva funcionalidad.

## Referencias aplicadas

- [Gemini, Header](https://github.com/google-gemini/gemini-cli/blob/main/packages/cli/src/ui/components/Header.tsx): marca que cede espacio al contenido según tamaño.
- [Codex, estado](https://github.com/openai/codex/blob/main/codex-rs/tui/src/status_indicator_widget.rs): actividad e interrupción en una región estable.
- [Pi, uso](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/usage.md): metadatos compactos, subordinados a la tarea.
- [Lazygit, configuración](https://github.com/jesseduffield/lazygit/blob/master/docs/Config.md): foco activo consistente.
- [K9s, skins](https://github.com/derailed/k9s#skins): presupuesto fijo para la marca.
- La [matriz de quince referencias](./tui-identity-plan.md) distingue código, documentación y repositorios de distribución. El efecto genómico de Seqera sigue siendo inspiración descrita por el usuario; el referente local verificable es `www/glyphs.js`.

## Skills y entorno

Instaladas `frontend-design` (Anthropic), `opentui` (documentación oficial de `anomalyco/opentui`, revisión `f8f608e2b9a41685d613a1156708ff06c826c3ce`) y la skill propia `helix-tui-art-direction`, en `~/.codex/skills/`. Las dos skills de terceros pasaron `quick_validate.py`. La skill propia incorpora identidad/contratos, validación y fuentes fechadas y también pasó el validador.

El runtime del proyecto permanece en Bun 1.3.14, Solid 1.9.10 y OpenTUI 0.4.3. Se instalaron dependencias con el lockfile congelado, sin ejecutar lifecycle scripts ni actualizar el lockfile.

La skill propia pasó además una prueba de uso independiente: otro agente produjo un brief que respetó idioma, marca, versión fijada, alcance de planificación y perímetro protegido. Las skills globales viven fuera del repositorio; reiniciar una sesión permite redescubrir su catálogo.

## Evidencia final

La fuente anterior, revisión `1de7c76718b19125b3d8598f73c11f25305714b6`, se verificó archivo por archivo: 243/243 coinciden. El [protocolo de capturas](design/tui-identity-baseline.md) y la [verificación diferencial](design/tui-identity-verification.md) explican cómo reproducir la evidencia desde `script/tui-identity/`. El [manifiesto](design/tui-identity/manifest.json) identifica fuentes y archivos conservados.

| Comprobación | Resultado y alcance |
|---|---|
| Suite completa `@helix/tui`, tras revisar el campo | 213 pass, 1 skip, 0 fail; 8 snapshots y 567 aserciones |
| Typecheck | `tsgo --noEmit`, sin errores |
| Lint de fuentes cambiadas y pruebas nuevas | 0 errores; las mismas 36 advertencias antes/después, ninguna añadida |
| Formato y diff | Prettier pasa en TS/TSX/JSON cambiados y harnesses; `git diff --check` pasa |
| Interacción diferencial | 15 flujos × 2 tamaños: 30 comparaciones, mismos efectos SDK y callbacks, incluido copiar con ratón |
| Auditoría AST | Las 25 llamadas SDK y 24 registros `useBindings` comparados son iguales; los cinco cierres de diálogos pasan a la cabecera compartida |
| Capturas | Entrega inicial: 52 antes + 52 después, 4 con plugins por defecto y 19 extras; revisión del campo: 16 casos nuevos, todos pasan |
| Animación desactivada | Recuento nativo de frames sin incremento en las sondas de reposo antes/después; test de reloj compartido, desactivación y desmontaje |
| Perímetro | Sin cambios en core, SDK, agentes, herramientas, paquetes/lockfile, `docs/tesis`, `script/tesis` ni `evaluation` |

Las capturas usan OpenTUI 0.4.3 nativo, proveedores Solid reales y SDK/eventos simulados. Los PNG rasterizan celdas y colores capturados, no una maqueta HTML ni screenshots de un emulador externo. La matriz de estrés habilita el plugin opcional `which-key`; los pares `before-default`/`after-default` respetan los plugins desactivados por defecto.

| Vista conservada | Antes | Después |
|---|---|---|
| Sesión por defecto, 120×40 oscuro | [PNG](design/tui-identity/captures/before-default/session-120x40-dark.png) | [PNG](design/tui-identity/captures/after-default/session-120x40-dark.png) |
| Bienvenida por defecto, 120×40 oscuro | [Original](design/tui-identity/captures/before-default/home-120x40-dark.png) | [Campo revisado](design/tui-identity/field-revision/welcome-120/home-120x40-dark.png) |
| Sesión sin logo, monocromo | [PNG](design/tui-identity/captures/before-default/session-120x40-dark-body-mono.png) | [PNG](design/tui-identity/captures/after-default/session-120x40-dark-body-mono.png) |
| Sesión con contexto, 160×48 oscuro | [PNG](design/tui-identity/captures/before/session-160x48-dark.png) | [PNG](design/tui-identity/captures/after/session-160x48-dark.png) |
| Sesión, 120×40 claro | [PNG](design/tui-identity/captures/before/session-120x40-light.png) | [PNG](design/tui-identity/captures/after/session-120x40-light.png) |
| Permiso, 80×24 oscuro | [PNG](design/tui-identity/captures/before/permission-80x24-dark.png) | [PNG](design/tui-identity/captures/after/permission-80x24-dark.png) |

La comparación sin logo conserva treinta y siete filas nativas por imagen, sin mover ni escalar celdas; el recorte posterior omite las tres filas de cabecera. En monocromo siguen visibles las diferencias: etiquetas `You`/`Helix`, prosa y herramientas en la misma columna, ausencia de raíles verticales por hablante, filete de herramienta y límite explícito del prompt. La ficha lateral conserva sus 42 columnas y campos; cambia su jerarquía de secciones. Es una evaluación visual de composición, no una puntuación de reconocimiento de marca.

La [entrada de seis líneas a 60×20](design/tui-identity/captures/after-extras/draft-six-lines/home-60x20-dark.png) no solapa el pie. La [vista animada del campo revisado](design/tui-identity/field-revision/motion/motion.gif) muestra las celdas nativas; la [entrada durante escritura](design/tui-identity/field-revision/typing/home-120x40-dark.png) permanece limpia. Las imágenes anteriores del par junto al logo se conservan como evidencia de la entrega inicial, no como diseño vigente. Menús, preguntas, errores y diálogos están en la [selección de capturas](design/tui-identity/captures/).

## Límites de la comprobación

No se probó un compositor IME físico, la cobertura de fuentes de cada emulador ni su integración de portapapeles. Se ejercitaron el textarea real, Unicode, pegado, flush tardío, selección nativa y el texto que recibe el adaptador de copia, interceptando la escritura al portapapeles. Los casos de 16/256 colores declaran capacidades en el renderer; sus spans RGB no prueban cuantización ANSI en el cable. `system` usa una paleta de terminal fija. Las mediciones breves de CPU son observaciones, sin pretensión estadística.

La igualdad diferencial cubre los caminos ejecutados; no demuestra equivalencia universal. Los handlers y contratos conservados, la revisión independiente y la suite existente complementan esos fixtures. No se ejecutaron modelos, comandos científicos ni pipelines para fabricar las evidencias de diseño.
