#!/usr/bin/env python3
"""Verify the saved cluster smoke test without an AWS account or credentials."""

import csv
import hashlib
import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "evaluation/trp/aws-academy-cluster-20261012"
REFERENCE = (
    ROOT / "evaluation/trp/reference/nextflow-f5/evidence/run/results/geometry.csv"
)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    manifest = json.loads((EVIDENCE / "manifest.json").read_text())
    for artifact in manifest["files"]:
        path = EVIDENCE / artifact["path"]
        assert path.is_file() and path.stat().st_size == artifact["bytes"]
        assert sha256(path) == artifact["sha256"], artifact["path"]
    initial = EVIDENCE / "initial-run/results/geometry.csv"
    controlled = EVIDENCE / "controlled-run/results/geometry.csv"
    assert controlled.read_bytes() == REFERENCE.read_bytes(), (
        "Controlled cluster CSV differs from frozen local reference"
    )
    assert initial.read_bytes() != REFERENCE.read_bytes(), (
        "The original cross-processor discrepancy must remain visible"
    )
    with controlled.open() as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 14
    for row in rows:
        for field in (
            "curvature",
            "twist",
            "twist_hand",
            "pitch",
            "pitch_hand",
            "tmscore",
            "yaw",
        ):
            assert math.isfinite(float(row[field]))
    with (EVIDENCE / "controlled-run/trace.tsv").open() as stream:
        trace = list(csv.DictReader(stream, delimiter="\t"))
    assert len(trace) == 2
    jobs = (EVIDENCE / "controlled-run/slurm-jobs.txt").read_text()
    for row, node in zip(trace, ("helix-worker1", "helix-worker2")):
        assert row["status"] == "COMPLETED" and row["exit"] == "0"
        record = next(
            line
            for line in jobs.splitlines()
            if line.startswith("JobId=" + row["native_id"] + " ")
        )
        assert "NodeList=" + node in record and "JobState=COMPLETED" in record
    checks = EVIDENCE / "cluster-checks"
    for node in ("helix-worker1", "helix-worker2"):
        limits = json.loads((checks / ("runtime-limits-" + node + ".json")).read_text())
        assert limits["cpu_max"] == "200000 100000"
        assert limits["memory_max"] == "2147483648" and limits["swap_max"] == "0"
        assert all(
            library["architecture"] == "Haswell" and library["num_threads"] == 1
            for library in limits["blas"]
        )
    assert "JobState=RUNNING" in (checks / "cancellation-before.txt").read_text()
    assert "JobState=CANCELLED" in (checks / "cancellation-after.txt").read_text()
    assert (
        checks / "persistence-sentinel.txt"
    ).read_text().strip() == "persistent-after-poweroff"
    assert "helix-worker1" in (checks / "resumed-hostnames.txt").read_text()
    assert "helix-worker2" in (checks / "resumed-hostnames.txt").read_text()
    renewal = json.loads((EVIDENCE / "session-renewal.json").read_text())
    assert renewal["before"]["Session to end"] != renewal["after"]["Session to end"]
    print(
        json.dumps(
            {
                "verified": True,
                "csv_rows": len(rows),
                "sha256": sha256(controlled),
                "scientific_jobs": len(trace),
                "workers": 2,
                "scope": "Infrastructure and one fixed Nextflow workflow; Helix remote adapter and full campaign remain pending",
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
