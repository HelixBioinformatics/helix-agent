# Verificación de comportamiento de la identidad TUI

La comprobación diferencial ejecutó **15 flujos en 120×40 y 60×20**, contra fuente congelada y fuente activa: **30 comparaciones, 60 ejecuciones satisfactorias**. Compara las llamadas HTTP del SDK (método, ruta, parámetros y JSON) y los valores de callbacks; no compara píxeles para inferir comportamiento.

Los resultados preservados están en [behavioral-comparison.json](tui-identity/verification/behavioral-comparison.json) y [behavioral-source-audit.json](tui-identity/verification/behavioral-source-audit.json). Se comprobaron Allow once, Allow always con confirmación separada, rechazo, clic en permiso, preguntas de selección/respuesta propia/rechazo, selector por teclado/ratón, renombrado, envío Unicode, pegado, flush tardío, selección/copia con ratón y doble Escape para interrumpir. Todo usa eventos y HTTP simulados; no llama a proveedores, herramientas ni pipelines.

## Reproducir

Se requieren Python 3, Bun y las dependencias ya instaladas del repositorio. El runner busca `bun` en `PATH` y, como alternativa, en `~/.bun/bin/bun`. Resuelve la raíz desde su ubicación, ejecuta Bun desde `packages/tui` con `--conditions=browser` y `@opentui/solid/preload`, y limita la concurrencia a dos procesos.

Desde la raíz:

```sh
python3 script/tui-identity/run-verification.py
```

El runner prepara el harness temporal y enlaces de dependencias en `tmp/tui-identity`, mantiene allí el estado y escribe resultados por fase en `tmp/tui-identity/verification`. Los scripts durables no modifican el producto. El comando completo vuelve a generar las 30 comparaciones; no se necesita repetirlo para consultar los informes ya conservados.

Smoke test de un caso y auditoría AST, conservando el informe completo existente:

```sh
python3 script/tui-identity/run-verification.py --phase after --flows permission-once --sizes 60x20 --skip-report
```

Sólo auditoría AST o reconstrucción del informe a partir de resultados existentes:

```sh
python3 script/tui-identity/run-verification.py --audit-only
python3 script/tui-identity/run-verification.py --report-only
```

`--flows`, `--sizes`, `--workers` y `--phase before|after|both` permiten acotar una ejecución. Un informe parcial declara su cantidad de casos; `--skip-report` evita sustituir el informe agregado durante un smoke test. La auditoría AST compara contenido con la fuente congelada, por lo que también funciona después de hacer commit; inspecciona llamadas `sdk.client.*`, registros `useBindings` y atributos de eventos JSX. Los cierres de diálogo extraídos a `DialogHeader` requieren revisar su traslado, además de comparar cantidades.

## Fuente anterior

La fuente congelada vive en `tmp/tui-identity/baseline/source`, con `src/`, `test/`, `package.json`, `tsconfig.json`, `bunfig.toml` y `sst-env.d.ts`. Su revisión registrada es `1de7c76718b19125b3d8598f73c11f25305714b6`. Aunque se congeló desde el worktree, se verificaron sus **243 archivos** contra los blobs de esa revisión: el conjunto y sus contenidos coinciden. El [manifiesto SHA-256](tui-identity/verification/baseline-source-sha256.json) y la [procedencia comprobada](tui-identity/verification/baseline-provenance.json) permiten identificar ese estado.

Si falta la copia temporal, se puede reconstruir sin sobrescribir una existente:

```sh
python3 script/tui-identity/run-verification.py --prepare-baseline 1de7c76718b19125b3d8598f73c11f25305714b6
```

Esto usa `git archive` local, no una descarga. Para otra revisión, un archivo de Git sólo reproduce los archivos comprometidos; no representa automáticamente cambios locales ni archivos nuevos. `--baseline` permite indicar otra copia explícita. Mantener el runtime fijado por el repositorio; las ejecuciones registradas usaron OpenTUI 0.4.3 y Bun 1.3.14.

## Alcance y límites

El caso de flush ejecuta el textarea real: doble Enter, inserción de `글` en el siguiente tick antes del segundo defer, y comprobación de un único envío de `Inspect 한글` y editor vacío. Comprueba esa carrera de integración; no simula un compositor IME físico del sistema operativo.

Unicode escrito usa puntos de código completos y NFC porque `mockInput.typeText()` de OpenTUI 0.4.3 divide pares sustitutos mediante `split("")`. El pegado con bracketed paste también cubre texto descompuesto, japonés y emoji. Cuatro intentos iniciales de prompt excedieron 20 segundos con alta concurrencia; sus reruns aislados pasaron y no se interpretaron como regresiones del producto.

El caso de selección arrastra el ratón sobre `liver_01` en el transcript nativo y comprueba la copia exacta y la limpieza de selección. Intercepta únicamente el adaptador de escritura: no cambia el portapapeles del sistema ni certifica su integración física.

La evidencia sólo establece igualdad para los caminos ejercitados. La auditoría de fuente complementa esos resultados; no demuestra por sí sola equivalencia funcional universal. La inspección visual, capacidades de terminal e IME físico tienen evidencia y límites propios en la entrega de diseño.

Tras trasladar los scripts se repitió el caso Allow once a 60×20 y la auditoría AST. Después de los últimos ajustes visuales se volvió a ejecutar la matriz AFTER completa de los 28 casos iniciales. Se añadieron y ejecutaron los dos pares de selección/copia y se regeneró el informe completo de 30 comparaciones. El informe conserva hashes de las fuentes modificadas; `package-evidence.py` comprueba que sigan correspondiendo al código al preservar los resultados.

La revisión posterior del campo ambiental volvió a ejecutar los 30 casos AFTER. Su [informe con hashes actualizados](tui-identity/field-revision/checks/behavioral-comparison.json) se conserva junto a las capturas revisadas; los informes de la entrega inicial permanecen como evidencia histórica.
