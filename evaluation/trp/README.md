# Evaluación TRP

Identificadores actualizados al 23/09/2026: tres objetivos y 21 resultados. Las evidencias fechadas conservan su numeración original; consulte [equivalencias](../../docs/tesis/renumeracion-20260923/README.md).

La fase F2 deja un catálogo inicial, referencias técnicas y el protocolo de los 21 resultados. **La evaluación empírica sigue pendiente.**

| Artefacto                                                      | Uso                                                                                  |
| -------------------------------------------------------------- | ------------------------------------------------------------------------------------ |
| [PROTOCOL.md](PROTOCOL.md), [protocol.json](protocol.json)     | Corpus, particiones, metas, denominadores, incertidumbre y enmiendas                 |
| [ANNOTATION.md](ANNOTATION.md)                                 | Encargo preparado; todavía no existe anotador confirmado                             |
| [freeze.template.json](freeze.template.json)                   | Campos que deben completarse antes de medir; no es una congelación efectiva          |
| [Catálogo](../../packages/helix/src/trp/catalog.json) | Dos operaciones admitidas, tres candidatas y un comparador web                       |
| [Auditoría](reference/audit.json)                              | Fuentes, versiones, licencia declarada, consultas y alcance de las anclas semánticas |
| [Referencia GeomeTRe](reference/geometre/reference.json)       | Ejecución real en Docker, aislada de la red, del ejemplo 2xqh/A                      |

## Verificación sin red

Desde la raíz del repositorio:

```bash
bun script/tesis/check_trp_catalog.ts
```

La resolución comprueba SHA-256 y tamaño de **todos** los insumos, salidas y registro de cada entrada admitida. No ejecuta el modelo ni Docker. Rechaza candidatos, archivos ausentes, alterados y enlaces que salgan de la raíz de evidencia. La coincidencia de hashes presupone que se confía en la copia del catálogo: no autentica al autor ni demuestra corrección biológica.

Desde `packages/helix`:

```bash
bun test test/trp
```

La compatibilidad de puertos compara declaraciones: formato, tipo de dato, espacio de identificadores, convención de cadena, marco, inserciones y escalas. F3 debe añadir mapeos, comprobación de identidades concretas, grafo y datos reales, e integrar estas decisiones en el agente. La descarga PDB no asegura automáticamente las precondiciones de GeomeTRe.

## Reproducir la operación geométrica

El ensayo utiliza el [ejemplo de los autores de GeomeTRe](https://github.com/BioComputingUP/GeomeTRe/blob/8bb0c50bb0bf73c16cc22e7bd4e3991a326841c9/README.md), versión 1.0. La estructura **2xqh**, cadena A, se recuperó de RCSB; sus 12 límites de unidades son entradas suministradas por el ejemplo. Las salidas contienen 12 filas de unidades y dos de resumen. No son una medición de detección de repeticiones ni de sensibilidad.

```bash
git clone --branch 1.0 https://github.com/BioComputingUP/GeomeTRe.git /tmp/geometre-source
git -C /tmp/geometre-source checkout 8bb0c50bb0bf73c16cc22e7bd4e3991a326841c9
docker build -t tesis/geometre:1.0-frozen -f script/tesis/geometre.Dockerfile /tmp/geometre-source
python3 script/tesis/run_geometre_reference.py --input evaluation/trp/reference/geometre/2xqh.pdb --source /tmp/geometre-source --work /tmp/geometre-reproduction --image tesis/geometre:1.0-frozen
```

Elegir directorios nuevos. El script rechaza un checkout distinto o modificado; guarda el digest real de la imagen, dependencias, entrada, salida, duración y validación del CSV. La imagen base y todas las dependencias de ejecución resueltas están fijadas en el Dockerfile. Los metadatos de construcción y marcas temporales pueden cambiar el digest de una reconstrucción; debe registrarse el digest nuevo, no atribuirle el del ensayo anterior. La construcción original que resolvió dependencias se refinó con esos pines y se repitió el ejemplo; el catálogo enlaza la segunda ejecución, conservada con su log de construcción.

La primera fila geométrica es un marcador sin par predecesor; `mean` y `std` resumen los pares y no son residuos. Curvatura, torsión, inclinación y yaw se expresan en radianes en esta implementación. TM-score es similitud estructural, no confianza del modelo. El archivo NPY auxiliar se conserva como bytes opacos; el verificador no deserializa sus objetos Python.

## Recursos excluidos y consecuencias

- **RepeatsDB:** se obtuvo una página real, con un registro `reviewed=false`. La respuesta no declara el marco de los límites. El sitio histórico declara [CC BY 4.0](https://old.repeatsdb.bio.unipd.it/about); debe comprobarse su alcance en la API actual. No se admite aún la conversión de sus límites a coordenadas geométricas.
- **ReUPred:** el archivo institucional sí incluye un aviso GNU GPL, a diferencia de lo inferido en la auditoría histórica. No se identificó versión de licencia ni copia completa. La invocación con Python 3 falla por sintaxis de Python 2. Falta reconstruir su entorno y producir una predicción real; no se declara imposible de ejecutar.
- **STRPsearch:** fuente y base incluidas identificadas por revisión/hash. Falta `typer` en el entorno anfitrión. Además, el nombre de entorno del [Dockerfile](https://github.com/BioComputingUP/STRPsearch/blob/ed325a7f6b77578ee96753f31dbdcfda4931cca8/Dockerfile) difiere del YAML. Faltan instalación reproducible de dependencias y ejecución científica. No se lo sustituye por GeomeTRe: cumplen funciones distintas.
- **RepeatsDB-lite:** comparador web; no se verificó una referencia ejecutable local.

El universo auditado tiene seis recursos; dos están admitidos. No se presenta 2/2 como cobertura de todos los recursos TRP ni como cierre total de R1.1. Un servicio HTTP no expone necesariamente el digest de su infraestructura: se conserva respuesta y fecha, sin inventar una imagen de servidor.

## Fuentes y licencias

Las coordenadas PDB se conservan bajo la [política CC0 de wwPDB](https://www.wwpdb.org/about/usage-policies); mantener la identificación y referencia bibliográfica contenidas en su cabecera. GeomeTRe y STRPsearch declaran GPL v3. No se redistribuyen sus árboles completos ni la base de STRPsearch en este repositorio.

El subconjunto de términos [EDAM](https://github.com/edamontology/edamontology/releases/tag/1.25.20260626T1230Z) mantiene atribución y licencia CC BY-SA 4.0, independientemente de la licencia del código propio. Las URI y etiquetas se comprobaron contra el OWL publicado, excluyendo términos obsoletos. Los campos `operation`, `input/output.data` e `input/output.format` siguen las anclas del [esquema oficial de bio.tools](https://github.com/bio-tools/biotoolsSchema/blob/c31233af4e136f985e83a58f3ca11b02628348f9/stable/biotools.xsd). Esto es un mapeo de campos: no afirma que las herramientas estén registradas ni que el catálogo local valide contra todo ese esquema.
