# Helix Agent: sitio de descarga

Sitio estático publicado por [pages.yml](../.github/workflows/pages.yml) en
https://helixbioinformatics.github.io/helix-agent/.

El nombre público es Helix Agent y la organización en GitHub es Helix Bioinformatics.
El ejecutable, las rutas de configuración y los archivos publicados usan `helix`.

La identidad combina un fondo oscuro con piezas cromadas y usa el verde de Helix como señal:
el verde bosque `#244d3e` y la salvia `#dcebb5` de Helix Learn, más `#b9e27f`, la salvia
encendida para fondos oscuros. El logotipo conserva la hélice y la tipografía Georgia.

## Archivos

No requiere compilación ni usa fuentes, bibliotecas o scripts de terceros.

| Archivo        | Qué hace                                                                                                          |
| -------------- | ----------------------------------------------------------------------------------------------------------------- |
| `index.html`   | Contenido en español e inglés. Los selectores de idioma y sistema funcionan con CSS incluso sin JavaScript.        |
| `styles.css`   | Estilos y animaciones de entrada.                                                                                 |
| `site.js`      | Preferencias, detección del sistema, copia de comandos, sesión ilustrativa, video y apariciones al hacer scroll.   |
| `helix-gl.js`  | Motor WebGL propio: la doble hélice de la portada y la proteína de la sección final.                               |
| `glyphs.js`    | Letras de ADN y proteína que se encienden en verde bajo el cursor, y el texto que se decodifica al aparecer.       |
| `gfp-data.js`  | Traza de la proteína verde fluorescente, generada por [`script/gfp-extract.py`](../script/gfp-extract.py).          |

Las figuras giran solas, responden al scroll y al cursor, y se pueden arrastrar. Al pasar el
cursor por la hélice se encienden sus pares de bases, nombrados según el inicio de TP53
humano. Los canvas solo dibujan mientras están en pantalla. Sin WebGL, la portada muestra
una hélice en SVG. Con `prefers-reduced-motion`, las figuras quedan quietas y el texto
aparece sin animación.

## La proteína

La sección final usa la GFP de *Aequorea victoria* según
[AlphaFold DB AF-P42212-F1](https://alphafold.ebi.ac.uk/entry/P42212) (v6), publicada con
licencia [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). La licencia exige
atribución, así que la línea de crédito al pie de la sección debe mantenerse.

El script asigna la estructura secundaria a partir de los puentes de hidrógeno del esqueleto,
porque el PDB de AlphaFold no trae registros `HELIX` ni `SHEET`. Para regenerar los datos:

```bash
curl -fL -A "Mozilla/5.0" -o AF-P42212-F1-model_v6.pdb https://alphafold.ebi.ac.uk/files/AF-P42212-F1-model_v6.pdb
python3 -I script/gfp-extract.py AF-P42212-F1-model_v6.pdb www/gfp-data.js
```

AlphaFold DB rechaza las descargas sin un User-Agent de navegador, de ahí la opción `-A`.

## Instalación

El workflow copia `install` e `install.ps1` desde la raíz al sitio publicado.
Para revisar también esos enlaces en local, prepara una carpeta temporal con
`www/` y ambos instaladores, y sírvela con un servidor HTTP estático.

La guía ofrece wget, curl nativo, PowerShell/WSL y descarga desde GitHub Releases.
Las instrucciones por distribución instalan los requisitos con su gestor de
paquetes; el agente se instala sin sudo. El instalador usa un descargador nativo
para los metadatos y los archivos, evitando los ejecutables de Snap por sus
[restricciones de acceso a archivos](https://snapcraft.io/docs/explanation/security/security-policies/).

En una primera visita, la descarga prioriza el sistema de escritorio informado por
el navegador (Windows, macOS o Linux); las elecciones manuales se conservan.
La distribución de Linux se elige manualmente porque los navegadores no la
[identifican de manera fiable](https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/User-agent_reduction).

En teléfonos y tabletas (puntero táctil sin hover), la sección de instalación indica que
Helix se instala desde una computadora y ofrece enviar el enlace. Los pasos siguen
disponibles con «Ver los pasos igualmente».

## Demo

La sesión de la sección 01 es ilustrativa y la página lo indica. El botón «Ver la grabación»
la sustituye, en el mismo marco, por `media/helix-agent-demo.mp4`, una copia del video de
demostración remultiplexada desde MOV sin recomprimir. `media/helix-agent-demo.jpg` es su
imagen de portada.
