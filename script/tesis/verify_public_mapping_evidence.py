#!/usr/bin/env python3
"""Verify sealed public mapping evidence without changing any input or report."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "evaluation/trp/campaign-20261012/mapping-public-contrasts"
sys.path.insert(0, str(Path(__file__).parent))
from public_mapping_contrasts import verify_sources


def read(path):
    return json.loads(Path(path).read_text())


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify():
    verify_sources()
    protocol = read(BASE / "protocol.json")
    audit = read(BASE / "audit.json")
    freeze = read(BASE / "oracle-freeze.json")
    ids = [c["id"] for c in protocol["cases"]]
    assert len(ids) == 30 == len(set(ids))
    assert {r["id"] for r in audit["rows"]} == set(ids)
    assert audit["oracleAgreement"] and audit["mismatches"] == []
    assert audit["verifierSha256"] == sha(ROOT / "script/tesis/audit_public_mapping_contrasts.py")
    assert read(BASE / "audit-method.json")["sha256"] == audit["verifierSha256"]
    assert freeze["producerOutputsObserved"] is False
    for record in freeze["files"]:
        path = ROOT / record["path"]
        assert path.stat().st_size == record["bytes"] and sha(path) == record["sha256"], record["path"]
    acquisition = read(BASE / "acquisition.json")
    assert {r["case"]["id"] for r in acquisition} == set(ids)
    for entry in acquisition:
        assert {r["kind"] for r in entry["records"]} == {"cif", "pdb", "sifts"}
        assert all(r["status"] == "available" and r["bytes"] <= 20_000_000 for r in entry["records"])
        sifts = next(r for r in entry["records"] if r["kind"] == "sifts")
        assert sifts["availabilityFallback"]
        assert sifts["url"] == entry["case"]["siftsAvailabilityFallbackUrl"]
    labels = 0
    prepared = 0
    for case in ids:
        oracle = read(BASE / "oracle" / (case + ".json"))
        actual = read(BASE / "reports" / (case + ".json"))
        expected_labels = [r["label"] for r in oracle["labelRows"]]
        actual_labels = [r["label"] for r in actual["labelOutcomes"]]
        assert len(actual_labels) == len(set(actual_labels)) == len(expected_labels)
        assert set(actual_labels) == set(expected_labels)
        labels += len(expected_labels)
        if actual["prepared"]["status"] == "mapped":
            expected = oracle["expectedPreparedMapping"]
            assert expected is not None
            assert actual["prepared"]["audit"]["mapping"] == [{k: v for k, v in r.items() if k != "uniprot"} for r in expected]
            prepared += len(expected)
        else:
            assert oracle["expectedPreparedError"] == actual["prepared"]["error"]["code"] == "sifts-identity"
    assert labels == audit["labelPositions"] == audit["labelMapped"]
    assert prepared == audit["preparedMappedResidues"]
    replay = read(BASE / "reproduction/verification.json")
    assert replay["ok"] and replay["primaryOutcomesPreserved"] and replay["newScientificCases"] == 0
    assert {r["id"] for r in replay["results"]} == {"1bhe-A", "2bm4-A", "1o8i-A"}
    for row in replay["results"]:
        case = row["id"]
        assert row["byteIdentical"]
        assert row["primarySha256"] == row["reproducedSha256"] == sha(BASE / "reports" / (case + ".json"))
        assert sha(BASE / "reproduction" / (case + "-primary.json")) == row["primarySha256"]
        assert sha(BASE / "reproduction" / (case + "-reproduced.json")) == row["primarySha256"]
    if (BASE / "manifest.json").exists():
        manifest = read(BASE / "manifest.json")
        paths = {str(p.relative_to(ROOT)) for p in BASE.rglob("*") if p.is_file() and p.name != "manifest.json"}
        assert paths == {r["path"] for r in manifest["files"]}
        for record in manifest["files"] + manifest["helpers"]:
            path = ROOT / record["path"]
            assert path.stat().st_size == record["bytes"] and sha(path) == record["sha256"], record["path"]
    return {"ok": True, "chains": len(ids), "labelResidues": labels, "preparedResidues": prepared,
            "reproducedCases": len(replay["results"]), "byteIdentical": True, "frozenExpectationsUnchanged": True,
            "discrepancies": 0, "noProductionMutation": True}


if __name__ == "__main__":
    print(json.dumps(verify(), ensure_ascii=False))
