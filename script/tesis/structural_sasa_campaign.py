#!/usr/bin/env python3
"""Prospectively frozen, descriptive SASA profile of the existing 108 structures.

This secondary analysis measures surface exposure. It does not label physical
failure, impose a burial threshold, or replace the primary steric experiment.
"""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import re
import statistics
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
PRIMARY = ROOT / "evaluation/trp/campaign-20261012/structural"
BASE = PRIMARY / "freesasa"
VERSION = "structural-sasa-descriptive/1.0.0"
PARAMETERS = {"algorithm": "LeeRichards", "probe-radius": 1.4,
              "n-slices": 20, "n-points": 100, "n-threads": 1}
OPTIONS = {"hetatm": False, "hydrogen": False, "join-models": False,
           "skip-unknown": False, "halt-at-unknown": True}
CHARGED_SIDECHAIN = {"ASP": "CB CG OD1 OD2", "GLU": "CB CG CD OE1 OE2",
                     "LYS": "CB CG CD CE NZ", "ARG": "CB CG CD NE CZ NH1 NH2"}
SIDECHAIN = {"ALA": "CB", "ARG": CHARGED_SIDECHAIN["ARG"], "ASN": "CB CG OD1 ND2",
             "ASP": CHARGED_SIDECHAIN["ASP"], "CYS": "CB SG", "GLN": "CB CG CD OE1 NE2",
             "GLU": CHARGED_SIDECHAIN["GLU"], "GLY": "", "HIS": "CB CG ND1 CD2 CE1 NE2",
             "ILE": "CB CG1 CG2 CD1", "LEU": "CB CG CD1 CD2", "LYS": CHARGED_SIDECHAIN["LYS"],
             "MET": "CB CG SD CE", "PHE": "CB CG CD1 CD2 CE1 CE2 CZ", "PRO": "CB CG CD",
             "SER": "CB OG", "THR": "CB OG1 CG2", "TRP": "CB CG CD1 CD2 NE1 CE2 CE3 CZ2 CZ3 CH2",
             "TYR": "CB CG CD1 CD2 CE1 CE2 CZ OH", "VAL": "CB CG1 CG2"}
AREA_FIELDS = ("total", "mainChain", "sideChain", "polar", "apolar")
RELATIVE_FIELDS = {name: "relative" + name[0].upper() + name[1:] for name in AREA_FIELDS}
POSITIVE_ORDER = ["8b", "22r", "21r", "12ab", "19r"]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


def load(path):
    return json.loads(path.read_text())


def close(a, b):
    return math.isclose(a, b, rel_tol=1e-10, abs_tol=1e-7)


def source_records():
    import freesasa
    paths = [Path(__file__).resolve(), Path(freesasa.__file__)]
    paths += [PRIMARY / name for name in ("cases.json", "protocol.json", "manifest.json",
              "summary.json", "runtime-600/summary.json", "runtime-600/manifest.json",
              "runtime-600/source-label-audit.json")]
    paths += sorted((BASE / "sources").glob("*"))
    return [{"path": str(path), "sha256": sha(path), "bytes": path.stat().st_size} for path in paths]


def reference_areas():
    source = (BASE / "sources/freesasa-2.2.1__lib__src__classifier_protor.c").read_text()
    values = {}
    for residue in SIDECHAIN:
        block = re.search(r"struct classifier_residue protor_" + residue + r"_cfg\s*=\s*\{(.*?)\n\};", source, re.S)
        row = re.search(r'\{"' + residue + r'",\s*([^}]+)\}', block.group(1))
        numbers = [float(v.strip()) for v in row.group(1).split(",")]
        values[residue] = dict(zip(AREA_FIELDS, numbers[:5]))
    return values


def pdb_atoms(path):
    atoms = []
    skipped = {"hydrogen": 0, "hetatm": 0}
    models = 0
    for line in Path(path).read_text().splitlines():
        if line.startswith("MODEL "):
            models += 1
            if models > 1:
                raise ValueError("multiple models in frozen selected-chain input")
        if line.startswith("HETATM"):
            skipped["hetatm"] += 1
        if not line.startswith("ATOM  "):
            continue
        element = line[76:78].strip()
        if element in {"H", "D"}:
            skipped["hydrogen"] += 1
            continue
        if element not in {"C", "N", "O", "S"}:
            raise ValueError("unsupported element; no inferred element or radius")
        if line[16:17] != " " or float(line[54:60]) != 1.0:
            raise ValueError("alternative conformation or nonunit occupancy")
        residue_name = line[17:20].strip()
        if residue_name not in SIDECHAIN:
            raise ValueError("nonstandard polymer residue")
        xyz = [float(line[30:38]), float(line[38:46]), float(line[46:54])]
        if not all(math.isfinite(v) for v in xyz):
            raise ValueError("nonfinite coordinates")
        atoms.append({"chain": line[21:22], "residue": line[22:27].strip(),
                      "residueName": residue_name, "name": line[12:16].strip(),
                      "element": element, "xyz": xyz})
    if not atoms or len({a["chain"] for a in atoms}) != 1:
        raise ValueError("input is not the frozen single polymer chain")
    keys = [(a["chain"], a["residue"], a["name"]) for a in atoms]
    if len(set(keys)) != len(keys):
        raise ValueError("duplicated atom identity")
    return atoms, skipped


def prepare():
    import freesasa
    if (BASE / "freeze.json").exists():
        raise ValueError("freeze already exists; never overwrite")
    cases = load(PRIMARY / "cases.json")
    if len(cases) != 108 or sum(c["group"] == "pratt-original" for c in cases) != 78:
        raise ValueError("original cohort changed")
    cases.sort(key=lambda c: (0, POSITIVE_ORDER.index(c["id"])) if c["id"] in POSITIVE_ORDER else (1, c["group"], c["id"]))
    input_audit = []
    for case in cases:
        if sha(case["scoreInputPath"]) != case["scoreInputSha256"]:
            raise ValueError("original coordinate file changed")
        atoms, skipped = pdb_atoms(case["scoreInputPath"])
        residues = {(a["chain"], a["residue"]) for a in atoms}
        if len(residues) != case["residues"]:
            raise ValueError("residue count does not match frozen cohort")
        input_audit.append({"id": case["id"], "atoms": len(atoms), "residues": len(residues), "excluded": skipped})
    protocol = {"version": VERSION, "createdUTC": datetime.now(timezone.utc).isoformat(),
                "kind": "prospective secondary descriptive surface-exposure profile",
                "question": "Measure side-chain solvent accessibility of ASP/GLU/LYS/ARG and polar/apolar atomic surface in the unchanged existing corpus, prioritizing the five published figure-linked cases.",
                "parameters": PARAMETERS, "classifier": "protor", "parserOptions": OPTIONS,
                "workers": 1, "perCaseTimeoutSeconds": 180, "maximumAttemptsPerCase": 1,
                "scope": "Complete selected single polymer chain from the existing steric inputs, first and only model; excludes hydrogen, water, ligands and other chains. Does not isolate the RepeatsDB repeat interval.",
                "chargedSidechainExpectedHeavyAtoms": {r: v.split() for r, v in CHARGED_SIDECHAIN.items()},
                "standardResidueExpectedHeavyAtoms": {r: ("N CA C O " + v).split() for r, v in SIDECHAIN.items()},
                "missingAtoms": "Keep all raw observed-atom areas. A D/E/K/R side chain with any expected side-chain atom absent is incomplete: set interpretable relative side-chain area to null, retain atom names/missing names. Missing atoms in neighboring residues may affect all areas and are recorded at structure level. No imputation.",
                "relativeAreaConvention": "Area divided by the embedded ProtOr extended Ala-X-Ala reference for the same residue and area component. A ratio may exceed 1 and is not clipped. FreeSASA counts CA and OXT as main-chain atoms.",
                "referenceAreasAngstromSquared": reference_areas(),
                "observables": ["atom SASA with ProtOr polarity", "all residue absolute area components", "embedded-reference relative area components", "D/E/K/R side-chain completeness and continuous side-chain rSA", "case medians/min/max of complete D/E/K/R side-chain rSA", "whole-chain polar/apolar surface fractions"],
                "notInferred": ["actual residue protonation", "charge compensation or salt-bridge strength", "counterion involvement", "energetic stability", "physical fold correctness", "sensitivity or specificity"],
                "thresholds": None, "biologicalClassifier": None, "confidenceScoresUsed": False,
                "comparison": "Descriptive observations only. Whole-chain SASA depends on composition, length, missing coordinates and omitted assembly partners; AF2 unrelaxed models and experimental refined coordinates are distinct preparations. No tuned cutoff, p-value, group-trained classifier or new ground truth.",
                "verification": "Frozen input/library hashes, PDB/FreeSASA atom identity and coordinates, finite nonnegative areas, additive components, residue and atom sums, exact embedded-reference normalization, missing-side-chain exclusion from interpretable summaries, deterministic reproduction of 22r, and no changes to existing primary or secondary steric manifests.",
                "sources": [{"title": "FreeSASA: An open source C library for solvent accessible surface area calculations", "author": "Simon Mitternacht", "year": 2016, "journal": "F1000Research", "volume": "5", "article": "189", "doi": "10.12688/f1000research.7931.1", "url": "https://f1000research.com/articles/5-189/v1"},
                            {"title": "FreeSASA CLI and relative-area reference convention", "url": "https://freesasa.github.io/doxygen/CLI.html"},
                            {"title": "FreeSASA Python API", "url": "https://freesasa.github.io/python/classes.html"},
                            {"title": "Python package source artifact 2.2.1", "url": "https://pypi.org/project/freesasa/2.2.1/"}],
                "runtimeIdentity": {"pythonDistribution": importlib.metadata.version("freesasa"),
                                    "sourceConfigPackageVersion": "2.0.2", "note": "The Python distribution version and bundled config.h package-version text differ. Do not claim C version 2.2.1. The installed module and source archive are pinned by SHA-256.",
                                    "python": sys.version, "defaultParametersObserved": freesasa.Parameters.defaultParameters}}
    save(BASE / "protocol.json", protocol)
    save(BASE / "freeze.json", {"version": VERSION, "createdUTC": datetime.now(timezone.utc).isoformat(), "protocolSha256": sha(BASE / "protocol.json"),
                                "cases": cases, "inputAudit": input_audit, "sources": source_records(), "libraryVersion": importlib.metadata.version("freesasa")})
    print(json.dumps({"prepared": len(cases), "priority": POSITIVE_ORDER, "method": "LeeRichards/ProtOr/1.4A/20slices/1thread", "threshold": None}))


def verify_frozen():
    freeze = load(BASE / "freeze.json")
    if freeze["protocolSha256"] != sha(BASE / "protocol.json") or freeze["sources"] != source_records():
        raise ValueError("frozen code, library, source documents or steric evidence changed")
    if freeze["libraryVersion"] != importlib.metadata.version("freesasa"):
        raise ValueError("library version changed")
    for case in freeze["cases"]:
        if sha(case["scoreInputPath"]) != case["scoreInputSha256"]:
            raise ValueError("coordinate input changed")
    return freeze


def score_one(path, output):
    import freesasa
    atoms, excluded = pdb_atoms(path)
    classifier = freesasa.Classifier.getStandardClassifier("protor")
    for atom in atoms:
        if classifier.classify(atom["residueName"], atom["name"]) not in {"Polar", "Apolar"} or classifier.radius(atom["residueName"], atom["name"]) <= 0:
            raise ValueError("atom absent from explicit ProtOr classifier")
    structure = freesasa.Structure(str(path), classifier=classifier, options=OPTIONS)
    if structure.nAtoms() != len(atoms):
        raise ValueError("library parser silently changed atom inventory")
    for i, atom in enumerate(atoms):
        actual = (structure.chainLabel(i), structure.residueNumber(i).strip(), structure.residueName(i).strip(), structure.atomName(i).strip())
        expected = (atom["chain"], atom["residue"], atom["residueName"], atom["name"])
        if actual != expected or any(not close(x, y) for x, y in zip(structure.coord(i), atom["xyz"])):
            raise ValueError("library parser atom identity or coordinates differ")
    result = freesasa.calc(structure, freesasa.Parameters(PARAMETERS))
    areas = result.residueAreas()
    grouped = {}
    for i, atom in enumerate(atoms):
        key = (atom["chain"], atom["residue"])
        grouped.setdefault(key, []).append({"name": atom["name"], "area": result.atomArea(i), "polarity": classifier.classify(atom["residueName"], atom["name"]), "radius": classifier.radius(atom["residueName"], atom["name"])})
    residue_rows = []
    for (chain, residue), own in grouped.items():
        area = areas[chain][residue]
        residue_name = area.residueType
        names = {a["name"] for a in own}
        expected = set(("N CA C O " + SIDECHAIN[residue_name]).split())
        missing = sorted(expected - names)
        charged = residue_name in CHARGED_SIDECHAIN
        missing_side = sorted(set(CHARGED_SIDECHAIN[residue_name].split()) - names) if charged else None
        relative = {name: getattr(area, attr) if area.hasRelativeAreas and math.isfinite(getattr(area, attr)) and getattr(area, attr) >= 0 else None for name, attr in RELATIVE_FIELDS.items()}
        row = {"chain": chain, "residue": residue, "residueName": residue_name,
               "observedAtomCount": len(own), "atoms": own, "missingExpectedHeavyAtoms": missing,
               "areaAngstromSquared": {name: getattr(area, name) for name in AREA_FIELDS},
               "relativeArea": relative, "hasRelativeAreas": area.hasRelativeAreas,
               "chargedResidueIdentity": charged, "missingChargedSidechainAtoms": missing_side,
               "chargedSidechainComplete": not missing_side if charged else None,
               "interpretableChargedSidechainRelativeArea": relative["sideChain"] if charged and not missing_side else None}
        residue_rows.append(row)
    totals = {name: sum(row["areaAngstromSquared"][name] for row in residue_rows) for name in AREA_FIELDS}
    charged_rows = [r for r in residue_rows if r["chargedResidueIdentity"]]
    complete = [r for r in charged_rows if r["chargedSidechainComplete"]]
    values = [r["interpretableChargedSidechainRelativeArea"] for r in complete]
    report = {"version": VERSION, "inputSha256": sha(path), "parameters": PARAMETERS, "classifier": "protor", "parserOptions": OPTIONS,
              "scope": "unchanged isolated selected polymer chain", "excludedAtoms": excluded,
              "atoms": len(atoms), "residues": len(residue_rows), "libraryTotalArea": result.totalArea(),
              "areaAngstromSquared": totals, "apolarAreaFraction": totals["apolar"] / totals["total"],
              "polarAreaFraction": totals["polar"] / totals["total"],
              "residuesWithMissingExpectedHeavyAtoms": sum(bool(r["missingExpectedHeavyAtoms"]) for r in residue_rows),
              "chargedResidues": len(charged_rows), "completeChargedSidechains": len(complete),
              "incompleteChargedSidechains": len(charged_rows) - len(complete),
              "chargedSidechainRelativeAreaMedian": statistics.median(values) if values else None,
              "chargedSidechainRelativeAreaMin": min(values) if values else None,
              "chargedSidechainRelativeAreaMax": max(values) if values else None,
              "residueObservations": residue_rows,
              "physicalFoldVerdict": "not_established", "burialThreshold": None, "confidenceScoresUsed": False}
    validate_report(report, reference_areas())
    save(output, report)


def validate_report(report, references):
    if report["physicalFoldVerdict"] != "not_established" or report["burialThreshold"] is not None or report["confidenceScoresUsed"]:
        raise ValueError("unsupported classifier or confidence dependency")
    rows = report["residueObservations"]
    if len(rows) != report["residues"] or sum(r["observedAtomCount"] for r in rows) != report["atoms"]:
        raise ValueError("atom or residue denominator differs")
    for row in rows:
        area = row["areaAngstromSquared"]
        if any(not math.isfinite(v) or v < 0 for v in area.values()):
            raise ValueError("nonfinite or negative SASA")
        if not close(area["total"], area["polar"] + area["apolar"]) or not close(area["total"], area["mainChain"] + area["sideChain"]):
            raise ValueError("SASA component identity failed")
        atoms = row["atoms"]
        if any(not math.isfinite(a["area"]) or a["area"] < 0 or a["radius"] <= 0 for a in atoms) or not close(sum(a["area"] for a in atoms), area["total"]):
            raise ValueError("atom sum identity failed")
        for polarity in ("polar", "apolar"):
            if not close(sum(a["area"] for a in atoms if a["polarity"].lower() == polarity), area[polarity]):
                raise ValueError("atom polarity component identity failed")
        for name, relative in row["relativeArea"].items():
            ref = references[row["residueName"]][name]
            if ref > 0 and (relative is None or not close(relative * ref, area[name])):
                raise ValueError("embedded reference normalization differs")
        names = {a["name"] for a in atoms}
        if row["missingExpectedHeavyAtoms"] != sorted(set(("N CA C O " + SIDECHAIN[row["residueName"]]).split()) - names):
            raise ValueError("missing atom evidence differs")
        if row["chargedResidueIdentity"]:
            missing = sorted(set(CHARGED_SIDECHAIN[row["residueName"]].split()) - names)
            if row["missingChargedSidechainAtoms"] != missing or row["chargedSidechainComplete"] != (not missing):
                raise ValueError("side-chain completeness differs")
            expected = row["relativeArea"]["sideChain"] if not missing else None
            if row["interpretableChargedSidechainRelativeArea"] != expected:
                raise ValueError("partial side chain entered interpretable exposure summary")
    for name in AREA_FIELDS:
        if not close(sum(r["areaAngstromSquared"][name] for r in rows), report["areaAngstromSquared"][name]):
            raise ValueError("whole-chain SASA sum differs")
    if not close(report["areaAngstromSquared"]["total"], report["libraryTotalArea"]):
        raise ValueError("library total SASA differs")
    charged = [r for r in rows if r["chargedResidueIdentity"]]
    complete = [r for r in charged if r["chargedSidechainComplete"]]
    values = [r["interpretableChargedSidechainRelativeArea"] for r in complete]
    expected = [statistics.median(values), min(values), max(values)] if values else [None] * 3
    actual = [report["chargedSidechainRelativeArea" + key] for key in ("Median", "Min", "Max")]
    if expected != actual or report["chargedResidues"] != len(charged) or report["completeChargedSidechains"] != len(complete):
        raise ValueError("charged-residue descriptive summary differs")


def summarize(rows):
    groups = {}
    for group in sorted({row["group"] for row in rows}):
        own = [r for r in rows if r["group"] == group]
        measured = [r for r in own if r["status"] == "evaluable"]
        applicable = [r for r in measured if r["charged_sidechain_relative_area_median"] is not None]
        medians = [r["charged_sidechain_relative_area_median"] for r in applicable]
        groups[group] = {"cases": len(own), "sasaEvaluable": len(measured), "sasaCoverage": len(measured) / len(own),
                         "casesWithInterpretableChargedSidechains": len(applicable),
                         "casesWithoutChargedResidues": sum(r["charged_residues"] == 0 for r in measured),
                         "chargedResidues": sum(r["charged_residues"] for r in measured),
                         "completeChargedSidechains": sum(r["complete_charged_sidechains"] for r in measured),
                         "incompleteChargedSidechains": sum(r["incomplete_charged_sidechains"] for r in measured),
                         "casesWithMissingHeavyAtoms": sum(r["residues_with_missing_heavy_atoms"] > 0 for r in measured),
                         "medianOfCaseChargedSidechainRelativeAreaMedians": statistics.median(medians) if medians else None}
    return {"version": VERSION, "freezeSha256": sha(BASE / "freeze.json"), "groups": groups,
            "knownPublishedCases": [r for r in rows if r["id"] in POSITIVE_ORDER],
            "physicalSensitivity": None, "physicalSpecificity": None, "classifierValidated": False,
            "biologicalThreshold": None, "primaryStericEvidencePreserved": True,
            "modelCalls": 0, "awsInstances": 0,
            "meaning": "Descriptive exposure measurements on isolated chains. Charged amino-acid identities do not establish actual protonation or failure. No new physical labels or tuned cutoff."}


def run():
    freeze = verify_frozen()
    if (BASE / "summary.json").exists():
        raise ValueError("campaign already completed")
    rows = []
    for case in freeze["cases"]:
        output = BASE / "reports" / case["group"] / (case["id"] + ".json")
        output.parent.mkdir(parents=True, exist_ok=True)
        attempt = output.with_suffix(".attempt.json")
        if attempt.exists():
            raise ValueError("attempt exists; do not silently repeat")
        started = time.monotonic()
        save(attempt, {"startedUTC": datetime.now(timezone.utc).isoformat(), "id": case["id"], "status": "running", "timeoutSeconds": 180})
        status, error = "evaluable", None
        try:
            result = subprocess.run([sys.executable, str(Path(__file__).resolve()), "score-one", "--input", case["scoreInputPath"], "--output", str(output)], capture_output=True, text=True, timeout=180,
                                    env=dict(os.environ, OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1", MKL_NUM_THREADS="1"))
            if result.returncode:
                status, error = "not_evaluable", result.stderr[-3000:] or result.stdout[-3000:]
                output.with_suffix(".error.log").write_text(result.stdout + "\n" + result.stderr)
        except subprocess.TimeoutExpired:
            status, error = "not_evaluable", "FreeSASA external child exceeded fixed180s cap"
            output.with_suffix(".error.log").write_text(error + "\n")
        elapsed = time.monotonic() - started
        report = load(output) if status == "evaluable" else {}
        if report and report["inputSha256"] != case["scoreInputSha256"]:
            raise ValueError("report input identity differs")
        row = {"id": case["id"], "group": case["group"], "label": case["label"], "status": status,
               "atoms": report.get("atoms"), "residues": report.get("residues"),
               "total_area_angstrom_squared": report.get("libraryTotalArea"), "apolar_area_fraction": report.get("apolarAreaFraction"),
               "charged_residues": report.get("chargedResidues"), "complete_charged_sidechains": report.get("completeChargedSidechains"),
               "incomplete_charged_sidechains": report.get("incompleteChargedSidechains"), "residues_with_missing_heavy_atoms": report.get("residuesWithMissingExpectedHeavyAtoms"),
               "charged_sidechain_relative_area_median": report.get("chargedSidechainRelativeAreaMedian"),
               "charged_sidechain_relative_area_min": report.get("chargedSidechainRelativeAreaMin"),
               "charged_sidechain_relative_area_max": report.get("chargedSidechainRelativeAreaMax"),
               "elapsed_seconds": elapsed, "error": error}
        rows.append(row)
        save(attempt, {"completedUTC": datetime.now(timezone.utc).isoformat(), "id": case["id"], "status": status, "elapsedSeconds": elapsed, "timeoutSeconds": 180})
        save(BASE / "progress.json", {"completed": len(rows), "total": len(freeze["cases"]), "rows": rows})
        print(json.dumps({"completed": len(rows), "total": 108, "id": case["id"], "status": status, "elapsedSeconds": elapsed}), flush=True)
        if status != "evaluable":
            print(error, flush=True)
    with (BASE / "outcomes.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    save(BASE / "summary.json", summarize(rows))
    verify_frozen()
    files = [{"path": p.relative_to(BASE).as_posix(), "bytes": p.stat().st_size, "sha256": sha(p)} for p in sorted(BASE.rglob("*")) if p.is_file() and p.name != "manifest.json"]
    save(BASE / "manifest.json", {"version": VERSION, "files": files})
    print(json.dumps(summarize(rows), ensure_ascii=False))


def verify():
    freeze = verify_frozen()
    for entry in load(BASE / "manifest.json")["files"]:
        path = BASE / entry["path"]
        if sha(path) != entry["sha256"] or path.stat().st_size != entry["bytes"]:
            raise ValueError("SASA evidence file changed")
    rows = load(BASE / "progress.json")["rows"]
    if [r["id"] for r in rows] != [c["id"] for c in freeze["cases"]] or load(BASE / "summary.json") != summarize(rows):
        raise ValueError("cohort identity or group summary differs")
    with (BASE / "outcomes.csv").open() as stream:
        table = list(csv.DictReader(stream))
    if len(table) != len(rows) or any(any(table[i][key] != (str(value) if value is not None else "") for key, value in row.items()) for i, row in enumerate(rows)):
        raise ValueError("CSV output differs from typed source")
    for case, row in zip(freeze["cases"], rows):
        if row["status"] == "evaluable":
            report = load(BASE / "reports" / case["group"] / (case["id"] + ".json"))
            if report["inputSha256"] != case["scoreInputSha256"] or report["residues"] != case["residues"]:
                raise ValueError("coordinate/residue inventory binding differs")
            validate_report(report, reference_areas())
        elif not row["error"] or row["total_area_angstrom_squared"] is not None:
            raise ValueError("unevaluable case has score or lacks explanation")
    print(json.dumps({"ok": True, "cases": len(rows), "evaluable": sum(r["status"] == "evaluable" for r in rows), "stericEvidencePreserved": True, "biologicalClassifier": None}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["prepare", "run", "verify", "score-one"])
    parser.add_argument("--input", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.action == "score-one":
        score_one(args.input, args.output)
    else:
        globals()[args.action]()
