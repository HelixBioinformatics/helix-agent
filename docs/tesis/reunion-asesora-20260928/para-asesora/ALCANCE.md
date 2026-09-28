# Alcance que debe conocer la anotadora

Helix Agent recibe solicitudes, prepara acciones y pide aprobación. El catálogo admite recuperación PDB, GeomeTRe sobre unidades suministradas y detección STRPsearch en su ruta dedicada. SIFTS aporta correspondencias de residuos. La ruta AFDB exige estructura, API de procedencia y PAE coherentes; conserva pLDDT y las limitaciones. El motor experimental usa Nextflow local. La detección no convierte automáticamente sus candidatos en una verdad biológica; no se promete una cadena completa de cualquier operación a cualquier otra.

No están admitidos como rutas completas: ReUPred y consulta anotada de RepeatsDB con contrato de loci resuelto; análisis genómicos, docking, diagnóstico clínico ni demostración de estabilidad física a partir de confianza alta. No evaluar como fallo la negativa correcta a una tarea fuera de alcance.

Entradas para piloto:
- experimental.pdb / experimental.cif: 2xqh, cadena A; unidades e inserción en unidades.json. La numeración de autor y label_seq_id difieren. La anotadora no debe asumir igualdad.
- predicha.cif, predicha-api.json, predicha-pae.json: AF-P69905-F1, ejemplo técnico de hemoglobina, tres segmentos artificiales 10–16, 17–23, 24–30. No son repeticiones anotadas. Umbrales de desarrollo proporcionados: pLDDT ≥70 y PAE ≤5 Å; permiten evaluar si se respeta lo pedido, no certificar un umbral biológico universal.

Las solicitudes del piloto permiten juzgar usando esta ficha. Si hace falta inspeccionar coordenadas, los archivos están disponibles; no se exige reconstruir a mano un mapeo de 206 residuos. La anotadora debe pedir el mapeo si lo necesita para un juicio particular.
