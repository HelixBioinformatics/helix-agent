#!/usr/bin/env python3
"""Independently verify the bounded steric campaign using the Python stdlib."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import statistics

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "evaluation/trp/campaign-20261012/structural"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(inputs=False):
    manifest = json.loads((BASE / "manifest.json").read_text())
    for entry in manifest["files"]:
        relative = Path(entry["path"])
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("unsafe evidence path")
        path = BASE / relative
        if path.is_symlink() or path.stat().st_size != entry["bytes"] or sha(path) != entry["sha256"]:
            raise ValueError("evidence changed: " + entry["path"])
    freeze = json.loads((BASE / "freeze.json").read_text())
    for name, key in (("cases.json", "casesSha256"), ("candidates.json", "candidatesSha256"), ("protocol.json", "protocolSha256")):
        if sha(BASE / name) != freeze[key]:
            raise ValueError("frozen source changed")
    for resource in ("geostd-library-complete.json", "chemical-components.json"):
        library = json.loads((BASE / resource).read_text())
        if inputs:
            for entry in library["files"]:
                path = Path(library["localPath"]) / entry["path"]
                if path.stat().st_size != entry["bytes"] or sha(path) != entry["sha256"]:
                    raise ValueError("installed chemistry source changed")
    cases = json.loads((BASE / "cases.json").read_text())
    with (BASE / "outcomes.csv").open() as stream:
        rows = list(csv.DictReader(stream))
    if len(cases) != 108 or len(rows) != len(cases):
        raise ValueError("case count differs")
    references = [case for case in cases if case["group"] != "pratt-original"]
    if len(references) != 30 or len({case["pdb"] for case in references}) != 30:
        raise ValueError("reference cohort differs")
    proteins = []
    for case in references:
        annotation = json.loads((ROOT / case["annotationPath"]).read_text())
        content = annotation["content"]
        if sha(ROOT / case["annotationPath"]) != case["annotationSha256"] or not content.get("reviewed") or content["chain"]["source"] != "RCSB/PDB":
            raise ValueError("reviewed experimental reference differs")
        if content["chain"]["structure"].lower() != case["pdb"] or content["chain"]["id"] != case["chain"] or case["physicalFailureLabel"] is not None:
            raise ValueError("reference identity or unsupported physical label")
        proteins.extend(case["uniprot"])
    if len(proteins) != len(set(proteins)):
        raise ValueError("duplicate mapped protein identity")
    for case, row in zip(cases, rows):
        if (case["group"], case["id"]) != (row["group"], row["id"]):
            raise ValueError("case identity differs")
        if inputs:
            for field, key in (("coordinatePath", "coordinateSha256"), ("scoreInputPath", "scoreInputSha256")):
                if sha(Path(case[field])) != case[key]:
                    raise ValueError("coordinate input changed")
        if row["status"] == "not_evaluable":
            if row["clashscore"] or row["num_clashes"] or not row["error"]:
                raise ValueError("unevaluable case given a numeric result")
            continue
        if row["status"] != "evaluable":
            raise ValueError("unknown evaluation status")
        report = json.loads((BASE / "reports" / case["group"] / (case["id"] + ".json")).read_text())
        flat = report["report"]["flat_results"]
        count = report["numClashes"]
        score = report["clashscore"]
        if report["inputSha256"] != case["scoreInputSha256"] or count != len(flat) or int(row["num_clashes"]) != count or float(row["clashscore"]) != score:
            raise ValueError("external report correspondence differs")
        if not math.isfinite(score) or score < 0 or not isinstance(count, int):
            raise ValueError("invalid physical observable")
        if any(clash["overlap"] > -0.4 or clash["probe_type"] != "bo" for clash in flat):
            raise ValueError("reported severe clash violates external method criterion")
        if count:
            denominator = count * 1000 / score
            if denominator <= 0 or abs(denominator - round(denominator)) > 1e-6:
                raise ValueError("clashscore/count denominator inconsistency")
        elif score != 0:
            raise ValueError("nonzero score without clashes")
    summary = json.loads((BASE / "summary.json").read_text())
    for group, record in summary["groups"].items():
        own = [row for row in rows if row["group"] == group]
        valid = [row for row in own if row["status"] == "evaluable"]
        scores = [float(row["clashscore"]) for row in valid]
        if record["cases"] != len(own) or record["evaluable"] != len(valid) or record["coverage"] != len(valid) / len(own):
            raise ValueError("group denominator differs")
        if scores and (record["clashscoreMin"] != min(scores) or record["clashscoreMax"] != max(scores) or record["clashscoreMedian"] != statistics.median(scores)):
            raise ValueError("group statistics differ")
    if summary["physicalSensitivity"] is not None or summary["physicalSpecificity"] is not None or summary["classifierValidated"]:
        raise ValueError("unjustified physical classification claim")
    adapter = json.loads((BASE / "agent-reference.json").read_text())
    physical = next(check for check in adapter["report"]["checks"] if check["id"] == "fold-plausibility")
    diagnostic = physical["value"]["stericDiagnostic"]
    reference = next(row for row in rows if row["group"] == "pratt-original" and row["id"] == "8b")
    if physical["status"] != "not_evaluable" or diagnostic["status"] != "measured" or diagnostic["foldVerdict"] != "not_established" or diagnostic["structureLevelThreshold"] is not None:
        raise ValueError("unsupported production physical verdict")
    if diagnostic["measurement"]["severeClashes"] != int(reference["num_clashes"]) or diagnostic["measurement"]["clashscore"] != float(reference["clashscore"]):
        raise ValueError("production/external observable differs")
    return {"ok": True, "cases": len(cases), "reviewedExperimentalReferences": len(references), "manifestFiles": len(manifest["files"]), "rawInputsAndInstalledChemistryVerified": inputs,
            "physicalClassificationMetrics": "not established", "productionObservableMatchesFrozenExternalRun": True}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", action="store_true")
    args = parser.parse_args()
    print(json.dumps(verify(args.inputs), sort_keys=True))
