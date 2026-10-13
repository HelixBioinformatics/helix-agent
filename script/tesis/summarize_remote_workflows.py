#!/usr/bin/env python3
"""Audit every retained attempt of the frozen remote development graph campaign.

This is an offline evidence audit. It does not submit, retry or repair jobs.
Original failures stay in the denominator even when a later revision succeeds.
The corpus contains one development protein, not independent biological cases.
"""
import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

from audit_remote_campaign import audit, record

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "evaluation/trp/campaign-20261012"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_text())


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    temporary.replace(path)


def numerical_reference(case_path, expected, run, reference):
    """Bind the independent standalone output to frozen inputs and actual argv."""
    spec = record(run, "specification.json")
    for field in ("chain", "model", "units", "insertions"):
        if spec[field]["value"] != expected[field]["value"]:
            raise ValueError("Executed specification differs from frozen case: " + field)
    if spec["graph"] != expected["graph"]:
        raise ValueError("Executed graph differs from frozen case")
    source = ROOT / expected["structure"]["value"]["path"]
    if sha(source) != expected["structure"]["value"]["sha256"]:
        raise ValueError("Frozen structure changed")
    if sha(run / "source.pdb") != sha(source):
        raise ValueError("Executed source differs from frozen input")
    execution = load(case_path.parent / "standalone-reference/execution.json")
    argv = execution["argv"]
    image = record(run, "execution.json")["container"]
    if execution["exitCode"] != 0 or image not in argv:
        raise ValueError("Standalone comparator did not execute the same exact image")
    ranges = lambda items: ",".join(f"{x['start']}_{x['end']}" for x in items)
    required = ["single", "/work/2xqh.pdb", expected["chain"]["value"],
                "/work/geometry.csv", ranges(expected["units"]["value"]["ranges"])]
    index = argv.index("single")
    if argv[index:index+len(required)] != required:
        raise ValueError("Standalone comparator belongs to different input settings")
    if expected["insertions"]["value"]:
        if argv[index+len(required):] != ["-ins_def", ranges(expected["insertions"]["value"])]:
            raise ValueError("Standalone insertion contract differs")
    elif argv[index+len(required):]:
        raise ValueError("Unexpected standalone arguments")
    for name in ("OPENBLAS_CORETYPE=Haswell", "OPENBLAS_NUM_THREADS=1", "OMP_NUM_THREADS=1", "MKL_NUM_THREADS=1"):
        if name not in argv:
            raise ValueError("Standalone numerical profile is absent: " + name)
    selected = case_path.parent / "standalone-reference/2xqh.pdb"
    # SELECT output, retained in the actual workflow, is compared with the
    # input mounted in the separately launched standalone container.
    outputs = list((run / "work").glob("*/*/selected.pdb"))
    if not outputs:
        outputs = list((run / "work").glob("*/*/2xqh.pdb"))
    if not outputs or not any(sha(candidate) == sha(selected) for candidate in outputs):
        raise ValueError("Standalone selected input is not linked to recorded SELECT output")
    gold = case_path.parent / "standalone-reference/geometry.csv"
    actual = run / "results/geometry.csv"
    row = load(case_path)
    if sha(gold) != row["localCsvSha256"] or sha(actual) != row["remoteCsvSha256"] or gold.read_bytes() != actual.read_bytes():
        raise ValueError("Per-input CSV comparison differs from its external anchor")
    reference.mkdir(parents=True, exist_ok=True)
    save(reference / "specification.json", expected)
    (reference / "source.pdb").write_bytes(source.read_bytes())
    (reference / "results").mkdir(exist_ok=True)
    (reference / "results/geometry.csv").write_bytes(gold.read_bytes())
    return {"frozen_source_sha256": sha(source), "selected_sha256": sha(selected),
            "standalone_execution_sha256": sha(case_path.parent / "standalone-reference/execution.json"),
            "csv_sha256": sha(actual), "same_tool_comparator_not_biological_truth": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-complete", action="store_true")
    parser.add_argument("--output", type=Path, default=BASE / "cloud/workflow-summary.json")
    args = parser.parse_args()
    freeze = load(BASE / "contract-corpus/freeze.json")
    expected_graph_hash = next(item["sha256"] for item in freeze["files"] if item["path"] == "graphs.json")
    if sha(BASE / "contract-corpus/graphs.json") != expected_graph_hash:
        raise ValueError("Graph corpus no longer matches its prospective freeze")
    corpus = load(BASE / "contract-corpus/graphs.json")
    frozen = {item["id"]: item for item in corpus["valid"]}
    attempts = []
    paths = sorted((BASE / "cloud").glob("lab*/workflows*/G-valid-*/case.json"))
    for case_path in paths:
        raw = load(case_path)
        identifier = raw["id"]
        if identifier not in frozen:
            raise ValueError("Unfrozen workflow ID: " + identifier)
        label = case_path.parent.parent.parent.name + "-" + case_path.parent.parent.name + "-" + identifier
        row = {"id": identifier, "lab": case_path.parent.parent.parent.name,
               "revision_directory": case_path.parent.parent.name,
               "case_path": case_path.relative_to(ROOT).as_posix(),
               "case_sha256": sha(case_path), "status": raw["status"],
               "units": len(frozen[identifier]["specification"]["units"]["value"]["ranges"]),
               "verified": False, "numerical_equal": None}
        if raw["status"] != "succeeded":
            row["cause"] = raw.get("cause", "not recorded")
            row["failure_preserved"] = (case_path.parent / "failure").exists()
            attempts.append(row)
            continue
        report_path = BASE / "trace" / (args.output.stem + "-audits") / (label + ".json")
        reference = BASE / "trace/workflow-references" / label
        oracle_path = BASE / "trace/workflow-oracles" / (label + ".json")
        try:
            check = numerical_reference(case_path, frozen[identifier]["specification"], case_path.parent / "evidence/run", reference)
            actions = raw["actions"]
            if [action["action"] for action in actions] != ["permission", "approval"]:
                raise ValueError("Independent driver did not observe one permission and one approval")
            if actions[1]["digest"] != raw["digest"] or actions[1]["answer"] != "Aprobar y ejecutar":
                raise ValueError("Observed driver approval belongs to a different proposal")
            protocol = record(case_path.parent / "evidence/run", "protocol.json")
            # Expected gate counts derive from the prescribed execution path
            # and externally observed driver actions, never by reading events.
            expected_events = [("admission", "accepted-for-review"),
                               ("protocol", "checked" if protocol["check"]["committed"] else "not-committed"),
                               ("permission", "requested"), ("permission", "returned-allowed"),
                               ("approval", "requested"), ("approval", "answered"),
                               ("admission", "recheck-accepted"), ("execution", "remote-started"),
                               ("admission", "analysis-accepted"), ("execution", "completed")]
            save(oracle_path, {"kind": "Independent driver actions and required successful-path gate counts",
                               "driver_case_sha256": row["case_sha256"], "human_annotation": False,
                               "expected": [{"source": source, "outcome": outcome, "count": 1} for source, outcome in expected_events]})
            result = audit(SimpleNamespace(bundle=case_path.parent / "evidence", sha256=raw["manifestSha256"],
                            expected_outcome="succeeded", event_oracle=oracle_path, reference_run=reference,
                            require_reference=True, fault_injection=False, output=report_path))
            save(report_path, result)
            row.update(verified=result["verified"], numerical_equal=True,
                       manifest_sha256=raw["manifestSha256"],
                       audit_path=report_path.relative_to(ROOT).as_posix(),
                       audit_sha256=sha(report_path), numerical_reference=check)
            if not result["verified"]:
                row["verification_errors"] = [c for c in result["checks"] if not c["passed"]]
        except (OSError, ValueError, KeyError, StopIteration) as error:
            row["verification_error"] = str(error)
        attempts.append(row)
    by_id = {identifier: [row for row in attempts if row["id"] == identifier] for identifier in frozen}
    first = [next((row for row in rows if row["revision_directory"] == "workflows"), rows[0])
             for rows in by_id.values() if rows]
    completed = sorted(identifier for identifier, rows in by_id.items() if any(row["verified"] for row in rows))
    summary = {
        "schema": "helix-remote-development-workflows/1.0",
        "audited_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "Frozen graph variants on one development protein 2XQH/A; synthetic approval, not held-out biological or human evaluation",
        "frozen_cases": len(frozen), "unique_proteins": 1,
        "attempts": attempts,
        "counts": {"attempts": len(attempts), "first_attempts": len(first),
                   "first_attempt_succeeded": sum(row["verified"] for row in first),
                   "first_attempt_failed": sum(row["status"] == "failed" for row in first),
                   "first_attempt_unverified_success": sum(row["status"] == "succeeded" and not row["verified"] for row in first),
                   "retry_attempts": len(attempts)-len(first), "unique_cases_verified": len(completed),
                   "unique_cases_not_observed": sum(not rows for rows in by_id.values())},
        "verified_case_ids": completed,
        "by_lab": {lab: dict(Counter(row["status"] for row in attempts if row["lab"] == lab)) for lab in sorted({row["lab"] for row in attempts})},
        "all_50_cases_verified": len(completed) == len(frozen),
        "scientific_R1_5_rate": None,
        "limitation": "Retries are engineering repairs and do not erase first-attempt failures or establish the reserved scientific metric.",
    }
    save(args.output, summary)
    csv_path = args.output.with_suffix(".csv")
    fields = ["id", "lab", "revision_directory", "status", "units", "verified", "numerical_equal", "case_path", "audit_path", "cause", "verification_error"]
    with csv_path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(attempts)
    print(json.dumps({"counts": summary["counts"], "all_50_cases_verified": summary["all_50_cases_verified"],
                      "verification_errors": [row for row in attempts if row.get("verification_error") or row.get("verification_errors")]}, ensure_ascii=False))
    return 1 if (args.require_complete and not summary["all_50_cases_verified"]) or any(row["status"] == "succeeded" and not row["verified"] for row in attempts) else 0


if __name__ == "__main__":
    raise SystemExit(main())
