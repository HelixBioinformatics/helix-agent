# Entrega privada y restauración de evidencia

Los archivos completos se conservan fuera del repositorio. Esta carpeta contiene el empaquetador y comprobantes de entrega, sin copiar coordenadas originales ni PAE a Git. Los artefactos son privados y locales; no se autorizó su publicación.

## Fuentes científicas verificadas

Se creó el archivo científico con 299 fuentes y 71.472.156 bytes originales:

- 78 PDB originales de rango 1 de Pratt;
- 78 JSON PAE originales;
- 78 JSON de puntuaciones asociados;
- 30 CIF experimentales y 30 PDB de las cadenas seleccionadas para el cálculo;
- cinco archivos existentes de procedencia y vinculación.

El archivo contiene también un manifiesto de entrega, por lo que tiene 300 miembros regulares. Se comprimió con zstd y se extrajo en un directorio nuevo. Cada fuente recuperada coincidió en tamaño y SHA-256 con la fuente original y su manifiesto previo. Se volvió a comprobar que los originales no cambiaron. El archivo, los manifiestos, los recibos y los archivos extraídos tienen permisos 0600; las carpetas privadas tienen permisos 0700.

El comprobante [scientific-artifact.json](scientific-artifact.json) registra ruta, SHA-256, tamaño y directorio de restauración. El archivo científico ocupa 13.421.716 bytes comprimidos. Los originales permanecen en sus ubicaciones previas.

## Por qué se requieren dos artefactos

El archivo de campaña conserva ejecuciones, fallos, decisiones, recibos, diagnósticos, datos públicos recuperados, fuentes congeladas y archivos originales de las observaciones. Sin embargo, ninguno de los 108 valores `coordinatePath` de `structural/cases.json` apunta dentro de la campaña. Los 78 PDB de Pratt están en `evaluation/trp/reference/pratt-author-20261001/originals`; los 30 CIF están en el directorio privado de controles de la estación. Los PDB seleccionados utilizados para puntuar esos controles también están fuera de la campaña.

Por ello, la entrega completa necesita el archivo de campaña y el archivo científico. Este último registra `originalPath`, `archiveMember`, tamaño y SHA-256 para cada fuente. No incluye credenciales, claves, entornos conda/venv ni directorios generales de aplicaciones. Los informes CCTBX con coordenadas derivadas quedan íntegros en el archivo privado de campaña y se excluyen de Git; no reemplazan las estructuras originales completas.

## Restauración y límites reales de los comandos

1. Comprobar el SHA-256 del archivo contra el recibo conservado fuera del archivo.
2. Extraer en un directorio nuevo, nunca sobre la única copia de trabajo.
3. Verificar cada miembro contra `members.json`. El empaquetador ya realizó esta comprobación en `verified-restoration` y conservó el resultado.
4. Conservar los nombres y el prefijo relativo del repositorio para las fuentes que ya estaban dentro de él. Los controles externos se encuentran bajo `external-inputs/structural-controls`.
5. Restaurar las rutas declaradas en un espacio de trabajo independiente con el mismo diseño, o usar un lector adicional explícito que resuelva el mapeo y verifique los SHA originales. No reescribir los archivos congelados para aparentar una reproducción intacta.

Los lotes originales de `structural_campaign.py`, `structural_sasa_campaign.py` y `structural_runtime_contrast.py` leen rutas absolutas congeladas. Los verificadores también comprueban fuentes y versiones declaradas; la comprobación FreeSASA incluye fuentes y el módulo compilado. No tienen una opción general de cambio de raíz o de mapa de entradas. Instalar la misma versión de un programa no demuestra por sí solo igualdad del hash de su módulo compilado.

Los comandos individuales sí aceptan una entrada reubicada y una salida nueva:

```text
python-con-cctbx script/tesis/structural_campaign.py score-one --input <archivo-restaurado> --output <resultado-nuevo>
python-con-freesasa script/tesis/structural_sasa_campaign.py score-one --input <archivo-restaurado> --output <resultado-nuevo>
```

Son réplicas individuales nuevas, con sus requisitos de entorno. No deben sobrescribir resultados congelados ni atribuirse a las tentativas originales. Esta preparación de entrega no ejecutó ninguno de esos cálculos científicos.

## Empaquetado de la campaña después del cierre

El empaquetador [package_private_artifacts.py](package_private_artifacts.py) exige una ruta de salida nueva fuera del repositorio. La acción `campaign` requiere además un recibo del agente raíz que confirme el fin de las escrituras:

```json
{
  "campaignReadyForArchive": true,
  "campaignPath": "evaluation/trp/campaign-20261012"
}
```

El recibo debe escribirse fuera de la campaña. El comando soportado es:

```text
python3 evaluation/trp/campaign-20261012/checks/delivery-20261013/package_private_artifacts.py campaign --eof-receipt <recibo-de-cierre.json> --output-dir <directorio-externo-nuevo>
```

La acción conserva todos los archivos regulares y directorios observados de la campaña, incluidos directorios vacíos. No aplica las exclusiones de Git. Conserva los bytes de archivos tar anteriores, incluidas sus entradas originales. Si encuentra un enlace externo o un tipo de archivo inesperado en el árbol de campaña, exige revisión explícita antes de empaquetar. Actualmente no se constató ninguno en el inventario de entrega.

El archivo completo incluye un manifiesto externo anclado y una copia idéntica dentro del archivo. Se verifica mediante extracción nueva, comprobación de cada fuente y comprobación de que el conjunto de archivos y carpetas no cambió durante el empaquetado. Sus comprobantes se escriben fuera del repositorio, para no crear un ciclo de autorreferencia ni cambiar el conjunto ya archivado.

La campaña completa y la selección NUL final quedan pendientes hasta la confirmación de fin de escrituras del documento, los datos y las guías. No se realizó `git add`, no se creó un commit y no se modificaron originales.

## Selección explícita para Git

[select_campaign_git_files.py](select_campaign_git_files.py) conserva los bytes exactos del selector revisado fuera del repositorio, con SHA-256 `ac8d602d1186d37f16b614d42217dc15bfb354c5b6dfcf063ccfcbc50b750f45`. Genera inventario, clasificación y listas NUL/JSON en un directorio externo nuevo. Conserva decisiones, fuentes, recibos y revisiones, y excluye datos originales, archivos completos, cachés y JSON con coordenadas derivadas vinculadas a SHA de originales Pratt. La revisión independiente de la selección debe cubrir además otros campos de coordenadas, texto y contenedores.

Su constante `ROOT` señala explícitamente `/home/webiwabou/Projects/bioinformatica-org`. Ejecutarlo en otra ubicación exige ajustar esa constante en una copia y registrar el nuevo hash del selector; no se altera con ello ningún dato ni umbral de la campaña. Las listas resultantes no acreditan por sí solas que las exclusiones estén conservadas en un archivo externo: la entrega completa verificada continúa siendo un requisito previo.

```text
python3 evaluation/trp/campaign-20261012/checks/delivery-20261013/select_campaign_git_files.py --output <directorio-externo-nuevo>
```

La opción amplia permite inspeccionar más metadata materializada y conserva todos los casos, primeras interpretaciones, revisiones y archivos legibles admitidos. Cada archivo original observado figura en el inventario con su clase y decisión. Los snapshots previos permanecen fechados y no sustituyen el corte de entrega final.
