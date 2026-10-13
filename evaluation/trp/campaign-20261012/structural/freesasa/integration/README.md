# Integración opcional de SASA en Helix

Helix puede registrar accesibilidad al solvente como diagnóstico opcional al
inspeccionar una estructura. El operador configura `HELIX_TRP_SURFACE_PYTHON` con
un intérprete que tenga FreeSASA 2.2.1 y Gemmi 0.7.5. El agente no puede escoger el
intérprete como argumento ni ejecutar texto de la estructura como código.

La envoltura está incluida en Helix y se ejecuta en modo aislado de Python con
un límite de 180 s. Utiliza Lee y Richards, ProtOr, sonda de 1.4 Å, 20 cortes y un
hilo. Selecciona la cadena polimérica completa del modelo ordinal solicitado,
excluye otros componentes del ensamblaje e hidrógenos y registra el hash de la
serialización PDB de Gemmi. Esta preparación redondea coordenadas a 0.001 Å; las
entradas PDB de la campaña ya tienen esa precisión. Cadenas incompatibles,
átomos alternativos, ocupaciones parciales, elementos o radios no admitidos
permanecen no evaluables.

Se devuelven áreas continuas polar/apolar y laterales, rSA de Asp/Glu/Lys/Arg,
átomos faltantes, denominadores y resúmenes de cadenas laterales completas. Un
residuo incompleto conserva su área parcial, pero su rSA interpretable es nula.
Una estructura sin esas identidades de aminoácidos tiene un estadístico no
aplicable, nunca un área cero inventada. No se infiere protonación, energía,
compensación de cargas o un fallo estructural.

`fold-plausibility`, el control C9, continúa como `not_evaluable` y la validez
biológica general como `not_established`. Tener una medición válida de SASA no
convierte este control en un clasificador físico. El diagnóstico incluye
versiones y hashes de las bibliotecas efectivamente cargadas y el hash de su
envoltura. Estos datos son deterministas: modificar el código, el entorno o las
coordenadas cambia la evidencia preparada y requiere una nueva aprobación.

La envoltura y sus hashes se incluyen tanto en la inspección portátil como en
el paquete aprobado de Nextflow. Los verificadores comprueban esos vínculos,
el origen y la selección. El diagnóstico estérico existente puede configurarse
de forma independiente o junto con SASA.

## Verificación real

`agent-reference.json` registra una invocación del adaptador de archivos real de
Helix con 22r y sus archivos ColabFold originales. Sus 40 cadenas laterales
completas y su mínimo, mediana y máximo rSA coinciden con el perfil externo
congelado. La evidencia portátil privada se verificó con un hash externo del
manifiesto. Las coordenadas, puntuaciones y PAE originales no se incluyen en este
directorio público. Esta es una invocación de inspección sin inferencia LLM, no
108 ejecuciones completas por el agente.

`implementation-validation.json` registra:

- 12 pruebas y 69 aserciones con FreeSASA; una prueba estérica opcional omitida.
- Compatibilidad por defecto: nueve pruebas y 36 aserciones; cuatro pruebas de
  motores opcionales omitidas porque no estaban configurados.
- Regresión con el motor CCTBX real: dos pruebas y 16 aserciones.
- Quince tareas de comprobación de tipos y una comprobación posterior de Helix.
- Comprobaciones de código Python y hashes de las fuentes finales.

Los controles negativos son de ingeniería: un intérprete ausente, la eliminación
controlada de OD1 en Asp28, la ausencia real de Asp/Glu/Lys/Arg en 8b y la
alteración de la envoltura. No se usan como etiquetas de validez física.

La incorporación se hizo después de concluir ambos lotes positivos en AWS y
después de aplicar y comprobar el cambio remoto. `application.json` conserva el
momento y las fuentes; `manifest.json` conserva esta evidencia por separado.
Los protocolos, etiquetas, áreas y manifiestos de la campaña SASA y de ambos
perfiles estéricos permanecen sin cambios.

Ejemplo en el entorno local utilizado para esta evaluación:

```sh
HELIX_TRP_SURFACE_PYTHON=/home/webiwabou/.local/state/helix/freesasa-20261012/venv/bin/python helix
```

Este entorno es independiente del de CCTBX. El perfil completo de 108 entradas,
sus fuentes primarias, el tratamiento de ausencias y la figura se describen en
`../README.md`.
