# Accesibilidad al solvente, perfil descriptivo secundario

Se midió SASA en las mismas 108 entradas congeladas de la campaña estructural:
78 modelos AF2 originales enviados por los autores de Pratt et al. y 30 cadenas
experimentales de beta-solenoides con anotación revisada en RepeatsDB. El cálculo
es externo y local. No utiliza llamadas a modelos, instancias AWS, etiquetas
nuevas, umbrales de enterramiento ni un clasificador de validez física.

## Protocolo y resultados

`protocol.json` y `freeze.json` fijaron corpus, entradas, código, versión,
biblioteca compilada, referencias y tratamiento de átomos faltantes antes de
obtener áreas. Se priorizaron los cinco casos previamente enlazados con figuras.
Se usaron Lee y Richards, radios ProtOr, una sonda de 1.4 Å, 20 cortes y un hilo.
Hubo un intento por entrada, un solo trabajador y un límite de 180 s por caso.
Los 108 casos resultaron evaluables; no hubo reintentos ni cambios del protocolo.

El artefacto Python instalado es FreeSASA 2.2.1. El `config.h` incluido en su
archivo fuente declara `PACKAGE_VERSION 2.0.2`. Se conservan ambas identidades y
los hashes del módulo y archivo fuente, evitando atribuir la versión de la
envoltura al motor C.

El análisis conserva por residuo las áreas total, lateral, principal, polar y
apolar. La rSA es el área dividida por la referencia ProtOr de un tripéptido
Ala-X-Ala extendido. Puede superar 1, por lo que no se recorta. La clasificación
de polaridad corresponde a átomos del clasificador ProtOr, no a una etiqueta de
hidrofobicidad de toda la proteína.

En Pratt se observaron 2,000 residuos Asp/Glu/Lys/Arg, todos con cadenas laterales
completas. Otros 29 de los 78 modelos no contienen estos residuos, incluido 8b;
su estadístico lateral se registra como no aplicable, no como cero. En las
referencias se observaron 2,369 residuos de estas identidades: 2,340 completos y
29 incompletos. Siete referencias presentan algún residuo con átomos pesados
faltantes. Las áreas de los átomos observados se conservan; los 29 residuos
laterales incompletos quedan fuera de los resúmenes interpretables.

En 22r se midieron 40 cadenas laterales completas de Asp y Lys. Su mediana rSA
es 0.5077180802. Asp28 presenta 0.0046550343 Å² de área lateral y rSA
0.0000463326. Las diez unidades idénticas de 22 residuos permiten visualizar
cuatro posiciones repetidas en el panel B de la figura. La accesibilidad lateral
de Asp6 dentro de la unidad es menor en varias repeticiones internas que en los
extremos. Estas observaciones describen contacto con el solvente; no demuestran
por sí mismas que una carga esté descompensada o que el pliegue sea incorrecto.

## Alcance e interpretación

Se utiliza la cadena polimérica completa seleccionada en la campaña original,
sin otros componentes del ensamblaje, aguas, ligandos ni hidrógenos. No se
restringe al intervalo de repeticiones anotado. Las áreas dependen de la
composición, longitud, coordenadas ausentes y componentes omitidos. Los átomos
faltantes en residuos vecinos también pueden alterar la exposición calculada.

Asp/Glu/Lys/Arg son identidades de aminoácidos, no una determinación de su estado
de protonación. No se evalúan energía, pH, contraiones, puentes salinos ni
compensación de cargas. Los modelos AF2 no están relajados y las referencias
experimentales fueron refinadas. No se usó el contraste entre grupos para
aprender un umbral o asignar etiquetas. La sensibilidad y especificidad físicas
permanecen sin estimar. La anotación revisada de repeticiones en RepeatsDB tampoco
certifica que todas las coordenadas experimentales carezcan de defectos.

## Artefactos y comprobaciones

- `outcomes.csv` y `summary.json`: resultados por entrada y denominadores.
- `residue-observations.csv`: 25,403 residuos con áreas, normalización y ausencias.
- `charged-residue-observations.csv`: los 4,369 residuos Asp/Glu/Lys/Arg, incluidos
  los incompletos con su exclusión interpretativa explícita.
- `reports/`: resultado completo por entrada, con áreas de los átomos observados.
- `surface-exposure.png`, `.pdf`, `.svg`: figura descriptiva, inspeccionada
  visualmente; el pie y `figure-source.json` registran su significado y fuentes.
- `independent-validation.json`: verificación independiente con Python estándar.
- `reproduction/`: segundo cálculo de 22r, idéntico byte a byte al original.
- `manifest.json`: manifiesto del cálculo principal SASA.
- `analysis-manifest.json`: manifiesto separado para artefactos derivados, sin
  alterar el manifiesto SASA ni los manifiestos estéricos previos.

El verificador comprueba hashes, identidad de cada átomo y residuo, áreas
finitas/no negativas, sumas entre átomos y residuos, componentes polar/apolar y
lateral/principal, normalización con las referencias integradas, denominadores,
ausencias y exclusión de cadenas laterales incompletas del resumen interpretable.

Reproducción del protocolo y verificación del cálculo, utilizando el entorno
instalado localmente:

```sh
/home/webiwabou/.local/state/helix/freesasa-20261012/venv/bin/python script/tesis/structural_sasa_campaign.py verify
python3 script/tesis/verify_sasa_campaign.py
```

Los modelos originales de los autores se mantienen en su directorio privado
excluido de Git. Este perfil no modifica los 105/108 resultados del ensayo
estérico primario de 180 s ni el contraste secundario de 600 s.

## Referencias primarias

Mitternacht, S. (2016). FreeSASA: An open source C library for solvent accessible
surface area calculations. *F1000Research, 5*, 189.
[doi:10.12688/f1000research.7931.1](https://f1000research.com/articles/5-189/v1).

La normalización, convenciones y opciones se comprobaron en la
[documentación oficial de FreeSASA](https://freesasa.github.io/doxygen/CLI.html)
y en el [API Python](https://freesasa.github.io/python/classes.html). Se conservan
copias y hashes de las páginas y del archivo fuente exacto descargado de PyPI.
