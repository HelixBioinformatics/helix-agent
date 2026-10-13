#!/usr/bin/env python3
"""Audit produced public mapping data against frozen independent expectations."""
import csv
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "evaluation/trp/campaign-20261012/mapping-public-contrasts"
sys.path.insert(0, str(Path(__file__).parent))
from public_mapping_contrasts import verify_sources


def load(path):
    return json.loads(Path(path).read_text())


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def audit():
    verify_sources()
    rows, residues, mismatches = [], [], []
    runs = {r["id"]: r for r in load(BASE / "run-summary.json")["rows"]}
    for entry in load(BASE / "oracle-index.json"):
        case = entry["case"]
        if entry["status"] != "oracle_ready" or runs[case["id"]]["status"] != "completed":
            rows.append({"id": case["id"], "pdb": case["pdb"], "chain": case["chain"], "status": runs[case["id"]]["status"], "observed_labels": None})
            continue
        oracle = load(ROOT / entry["oraclePath"])
        actual = load(BASE / "reports" / (case["id"] + ".json"))
        assert actual["sourceHashes"] == {kind: oracle["sources"][kind]["xmlSha256" if kind == "sifts" else "sha256"] for kind in ("cif", "pdb", "sifts")}
        expected_error = oracle["sifts"]["expectedParserError"]
        if expected_error is None:
            sifts_equal = actual["sifts"]["status"] == "mapped" and actual["sifts"]["value"]["rows"] == oracle["sifts"]["expectedRows"]
        else:
            sifts_equal = actual["sifts"]["status"] == "rejected" and expected_error in actual["sifts"]["error"]["message"]
        if not sifts_equal:
            mismatches.append({"id": case["id"], "stage": "sifts_parser", "expectedError": expected_error, "actualStatus": actual["sifts"]["status"]})
        inspected = actual["inspection"]["status"] == "completed"
        admitted = inspected and actual["inspection"]["source"]["summary"]["mechanicalAdmission"] and actual["inspection"]["target"]["summary"]["mechanicalAdmission"]
        outcomes = {r["label"]: r for r in actual["labelOutcomes"]}
        mapped, correct, unsupported, guarded = 0, 0, 0, 0
        for expected in oracle["labelRows"]:
            found = outcomes[expected["label"]]
            wanted = expected["expectedMapping"]
            if found["status"] == "mapped":
                mapped += 1
                equal = wanted is not None and found["value"]["mapping"] == [wanted] and found["value"]["ranges"] == [{"start": wanted["author"], "end": wanted["author"]}]
            elif not admitted:
                guarded += 1
                equal = found["status"] in ("rejected", "unavailable-inspection")
            else:
                unsupported += 1
                equal = wanted is None and found["status"] == "rejected"
            correct += equal
            if not equal:
                mismatches.append({"id": case["id"], "stage": "label_to_author", "label": expected["label"], "expected": wanted, "actual": found})
            residues.append({"case": case["id"], "label": expected["label"], "expected_author": None if wanted is None else wanted["author"],
                             "reference_unmappable_reason": expected["unmappableReason"], "producer_status": found["status"],
                             "inspection_admitted": admitted, "agrees_with_guarded_contract": equal})
        prepared_expected = oracle["expectedPreparedMapping"]
        if actual["prepared"]["status"] == "mapped":
            wanted = None if prepared_expected is None else [{k: v for k, v in row.items() if k != "uniprot"} for row in prepared_expected]
            preparation_equal = wanted is not None and actual["prepared"]["audit"]["mapping"] == wanted
        else:
            expected_error = oracle["expectedPreparedError"]
            observed_error = actual["prepared"]["error"]
            message, code = observed_error["message"], observed_error.get("code")
            preparation_equal = (not admitted or expected_error is not None and (
                expected_error in message or code == expected_error or
                expected_error == "noncontiguous-interval" and (code == "sifts-contiguity" or "Noncontiguous author interval" in message) or
                expected_error in ("identity-or-insertion", "missing-or-ambiguous-author", "coordinate-mismatch", "displacement-mismatch", "unsupported-author-numbering") and code == "coordinate-mapping"))
        if not preparation_equal:
            mismatches.append({"id": case["id"], "stage": "uniprot_prepare", "expectedError": oracle["expectedPreparedError"], "actual": actual["prepared"]})
        rows.append({"id": case["id"], "pdb": case["pdb"], "chain": case["chain"], "status": "completed", "observed_labels": len(oracle["labelRows"]),
                     "label_mapped": mapped, "label_guarded": guarded, "label_unsupported": unsupported, "label_contract_agreement": correct,
                     "sifts_parser_status": actual["sifts"]["status"], "sifts_parser_equal": sifts_equal,
                     "xml_chain_rows": len(oracle["sifts"]["rawChainRows"]), "xml_observed_with_accession": len(oracle["sifts"]["observedWithAccession"]),
                     "xml_unobserved_with_accession": len(oracle["sifts"]["unobservedWithAccession"]),
                     "cif_rows_with_insertion": sum(bool(r["insertion"]) for r in oracle["rawCifCaRows"]),
                     "cif_rows_with_alt": sum(bool(r["alt"]) for r in oracle["rawCifCaRows"]),
                     "prepared_status": actual["prepared"]["status"], "prepared_equal": preparation_equal,
                     "prepared_residues": len(actual["prepared"]["audit"]["mapping"]) if actual["prepared"]["status"] == "mapped" else 0,
                     "prepared_expected_error": oracle["expectedPreparedError"],
                     "inspection_blocking": None if admitted else actual.get("inspection", {})})
    complete = [r for r in rows if r["status"] == "completed"]
    summary = {"schema": "public-mapping-development-audit/1.0", "selectedChains": 30, "sourcesAndRuntimeCompleted": len(complete),
               "labelPositions": sum(r["observed_labels"] for r in complete), "labelMapped": sum(r["label_mapped"] for r in complete),
               "labelGuardedByInspection": sum(r["label_guarded"] for r in complete), "labelUnsupported": sum(r["label_unsupported"] for r in complete),
               "siftsParserMappedChains": sum(r["sifts_parser_status"] == "mapped" for r in complete), "siftsParserRejectedChains": sum(r["sifts_parser_status"] == "rejected" for r in complete),
               "preparedMappedChains": sum(r["prepared_status"] == "mapped" for r in complete), "preparedRejectedChains": sum(r["prepared_status"] == "rejected" for r in complete),
               "preparedMappedResidues": sum(r["prepared_residues"] for r in complete),
               "observedSiftsAccessionRows": sum(r["xml_observed_with_accession"] for r in complete),
               "unobservedSiftsAccessionRows": sum(r["xml_unobserved_with_accession"] for r in complete),
               "sourceInsertionRows": sum(r["cif_rows_with_insertion"] for r in complete), "sourceAlternateRows": sum(r["cif_rows_with_alt"] for r in complete),
               "oracleAgreement": not mismatches, "mismatches": mismatches, "rows": rows,
               "reservedScientificEvaluation": False, "humanReference": False, "biologicalValidity": "not_established", "modelCalls": 0, "awsInstances": 0,
               "scope": "Independent source-row expectations, shared Gemmi lexical parser; all selected chains retained. Guarded-by-inspection rows remain unmapped and do not imply an identity-mapper success. Numeric cross-reference equality is not repeat annotation or physical validity.",
               "verifierSha256": sha(__file__)}
    (BASE / "audit.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    for name, values in (("chain-outcomes.csv", [{k: v for k, v in r.items() if k != "inspection_blocking"} for r in rows]), ("residue-outcomes.csv", residues)):
        fields = sorted(set(k for r in values for k in r))
        with (BASE / name).open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows(values)
    print(json.dumps({k: v for k, v in summary.items() if k not in ("rows", "mismatches")}, ensure_ascii=False))
    return summary


if __name__ == "__main__":
    audit()
