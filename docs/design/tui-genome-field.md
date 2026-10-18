# Campo genómico de bienvenida

Revisión del 17 de octubre de 2026 a partir de dos capturas del usuario. Sustituye el par fijo junto al logo: la preferencia es un fondo casi negro, con letras apenas visibles y una secuencia que se descubre ocasionalmente. La segunda captura suministrada aporta la referencia visual; no se afirma haber ejecutado la TUI de Seqera.

## Resultado y límites de presentación

La trama sintética cubre el espacio libre de Home, con una base cada dos celdas y filas alternas complementarias. No se leen archivos biológicos ni se consume aleatoriedad global. Logo, promesa, prompt, plugins, avisos y footer conservan su contenido y acciones. El campo respeta los rectángulos completos de contenido más un margen, sin letras dentro de entradas vacías ni delante de su marcador.

Cada episodio revela ocho bases en posición fija, y su complemento cuando también cabe. Una envolvente suave recorre las letras; no las sustituye ni desplaza. El episodio dura 2,6 segundos, con pasos de 100 ms, seguido de entre 7,5 y 9,3 segundos de reposo. La primera revelación se prepara a los 900 ms. En reposo queda un solo timeout, sin solicitudes de render de la decoración. La trama base mezcla un 4,5 % de la tinta secundaria con el fondo; el realce sube gradualmente hacia salvia o bosque según el tema.

Se desactiva por completo al escribir, abrir un diálogo, perder foco, desactivar animaciones o abandonar Home. El chat no monta el efecto. También se omite por debajo de 40×22 o sin RGB/256 colores declarados. No añade opciones, bindings, eventos SDK, persistencia, tráfico ni dependencias.

La pintura usa `renderBefore` en el box existente de Home, con posiciones nativas y máscara de sus hijos. No crea renderables adicionales: la trama carece de zonas clicables o texto seleccionable. El soporte de 256 colores se ejercita en las capacidades del renderer; la suavidad y cuantización del emulador físico siguen dependiendo de su implementación.

## Evidencia

- [Animación de celdas nativas](tui-identity/field-revision/motion/motion.gif): muestras del renderer real cada aproximadamente 100 ms. El último frame de reposo se mantiene ocho segundos en el GIF para representar la pausa; no es una grabación de un emulador externo.
- [80×24](tui-identity/field-revision/welcome-80/home-80x24-dark.png), [120×40](tui-identity/field-revision/welcome-120/home-120x40-dark.png), [160×48](tui-identity/field-revision/welcome-160/home-160x48-dark.png), [60×20](tui-identity/field-revision/welcome-60/home-60x20-dark.png) y [claro](tui-identity/field-revision/welcome-light/home-120x40-light.png).
- [Durante escritura](tui-identity/field-revision/typing/home-120x40-dark.png), [menú en Home](tui-identity/field-revision/menu/menu-120x40-dark.png), [animaciones apagadas](tui-identity/field-revision/off/home-120x40-dark.png) y [chat](tui-identity/field-revision/session/session-120x40-dark.png).

Los 16 casos nativos pasan, incluidos resize, `wcwidth`, ASCII y capacidades de 16/256 colores. Las seis pruebas específicas verifican contenido protegido, grilla de hit testing idéntica, ausencia de selección del fondo, ocho bases y complementos, límites al redimensionar y eliminación del timer en pausa/desmontaje/fallback. El reloj manual no modifica temporizadores globales.

La suite completa pasa con **213 pass, 1 skip, 0 fail**, ocho snapshots y 567 aserciones. Typecheck y formato pasan. Lint conserva 36 advertencias anteriores y no añade ninguna. La [matriz diferencial AFTER de 30 casos](tui-identity/field-revision/checks/behavioral-comparison.json) se volvió a ejecutar: mismos payloads HTTP y callbacks contra la fuente anterior congelada. No hay cambios en core, SDK, herramientas, prompts internos, dependencias ni perímetro de tesis.

## Reproducción

Desde la raíz, con Python 3, Pillow, Bun y dependencias del proyecto instaladas:

```sh
python3 script/tui-identity/run-field-captures.py
python3 script/tui-identity/render-captures.py field-revision
bun run --cwd packages/tui test
bun run --cwd packages/tui typecheck
```

El runner admite una lista de casos, por ejemplo `run-field-captures.py motion,typing,off`. Estado y capturas originales quedan en `tmp/tui-identity/`; las imágenes, logs y hashes se conservan en [field-revision](tui-identity/field-revision/). El informe de comportamiento sigue el [protocolo diferencial](tui-identity-verification.md). Después de las comprobaciones y de guardar sus logs, `package-field-evidence.py` valida matrices y hashes y preserva este conjunto sin sustituir las capturas iniciales.
