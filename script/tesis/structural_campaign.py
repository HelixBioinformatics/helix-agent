#!/usr/bin/env python3
"""Acquire reviewed experimental references and run a bounded physical diagnostic.

Run with Python 3.12, cctbx-base==2025.11 and gemmi==0.7.5. This exploratory
external validation does not set physical ground truth or complete R3.8.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import io
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "evaluation/trp/campaign-20261012/structural"
PRATT = ROOT / "evaluation/trp/reference/pratt-author-20261001"
PRIVATE = Path.home() / ".local/state/helix/structural-20261012"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n")


def fetch(url, path):
    if not path.exists():
        request = urllib.request.Request(url, headers={"User-Agent": "Helix-thesis-reference-acquisition/1.0"})
        with urllib.request.urlopen(request, timeout=60) as response:
            content = response.read(20_000_001)
        if len(content) > 20_000_000:
            raise ValueError("source exceeds 20 MB acquisition limit")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    return path.read_bytes()


def prepare():
    import gemmi

    if (BASE / "freeze.json").exists():
        raise ValueError("freeze exists; run or verify, never overwrite")
    protocol = json.loads((BASE / "protocol.json").read_text())
    if importlib.metadata.version("cctbx-base") != protocol["engine"]["version"]:
        raise ValueError("external engine version differs from protocol")
    controls = []
    candidates = []
    used_proteins = set()
    used_pdbs = set()
    raw_sources = []
    for skip in range(0, 800, 100):
        query = dict(protocol["referenceSelection"]["query"], skip=skip)
        url = protocol["referenceSelection"]["endpoint"] + "?" + urllib.parse.urlencode(query)
        page = BASE / f"repeatsdb-beta-page-{skip:05d}.json"
        raw = json.loads(fetch(url, page))
        raw_sources.append({"url": url, "path": page.relative_to(BASE).as_posix(), "sha256": sha(page)})
        for item in raw["items"].values():
            content = item["content"]
            chain = content["chain"]
            pdb_id = chain["structure"].lower()
            chain_id = chain["id"]
            proteins = sorted(content.get("features_uniprot", []) or [key[8:] for key in content.get("features", {}) if key.startswith("UniProt-")])
            row = {"pdb": pdb_id, "chain": chain_id, "annotationUuid": item["uuid"], "reviewed": content.get("reviewed"), "uniprot": proteins, "status": "excluded", "reason": None}
            candidates.append(row)
            if not content.get("reviewed"):
                row["reason"] = "annotation not reviewed"
                continue
            if chain["source"] != "RCSB/PDB":
                row["reason"] = "not a PDB source"
                continue
            if pdb_id == "2xqh" or "P69905" in proteins:
                row["reason"] = "existing development reference"
                continue
            if pdb_id in used_pdbs or any(p in used_proteins for p in proteins):
                row["reason"] = "duplicate PDB or UniProt identity"
                continue
            cif_path = PRIVATE / "controls" / f"{pdb_id}.cif"
            try:
                cif_url = f"https://files.rcsb.org/download/{pdb_id.upper()}.cif"
                fetch(cif_url, cif_path)
                block = gemmi.cif.read_file(str(cif_path)).sole_block()
                methods = list(block.find_values("_exptl.method"))
                if not methods or any("THEORETICAL" in x.upper() for x in methods):
                    raise ValueError("no experimental method")
                structure = gemmi.make_structure_from_block(block)
                if len(structure) != 1:
                    raise ValueError("multiple coordinate models")
                coordinate_chain = structure[0].find_chain(chain_id)
                if coordinate_chain is None:
                    raise ValueError("selected author chain absent")
                residues = [r for r in coordinate_chain if r.entity_type == gemmi.EntityType.Polymer]
                atoms = [a for r in residues for a in r]
                if not atoms:
                    raise ValueError("empty selected polymer chain")
                if any(a.altloc not in ("\x00", " ") or abs(a.occ - 1) > 0.001 for a in atoms):
                    raise ValueError("ambiguous/partially occupied alternate atoms")
                if any(not all(math.isfinite(v) for v in (a.pos.x, a.pos.y, a.pos.z)) for a in atoms):
                    raise ValueError("nonfinite coordinates")
                # Preserve exactly the selected deposited polymer chain. An explicit
                # scope is used rather than guessing the numbering of API loci.
                mono = gemmi.Structure()
                mono.name = pdb_id
                model = gemmi.Model("1")
                polymer_chain = gemmi.Chain(chain_id)
                for residue in residues:
                    polymer_chain.add_residue(residue.clone())
                model.add_chain(polymer_chain)
                mono.add_model(model)
                score_path = PRIVATE / "controls" / f"{pdb_id}-{chain_id}.pdb"
                mono.write_pdb(str(score_path))
                if any(a.element.name not in ("C", "N", "O", "S", "H", "D", "Se") for a in atoms):
                    raise ValueError("unsupported nonprotein element in polymer")
                annotation_path = BASE / "annotations" / f"{pdb_id}-{chain_id}.json"
                save(annotation_path, item)
                row.update(status="selected", reason=None, experimentalMethods=methods, atoms=len(atoms), residues=len(residues))
                controls.append({"id": f"{pdb_id}-{chain_id}", "group": "experimental-reviewed-beta-solenoid", "pdb": pdb_id, "chain": chain_id, "uniprot": proteins, "reviewed": True,
                                 "label": "reference_repeat_structure", "physicalFailureLabel": None, "annotationUuid": item["uuid"], "annotationPath": annotation_path.relative_to(ROOT).as_posix(), "annotationSha256": sha(annotation_path),
                                 "coordinateUrl": cif_url, "coordinatePath": str(cif_path), "coordinateSha256": sha(cif_path), "scoreInputPath": str(score_path), "scoreInputSha256": sha(score_path), "experimentalMethods": methods, "atoms": len(atoms), "residues": len(residues)})
                used_pdbs.add(pdb_id)
                used_proteins.update(proteins)
            except Exception as exc:
                row["reason"] = f"{type(exc).__name__}: {exc}"
            if len(controls) >= protocol["referenceSelection"]["target"]:
                break
        if len(controls) >= protocol["referenceSelection"]["target"] or skip + 100 >= raw["count"]:
            break
    pratt_cases = json.loads((PRATT / "cases.json").read_text())
    models = []
    for case in pratt_cases:
        metadata = json.loads((PRATT / "metadata" / f"{case['identifier']}.json").read_text())
        path = PRATT / "originals" / metadata["structureFile"]
        if sha(path) != metadata["structureSha256"]:
            raise ValueError("Pratt original integrity mismatch")
        models.append({"id": case["identifier"], "group": "pratt-original", "label": case["label"], "physicalFailureLabel": True if case["label"] == "published_problem" else None,
                       "labelEvidence": case["labelEvidence"], "coordinatePath": str(path), "coordinateSha256": sha(path), "scoreInputPath": str(path), "scoreInputSha256": sha(path), "residues": case["sequenceLength"]})
    save(BASE / "candidates.json", candidates)
    save(BASE / "cases.json", models + controls)
    save(BASE / "freeze.json", {"version": protocol["version"], "createdUTC": datetime.now(timezone.utc).isoformat(), "kind": protocol["kind"], "protocolSha256": sha(BASE / "protocol.json"), "scriptSha256": sha(Path(__file__)),
                               "casesSha256": sha(BASE / "cases.json"), "candidatesSha256": sha(BASE / "candidates.json"), "sources": raw_sources,
                               "packages": {name: importlib.metadata.version(name) for name in ("cctbx-base", "gemmi", "numpy", "scipy")}, "python": sys.version, "referencesSelected": len(controls), "prattModels": len(models)})
    print(json.dumps({"prepared": len(models) + len(controls), "references": len(controls), "candidatesInspected": len(candidates), "physicalClassifierFrozen": False}))


def verify_inputs():
    freeze = json.loads((BASE / "freeze.json").read_text())
    for name, key in (("protocol.json", "protocolSha256"), ("cases.json", "casesSha256"), ("candidates.json", "candidatesSha256")):
        if sha(BASE / name) != freeze[key]:
            raise ValueError("frozen file changed: " + name)
    if sha(Path(__file__)) != freeze["scriptSha256"]:
        raise ValueError("frozen diagnostic script changed")
    for entry in freeze["sources"]:
        if sha(BASE / entry["path"]) != entry["sha256"]:
            raise ValueError("source response changed")
    cases = json.loads((BASE / "cases.json").read_text())
    for case in cases:
        for path_key, hash_key in (("coordinatePath", "coordinateSha256"), ("scoreInputPath", "scoreInputSha256")):
            if sha(Path(case[path_key])) != case[hash_key]:
                raise ValueError("input changed: " + case["id"])
    return freeze, cases


def score_one(input_path, output_path):
    from contextlib import redirect_stdout, redirect_stderr
    from iotbx.cli_parser import run_program
    from mmtbx.programs.clashscore2 import Program

    buffer = io.StringIO()
    started = time.monotonic()
    with redirect_stdout(buffer), redirect_stderr(buffer):
        result = run_program(program_class=Program, args=[str(input_path), "keep_hydrogens=False", "do_flips=False", "nuclear=False", "b_factor_cutoff=None", "fast=False", "verbose=False", "json=False"], logger=buffer)
    report = json.loads(result.as_JSON())
    if len(report["summary_results"]) != 1:
        raise ValueError("single coordinate model required")
    summary = next(iter(report["summary_results"].values()))
    if not isinstance(summary["clashscore"], (int, float)) or not math.isfinite(summary["clashscore"]):
        raise ValueError("nonfinite or absent clashscore")
    if summary["num_clashes"] != len(report["flat_results"]):
        raise ValueError("clash count/detail mismatch")
    save(output_path, {"engine": "CCTBX Reduce2/Probe2", "version": importlib.metadata.version("cctbx-base"), "inputSha256": sha(input_path), "elapsedSeconds": time.monotonic() - started, "parameters": {"keepHydrogens": False, "doFlips": False, "nuclear": False, "bFactorCutoff": None}, "clashscore": summary["clashscore"], "numClashes": summary["num_clashes"], "report": report})
    output_path.with_suffix(".log").write_text(buffer.getvalue())


def run():
    freeze, cases = verify_inputs()
    if importlib.metadata.version("cctbx-base") != freeze["packages"]["cctbx-base"]:
        raise ValueError("engine version changed")

    def task(case):
        output = BASE / "reports" / case["group"] / (case["id"] + ".json")
        output.parent.mkdir(parents=True, exist_ok=True)
        status = "evaluable"
        error = None
        if not output.exists():
            env = dict(os.environ, OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1", MKL_NUM_THREADS="1")
            try:
                result = subprocess.run([sys.executable, str(Path(__file__).resolve()), "score-one", "--input", case["scoreInputPath"], "--output", str(output)], capture_output=True, text=True, timeout=180, env=env)
                if result.returncode:
                    status = "not_evaluable"
                    error = result.stderr[-3000:] or result.stdout[-3000:]
                    output.with_suffix(".error.log").write_text(result.stdout + "\n" + result.stderr)
            except subprocess.TimeoutExpired as exc:
                status = "not_evaluable"
                error = "external validator exceeded prospectively fixed 180 second case limit"
                output.with_suffix(".error.log").write_text(str(exc))
        if status == "evaluable":
            report = json.loads(output.read_text())
            if report["inputSha256"] != case["scoreInputSha256"]:
                raise ValueError("report input changed")
        else:
            report = {}
        return {"id": case["id"], "group": case["group"], "label": case["label"], "status": status, "clashscore": report.get("clashscore"), "num_clashes": report.get("numClashes"), "elapsed_seconds": report.get("elapsedSeconds"), "error": error}

    rows = []
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = {pool.submit(task, c): c for c in cases}
        for future in as_completed(futures):
            row = future.result()
            rows.append(row)
            print(json.dumps({"completed": len(rows), "total": len(cases), "id": row["id"], "status": row["status"]}), flush=True)
    order = {(c["group"], c["id"]): i for i, c in enumerate(cases)}
    rows.sort(key=lambda r: order[(r["group"], r["id"])])
    with (BASE / "outcomes.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    groups = {}
    for group in sorted({r["group"] for r in rows}):
        own = [r for r in rows if r["group"] == group]
        valid = [r for r in own if r["status"] == "evaluable"]
        values = sorted(r["clashscore"] for r in valid)
        groups[group] = {"cases": len(own), "evaluable": len(valid), "coverage": len(valid) / len(own), "clashscoreMin": min(values) if values else None, "clashscoreMax": max(values) if values else None,
                         "clashscoreMedian": ((values[(len(values)-1)//2] + values[len(values)//2]) / 2) if values else None, "modelsWithAtLeastOneClash": sum(r["num_clashes"] > 0 for r in valid)}
    save(BASE / "summary.json", {"version": freeze["version"], "freezeSha256": sha(BASE / "freeze.json"), "kind": freeze["kind"], "groups": groups, "publishedProblems": [r for r in rows if r["label"] == "published_problem"],
                                 "physicalSensitivity": None, "physicalSpecificity": None, "classifierValidated": False, "HelixIntegrated": False,
                                 "interpretation": "Physical steric observables are available where the external validator succeeds. An atomic clash is not a calibrated structure-level fold classifier, and reviewed repeat annotations do not certify absence of every physical modeling error.",
                                 "cost": {"modelCalls": 0, "awsInstances": 0}, "unevaluable": [r for r in rows if r["status"] != "evaluable"]})
    print(json.dumps({"groups": groups, "physicalSensitivity": None, "physicalSpecificity": None}))


def verify():
    _, cases = verify_inputs()
    summary = json.loads((BASE / "summary.json").read_text())
    with (BASE / "outcomes.csv").open() as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != len(cases):
        raise ValueError("outcome inventory mismatch")
    for case, row in zip(cases, rows):
        if (case["group"], case["id"]) != (row["group"], row["id"]):
            raise ValueError("outcome identity mismatch")
        if row["status"] == "evaluable":
            report = json.loads((BASE / "reports" / case["group"] / (case["id"] + ".json")).read_text())
            if report["inputSha256"] != case["scoreInputSha256"] or report["numClashes"] != len(report["report"]["flat_results"]) or float(row["clashscore"]) != report["clashscore"]:
                raise ValueError("clash report mismatch")
    if summary["physicalSensitivity"] is not None or summary["physicalSpecificity"] is not None:
        raise ValueError("unjustified classification metric")
    print(json.dumps({"ok": True, "cases": len(cases), "outputs": len(rows), "physicalClassificationMetrics": "not computed"}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["prepare", "run", "verify", "score-one"])
    parser.add_argument("--input", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.action == "score-one":
        score_one(args.input, args.output)
    else:
        globals()[args.action]()


if __name__ == "__main__":
    main()
