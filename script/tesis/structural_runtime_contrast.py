#!/usr/bin/env python3
"""Prospective secondary runtime contrast for the three primary timeouts.

Preserve primary results. Retry unchanged inputs/method once, sequentially,
with a 600 second external computational cap and no classification threshold.
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
import statistics
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
PRIMARY = ROOT / "evaluation/trp/campaign-20261012/structural"
BASE = PRIMARY / "runtime-600"
DRIVER = ROOT / "script/tesis/structural_campaign.py"
IDS = {"23ab", "1ea0-A", "1llw-A"}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n")


def sources():
    records = [{"kind": "primary", "path": str(PRIMARY / name), "sha256": sha(PRIMARY / name)} for name in ("freeze.json", "manifest.json", "protocol.json", "cases.json", "summary.json", "outcomes.csv")]
    for name in ("geostd-library-complete.json", "chemical-components.json"):
        manifest = json.loads((PRIMARY / name).read_text())
        for entry in manifest["files"]:
            path = Path(manifest["localPath"]) / entry["path"]
            if path.stat().st_size != entry["bytes"] or sha(path) != entry["sha256"]:
                raise ValueError("chemistry resource changed")
            records.append({"kind": "chemistry", "path": str(path), "sha256": sha(path)})
    diagnostic = next(check for check in json.loads((PRIMARY / "agent-reference.json").read_text())["report"]["checks"] if check["id"] == "fold-plausibility")["value"]["stericDiagnostic"]
    site = Path(sys.prefix) / "lib/python3.12/site-packages"
    for name, expected in diagnostic["engine"]["modulesSha256"].items():
        if name.startswith("mmtbx/"):
            path = site / name
        else:
            matches = list(site.glob(name + "*.so"))
            if len(matches) != 1:
                raise ValueError("compiled engine identity ambiguous")
            path = matches[0]
        if sha(path) != expected:
            raise ValueError("external engine changed")
        records.append({"kind": "engine", "path": str(path), "sha256": sha(path)})
    records.append({"kind": "driver", "path": str(DRIVER), "sha256": sha(DRIVER)})
    records.append({"kind": "secondary-driver", "path": str(Path(__file__).resolve()), "sha256": sha(Path(__file__))})
    return records


def prepare():
    if (BASE / "freeze.json").exists():
        raise ValueError("secondary freeze exists; do not overwrite")
    with (PRIMARY / "outcomes.csv").open() as stream:
        primary_rows = list(csv.DictReader(stream))
    selected_rows = [row for row in primary_rows if row["id"] in IDS]
    if len(selected_rows) != 3 or any(row["status"] != "not_evaluable" or "180 second" not in row["error"] for row in selected_rows):
        raise ValueError("primary timeout inventory differs")
    cases = [case for case in json.loads((PRIMARY / "cases.json").read_text()) if case["id"] in IDS]
    cases.sort(key=lambda case: ["23ab", "1ea0-A", "1llw-A"].index(case["id"]))
    for case in cases:
        if sha(Path(case["scoreInputPath"])) != case["scoreInputSha256"]:
            raise ValueError("original input changed")
    save(BASE / "freeze.json", {"version": "structural-runtime-contrast/1.0.0", "createdUTC": datetime.now(timezone.utc).isoformat(), "kind": "prospective secondary computational-cap contrast after primary180s failures",
                               "reason": "Determine whether the external computational cap alone accounts for the three primary unevaluable results. No physical classifier, biological threshold, labels or coordinate preparation are changed.",
                               "primaryTimeoutSeconds": 180, "secondaryTimeoutSeconds": 600, "workers": 1, "maximumAttemptsPerCase": 1, "selectedCases": cases, "primaryRows": selected_rows,
                               "primaryEvaluable": 105, "primaryTotal": 108, "sources": sources(), "packages": {name: importlib.metadata.version(name) for name in ("cctbx-base", "gemmi", "numpy", "scipy")}, "python": sys.version,
                               "interpretation": "Primary failures and denominators remain unchanged. Report secondary successes and expanded-profile availability separately."
                               })
    print(json.dumps({"prepared": len(cases), "timeoutSeconds": 600, "workers": 1, "primaryPreserved": True}))


def verify_frozen():
    freeze = json.loads((BASE / "freeze.json").read_text())
    if freeze["sources"] != sources():
        raise ValueError("frozen method or primary evidence changed")
    if freeze["packages"] != {name: importlib.metadata.version(name) for name in freeze["packages"]}:
        raise ValueError("package version changed")
    for case in freeze["selectedCases"]:
        if sha(Path(case["scoreInputPath"])) != case["scoreInputSha256"]:
            raise ValueError("case coordinate identity changed")
    return freeze


def run():
    freeze = verify_frozen()
    if (BASE / "summary.json").exists():
        raise ValueError("secondary contrast already completed; never retry indefinitely")
    rows = []
    for case in freeze["selectedCases"]:
        output = BASE / "reports" / case["group"] / (case["id"] + ".json")
        output.parent.mkdir(parents=True, exist_ok=True)
        attempt = output.with_suffix(".attempt.json")
        if attempt.exists():
            raise ValueError("attempt already exists; investigate authoritative process state before resuming")
        started = time.monotonic()
        save(attempt, {"id": case["id"], "startedUTC": datetime.now(timezone.utc).isoformat(), "controllerPid": os.getpid(), "timeoutSeconds": 600, "status": "running"})
        status = "evaluable"
        error = None
        try:
            result = subprocess.run([sys.executable, str(DRIVER), "score-one", "--input", case["scoreInputPath"], "--output", str(output)], capture_output=True, text=True, timeout=600,
                                    env=dict(os.environ, OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1", MKL_NUM_THREADS="1"))
            if result.returncode:
                status = "not_evaluable"
                error = result.stderr[-3000:] or result.stdout[-3000:]
                output.with_suffix(".error.log").write_text(result.stdout + "\n" + result.stderr)
        except subprocess.TimeoutExpired:
            status = "not_evaluable"
            error = "external validator exceeded secondary600s computational cap"
            output.with_suffix(".error.log").write_text(error + "\n")
        elapsed = time.monotonic() - started
        report = json.loads(output.read_text()) if status == "evaluable" else {}
        if report and report["inputSha256"] != case["scoreInputSha256"]:
            raise ValueError("secondary output input differs")
        row = {"id": case["id"], "group": case["group"], "status": status, "clashscore": report.get("clashscore"), "num_clashes": report.get("numClashes"), "elapsed_seconds": elapsed, "error": error}
        rows.append(row)
        save(attempt, {"id": case["id"], "completedUTC": datetime.now(timezone.utc).isoformat(), "timeoutSeconds": 600, "status": status, "elapsedSeconds": elapsed})
        save(BASE / "progress.json", {"completed": len(rows), "total": 3, "rows": rows})
        print(json.dumps({"completed": len(rows), "total": 3, "id": case["id"], "status": status, "elapsedSeconds": elapsed}), flush=True)
    with (BASE / "outcomes.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    with (PRIMARY / "outcomes.csv").open() as stream:
        primary_rows = list(csv.DictReader(stream))
    secondary_by_id = {row["id"]: row for row in rows}
    expanded = []
    for row in primary_rows:
        if row["id"] in secondary_by_id:
            secondary = secondary_by_id[row["id"]]
            expanded.append({**row, **secondary})
        else:
            expanded.append(row)
    groups = {}
    for group in sorted({row["group"] for row in expanded}):
        own = [row for row in expanded if row["group"] == group]
        valid = [row for row in own if row["status"] == "evaluable"]
        scores = [float(row["clashscore"]) for row in valid]
        groups[group] = {"cases": len(own), "evaluable": len(valid), "coverage": len(valid) / len(own), "clashscoreMedian": statistics.median(scores), "clashscoreMin": min(scores), "clashscoreMax": max(scores)}
    save(BASE / "summary.json", {"version": freeze["version"], "freezeSha256": sha(BASE / "freeze.json"), "primaryPreserved": True, "primaryEvaluable": 105, "primaryTotal": 108,
                                "secondaryRetried": 3, "secondaryRecovered": sum(row["status"] == "evaluable" for row in rows), "secondaryRows": rows, "expandedProfile": groups,
                                "physicalSensitivity": None, "physicalSpecificity": None, "classifierValidated": False,
                                "meaning": "A bounded technical runtime contrast, not a new biological criterion or a replacement of primary180s failures."})
    verify_frozen()
    files = [{"path": path.relative_to(BASE).as_posix(), "bytes": path.stat().st_size, "sha256": sha(path)} for path in sorted(BASE.rglob("*")) if path.is_file() and path.name != "manifest.json"]
    save(BASE / "manifest.json", {"version": "structural-runtime-secondary-evidence/1.0.0", "files": files})
    print(json.dumps({"secondaryRecovered": sum(row["status"] == "evaluable" for row in rows), "expandedProfile": groups, "primaryPreserved": True}))


def verify():
    freeze = verify_frozen()
    manifest = json.loads((BASE / "manifest.json").read_text())
    for entry in manifest["files"]:
        path = BASE / entry["path"]
        if path.stat().st_size != entry["bytes"] or sha(path) != entry["sha256"]:
            raise ValueError("secondary output changed")
    with (BASE / "outcomes.csv").open() as stream:
        rows = list(csv.DictReader(stream))
    if [row["id"] for row in rows] != [case["id"] for case in freeze["selectedCases"]]:
        raise ValueError("secondary identity differs")
    for case, row in zip(freeze["selectedCases"], rows):
        if row["status"] == "evaluable":
            report = json.loads((BASE / "reports" / case["group"] / (case["id"] + ".json")).read_text())
            if report["inputSha256"] != case["scoreInputSha256"] or report["numClashes"] != int(row["num_clashes"]) or report["clashscore"] != float(row["clashscore"]):
                raise ValueError("secondary observable differs")
            if report["numClashes"] != len(report["report"]["flat_results"]) or any(contact["overlap"] > -0.4 for contact in report["report"]["flat_results"]):
                raise ValueError("invalid clash records")
            if not math.isfinite(report["clashscore"]):
                raise ValueError("nonfinite clashscore")
        elif row["clashscore"] or not row["error"]:
            raise ValueError("unevaluable case has result")
    summary = json.loads((BASE / "summary.json").read_text())
    if summary["physicalSensitivity"] is not None or summary["physicalSpecificity"] is not None or summary["classifierValidated"]:
        raise ValueError("unsupported physical classification")
    print(json.dumps({"ok": True, "cases": len(rows), "primaryPreserved": True, "secondaryRecovered": summary["secondaryRecovered"]}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["prepare", "run", "verify"])
    args = parser.parse_args()
    globals()[args.action]()
