#!/usr/bin/env python3
"""Snapshot actual thesis requirements and run read-only evidence checks.

This records available engineering evidence and missing evaluation dependencies.
It neither calls a model nor starts cloud resources, edits Word, or infers that
an independently validated scientific metric has been achieved.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
from xml.etree import ElementTree as ET
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).resolve().parent
WORD = Path("/home/webiwabou/Projects/Tesis.docx")
NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
XLS_NS = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def read_json(path):
    return json.loads(path.read_text())


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


def word_snapshot():
    with ZipFile(WORD) as archive:
        body = ET.fromstring(archive.read("word/document.xml")).find("w:body", NS)
        paragraphs = ["".join(t.text or "" for t in p.findall(".//w:t", NS))
                      for p in body.findall("w:p", NS)]
    expected = [f"R{objective}.{i}" for objective, size in ((1, 9), (2, 4), (3, 8))
                for i in range(1, size + 1)]
    rows = []
    for identifier in expected:
        matches = [{"paragraph_index_zero_based": i, "text": text}
                   for i, text in enumerate(paragraphs)
                   if re.match(re.escape(identifier) + r"\.\s", text)]
        if not matches:
            raise ValueError("Missing expected Word definition: " + identifier)
        rows.append({"id": identifier, "definition": matches[0],
                     "occurrences": len(matches)})
    stale = []
    patterns = (
        "detector pendiente", "detección admitida de repeticiones",
        "STRPsearch continúa candidato", "sin confirmación", "no están disponibles",
        "clúster todavía no", "mapeos SIFTS/UniProt",
    )
    for i, text in enumerate(paragraphs):
        if any(pattern.casefold() in text.casefold() for pattern in patterns):
            stale.append({"paragraph_index_zero_based": i, "text": text,
                          "review_action": "Reconcile current status or explicitly retain as dated history; do not erase prior failures."})
    return {"path": str(WORD), "sha256_at_audit": sha256(WORD),
            "paragraphs": len(paragraphs), "results": rows,
            "historical_or_stale_status_candidates": stale}


def expert_workbook_snapshot():
    workbook = ROOT / "docs/tesis/evaluacion-experta-20260930/para-asesora/evaluacion.xlsx"
    mapping = read_json(ROOT / "evaluation/trp/corpus-20260930/workbook-cell-map.json")
    # Worksheet membership is resolved from workbook relationships, so this is
    # not dependent on a particular numbered sheet in an XLSX archive.
    with ZipFile(workbook) as archive:
        workbook_xml = ET.fromstring(archive.read("xl/workbook.xml"))
        relationships = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        targets = {x.get("Id"): x.get("Target") for x in relationships}
        strings = []
        if "xl/sharedStrings.xml" in archive.namelist():
            strings = ["".join(t.text or "" for t in item.findall(".//s:t", XLS_NS))
                       for item in ET.fromstring(archive.read("xl/sharedStrings.xml"))]
        sheets = {}
        for sheet in workbook_xml.findall("s:sheets/s:sheet", XLS_NS):
            relationship = sheet.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
            target = targets[relationship]
            path = target.lstrip("/") if target.startswith("/") else "xl/" + target
            cells = {}
            for cell in ET.fromstring(archive.read(path)).findall(".//s:c", XLS_NS):
                value = cell.find("s:v", XLS_NS)
                if cell.get("t") == "inlineStr":
                    text = "".join(t.text or "" for t in cell.findall(".//s:t", XLS_NS))
                elif value is None:
                    text = ""
                elif cell.get("t") == "s":
                    text = strings[int(value.text)]
                else:
                    text = value.text or ""
                cells[cell.get("r")] = text.strip()
            sheets[sheet.get("name")] = cells
    candidate = next((name for name in sheets if name.casefold() == "solicitudes"), None)
    if candidate is None:
        raise ValueError("Expert workbook requests worksheet missing: " + ", ".join(sheets))
    cells = sheets[candidate]
    counts = {name: sum(bool(cells.get(fields[name], "")) for fields in mapping.values())
              for name in ("Solicitud definitiva", "Objetivo esperado", "Factibilidad", "Paráfrasis 1", "Paráfrasis 2")}
    return {"path": str(workbook.relative_to(ROOT)), "sha256": sha256(workbook),
            "worksheet": candidate, "cases": len(mapping), "nonempty_response_fields": counts,
            "scope": "Cell availability, not authentication or scientific validation of any entered annotation."}


def checks():
    commands = {
        "traceability-index": ["python", "script/tesis/audit_thesis_traceability.py"],
        "local-resource-archives": ["python", "script/tesis/audit_resource_runs.py"],
        "aws-infrastructure-evidence": ["python", "script/tesis/verify_aws_academy_evidence.py"],
        "pratt-original-integrity": ["python", "script/tesis/evaluate_pratt_originals.py", "verify"],
        "development-invalid-graphs": ["bun", "script/tesis/check_trp_graph.ts"],
    }
    results = []
    for name, command in commands.items():
        run = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, timeout=180)
        path = BASE / "checks" / (name + ".json")
        try:
            output = json.loads(run.stdout)
        except json.JSONDecodeError:
            output = {"stdout": run.stdout}
        record = {"command": command, "exit_code": run.returncode,
                  "stdout": output, "stderr": run.stderr, "read_only_sources": True}
        save(path, record)
        results.append({"name": name, "passed": run.returncode == 0,
                        "path": path.relative_to(ROOT).as_posix(), "sha256": sha256(path)})
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-checks", action="store_true")
    args = parser.parse_args()
    word = word_snapshot()
    protocol = read_json(ROOT / "evaluation/trp/protocol.json")
    definitions = {r["id"] for r in word["results"]}
    if definitions != {m["id"] for m in protocol["metrics"]}:
        raise ValueError("Word and protocol result identifiers differ")
    sources = ["evaluation/trp/protocol.json", "evaluation/trp/PROTOCOL.md",
               "evaluation/trp/ANNOTATION.md", "evaluation/trp/corpus-20260930/decisions.json",
               "evaluation/trp/corpus-20260930/validation.json", "docs/tesis/trazabilidad.json",
               "docs/tesis/checkpoint.json", "evaluation/trp/reference/pratt-author-20261001/summary.json",
               "evaluation/trp/reference/resources-r32/freeze.json",
               "evaluation/trp/aws-academy-cluster-20261012/report.json"]
    audit = {
        "schema": "helix-thesis-campaign-audit/1.0", "audited_at": datetime.now(timezone.utc).isoformat(),
        "status": "audit_of_current_state_not_final_evaluation",
        "observed_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "word": word, "protocol_version": protocol["version"],
        "result_ids": [r["id"] for r in word["results"]],
        "protocol_sample_minima": protocol["sample_minima"],
        "protocol_thresholds": protocol["thresholds"],
        "expert_workbook": expert_workbook_snapshot(),
        "model_decision": read_json(ROOT / "evaluation/trp/corpus-20260930/decisions.json")["model"],
        "observed_model_access": {
            "baseline_listing": read_json(BASE / "model-access.json") if (BASE / "model-access.json").exists() else None,
            "development_probe": read_json(BASE / "model-access-probe.json") if (BASE / "model-access-probe.json").exists() else None,
        },
        "source_hashes": [{"path": p, "sha256": sha256(ROOT / p)} for p in sources],
        "verification": checks() if not args.skip_checks else [],
        "prohibited_inferences": [
            "Passing historical engineering checks does not prove completion of the held-out campaign.",
            "An infrastructure-only workflow does not prove Helix submitted or governed Slurm work.",
            "78 mechanical alarms and five illustrated problems do not establish physical sensitivity or specificity.",
            "A blank expert workbook does not provide independent labels, human paraphrases, or kappa.",
        ],
    }
    save(BASE / "audit.json", audit)
    print(json.dumps({"results": len(definitions), "expert": audit["expert_workbook"]["nonempty_response_fields"],
                      "checks_passed": sum(x["passed"] for x in audit["verification"]),
                      "checks_run": len(audit["verification"])}))
    return 0 if all(x["passed"] for x in audit["verification"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
