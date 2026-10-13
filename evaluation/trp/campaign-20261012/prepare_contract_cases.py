#!/usr/bin/env python3
"""Prospectively freeze synthetic contract cases without consulting validator outputs.

All structures remain development examples. Resource expectations refer to the
declared admission contract; actual resource feasibility is initially unknown.
"""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
from itertools import combinations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).resolve().parent
CORPUS = BASE / "contract-corpus"


def encoded(data):
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(data):
    return hashlib.sha256(data).hexdigest()


def write(name, value):
    path = CORPUS / name
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    return {"path": name, "sha256": digest(path.read_bytes()), "bytes": path.stat().st_size}


def main():
    if (CORPUS / "freeze.json").exists():
        raise SystemExit("Contract corpus freeze exists; preserve it and use a new dated corpus for amendments.")
    CORPUS.mkdir(parents=True, exist_ok=True)
    source_path = ROOT / "evaluation/trp/development/f3-reference-spec.json"
    source = json.loads(source_path.read_text())
    units = source["units"]["value"]["ranges"]
    valid = []
    for size in (3, 4, 6, 8, 10):
        candidates = sorted(combinations(range(len(units)), size),
                            key=lambda indices: digest(("contract-20261012|" + encoded(indices)).encode()))
        for indices in candidates[:10]:
            spec = deepcopy(source)
            spec["units"]["value"]["ranges"] = [deepcopy(units[i]) for i in indices]
            spec["units"]["origin"] = {
                "kind": "derived", "reference": "evaluation/trp/reference/geometre/units.json",
                "detail": "Fixed subset of published development units, not an independent biological annotation.",
            }
            identifier = f"G-valid-{len(valid)+1:03d}"
            valid.append({"id": identifier, "expected_contract_valid": True,
                          "oracle": "At least three resolved, disjoint original units; unchanged typed route and input identity.",
                          "unit_indices_zero_based": list(indices), "specification": spec})
    modes = (
        ("cycle", "cycle"), ("missing-dependency", "required-step"),
        ("excluded-operation", "excluded-operation"), ("format", "edge-format"),
        ("protein", "edge-protein"), ("chain", "edge-chain"),
        ("numbering", "edge-numbering"), ("insertions", "edge-insertionCodes"),
        ("confidence", "edge-confidence"), ("required-parameter", "schema"),
    )
    invalid = []
    for mode_index, (mode, expected_code) in enumerate(modes):
        for variant in range(3):
            base = valid[mode_index * 3 + variant]
            spec = deepcopy(base["specification"])
            edge = spec["graph"]["edges"][variant]
            if mode == "cycle":
                edge["from"] = edge["to"]
            elif mode == "missing-dependency":
                spec["graph"]["nodes"].pop(variant)
            elif mode == "excluded-operation":
                spec["graph"]["nodes"][-1]["operation"] = ("reupred.detect", "shell.exec", "unknown.compose")[variant]
            elif mode == "required-parameter":
                del spec[("chain", "model", "structure")[variant]]
            else:
                key = {"numbering": "numbering", "insertions": "insertionCodes"}.get(mode, mode)
                value = {
                    "format": ("mmcif", "json", "pdb"), "protein": ("1a0c", "1iq1", "P69905"),
                    "chain": ("B", "b", "label:A"), "numbering": ("uniprot", "label-seq-id", "unresolved"),
                    "insertions": ("excluded", "preserved", "unresolved"),
                    "confidence": ("plddt-0-100", "pae-angstrom", "ptm-0-1"),
                }[mode][variant]
                edge["contract"][key] = value
            invalid.append({"id": f"G-invalid-{mode}-{variant+1}",
                            "base_case": base["id"], "mode": mode,
                            "expected_contract_valid": False, "expected_code": expected_code,
                            "oracle": "Single declared contract perturbation; expected label fixed without inspecting validator output.",
                            "specification": spec})
    files = ROOT / "evaluation/trp/reference/nextflow-f5/evidence/run"
    materialized = {p.name: p.read_bytes() for p in files.iterdir() if p.is_file()}
    bundle = sum(len(b) for b in materialized.values())
    selected = len(materialized["selection.pdb"])
    demand = {"cpus": 3, "memoryBytes": 4096 * 1024**2,
              "workBytes": ((12 * 1024**2 + 7 * bundle + 4 * selected + 4095) // 4096) * 4096,
              "wallSeconds": 1080}
    resource = []
    for key, delta in (("cpus", 1), ("memoryBytes", 1024**2),
                       ("workBytes", 4096), ("wallSeconds", 1)):
        for expected in (True, False):
            for i in range(5):
                budget = deepcopy(demand)
                offset = i * delta if expected else -(i + 1) * delta
                budget[key] += offset
                # Below-budget fixtures can be invalid/nonpositive; their oracle
                # is still contract rejection, never a claim of observed OOM.
                resource.append({"id": f"R-contract-{key}-{'admit' if expected else 'reject'}-{i+1}",
                                 "varied_resource": key, "offset": offset, "declared_budget": budget,
                                 "expected_contract_admission": expected,
                                 "physical_feasibility": None, "observed_execution": None,
                                 "scope": "Synthetic admission boundary; excluded from R2.4 observed-feasibility rate until contrasted independently."})
    records = [write("graphs.json", {"kind": "engineering-contract-corpus", "held_out_biological": False,
                                      "source_structure": "2xqh/A", "unique_proteins": 1,
                                      "valid": valid, "invalid": invalid}),
               write("resources.json", {"kind": "engineering-admission-boundaries", "demand": demand,
                                         "formula": "ceil((12*1048576 + 7*bundleBytes + 4*selectionBytes)/4096)*4096",
                                         "input_materialization": "Frozen directory snapshot; not a new approved Helix proposal.",
                                         "cases": resource})]
    for path in (source_path, Path(__file__), ROOT / "packages/helix/src/trp/graph.ts",
                 ROOT / "packages/helix/src/trp/specification.ts", ROOT / "packages/helix/src/trp/resources.ts"):
        records.append({"source_path": path.relative_to(ROOT).as_posix(), "sha256": digest(path.read_bytes())})
    write("freeze.json", {"schema": "helix-contract-freeze/1.0", "frozen_at": datetime.now(timezone.utc).isoformat(),
                          "outputs_observed_before_freeze": False, "held_out_scientific_campaign": False,
                          "valid_graphs": 50, "invalid_graphs": 30,
                          "expected_admitted_resource_contracts": 20, "expected_rejected_resource_contracts": 20,
                          "preserved_protocol_thresholds": True, "files": records})
    print(json.dumps({"valid_graphs": len(valid), "invalid_graphs": len(invalid),
                      "resource_cases": len(resource), "R2.4_observed_feasibility_labels": 0}))


if __name__ == "__main__":
    main()
