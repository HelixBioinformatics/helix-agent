#!/usr/bin/env python3
"""Write a results/conclusions/annex candidate from actual Academy evidence.

Never overwrites the author's Word. All body elements before Chapter 4 and
every ZIP part except document.xml are preserved. The last evidence summaries
are read at each invocation, so a final regeneration uses measured results,
never a projected number of completed executions.

Run through an isolated environment with lxml, for example:
UV_NO_PROGRESS=1 uv run --with lxml python script/tesis/update_academy_campaign_docx.py
"""
import argparse
from copy import copy, deepcopy
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import runpy
from zipfile import ZipFile, ZIP_DEFLATED

from lxml import etree as E
from update_identifier_docx import q, text, replace_text

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "evaluation/trp/campaign-20261012"
SOURCE = Path("/home/webiwabou/Projects/Tesis.docx")
TARGET = Path("/home/webiwabou/Projects/Tesis-AWS-20261012-candidate.docx")
SECTION_TITLE = "Campaña técnica en AWS Academy y estado de la evaluación"
ANNEX_TITLE = "A.25. Ejecución de Helix en AWS Academy y reproducción"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path, optional=False):
    if optional and not path.exists():
        return None
    return json.loads(path.read_text())


def as_spanish(value, digits=2):
    return f"{value:.{digits}f}".replace(".", ",")


def result_of(audit, name):
    row = next(item for item in audit["checks"] if item["name"] == name)
    if not row["passed"]:
        raise ValueError("Unverified actual result: " + name)
    return row["result"]


class Writer:
    def __init__(self, body):
        self.body = body
        self.normal = next(p for p in body if text(p).startswith("Este capítulo presenta los 21 resultados"))
        self.heading = next(p for p in body if text(p) == "Verificación de Helix en la segunda estación")
        self.table_template = next(t for t in body if t.tag == q("tbl") and text(t).startswith("ResultadoMétodo o herramientaReferencia del método"))

    def paragraph(self, value, heading=False, note=False):
        if "\u2014" in value:
            raise ValueError("Em dash in newly authored prose")
        template = self.heading if heading else self.normal
        p = E.Element(q("p"))
        old_pr = template.find(q("pPr"))
        if old_pr is not None:
            p.append(deepcopy(old_pr))
        if heading or value.startswith("Tabla "):
            ppr = p.find(q("pPr"))
            if ppr is None:
                ppr = E.SubElement(p, q("pPr"))
            keep = ppr.find(q("keepNext"))
            if keep is None:
                keep = E.SubElement(ppr, q("keepNext"))
            keep.set(q("val"), "1")
        r = E.SubElement(p, q("r"))
        pr = E.SubElement(r, q("rPr"))
        E.SubElement(pr, q("rFonts"), {q("ascii"): "Times New Roman", q("hAnsi"): "Times New Roman"})
        E.SubElement(pr, q("sz"), {q("val"): "24"})
        if heading:
            E.SubElement(pr, q("b"))
        if note:
            E.SubElement(pr, q("i"))
            E.SubElement(pr, q("color"), {q("val"): "FF0000"})
        E.SubElement(r, q("t")).text = value
        return p

    def table(self, headers, rows, widths):
        table = E.Element(q("tbl"))
        table.append(deepcopy(self.table_template.find(q("tblPr"))))
        grid = E.SubElement(table, q("tblGrid"))
        for width in widths:
            E.SubElement(grid, q("gridCol"), {q("w"): str(width)})
        for index, values in enumerate([headers, *rows]):
            tr = E.SubElement(table, q("tr"))
            pr = E.SubElement(tr, q("trPr"))
            E.SubElement(pr, q("cantSplit"))
            if index == 0:
                E.SubElement(pr, q("tblHeader"))
            for value, width in zip(values, widths, strict=True):
                tc = E.SubElement(tr, q("tc"))
                tcp = E.SubElement(tc, q("tcPr"))
                E.SubElement(tcp, q("tcW"), {q("w"): str(width), q("type"): "dxa"})
                E.SubElement(tcp, q("vAlign"), {q("val"): "top"})
                borders = E.SubElement(tcp, q("tcBorders"))
                for edge in ("top", "bottom", "left", "right"):
                    E.SubElement(borders, q(edge), {q("val"): "single", q("sz"): "4", q("color"): "808080"})
                if index == 0:
                    E.SubElement(tcp, q("shd"), {q("val"): "clear", q("fill"): "E7E6E6"})
                p = E.SubElement(tc, q("p"))
                pp = E.SubElement(p, q("pPr"))
                E.SubElement(pp, q("spacing"), {q("before"): "40", q("after"): "40", q("line"): "240", q("lineRule"): "auto"})
                E.SubElement(pp, q("jc"), {q("val"): "left"})
                r = E.SubElement(p, q("r"))
                rp = E.SubElement(r, q("rPr"))
                E.SubElement(rp, q("rFonts"), {q("ascii"): "Times New Roman", q("hAnsi"): "Times New Roman"})
                E.SubElement(rp, q("sz"), {q("val"): "20"})
                if index == 0:
                    E.SubElement(rp, q("b"))
                E.SubElement(r, q("t")).text = value
        return table

    def insert_before(self, anchor, elements):
        index = list(self.body).index(anchor)
        for element in elements:
            self.body.insert(index, element)
            index += 1


def evidence():
    paths = {
        "remote": BASE / "trace/lab1-helix-reference.json",
        "pressure": BASE / "trace/lab2-pressure-evidence.json",
        "graphs": BASE / "checks/contract-graphs.json",
        "graphs_source": BASE / "contract-corpus/graphs.json",
        "graphs_freeze": BASE / "contract-corpus/freeze.json",
        "model": BASE / "model-access-probe.json",
        "cancel": BASE / "cloud/lab1/cancellation/running-job/recovery-summary.json",
        "cancel_request": BASE / "cloud/lab1/cancellation/running-job/evidence/run/remote-cancel-request.json",
        "cancel_native": BASE / "cloud/lab1/cancellation/running-job/supplemental-before-abort.json",
        "protocol": ROOT / "evaluation/trp/protocol.json",
        "structural": BASE / "structural/summary.json",
        "structural_protocol": BASE / "structural/protocol.json",
        "structural_agent": BASE / "structural/agent-reference.json",
        "structural_retry": BASE / "structural/runtime-600/summary.json",
        "sasa": BASE / "structural/freesasa/summary.json",
        "sasa_protocol": BASE / "structural/freesasa/protocol.json",
        "sasa_manifest": BASE / "structural/freesasa/manifest.json",
        "sasa_validation": BASE / "structural/freesasa/independent-validation.json",
        "sasa_agent": BASE / "structural/freesasa/integration/agent-reference.json",
        "sasa_integration": BASE / "structural/freesasa/integration/implementation-validation.json",
        "sasa_22r": BASE / "structural/freesasa/reports/pratt-original/22r.json",
        "model_pilot": BASE / "model-pilot/audit.json",
        "model_pilot_freeze": BASE / "model-pilot/freeze.json",
        "model_settings": BASE / "model-pilot/settings-probe/observed.jsonl",
        "model_settings_freeze": BASE / "model-pilot/settings-probe/freeze.json",
        "cancel_clean": BASE / "trace/running-cancellation-clean.json",
        "cancel_clean_terminal": BASE / "cloud/lab1/cancellation/next-ctx-abort/driver-terminal.json",
        "cancel_clean_before": BASE / "cloud/lab1/cancellation/next-ctx-abort/out/running-job/before-abort.json",
        "cancel_clean_request": BASE / "cloud/lab1/cancellation/next-ctx-abort/out/running-job/abort-request.json",
        "cancel_clean_after": BASE / "cloud/lab1/cancellation/next-ctx-abort/out/running-job/after-abort.json",
        "cancel_prior_race": BASE / "cloud/lab1/cancellation/fast-stub-timing-race/case.json",
        "cancel_driver_error": BASE / "cloud/lab1/cancellation/driver-error-no-submit/driver-error.json",
        "mapped_terminal": BASE / "cloud/lab1/mapped-reference-protocol/driver-terminal.json",
        "mapped_audit": BASE / "trace/mapped-reference.json",
        "mapped_copy": BASE / "trace/mapped-reference-copy.json",
        "public_mapping": BASE / "mapping-public-contrasts/summary.json",
        "public_mapping_audit": BASE / "mapping-public-contrasts/audit.json",
        "public_mapping_protocol": BASE / "mapping-public-contrasts/protocol.json",
        "public_mapping_freeze": BASE / "mapping-public-contrasts/oracle-freeze.json",
        "public_mapping_manifest": BASE / "mapping-public-contrasts/manifest.json",
        "regression": BASE / "checks/final-regression/summary.json",
        "workflow": BASE / "cloud/workflow-summary.json",
        "r24_head": BASE / "cloud/lab2/r24-summary.json",
        "r24_original": BASE / "cloud/lab2/r24-campaign/all-original-attempts.json",
        "r24_manifest": BASE / "cloud/lab2/r24-evidence-manifest.json",
        "negative_events": BASE / "event-negative-contrasts/audit.json",
        "negative_events_protocol": BASE / "event-negative-contrasts/protocol.json",
        "negative_events_sources": BASE / "event-negative-contrasts/source-snapshot.json",
    }
    data = {key: ([json.loads(line) for line in path.read_text().splitlines() if line.strip()]
                  if path.suffix == ".jsonl" else load(path, optional=key.startswith("structural") or key == "workflow"))
            for key, path in paths.items()}
    data["expert"] = runpy.run_path(str(BASE / "audit_campaign.py"))["expert_workbook_snapshot"]()
    if any(data["expert"]["nonempty_response_fields"].values()):
        raise ValueError("Human response cells are now populated; review dependent prose before regeneration")
    if not data["remote"]["verified"] or not data["pressure"]["verified"]:
        raise ValueError("Current independent cloud audits do not pass")
    if data["graphs"]["accepted_valid"] != 50 or data["graphs"]["accepted_invalid"] != 0:
        raise ValueError("Unexpected static graph outcomes; rewrite narrative from evidence")
    if data["model"]["exit_code"] != 0 or "HELIX_PILOT_OK" not in data["model"]["stdout"]:
        raise ValueError("Requested-model access probe not established")
    expected = [f"R{objective}.{i}" for objective, count in ((1, 9), (2, 4), (3, 8)) for i in range(1, count+1)]
    if [row["id"] for row in data["protocol"]["metrics"]] != expected:
        raise ValueError("Current result identifiers differ")
    validate_surface(data, paths)
    validate_model_pilot(data, paths)
    validate_clean_cancellation(data, paths)
    validate_mapped_reference(data, paths)
    validate_public_mapping(data, paths)
    validate_resource_and_refusal_contrasts(data, paths)
    # Saved case outcomes count only when their completed artifact and
    # input-specific CSV hashes remain available. Unfinished cases are absent.
    cases = []
    failed_cases = []
    planned = {row["id"]: row for row in data["graphs_source"]["valid"]}
    graph_file = next(row for row in data["graphs_freeze"]["files"] if row.get("path") == "graphs.json")
    if sha(paths["graphs_source"]) != graph_file["sha256"]:
        raise ValueError("Prospective graph cases changed")
    for path in sorted((BASE / "cloud").glob("lab*/workflows*/G-valid-*/case.json")):
        raw = load(path)
        if raw["id"] not in planned:
            raise ValueError("Cloud case is not in the frozen fifty valid graphs")
        if raw.get("status") != "succeeded":
            if raw.get("status") == "failed":
                failed_cases.append({"path": path.relative_to(ROOT).as_posix(), "value": raw, "sha256": sha(path)})
            continue
        bundle = path.parent / "evidence"
        csv = bundle / "run/results/geometry.csv"
        if sha(bundle / "manifest.json") != raw["manifestSha256"]:
            raise ValueError("Workflow manifest changed: " + str(path))
        if raw.get("equal") is not True or sha(csv) != raw["remoteCsvSha256"] or sha(path.parent / "standalone-reference/geometry.csv") != raw["localCsvSha256"] or raw["remoteCsvSha256"] != raw["localCsvSha256"]:
            raise ValueError("Input-specific workflow comparison not established: " + str(path))
        run = load(bundle / "run/run.json")
        if run["status"] != "succeeded" or run["measuredTasks"] != {"scientificTasks": 2, "stubTasks": 2}:
            raise ValueError("Actual workflow not completed: " + str(path))
        observed = load(bundle / "run/specification.json")
        expected = planned[raw["id"]]["specification"]
        for key in ("units", "insertions", "chain", "model"):
            if observed[key]["value"] != expected[key]["value"]:
                raise ValueError("Actual workflow changed frozen case " + raw["id"] + ": " + key)
        cases.append({"path": path.relative_to(ROOT).as_posix(), "value": raw, "sha256": sha(path)})
    all_successful_attempts = cases
    # Retain every successful attempt as evidence, but count each frozen ID
    # once. Prefer its original attempt when it succeeded; retries add no case.
    unique = {}
    for item in sorted(cases, key=lambda item: (Path(item["path"]).parent.parent.name != "workflows", item["path"])):
        unique.setdefault(item["value"]["id"], item)
    data["additional_cloud_summaries"] = list(unique.values())
    data["successful_cloud_attempts"] = all_successful_attempts
    data["failed_cloud_cases"] = failed_cases
    data["source_records"] = [{"path": path.relative_to(ROOT).as_posix(), "sha256": sha(path)}
                              for path in paths.values() if path.exists()]
    data["source_records"].append({"path": data["expert"]["path"], "sha256": data["expert"]["sha256"]})
    data["source_records"].extend({"path": item["path"], "sha256": item["sha256"]} for item in all_successful_attempts + failed_cases)
    data["source_records"].extend(data.pop("additional_source_records"))
    summary = data["workflow"]
    if summary is not None:
        if summary["schema"] != "helix-remote-development-workflows/1.0" or summary["frozen_cases"] != len(planned) or summary["unique_proteins"] != 1 or summary["scientific_R1_5_rate"] is not None:
            raise ValueError("Workflow campaign scope changed; review scientific interpretation")
        rows = summary["attempts"]
        for row in rows:
            if row["id"] not in planned:
                raise ValueError("Final summary includes a case outside the freeze")
            path = ROOT / row["case_path"]
            if sha(path) != row["case_sha256"]:
                raise ValueError("Attempt changed since independent audit: " + row["case_path"])
            data["source_records"].append({"path": row["case_path"], "sha256": row["case_sha256"]})
            if row["verified"]:
                report_path = ROOT / row["audit_path"]
                if sha(report_path) != row["audit_sha256"] or load(report_path)["verified"] is not True or row["numerical_equal"] is not True:
                    raise ValueError("Successful attempt lacks a current independent audit")
                if sha(path.parent / "evidence/manifest.json") != row["manifest_sha256"]:
                    raise ValueError("Attempt manifest changed since independent audit")
                data["source_records"].append({"path": row["audit_path"], "sha256": row["audit_sha256"]})
        by_id = {identifier: [row for row in rows if row["id"] == identifier] for identifier in planned}
        first = [next((row for row in attempts if row["revision_directory"] == "workflows"), attempts[0])
                 for attempts in by_id.values() if attempts]
        verified = {row["id"] for row in rows if row["verified"]}
        counters = {"attempts": len(rows), "first_attempts": len(first),
                    "first_attempt_succeeded": sum(row["verified"] for row in first),
                    "first_attempt_failed": sum(row["status"] == "failed" for row in first),
                    "first_attempt_unverified_success": sum(row["status"] == "succeeded" and not row["verified"] for row in first),
                    "retry_attempts": len(rows)-len(first), "unique_cases_verified": len(verified),
                    "unique_cases_not_observed": sum(not attempts for attempts in by_id.values())}
        if summary["counts"] != counters or set(summary["verified_case_ids"]) != verified or summary["all_50_cases_verified"] != (len(verified) == len(planned)):
            raise ValueError("Final campaign summary counters do not match retained attempts")
    return data


def validate_resource_and_refusal_contrasts(data, paths):
    summary, original = data["r24_head"], data["r24_original"]
    if not summary["verified"] or not original["verified"] or summary["original40SummarySha256"] != sha(paths["r24_original"]):
        raise ValueError("Head workspace resource summaries changed")
    cases = original["cases"]
    feasible = sum(row["physicalFeasibilityLabel"] is True for row in cases)
    infeasible = sum(row["physicalFeasibilityLabel"] is False for row in cases)
    rejected = sum(row["physicalFeasibilityLabel"] is True and row["helixAccepted"] is False for row in cases)
    correct = sum(row["physicalFeasibilityLabel"] == row["helixAccepted"] for row in cases)
    if len(cases) != 40 or len({row["id"] for row in cases}) != 40 or (feasible, infeasible, rejected, correct) != (26, 14, 6, 34):
        raise ValueError("Original forty resource case denominators differ")
    if original["scopedFalseRejectionRate"] != rejected/feasible or original["scopedAccuracy"] != correct/len(cases):
        raise ValueError("Head resource rates do not match cases")
    if original["actualDispatchedAttempts"] != 42 or original["preservedUnknownAttempts"] != 2 or original["scientificR24Complete"] or original["aggregateRemotePlusRealClientR22Enforced"]:
        raise ValueError("Resource attempts or adaptation scope differ")
    if summary["extensionCounts"] != {"planned": 6, "empiricallyFeasible": 0, "empiricallyInfeasible": 6, "unknown": 0, "scopedFalseRejections": 0} or not summary["extensionChosenAfterObservingOriginalGrid"] or not summary["originalDenominatorPreserved"]:
        raise ValueError("Separate extension is not preserved")
    manifest = data["r24_manifest"]
    if sha(paths["r24_manifest"]) != "6ac7492e8161a9e39deedc7b6f4e7c90d5e02ca17f41fb5762f429146d8591f1":
        raise ValueError("Archived head campaign manifest changed")
    for row in manifest["files"]:
        file = ROOT / row["path"]
        if file.stat().st_size != row["bytes"] or sha(file) != row["sha256"]:
            raise ValueError("Archived head resource file changed: " + row["path"])
    audit = data["negative_events"]
    counts = {"admission": 4, "protocol": 3, "permission": 4, "approval": 2}
    if not audit["verified"] or audit["unique_gate_cases"] != 4 or audit["eligible_records_by_source"] != counts or audit["matched_records_by_source"] != counts or audit["human_labels"] != 0 or audit["model_calls"] != 0 or audit["kappa"] is not None:
        raise ValueError("Negative action oracle counts or scope differ")
    if audit["protocolSha256"] != sha(paths["negative_events_protocol"]) or data["negative_events_sources"]["freezeSha256"] != audit["protocolSha256"]:
        raise ValueError("Negative action oracle prospective freeze changed")
    for case in audit["cases"]:
        if not case["verified"]:
            raise ValueError("Negative action case is unverified")
        for row in case["records"]:
            if sha(ROOT / row["path"]) != row["sha256"]:
                raise ValueError("Negative action source changed: " + row["path"])


def validate_surface(data, paths):
    summary = data["sasa"]
    if summary["physicalSensitivity"] is not None or summary["physicalSpecificity"] is not None or summary["classifierValidated"] or summary["biologicalThreshold"] is not None:
        raise ValueError("Surface evidence gained an unsupported physical classifier")
    if not data["sasa_validation"]["ok"] or data["sasa_validation"]["cases"] != 108 or data["sasa_validation"]["evaluable"] != 108:
        raise ValueError("SASA independent verification is incomplete")
    missing_charged_cases = missing_heavy_cases = residue_total = measured_cases = 0
    sources = []
    for entry in data["sasa_manifest"]["files"]:
        path = paths["sasa_manifest"].parent / entry["path"]
        if path.stat().st_size != entry["bytes"] or sha(path) != entry["sha256"]:
            raise ValueError("Frozen SASA evidence changed")
        if entry["path"].startswith("reports/") and entry["path"].endswith(".json") and not entry["path"].endswith(".attempt.json"):
            report = load(path)
            residue_total += report["residues"]
            measured_cases += 1
            if entry["path"].startswith("reports/experimental-reviewed-beta-solenoid/"):
                missing_charged_cases += report["incompleteChargedSidechains"] > 0
                missing_heavy_cases += report["residuesWithMissingExpectedHeavyAtoms"] > 0
            sources.append({"path": path.relative_to(ROOT).as_posix(), "sha256": entry["sha256"]})
    if missing_charged_cases != 6 or missing_heavy_cases != 7 or measured_cases != 108:
        raise ValueError("Missing-coordinate denominators changed")
    data["sasa_incomplete_charged_cases"] = missing_charged_cases
    data["sasa_missing_heavy_cases"] = missing_heavy_cases
    data["sasa_residue_total"] = residue_total
    agent = data["sasa_agent"]
    physical = next(c for c in agent["report"]["checks"] if c["id"] == "fold-plausibility")
    diagnostic = physical["value"]["surfaceDiagnostic"]
    if not agent["matchesExternalFrozenRun"] or not agent["verification"]["ok"] or agent["verification"]["files"] != 10 or physical["status"] != "not_evaluable" or diagnostic["foldVerdict"] != "not_established" or diagnostic["burialThreshold"] is not None:
        raise ValueError("Real surface adapter evidence differs")
    for key in ("chargedResidues", "completeChargedSidechains", "chargedSidechainRelativeAreaMedian", "chargedSidechainRelativeAreaMin", "chargedSidechainRelativeAreaMax"):
        if diagnostic["measurement"][key] != data["sasa_22r"][key]:
            raise ValueError("Surface adapter does not match frozen measurement")
    data["additional_source_records"] = sources


def validate_model_pilot(data, paths):
    audit, freeze = data["model_pilot"], data["model_pilot_freeze"]
    if not audit["verified"] or len(audit["cases"]) != 4 or audit["freeze_sha256"] != sha(paths["model_pilot_freeze"]) or audit["reserved_scientific_metrics"] is not None or audit["actual_api_billing_available"]:
        raise ValueError("Actual model pilot scope changed")
    if freeze["reserved_cases_used"] or freeze["human_annotation"] or freeze["scientific_execution_enabled"]:
        raise ValueError("Development model pilot changed its scope")
    prepared = [c for c in audit["cases"] if c["preparation_digest"]]
    if len(prepared) != 2 or any(not c["verified"] for c in audit["cases"]):
        raise ValueError("Expected two preparations and two scope probes")
    for case in audit["cases"]:
        output = BASE / "model-pilot" / case["id"] / "stdout.jsonl"
        if sha(output) != case["source_output_sha256"] or case["actual_charge_usd"] is not None:
            raise ValueError("Model output changed or actual charge was invented")
        data["additional_source_records"].append({"path": output.relative_to(ROOT).as_posix(), "sha256": sha(output)})
    totals = {key: sum(c["usage"][key] for c in audit["cases"]) for key in audit["usage_totals"]}
    if totals != audit["usage_totals"] or not math.isclose(sum(c["published_standard_api_equivalent_usd"] for c in audit["cases"]), audit["published_standard_api_equivalent_usd"], abs_tol=1e-12):
        raise ValueError("Cache-corrected model accounting differs")
    configured = [r for r in data["model_settings"] if r["stage"] == "configured-parameters" and r.get("agent") == "settings-probe"]
    requests = [r for r in data["model_settings"] if r["stage"] == "outbound-request"]
    if len(configured) != 1 or configured[0]["reasoningEffort"] != "medium" or configured[0]["maximumOutputTokens"] is not None or configured[0]["serviceTier"] is not None or not requests or any(r["maximumOutputTokens"] is not None or r["serviceTier"] is not None for r in requests):
        raise ValueError("Observed provider settings changed; revise limitations")


def validate_clean_cancellation(data, paths):
    audit, terminal = data["cancel_clean"], data["cancel_clean_terminal"]
    before, request, after = data["cancel_clean_before"]["found"], data["cancel_clean_request"], data["cancel_clean_after"]
    if not audit["verified"] or any(not c["passed"] for c in audit["checks"]) or terminal["independentAudit"]["sha256"] != sha(paths["cancel_clean"]) or terminal["execExitCode"] != 0:
        raise ValueError("Clean cancellation audit does not pass")
    for name, expected in terminal["sidecars"].items():
        path = paths["cancel_clean_terminal"].parent / name
        if sha(path) != expected:
            raise ValueError("Clean cancellation sidecar changed: " + name)
        data["additional_source_records"].append({"path": path.relative_to(ROOT).as_posix(), "sha256": expected})
    if before["id"] != terminal["nativeJob"] or before["queueState"] != "RUNNING" or "JobState=RUNNING" not in before["source"] or request["nativeId"] != before["id"] or request["mechanism"] != "Tool.Context.abort" or "JobState=CANCELLED" not in after["source"] or "ExitCode=143:0" not in after["source"]:
        raise ValueError("Independent native before/abort/after sequence differs")
    running = datetime.fromisoformat(before["observedAt"])
    requested = datetime.fromisoformat(request["requestedAt"].replace("Z", "+00:00"))
    if not running < requested or not terminal["automaticFinalization"] or terminal["manualRecovery"] or not terminal["controllerStopped"] or terminal["ownedJobsRemaining"] or terminal["worker2ContainerReadback"]["exitCode"] != 0 or terminal["worker2ContainerReadback"]["stdoutBytes"] != 0:
        raise ValueError("Clean cancellation or cleanup sequence is incomplete")


def validate_mapped_reference(data, paths):
    terminal, audit, copied = data["mapped_terminal"], data["mapped_audit"], data["mapped_copy"]
    if terminal["status"] != "succeeded" or terminal["execExitCode"] != 0 or not terminal["sourcesUnchangedSinceProspectiveSnapshot"] or terminal["humanEvaluation"] or terminal["heldOutScientific"]:
        raise ValueError("Mapped reference scope or terminal changed")
    if not audit["verified"] or any(not c["passed"] for c in audit["checks"]) or terminal["audit"]["sha256"] != sha(paths["mapped_audit"]) or terminal["portableCopy"]["sha256"] != sha(paths["mapped_copy"]):
        raise ValueError("Mapped reference independent audit changed")
    if terminal["mapping"]["mappedResidues"] != 206 or terminal["mapping"]["inputUnits"] != 12 or terminal["mapping"]["mappedUnits"] != 12 or not terminal["numerical"]["equal"] or terminal["numerical"]["actualCsvSha256"] != terminal["numerical"]["expectedCsvSha256"]:
        raise ValueError("Mapped residues, units or numerical comparison differ")
    if terminal["portable"]["files"] != 156 or terminal["audit"]["checksPassed"] != 9 or terminal["audit"]["faultsInjected"] != 320 or terminal["audit"]["faultsDetected"] != 320 or not copied["result"]["ok"] or copied["scientificExecutionRepeated"]:
        raise ValueError("Mapped portable scope or fault audit differs")
    for relative, expected in terminal["sidecars"].items():
        path = ROOT / relative
        if sha(path) != expected:
            raise ValueError("Mapped reference sidecar changed")
        data["additional_source_records"].append({"path": relative, "sha256": expected})
    bundle = Path(audit["bundle"])
    if sha(bundle / "manifest.json") != terminal["portable"]["manifestSha256"]:
        raise ValueError("Mapped reference manifest changed")
    for task in terminal["taskTelemetry"]:
        for path_key, hash_key in (("traceSource", "traceSourceSha256"), ("trackerSource", "trackerSourceSha256")):
            path = bundle / "run" / task[path_key]
            if sha(path) != task[hash_key]:
                raise ValueError("Mapped task telemetry source changed")
            data["additional_source_records"].append({"path": path.relative_to(ROOT).as_posix(), "sha256": task[hash_key]})
    regression = data["regression"]
    log = paths["regression"].parent / "domain.log"
    if regression["exit_code"] != 0 or regression["failed"] != 0 or sha(log) != regression["log_sha256"]:
        raise ValueError("Default regression evidence changed")
    data["additional_source_records"].append({"path": log.relative_to(ROOT).as_posix(), "sha256": sha(log)})


def validate_public_mapping(data, paths):
    summary, audit = data["public_mapping"], data["public_mapping_audit"]
    if summary["auditSha256"] != sha(paths["public_mapping_audit"]) or summary["protocolSha256"] != sha(paths["public_mapping_protocol"]) or summary["oracleFreezeSha256"] != sha(paths["public_mapping_freeze"]):
        raise ValueError("Public mapping summary is no longer bound to its sources")
    for key, value in audit.items():
        if key not in ("schema", "rows", "mismatches") and summary[key] != value:
            raise ValueError("Public mapping summary differs from audit: " + key)
    if not audit["oracleAgreement"] or audit["mismatches"] or audit["reservedScientificEvaluation"] or audit["humanReference"] or audit["biologicalValidity"] != "not_established":
        raise ValueError("Public mapping scope changed or independent comparison failed")
    verifier = runpy.run_path(str(ROOT / "script/tesis/verify_public_mapping_evidence.py"))["verify"]()
    if not verifier["ok"] or verifier["chains"] != audit["selectedChains"] or verifier["labelResidues"] != audit["labelPositions"] or verifier["preparedResidues"] != audit["preparedMappedResidues"]:
        raise ValueError("Public mapping final verifier disagrees")
    if audit["selectedChains"] != 30 or audit["preparedMappedChains"] != 28 or audit["preparedRejectedChains"] != 2 or len(summary["missingCaExpectedRejections"]) != 2:
        raise ValueError("Public mapping chain denominators changed; revise prose")
    expected_counts = {"labelPositions": 11751, "labelMapped": 11751, "preparedMappedResidues": 11215,
                       "observedSiftsAccessionRows": 11749, "unobservedSiftsAccessionRows": 265,
                       "siftsParserMappedChains": 30, "sourceInsertionRows": 0, "sourceAlternateRows": 0}
    if any(audit[key] != value for key, value in expected_counts.items()):
        raise ValueError("Public mapping residue counts changed; revise fixed explanatory prose")
    if {(r["case"], r["residue"], r["author"]) for r in summary["missingCaExpectedRejections"]} != {("2bm4-A", "GLY", "182"), ("1o8i-A", "LYS", "353")}:
        raise ValueError("The expected source-level missing-CA rejections changed")
    for record in data["public_mapping_manifest"]["files"] + data["public_mapping_manifest"]["helpers"] + summary["retrospectiveDependencies"]:
        path = ROOT / record["path"]
        if sha(path) != record["sha256"] or "bytes" in record and path.stat().st_size != record["bytes"]:
            raise ValueError("Public mapping file changed: " + record["path"])
        data["additional_source_records"].append({"path": record["path"], "sha256": record["sha256"]})
    data["public_mapping_verification"] = verifier


def measured_campaign(writer, data):
    audit = data["remote"]
    jobs = result_of(audit, "four_native_jobs_and_worker_placement")
    cold = result_of(audit, "portable_integrity_and_cold_counts")
    methods = result_of(audit, "source_backed_methods_and_template")
    events = result_of(audit, "event_chain_and_independent_gate_oracle")
    faults = result_of(audit, "per_artifact_cold_fault_injection")
    csv_result = result_of(audit, "input_specific_numerical_reference")
    pressure, graphs = data["pressure"], data["graphs"]
    paragraphs = [writer.paragraph(SECTION_TITLE, heading=True)]
    # Plan: state the adaptation, actual target and distinction from held-out data.
    paragraphs.append(writer.paragraph("La campaña iniciada el 12 de octubre de 2026 conserva los tres objetivos y las metas del protocolo 1.0.1. Se adaptó el despliegue a los permisos, créditos y tipos de instancia de AWS Academy: dos laboratorios independientes, cada uno con un controlador y dos trabajadores Slurm. La instalación se realizó directamente sobre instancias permitidas; no se utilizó AWS ParallelCluster. Los planes de casos y condiciones se registraron antes de sus salidas. Esta campaña técnica amplía la evidencia de ejecución, mientras las mediciones dependientes de referencia humana conservan sus condiciones de inicio."))
    # Plan: report the integrated run, native jobs, exact comparison and limits.
    paragraphs.append(writer.paragraph(f"Helix preparó y ejecutó la referencia 2xqh/A mediante trp_prepare y trp_run sobre Slurm, con Nextflow 25.10.4 y la imagen de GeomeTRe fijada por digest. Se observaron los trabajos nativos {', '.join(jobs['native_ids'])}: dos simulados y dos científicos. SELECT se ejecutó en helix-worker1 y GEOMETRY en helix-worker2. El CSV contiene {csv_result['rows']} filas, correspondientes a doce unidades y dos resúmenes, y coincide byte a byte con la referencia local de las mismas coordenadas, unidades e inserciones. La comparación no enfrenta subconjuntos distintos ni interpreta las salidas simuladas como datos científicos."))
    mapped = data["mapped_terminal"]
    mapping, portable = mapped["mapping"], mapped["portable"]
    paragraphs.append(writer.paragraph(f"Se contrastó además la ruta con correspondencias SIFTS de la misma proteína de desarrollo. Helix convirtió {mapping['inputUnits']} unidades desde numeración UniProt a {mapping['mappedUnits']} unidades PDB con {mapping['mappedResidues']} residuos mapeados, preservando identidad, cadena y marcos. Los cuatro trabajos nativos {', '.join(mapped['nativeTasks']['native_ids'])} terminaron: dos simulados y dos científicos, con SELECT y GEOMETRY en trabajadores diferentes. El CSV coincide byte a byte con su referencia específica. El paquete automático de {portable['files']} archivos pasó nueve comprobaciones independientes, detectó {mapped['audit']['faultsDetected']}/{mapped['audit']['faultsInjected']} fallos inyectados y verificó una copia fuera del repositorio sin repetir la ejecución científica. Este contraste amplía la ruta técnica mapeada; no añade una segunda proteína ni anotación humana a la reserva."))
    public = data["public_mapping"]
    paragraphs.append(writer.paragraph(f"Se amplió la cobertura técnica de correspondencias sobre las {public['selectedChains']} cadenas PDB públicas del conjunto experimental, excluyendo 2xqh y los modelos privados. La selección, fuentes, expectativas y código de comparación se fijaron antes de ejecutar el mapeador real de Helix. Las expectativas se extrajeron por separado de filas de átomos mmCIF, columnas PDB y referencias por residuo del XML SIFTS oficial; no se interpolaron segmentos ni se reutilizó el mapeo producido como referencia. El lector léxico de CIF, Gemmi 0.7.5, es compartido, pero la unión, identidad y comprobación de coordenadas se implementaron aparte. Esta independencia no cubre posibles fallos comunes del lector."))
    paragraphs.append(writer.paragraph(f"El mapeo individual label_seq_id a numeración de autor coincidió en {public['labelMapped']}/{public['labelPositions']} posiciones con CA y el parser SIFTS coincidió en {public['siftsParserMappedChains']}/{public['selectedChains']} cadenas. Las solicitudes completas UniProt se admitieron en {public['preparedMappedChains']}/{public['selectedChains']} cadenas, con {public['preparedMappedResidues']} residuos convertidos; las {public['preparedRejectedChains']} restantes se rechazaron correctamente porque GLY182 de 2bm4-A y LYS353 de 1o8i-A, UniProt375, contienen sólo N y carecen de CA en las fuentes oficiales, aunque SIFTS los marca observados. Se conservaron ambos rechazos, {public['unobservedSiftsAccessionRows']} residuos no observados de SIFTS y cuatro posiciones con CA sin referencia observada a la accesión seleccionada. Los tres denominadores no se suman ni se convierten en una tasa de anotación biológica."))
    paragraphs.append(writer.paragraph("Los intervalos de este contraste son sondas de numeración, no límites de repeticiones anotados por una experta. No aparecieron códigos de inserción ni ubicaciones alternativas, por lo que no se acredita cobertura de esos dominios. Una cadena admitida y ambos rechazos se reprodujeron con informes idénticos byte a byte. El resultado amplía la verificación de desarrollo de R1.6 sin reemplazar la evaluación reservada ni establecer validez biológica."))
    telemetry = {t["process"]: t for t in mapped["taskTelemetry"]}
    paragraphs.append(writer.paragraph(f"El rastreador de Nextflow registró para SELECT {telemetry['SELECT']['nextflowCommandRealtime'].replace('.', ',')} y RSS máximo {telemetry['SELECT']['nextflowPeakRssFormatted'].replace('.', ',')}, y para GEOMETRY {telemetry['GEOMETRY']['nextflowCommandRealtime'].replace('.', ',')} y RSS máximo {telemetry['GEOMETRY']['nextflowPeakRssFormatted'].replace('.', ',')}. Son observaciones instrumentales por tarea, basadas en el árbol de procesos, y no un pico físico global del controlador, cliente o clúster. Se conservan tiempos nativos, espera del planificador y archivos crudos por separado. Las observaciones finales de almacenamiento tampoco son picos ni límites duros de disco."))
    paragraphs.append(writer.paragraph("La primera comprobación de infraestructura con selección automática del núcleo OpenBLAS produjo una discrepancia numérica conservada en los registros. Fijar el perfil Haswell y una sola hebra de BLAS reprodujo el CSV de esta referencia sin modificar el algoritmo de GeomeTRe ni ampliar la tolerancia. La ruta integrada conservó ese perfil dentro de la propuesta aprobada y contrastó sus observaciones efectivas. La coincidencia corresponde a este caso y estas versiones; no establece igualdad universal entre arquitecturas o proteínas."))
    # Plan: retain the failed launch and distinguish export helper from science.
    paragraphs.append(writer.paragraph("El primer intento de Helix falló durante el recorrido simulado: SELECT, trabajo 15, terminó con código 126 porque Docker no podía atravesar un directorio remoto con permisos 0700 sobre NFS con root_squash. No se inició una tarea científica. Se corrigió el permiso de tránsito del directorio a 0711, manteniendo archivos privados y root_squash; una nueva propuesta con digest distinto produjo la ejecución satisfactoria. El error posterior del conductor de archivo, que buscaba nombres de logs locales, se documentó por separado y se recuperó desde la copia portable completa, sin repetir la ejecución científica. Ambos registros se conservan."))
    cancel = data["cancel"]
    if cancel["nativeStatus"] != "CANCELLED" or "255" not in data["cancel_request"]["reason"] or "JobState=CANCELLED" not in data["cancel_native"]["native"]:
        raise ValueError("Actual failure-cleanup scope changed; review its description")
    paragraphs.append(writer.paragraph("Una prueba con mil unidades sintéticas conservó un fallo diferente: el observador de sesenta segundos venció antes de la etapa científica y el límite de ciento ochenta segundos del conductor terminó el transporte SSH. El monitor registró salida SSH 255 y la limpieza de Helix canceló GEOMETRY, trabajo nativo 24, con estado CANCELLED, salida 143:0 y 51 segundos de ejecución. Se comprobó controlador detenido, ausencia de trabajos propios activos y contenedor terminado. La copia de 145 archivos se recuperó de esa misma ejecución sin reenviarla. La verificación de integridad y cancelación nativa pasó, pero la auditoría del camino detectó que faltaba el evento terminal de fallo automático en el ledger recuperado. El ensayo y el empaquetado automático no pasaron. Esto demuestra limpieza ante fallo de transporte observado, sin atribuirla a cancelación explícita del usuario ni a un caso biológico."))
    race, driver_error = data["cancel_prior_race"], data["cancel_driver_error"]
    if race["status"] != "failed" or race["before"] != "RUNNING" or "JobState=COMPLETED" not in race["after"] or driver_error["scientificJobsSubmitted"] != 0:
        raise ValueError("Historical cancellation failures changed")
    paragraphs.append(writer.paragraph("También se conservan un error inicial del conductor anterior al envío de tareas y una carrera de temporización del trabajo corto 20: aunque se observó RUNNING y se solicitó interrupción, la consulta posterior encontró COMPLETED. La comprobación estricta mantuvo ese ensayo como fallido. Ninguno de esos intentos se reetiqueta como satisfactorio por el resultado de una prueba posterior."))
    clean = data["cancel_clean_terminal"]
    clean_counts = result_of(data["cancel_clean"], "portable_integrity_and_cold_counts")
    paragraphs.append(writer.paragraph(f"La prueba posterior de cancelación explícita observó independientemente GEOMETRY, trabajo {clean['nativeJob']}, como RUNNING en helix-worker2 antes de emitir Tool.Context.abort. Slurm confirmó CANCELLED con código {clean['nativeExitCode']} y {clean['nativeRuntimeSeconds']} segundos de ejecución. El controlador se detuvo, no quedaron trabajos propios activos y una consulta separada a Docker devolvió cero contenedores. El paquete de {clean_counts['files']} archivos se finalizó automáticamente, conservó el evento terminal y pasó las seis comprobaciones de auditoría independiente, sin recuperación manual ni reconstrucción de eventos. El conductor terminó con una prueba aprobada y seis aserciones. El flujo interrumpido conserva estado failed: el resultado satisfactorio corresponde al ensayo de cancelación y limpieza, no a un análisis científico completo ni a intervención humana anotada."))
    paragraphs.append(writer.paragraph(f"La auditoría independiente comprobó {cold['files']} archivos del paquete satisfactorio y detectó {faults['detected']}/{faults['injected']} ausencias, alteraciones y otros fallos inyectados en una copia; la copia restaurada también verificó correctamente. Se contrastaron los {events['recorded_events']} eventos obligatorios del camino observado y los {methods['fields_checked']} campos de métodos contra sus fuentes, incluida la reproducción exacta de la plantilla de texto. El paquete del intento fallido conserva 91 archivos y detectó 190/190 inyecciones. Estas cantidades verifican integridad, secuencia y enlaces declarados, sin autenticar autores ni establecer exactitud biológica o cobertura de una sesión humana completa."))
    paragraphs.append(writer.paragraph("Se completaron cuatro sesiones locales deterministas de rechazo: permiso denegado, aprobación rechazada, violación del protocolo y presupuesto insuficiente. Las acciones observadas por callbacks externos se fijaron antes de leer los registros del productor. Coincidieron 13/13 registros elegibles por tipo, orden y causa: cuatro de admisión, tres de protocolo, cuatro de permisos y dos de aprobación. Los rechazos de preparación se encuentran en rejected.json y protocol.refusals, no en un ledger de ejecución inexistente. Los dos fallos posteriores a la preparación finalizaron automáticamente paquetes de 25 archivos, verificados en frío. Los servicios de Helix y el inventario son reales; el actor de permiso y de respuesta a la interfaz es sintético. No hubo llamadas al modelo, trabajos de AWS, anotaciones humanas ni cálculo de kappa. Los fallos iniciales del conductor también se conservaron."))
    # Plan: independent hardware evidence must not become a circular R2.4 rate.
    paragraphs.append(writer.paragraph(f"En el segundo laboratorio se ejecutaron {pressure['prospective_cases']} contrastes de capacidad registrados de antemano: {pressure['permitted_container_contrasts']} pruebas permitidas de presión o contención y {pressure['infeasible_per_node_requests']} solicitudes que excedían CPU o RAM por nodo. La auditoría reconstruyó {pressure['rechecked']}/{pressure['prospective_cases']} resultados desde las salidas crudas y el inventario del planificador. Cada trabajador declaraba dos CPU y 7400 MiB para Slurm. Las pruebas de memoria tuvieron éxito cuando el núcleo terminó al proceso hijo que superaba su límite; no son tareas científicas satisfactorias. Estas observaciones no incluyen decisiones de admisión de Helix sobre un corpus biológico y, por tanto, no calculan el acierto ni el falso rechazo previstos por R2.4."))
    head = data["r24_original"]
    paragraphs.append(writer.paragraph(f"Un contraste posterior congeló cuarenta combinaciones de veinte grafos de desarrollo y dos presupuestos por grafo. Las decisiones originales de admisión se compararon con ejecuciones independientes de los mismos datos sobre trabajos reales de Slurm. Un supervisor impuso una cuota XFS al espacio del controlador y un cgroup de una CPU, 2 GiB y swap cero. El espacio medido incluye entradas, trabajo de Nextflow, logs y una copia materializada del paquete, pero excluye la preparación y exportación del cliente real y los caches preexistentes. No representa una medición del presupuesto agregado cliente más clúster."))
    paragraphs.append(writer.paragraph(f"Los cuarenta IDs originales quedaron resueltos mediante {head['actualDispatchedAttempts']} tentativas despachadas; se mantienen dos observaciones inconclusas anteriores al punto de recuperación. Se observaron {head['empiricallyFeasible']} casos factibles y {head['empiricallyInfeasible']} inviables, con {head['scopedFalseRejections']} rechazos de casos factibles. El acierto en este alcance fue 34/40, {as_spanish(head['scopedAccuracy']*100)}%, y el falso rechazo 6/26, {as_spanish(head['scopedFalseRejectionRate']*100)}%, superior a la meta original de 5%. Estas diferencias no acreditan error del estimador sobre el mismo presupuesto, porque la decisión del productor y el ensayo independiente incluyen componentes distintos. La revisión posterior motivó un perfil adicional que incorpora el cliente real en la misma cuota y los mismos límites del controlador."))
    paragraphs.append(writer.paragraph("Se añadieron seis casos de desarrollo con 64 KiB, elegidos después de observar los resultados anteriores. Los seis fueron inviables por fallos reales de cuota durante la materialización. Esta extensión se informa por separado: el denominador original sigue siendo cuarenta; no se presenta el total de 46 como campaña original ni se recalculan sus metas para aparentar cumplimiento. Las entradas, fuentes, cambios de ventana, tentativas y evidencias permanecen identificados por hash."))
    paragraphs.append(writer.paragraph(f"Se congelaron {graphs['valid_graphs']} composiciones contractualmente válidas y {graphs['invalid_graphs']} inválidas antes de medir sus veredictos. Se admitieron {graphs['accepted_valid']}/{graphs['valid_graphs']} válidas y {graphs['accepted_invalid']}/{graphs['invalid_graphs']} inválidas; los treinta motivos esperados se detectaron sin excepciones del control. Los positivos son subconjuntos de tres, cuatro, seis, ocho o diez unidades de una sola estructura de desarrollo, 2xqh/A. Los negativos cubren diez modos con tres variantes cada uno. La tasa técnica de aceptación indebida es 0/30; no representa treinta proteínas independientes ni la reserva T-LANG. El recorrido estático no equivale a ejecutar cada flujo."))
    # Additional execution counts must come from completed saved summaries.
    completed = data["additional_cloud_summaries"]
    final_workflows = data["workflow"]
    if final_workflows is not None:
        count = final_workflows["counts"]
        paragraphs.append(writer.paragraph(f"El lote de variantes registra {count['first_attempts']}/50 casos con primera tentativa observada: {count['first_attempt_succeeded']} satisfactorias y verificadas, {count['first_attempt_failed']} fallidas y {count['first_attempt_unverified_success']} declaradas satisfactorias sin verificación completa. Se conservaron {count['retry_attempts']} tentativas adicionales, para un total de {count['attempts']} ejecuciones registradas. El resultado final comprende {count['unique_cases_verified']}/50 IDs únicos con al menos una ejecución verificada y {count['unique_cases_not_observed']} casos sin tentativa observada. Un reintento no aumenta el número de casos ni elimina un fallo de la primera tentativa. La auditoría final y el CSV de tentativas se conservan en cloud/workflow-summary.json y cloud/workflow-summary.csv."))
        paragraphs.append(writer.paragraph("Cada tentativa satisfactoria verificada conserva los cuatro trabajos nativos y coincide byte a byte con su comparador local sobre el mismo subconjunto de unidades, coordenadas, cadena, inserciones, imagen y perfil numérico. Las tentativas fallidas se registran con causa y directorio de revisión; una reparación y recuperación se identifican separadamente. Esta campaña usa una sola proteína de desarrollo con aprobación sintética. Su tasa técnica de primera tentativa y el resultado tras reparaciones no se presentan como el 95% científico de R1.5, que requiere las cincuenta especificaciones externas previstas."))
    elif completed:
        by_lab = {lab: sum("/" + lab + "/" in item["path"] for item in completed) for lab in ("lab1", "lab2")}
        paragraphs.append(writer.paragraph(f"Además de la referencia completa, se conservaron {len(completed)}/50 ejecuciones terminadas de las variantes válidas: {by_lab['lab1']} en el primer laboratorio y {by_lab['lab2']} en el segundo. Cada salida coincide byte a byte con su comparador local, ejecutado sobre el mismo subconjunto y la misma imagen. Los conteos proceden de archivos de caso con estado satisfactorio, manifiesto y CSV comprobados; el tamaño planificado del lote no se presenta como ejecutado. Son variantes de una sola proteína de desarrollo y no sustituyen las cincuenta intenciones y referencias humanas de R1.3."))
    failures = data["failed_cloud_cases"]
    if failures and final_workflows is None:
        ids = ", ".join(item["value"]["id"] for item in failures)
        paragraphs.append(writer.paragraph(f"Se conservan además {len(failures)} veredictos de fallo del conductor ({ids}) y sus causas. Un fallo de serialización o empaquetado no se convierte en resultado científico satisfactorio ni se elimina por una tentativa posterior. El resumen final debe distinguir primera tentativa, recuperación y resultado por caso; un reintento conserva la identidad del caso y no aumenta el denominador de cincuenta variantes."))
    paragraphs.append(writer.paragraph("El modelo elegido por el autor es OpenAI gpt-6-sol con razonamiento medio y presupuesto total de US$100, que incluye hasta US$10 para el piloto. Una comprobación real mediante el OAuth local existente devolvió HELIX_PILOT_OK y registró 3707 tokens de entrada, 12 de salida y 125 de razonamiento. Se corrigió previamente un filtro del complemento que omitía esa versión al listar modelos. La estación de oficina no respondió por SSH en ese intento. El coste cero mostrado por el complemento es metadato de su integración y no demuestra gratuidad ni facturación observada de API. Esta comprobación de acceso no contiene casos reservados ni juicios humanos."))
    pilot, usage = data["model_pilot"], data["model_pilot"]["usage_totals"]
    paragraphs.append(writer.paragraph(f"Un piloto posterior ejecutó cuatro solicitudes reales de desarrollo con ese modelo: dos preparaciones con argumentos completos suministrados y dos consultas sobre falta de entradas o alcance no admitido. Las dos primeras produjeron una llamada trp_prepare completada y las otras dos conservaron la ausencia de preparación; ninguna llamó a trp_run ni ejecutó tareas científicas. La auditoría automática de las cuatro salidas pasó y no hay puntuación semántica independiente. Se registraron {usage['input']} tokens de entrada, {usage['cache_read']} de lectura de caché, {usage['output']} de salida y {usage['reasoning']} de razonamiento, con total conservado de {usage['total']}. La equivalencia con tarifas públicas estándar de API, corregida para incluir las lecturas de caché, es US${as_spanish(pilot['published_standard_api_equivalent_usd'], 7)}. No es una factura, un cargo observado ni el consumo real de créditos API de la autenticación OAuth utilizada."))
    paragraphs.append(writer.paragraph("El piloto fijó dos pasos por caso, 180 segundos de tiempo máximo y un límite propuesto de 8192 tokens de salida por paso. Una sonda posterior dejó maximumOutputTokens=null y serviceTier=null en la configuración observada y en las solicitudes capturadas; el agente principal de esa sonda tenía razonamiento medium configurado. Por ello, el límite de salida no se presenta como confirmado en la solicitud enviada ni se asigna un nivel de servicio efectivo o una revisión del proveedor no observados. Estas limitaciones deben resolverse y congelarse antes de una campaña científica reservada; no impidieron los cuatro ensayos de desarrollo descritos."))
    regression = data["regression"]
    paragraphs.append(writer.paragraph(f"La regresión posterior de TRP y componentes relacionados pasó {regression['passed']} pruebas, con {regression['assertions']} aserciones, {regression['skipped_opt_in']} pruebas opcionales omitidas y cero fallos. Las comprobaciones de motores opcionales y nube tienen registros propios; una omisión no cuenta como ejecución aprobada. Esta regresión de software no estima admisibilidad del lenguaje, acuerdo humano ni validez biológica."))
    paragraphs.append(writer.paragraph("NOTA PARA EL AUTOR. La asesora está designada para la referencia independiente. El libro de setenta solicitudes continúa sin respuestas definitivas, referencias ni paráfrasis humanas recibidas. R1.3 requiere cincuenta intenciones factibles y cien paráfrasis revisadas; R3.3 requiere al menos cien turnos humanos reales y sus primeras etiquetas independientes. Las respuestas sintéticas del conductor a Question.Service no cuentan como anotación humana ni permiten calcular kappa. Estas dependencias no se resuelven con más créditos AWS.", note=True))
    return paragraphs


def structural_sections(writer, data):
    summary = data["structural"]
    if summary is None:
        return [writer.paragraph("El diagnóstico estérico de C9 dispone de una invocación real del adaptador Helix para 8b, con reporte y copia portable verificados. Las mediciones adicionales continúan en ejecución y todavía no se incorporan como resultados terminados. El veredicto general de plausibilidad del pliegue permanece no evaluable; no se calcula sensibilidad física ni especificidad.")]
    if summary.get("physicalSensitivity") is not None or summary.get("physicalSpecificity") is not None or summary.get("classifierValidated") is not False:
        raise ValueError("Structural scientific scope changed; review rather than silently reuse narrative")
    groups = summary["groups"]
    rows = []
    for name, label in (("pratt-original", "AF2 originales de Pratt, sin relajación"), ("experimental-reviewed-beta-solenoid", "Referencias experimentales con repetición revisada")):
        group = groups[name]
        rows.append([label, f"{group['evaluable']}/{group['cases']}",
                     f"{as_spanish(group['clashscoreMin'])} a {as_spanish(group['clashscoreMax'])}; mediana {as_spanish(group['clashscoreMedian'])}"])
    paragraphs = [writer.paragraph("Diagnósticos estérico y de superficie y límites de R3.8", heading=True)]
    # Plan: cite verified method while keeping molecular validity unclassified.
    paragraphs.append(writer.paragraph("Se incorporó a C9 un diagnóstico opcional de choques estéricos mediante cctbx-base 2025.11, con Reduce2/Probe2. El cálculo conserva el criterio atómico de solapamiento desfavorable de 0,4 Å y reporta contactos y clashscore, normalizado por mil átomos; utiliza preparación de hidrógenos, sin inversión de cadenas laterales ni selección por factor B. La metodología de MolProbity se sustenta en Williams et al. (2018), y la implementación y sus parámetros se identifican mediante versión y hashes. No se fijó un umbral de aprobación para una molécula completa: el valor medido no transforma automáticamente un modelo en físicamente correcto o incorrecto."))
    paragraphs.append(writer.paragraph("Tabla 4.1. Cobertura y valores del diagnóstico estérico por grupo"))
    paragraphs.append(writer.table(["Grupo", "Casos evaluables / previstos", "Clashscore observado"], rows, [3600, 1800, 3600]))
    problems = summary["publishedProblems"]
    available = [p for p in problems if p.get("clashscore") is not None]
    values = "; ".join(f"{p['id']}: {p['num_clashes']} contactos y clashscore {as_spanish(p['clashscore'])}" for p in available)
    paragraphs.append(writer.paragraph("Los cinco ejemplos problemáticos vinculados previamente a las figuras de Pratt conservan sus etiquetas publicadas. Sus observables estéricos fueron: " + values + ". Un choque observado es una señal local de geometría; no identifica por sí solo cargas internas apiladas, hidrofobicidad expuesta ni todos los problemas ilustrados en el artículo."))
    paragraphs.append(writer.paragraph("Las treinta cadenas experimentales se obtuvieron de anotaciones revisadas de β-solenoides, clase 3.1 de RepeatsDB, conservando selección, exclusiones, identidad PDB/UniProt y coordenadas. La etiqueta confirma una referencia del dominio de repeticiones; no certifica que cada átomo esté libre de defectos. Además, los originales AF2 son modelos sin relajación, mientras las estructuras experimentales han sido refinadas, y se analizó únicamente la cadena seleccionada. Ese origen y tratamiento diferentes confunden la comparación de puntajes. Los resultados se presentan como diagnóstico descriptivo, sin ajustar un umbral retrospectivo ni convertir esas treinta referencias en negativos físicos demostrados."))
    paragraphs.append(writer.paragraph("El lote de 108 diagnósticos se ejecutó mediante el motor externo CCTBX en la estación local, sin llamadas al modelo ni uso de AWS. El adaptador real de Helix se contrastó por separado: reprodujo el diagnóstico externo fijado para 8b y verificó su copia portable de diez archivos. No se presentan esas 108 mediciones como 108 sesiones del agente. C9 conserva el veredicto general no evaluable y la validez biológica no establecida. La sensibilidad física y la especificidad de R3.8 siguen sin calcular. Se requiere una regla de decisión validada, referencias pertinentes de fallo y ausencia de fallo, y separación entre desarrollo y reserva; los originales examinados para diseñar el control no se presentan como reserva intacta."))
    original, control = groups["pratt-original"], groups["experimental-reviewed-beta-solenoid"]
    paragraphs.append(writer.paragraph(f"Presentaron al menos un choque {original['modelsWithAtLeastOneClash']}/{original['evaluable']} originales evaluables y {control['modelsWithAtLeastOneClash']}/{control['evaluable']} referencias evaluables. Esto muestra por qué la mera presencia de un contacto no discrimina un fallo físico demostrado. La cobertura de cálculo fue {as_spanish(100*original['coverage'], 1)}% para originales y {as_spanish(100*control['coverage'], 1)}% para referencias, sin convertirla en cobertura de una clasificación física validada."))
    failed = sum(g["cases"] - g["evaluable"] for g in groups.values())
    if failed:
        ids = ", ".join(case["id"] for case in summary["unevaluable"])
        paragraphs.append(writer.paragraph(f"Se conservan {failed} casos no evaluables ({ids}) por exceder el límite prospectivo de 180 segundos, con sus motivos y logs. No se reemplazaron después de observar el resultado ni se eliminaron del total previsto. La cobertura de lectura del puntaje es distinta de la cobertura de un veredicto físico validado, que permanece sin establecer."))
    secondary = data["structural_retry"]
    if secondary is not None:
        if secondary.get("primaryPreserved") is not True or secondary.get("primaryEvaluable") != sum(g["evaluable"] for g in groups.values()) or secondary.get("primaryTotal") != sum(g["cases"] for g in groups.values()):
            raise ValueError("Secondary runtime contrast does not preserve the primary cohort")
        details = "; ".join(f"{row['id']}: clashscore {as_spanish(row['clashscore'])}, {as_spanish(row['elapsed_seconds'], 1)} segundos" if row['status'] == 'evaluable' else f"{row['id']}: no evaluable" for row in secondary["secondaryRows"])
        paragraphs.append(writer.paragraph(f"Después del lote primario se congeló un contraste secundario de tiempo para los tres casos que vencieron: mismos archivos, parámetros y motor, una tentativa de hasta 600 segundos por caso y un trabajador. Se recuperó valor estérico en {secondary['secondaryRecovered']}/{secondary['secondaryRetried']} ({details}). Los {secondary['primaryEvaluable']}/{secondary['primaryTotal']} valores del perfil primario y sus exclusiones permanecen intactos; el perfil ampliado se reporta por separado en structural/runtime-600/summary.json y no modifica etiquetas, umbrales físicos ni la inferencia pendiente."))
        expanded = secondary["expandedProfile"]
        paragraphs.append(writer.paragraph(f"El perfil secundario combinado dispone de {expanded['pratt-original']['evaluable']}/{expanded['pratt-original']['cases']} originales y {expanded['experimental-reviewed-beta-solenoid']['evaluable']}/{expanded['experimental-reviewed-beta-solenoid']['cases']} referencias con puntaje. La referencia recuperada 1ea0-A tiene clashscore {as_spanish(expanded['experimental-reviewed-beta-solenoid']['clashscoreMax'])}, superior al de cuatro de los cinco problemas ilustrados. Este solapamiento refuerza el límite de una interpretación clasificatoria. La concurrencia también cambió respecto del primario, por lo que no se atribuye la recuperación exclusivamente a ampliar el tiempo."))
    paragraphs.extend(surface_sections(writer, data))
    paragraphs.append(writer.paragraph("NOTA PARA EL AUTOR. Mantener separados el puntaje estérico, la alarma de confianza y la etiqueta de fallo físico. Las treinta referencias revisadas aportan un comparador pertinente, pero no completan por sí solas la especificidad. El contraste entre modelos no relajados y referencias refinadas debe conservarse como limitación de cualquier ilustración o comparación de grupos.", note=True))
    if (BASE / "structural/steric-distribution.png").exists():
        paragraphs.append(writer.paragraph("NOTA PARA EL AUTOR. La ilustración propia structural/steric-distribution.png, también disponible en PDF y SVG junto con su pie, muestra estos valores sin imponer un corte físico. Puede incorporarse al informe después de revisar tamaño y ubicación; debe acompañarse de la diferencia entre modelos no relajados y estructuras refinadas y de los casos no evaluables.", note=True))
    return paragraphs


def surface_sections(writer, data):
    summary = data["sasa"]
    groups = summary["groups"]
    original, control = groups["pratt-original"], groups["experimental-reviewed-beta-solenoid"]
    paragraphs = [writer.paragraph("Accesibilidad al solvente como observable descriptivo", heading=True)]
    paragraphs.append(writer.paragraph("Se congeló un perfil descriptivo separado antes de calcular SASA en las mismas 108 entradas. FreeSASA implementa el cálculo de área accesible al solvente descrito por Mitternacht (2016). Se fijaron Lee y Richards, radios ProtOr, una sonda de 1,4 Å, 20 cortes y un hilo. La distribución Python utilizada es 2.2.1; el config.h incluido en su archivo fuente declara 2.0.2, por lo que ambas identidades y el hash del módulo compilado se conservan sin atribuirle al motor C la versión de la envoltura. La accesibilidad lateral relativa, rSA, divide el área por la referencia ProtOr de un tripéptido Ala-X-Ala extendido; puede superar 1 y no se recorta. No se eligió un umbral de enterramiento ni una regla de clasificación física."))
    paragraphs.append(writer.paragraph(f"Se obtuvieron áreas válidas en {original['sasaEvaluable']}/{original['cases']} originales y {control['sasaEvaluable']}/{control['cases']} referencias. Se conservan {data['sasa_residue_total']} observaciones por residuo y {original['chargedResidues']+control['chargedResidues']} Asp/Glu/Lys/Arg. Los originales contienen {original['chargedResidues']} cadenas laterales completas; {original['casesWithoutChargedResidues']} modelos, incluido 8b, no contienen esas identidades y su resumen lateral es no aplicable, no cero. Las referencias contienen {control['chargedResidues']} de esos residuos: {control['completeChargedSidechains']} completos y {control['incompleteChargedSidechains']} incompletos, estos últimos distribuidos en {data['sasa_incomplete_charged_cases']} estructuras. {data['sasa_missing_heavy_cases']} referencias tienen alguna ausencia de átomos pesados, incluida una con ausencias fuera de Asp/Glu/Lys/Arg. Las áreas parciales se conservan, pero una cadena lateral incompleta no entra en los resúmenes interpretables."))
    report = data["sasa_22r"]
    asp = next(r for r in report["residueObservations"] if r["residue"] == "28")
    paragraphs.append(writer.paragraph(f"En 22r, enlazado con la Figura 3B de Pratt et al., se midieron {report['completeChargedSidechains']} cadenas laterales completas de Asp y Lys, con mediana rSA {as_spanish(report['chargedSidechainRelativeAreaMedian'], 8)}. Asp28 tiene área lateral {as_spanish(asp['areaAngstromSquared']['sideChain'], 10)} Å² y rSA {as_spanish(asp['interpretableChargedSidechainRelativeArea'], 8)}. Su secuencia contiene diez unidades idénticas de 22 residuos, lo que permite comparar cuatro posiciones laterales repetidas. Estas mediciones describen exposición al solvente y no establecen protonación, compensación de cargas, contraiones, energía ni incorrección del pliegue."))
    files = data["sasa_agent"]["verification"]["files"]
    paragraphs.append(writer.paragraph(f"Se incorporó a Helix una envoltura opcional configurada por el operador mediante HELIX_TRP_SURFACE_PYTHON, con versiones y hashes de FreeSASA y Gemmi, selección explícita y límite de 180 segundos. La inspección real de archivos para 22r coincidió con los observables externos y verificó una copia portable privada de {files} archivos. La eliminación controlada de OD1 en Asp28 permaneció identificada como cadena lateral incompleta y el caso 8b conservó un estadístico no aplicable. Esos controles verifican ingeniería, no etiquetas biológicas. El paquete aprobado incluye la envoltura y su hash; C9 conserva no evaluable y la validez biológica no establecida. Las 108 mediciones externas no se presentan como 108 sesiones del agente."))
    paragraphs.append(writer.paragraph("La SASA se calculó sobre la cadena polimérica completa seleccionada, sin otras cadenas, ligandos, aguas ni hidrógenos. Las ausencias en residuos vecinos y los componentes omitidos también pueden cambiar el área. La composición, longitud y preparación distintas impiden atribuir el contraste entre grupos exclusivamente a validez física. La figura propia structural/freesasa/surface-exposure.png, con versiones PDF/SVG y pie, muestra las distribuciones y cuatro posiciones de 22r sin añadir un corte de decisión. La sensibilidad y especificidad físicas continúan sin estimar."))
    return paragraphs


def result_table(writer, data):
    diag = data["structural"]
    diag_text = "Diagnóstico estérico en curso" if diag is None else "; ".join(f"{diag['groups'][name]['evaluable']}/{diag['groups'][name]['cases']}" for name in ("pratt-original", "experimental-reviewed-beta-solenoid")) + " diagnósticos estéricos evaluables"
    sasa_text = "; ".join(f"{data['sasa']['groups'][name]['sasaEvaluable']}/{data['sasa']['groups'][name]['cases']}" for name in ("pratt-original", "experimental-reviewed-beta-solenoid")) + " áreas de superficie evaluables"
    if data["workflow"] is None:
        workflow_text = str(len(data["additional_cloud_summaries"])) + "/50 variantes técnicas terminadas con comparador propio."
    else:
        counts = data["workflow"]["counts"]
        workflow_text = f"Primera tentativa: {counts['first_attempt_succeeded']}/{counts['first_attempts']} verificadas, {counts['first_attempt_failed']} fallos. {counts['unique_cases_verified']}/50 casos únicos verificados tras {counts['retry_attempts']} tentativas adicionales."
    rows = [
        ["R1.1", "Catálogo 1.2.0: tres operaciones admitidas de seis recursos auditados.", "Implementación parcial del dominio; ReUPred y contrato de loci RepeatsDB pendientes."],
        ["R1.2", "Especificación tipada, origen de parámetros y aprobación vinculada. Piloto real: dos preparaciones suministradas y dos consultas de alcance.", "Software verificado en desarrollo; cuatro acciones auditadas sin puntuación semántica independiente ni desempeño reservado."],
        ["R1.3", "Setenta solicitudes preparadas; referencias y cien paráfrasis humanas sin recibir.", "Preparación; admisibilidad y estabilidad externas sin calcular."],
        ["R1.4", "Protocolo 1.0.1 con veintiún indicadores; planes técnicos y enmiendas operativas fechados.", "Diseño implementado; congelación final de campañas científicas pendiente."],
        ["R1.5", "Referencia local y Helix sobre dos trabajadores Slurm; CSV coincidente. " + workflow_text, "Motor verificado en desarrollo; meta de 95% sobre cincuenta especificaciones externas pendiente."],
        ["R1.6", f"Slurm: 206 residuos y doce unidades, CSV idéntico. Fuentes públicas: {data['public_mapping']['labelMapped']}/{data['public_mapping']['labelPositions']} label/autor; SIFTS 30/30; preparación 28/30 con 11215 residuos y dos rechazos correctos.", "Correspondencias contrastadas con fuentes separadas en desarrollo; cero inserciones observadas. Referencia humana y evaluación reservada pendientes."],
        ["R1.7", "Cincuenta grafos válidos y treinta inválidos; validación y recorrido simulado previos a ejecutar en Slurm.", "Controles implementados y contrastados técnicamente; generalización de la reserva pendiente."],
        ["R1.8", "Informes conservan comprobaciones realizadas, omitidas y no evaluables, con motivos.", "Implementado en las ejecuciones observadas; cobertura de campaña completa pendiente."],
        ["R1.9", "Cero de treinta inválidas admitidas; diez modos con tres variantes, además de la regresión histórica.", "Corpus técnico medido; no se presenta como desempeño sobre proteínas independientes."],
        ["R2.1", "Inventarios fechados de controlador y nodos; memoria y CPU por trabajo, sin sumar RAM entre trabajadores.", "Implementado local y remoto; recurso compartido y alcance de reservas explícitos."],
        ["R2.2", "Cuatro tareas por flujo, conteos verificables en frío; siete contrastes locales con margen mediano 13,54%.", "Ingeniería local verificada; cota estricta y margen de almacenamiento remoto no demostrados."],
        ["R2.3", "Negativas tipificadas y reobservación antes de ejecutar; límites de capacidad contrastados independientemente.", "Mecanismo implementado; corpus completo de decisiones de flujos pendiente."],
        ["R2.4", "Hardware: cuarenta contrastes. Espacio del controlador: cuarenta casos, 26 factibles, 14 inviables; acierto 34/40 y falso rechazo 6/26. Extensión separada de seis inviables.", "Falso rechazo acotado: 23,08%, superior a 5%; alcance distinto del presupuesto completo. Evaluación agregada y científica pendientes."],
        ["R3.1", "Paquetes de 144 y 156 archivos: 296/296 y 320/320 fallos inyectados detectados; copia mapeada verificada fuera del repositorio.", "Integridad y conteos verificados sin red ni modelo; intentos fallidos conservados, sin acreditar verdad biológica."],
        ["R3.2", "Diez eventos de la referencia y 13/13 registros de cuatro sesiones de rechazo, con acciones externas, causas y orden contrastados. Cancelación nativa y empaquetado automático auditados.", "Cobertura técnica verificada en esos caminos; actores sintéticos. Cobertura de sesiones humanas pendiente."],
        ["R3.3", "Clasificador y conteo implementados; no hay corpus de cien turnos con primeras etiquetas independientes.", "Kappa y corrección emparejada sin calcular; respuestas del conductor no son turnos humanos."],
        ["R3.4", "Veinte campos de métodos enlazados a fuentes; plantilla de Markdown reproducida exactamente.", "Derivación mecánica verificada en la referencia; cobertura de campaña completa pendiente."],
        ["R3.5", "Nueve controles documentados; diagnósticos opcionales estérico y FreeSASA en C9, con versiones y hashes.", "Catálogo implementado; no comprende un clasificador validado de todos los fallos físicos."],
        ["R3.6", "Valores y estados: " + diag_text + "; " + sasa_text + ".", "Batería mecánica y observables implementados; veredicto físico general no evaluable."],
        ["R3.7", "Reportes por instancia con fuente, versión, marco, confianza y diagnóstico disponible.", "Artefactos implementados y verificables; validez biológica no establecida."],
        ["R3.8", "Setenta y ocho originales Pratt y cinco ejemplos problemáticos; treinta referencias revisadas del dominio.", "Sensibilidad física y especificidad sin calcular; faltan regla validada y etiquetas físicas pertinentes."],
    ]
    return [writer.paragraph("Estado de los veintiún resultados", heading=True),
            writer.paragraph("Tabla 4.2. Evidencia y estado de verificación por resultado esperado"),
            writer.table(["ID", "Evidencia observada", "Estado y alcance pendiente"], rows, [900, 3900, 4200]),
            writer.paragraph("La palabra implementado identifica software o diseño construido y verificado en el alcance descrito. No equivale al cumplimiento de un indicador científico reservado. Los porcentajes objetivo y sus denominadores originales permanecen vigentes; los valores ausentes se informan como no calculados y no como cero aciertos.")]


def annex(writer, data):
    paragraphs = [writer.paragraph(ANNEX_TITLE, heading=True)]
    paragraphs.append(writer.paragraph("La adaptación operativa utiliza dos cuentas Learner Lab de US$50 cada una, sin sumar sus créditos, RAM o cuotas como si pertenecieran a un solo equipo. Cada clúster reside dentro de una cuenta y una red propia. La topología permitida tiene un controlador t3.medium de dos vCPU y 4 GiB y dos trabajadores m5.large de dos vCPU y 8 GiB cada uno; Slurm reserva 7400 MiB por trabajador. Se asignaron volúmenes raíz de 50, 20 y 20 GiB, noventa por cuenta, que incluyen sistema y cachés. La instalación manual con el perfil de laboratorio disponible conserva Slurm, Docker y un directorio NFS compartido. No presupone permisos de AWS ParallelCluster, instancias grandes, GPU ni ejecución MPI."))
    paragraphs.append(writer.paragraph("Se verificó una duración de cuatro horas por sesión de Academy y su renovación mediante Start Lab. Las credenciales temporales se mantienen fuera del repositorio. Un temporizador del huésped detiene cada instancia a los 180 minutos de su arranque, y la admisión observa el tiempo restante antes de aceptar un flujo. Renovar la sesión no elimina ese temporizador. Se conservan puntos de recuperación y copias locales de evidencia antes de detener cómputo. Las instancias detenidas dejan de ejecutar, pero los volúmenes conservados siguen generando costo; el panel de presupuesto puede reflejar consumos con ocho a doce horas de retraso. No se afirma un costo final a partir de una cifra retrasada."))
    paragraphs.append(writer.paragraph("El operador fija destino SSH, claves, confianza del anfitrión, cola y nodos en una configuración privada. El modelo no suministra esas credenciales ni inventa capacidades. El destino, la configuración de Nextflow, los programas, entradas, presupuesto e imagen se incorporan al digest antes de la respuesta de aprobación. Una modificación invalida la propuesta. El controlador realiza el recorrido simulado, publica un nuevo inventario y espera la decisión de admisión reconocida por el agente antes de lanzar tareas científicas. Se guardan IDs y estados nativos, ubicación por nodo, observaciones cgroup, transferencias y fallos."))
    paragraphs.append(writer.paragraph("Los contenedores científicos observados tuvieron cuota de dos CPU, límite de 2 GiB y swap cero; se fijó BLAS a una hebra y perfil Haswell para el contraste numérico documentado. La cuota CPU representa ancho de cómputo, sin reservar núcleos exclusivos. La reserva del controlador y la estimación de disco de esta ruta no disponen de los límites duros XFS/cgroup de la asignación local descrita en A.20. La capacidad de un trabajo se decide por nodo; dos trabajadores de 8 GiB no permiten ejecutar un proceso que exija 16 GiB en uno de ellos."))
    paragraphs.append(writer.paragraph("La reproducción de infraestructura utiliza script/tesis/aws_academy_access.py, aws_academy_cluster.py y aws-academy-bootstrap.sh, con su estado privado fuera del repositorio. La campaña de límites se conserva en cloud/lab2-pressure/plan.json y sus cuarenta registros. script/tesis/audit_remote_campaign.py comprueba la copia de Helix usando un hash de manifiesto conservado por separado, las trazas nativas, el enlace de aprobación y los métodos derivados. Su opción --reference-run exige las mismas coordenadas, cadena, modelo, unidades e inserciones antes de comparar CSV; --fault-injection altera solo una copia. trace/audit_pressure.py reconstruye la capacidad observada de cada nodo y los resultados de presión sin acceder a AWS."))
    paragraphs.append(writer.paragraph("Los cincuenta grafos válidos y treinta inválidos se reproducen mediante evaluation/trp/campaign-20261012/run_contract_graphs.ts. Los archivos contract-corpus/graphs.json y freeze.json fijan sus etiquetas; las modificaciones posteriores de recursos conservan el código de procedencia original en frozen-sources sin alterar los casos. Las variantes de 2xqh y sus ejecuciones siguen siendo desarrollo. Los cuarenta presupuestos sintéticos adicionales verifican fronteras de contrato y mantienen factibilidad física sin etiqueta: no son la matriz empírica de R2.4."))
    if data["workflow"] is not None:
        paragraphs.append(writer.paragraph("script/tesis/summarize_remote_workflows.py reconstruye el resumen final desde cada case.json y cada directorio de revisión conservado. Contrasta especificación y coordenadas con el caso congelado, los argumentos e imagen del comparador independiente y su entrada con la salida SELECT. Después utiliza el auditor remoto y conserva el informe de cada tentativa. Los campos de primera tentativa, fallos, tentativas adicionales y casos únicos se recalculan antes de incorporarlos al Word. No se reutiliza el CSV de las doce unidades para comparar un subconjunto distinto."))
    if data["structural"] is not None:
        paragraphs.append(writer.paragraph("El diagnóstico estérico se reproduce desde structural/protocol.json y la lista de fuentes y casos congelada. Se utiliza mmtbx.programs.clashscore2.Program de cctbx-base 2025.11: keepHydrogens=false, doFlips=false, nuclear=false, bFactorCutoff=null y fast=false. La implementación mantenida se consulta en https://github.com/cctbx/cctbx_project/blob/master/mmtbx/programs/clashscore2.py; la versión instalada queda fijada mediante los hashes de módulos y recursos registrados. Las coordenadas originales no se relajan ni reparan. El análisis comprende la cadena seleccionada, sin incorporar otras cadenas, ligandos o aguas al contraste acotado. El umbral atómico de 0,4 Å no es un límite de aceptación de moléculas completas. Los JSON y logs registran versiones, hashes, número de contactos, puntaje y no evaluabilidad; physicalSensitivity, physicalSpecificity y classifierValidated no se sustituyen por valores supuestos."))
    paragraphs.append(writer.paragraph("El perfil SASA se reproduce con script/tesis/structural_sasa_campaign.py y el verificador independiente verify_sasa_campaign.py. structural/freesasa/protocol.json, freeze.json, manifest.json y analysis-manifest.json conservan parámetros, módulo compilado, archivo fuente y entradas; los CSV por residuo incluyen ausencias y rSA interpretable nula para cadenas laterales incompletas. 22r se reprodujo byte a byte en el mismo entorno. La figura PNG/PDF/SVG y su pie se derivan de esos registros. La integración de Helix se documenta separadamente en structural/freesasa/integration/: diagnóstico configurado por el operador, paquetes privados con coordenadas originales y envoltura identificada por hash. Los hashes de versiones reales forman parte de la evidencia determinista ligada a la aprobación; una variación invalida el contenido preparado. Mitternacht (2016) y la documentación oficial de FreeSASA sustentan el método, fuera del corpus de revisión sistemática."))
    paragraphs.append(writer.paragraph("El piloto de lenguaje se conserva en model-pilot/freeze.json y audit.json. Su auditoría contrasta las salidas JSONL y las dos llamadas de preparación con los argumentos previamente suministrados, sin ejecución científica ni puntuación semántica humana. La equivalencia de tarifas incorpora la lectura de caché, conserva actual_charge_usd=null y no sustituye registros de facturación. model-pilot/settings-probe/observed.jsonl conserva una sonda separada: razonamiento medio configurado, maximumOutputTokens=null y serviceTier=null en los registros observados. Las solicitudes registradas de esa sonda no establecen por sí mismas todas las condiciones efectivas de los cuatro casos anteriores; esos límites y la revisión del proveedor deben comprobarse antes de medir la reserva."))
    paragraphs.append(writer.paragraph("La cancelación limpia se conserva en cloud/lab1/cancellation/next-ctx-abort/driver-terminal.json y trace/running-cancellation-clean.json. El terminal enlaza por hash el fixture, el snapshot previo de fuentes, el registro del conductor y las lecturas independientes antes y después de Tool.Context.abort. El generador del informe verifica esas piezas y su orden temporal, además del estado nativo CANCELLED, la salida 143:0, el controlador detenido y la ausencia de trabajos y contenedores. La prueba aprobada no borra los intentos anteriores ni convierte la terminación del flujo en una salida científica satisfactoria."))
    paragraphs.append(writer.paragraph("La ejecución mapeada se conserva en cloud/lab1/mapped-reference-protocol/driver-terminal.json, enlazado por hash a fuentes, conductor, auditoría, copia portable y observaciones finales. Cada tarea conserva .command.trace y el programa rastreador .command.run; sus máximos RSS son salidas instrumentales por árbol de procesos. No se suman para inventar un pico global ni se sustituyen por el límite permitido de 2 GiB. Los alcances de almacenamiento final del directorio del controlador y del archivo del cliente son distintos, incluyen duplicados diferentes y no miden picos. checks/final-regression/summary.json y domain.log conservan el resultado de la regresión de software con las pruebas opcionales explícitamente omitidas."))
    paragraphs.append(writer.paragraph("El contraste público se conserva en mapping-public-contrasts/: protocol.json fija treinta identidades y límites, audit-method.json identifica el auditor separado y oracle-freeze.json sella fuentes y expectativas antes del productor. manifest.json enlaza todas las fuentes, informes y helpers por hash. script/tesis/public_mapping_contrasts.py obtiene CIF/PDB de https://files.rcsb.org/download/ y SIFTS de https://ftp.ebi.ac.uk/pub/databases/msd/sifts/: intenta xml_remediated y sólo tras HTTP 404 admite xml, alternativa registrada en las treinta cadenas. Se conservan URL efectiva, fecha, Last-Modified y SHA, con una petición por URL, 30 segundos de transporte, 20 MB por archivo y XML descomprimido, y un intento científico por cadena con límite de 180 segundos. Gemmi es compartido como lector léxico; las operaciones comparadas son independientes. El fixture heredado de especificación tipada tiene su hash capturado retrospectivamente, identificado como tal; no se atribuye a la congelación previa."))
    paragraphs.append(writer.paragraph("script/tesis/audit_public_mapping_contrasts.py compara las filas y salidas reales con las expectativas congeladas; verify_public_mapping_evidence.py comprueba además hashes, conjuntos exactos de etiquetas, denominadores y la reproducción de una cadena admitida y ambos rechazos. summary.json conserva 11751 correspondencias label/autor, 11749 filas SIFTS observadas con accesión, 265 no observadas y 11215 residuos preparados en 28 cadenas. Dos cadenas se rechazan por residuos observados sin CA; cuatro CA carecen de la referencia observada seleccionada. Cero inserciones o ubicaciones alternativas no acreditan cobertura real de esos casos. Ninguno de estos conteos valida límites biológicos de repetición ni deriva de una anotación humana. Las fuentes metodológicas oficiales se consultan en https://www.ebi.ac.uk/pdbe/docs/sifts/quick.html y https://www.ebi.ac.uk/pdbe/docs/sifts/efamily.html."))
    paragraphs.append(writer.paragraph("Las enmiendas operativas describen la topología manual permitida, la separación de campañas deterministas y humanas y el perfil numérico fijado. Mantienen las metas de F2 y conservan intentos fallidos. No se usaron resultados reservados para rebajar metas, eliminar casos o elegir un corte físico. Las referencias metodológicas de MolProbity y de la implementación mantenida se citan como fuentes del método fuera de la revisión sistemática del Capítulo 3."))
    paragraphs.append(writer.paragraph("El primer contraste de factibilidad de desarrollo se reproduce desde cloud/lab2/r24-campaign, r24-continuation y r24-extension. r24-summary.json distingue los cuarenta IDs originales, sus 42 tentativas y los seis casos posteriores; r24-evidence-manifest.json conserva 7763 archivos. Su unidad es el bloque asignado del proyecto XFS del controlador, con el cliente real fuera del alcance. event-negative-contrasts/protocol.json fija las cuatro sesiones de rechazo antes del resultado; audit.json contrasta las acciones externas con los registros efectivos y conserva dos paquetes automáticos fallidos. Ambas campañas tienen referencias deterministas, sin etiquetas humanas ni validación biológica."))
    paragraphs.append(writer.paragraph("NOTA PARA EL AUTOR. La entrega externa requerida continúa siendo el Excel con referencias y paráfrasis y, en una segunda etapa, la anotación de turnos humanos reales. La financiación de AWS y el acceso al modelo permiten continuar trabajo técnico, pero no reemplazan esas entregas. Mantener como pendientes las mediciones dependientes y documentar el consumo real cuando el panel y los registros de facturación permitan contrastarlo.", note=True))
    return paragraphs


def replacements():
    # Two-pass refinement: retain historical measurements but correct present
    # dependency claims; avoid claiming broad completion from narrow evidence.
    return {
        "Este capítulo presenta los 21 resultados esperados": "Este capítulo presenta los 21 resultados de los tres objetivos específicos y distingue implementación, contraste técnico y evaluación científica reservada. Conserva las referencias históricas de las fases F1 a F5 e incorpora la campaña iniciada el 12 de octubre de 2026: ejecución real de Helix en Slurm sobre AWS Academy, comprobaciones de recursos, evidencia portable, piloto real del modelo elegido y diagnósticos estérico y de superficie. El Anexo A documenta el plan y las condiciones de reproducción. Las mediciones que requieren referencia independiente permanecen explícitas.",
        "La arquitectura prevista sigue el orden pregunta": "La arquitectura implementada enlaza pregunta, especificación, aprobación, composición, validación, admisión, ejecución y evidencia. La aprobación identifica un contenido concreto, incluido el destino remoto cuando existe; un cambio posterior no hereda automáticamente esa aprobación. Identificadores, numeración y recursos se comprueban antes de ejecutar, y los veredictos se conservan con sus datos. La existencia de la ruta no demuestra por sí sola comprensión de todas las solicitudes.",
        "Relación con el objetivo: OE1. Preparar al menos 50 enunciados": "El instrumento de referencia contiene setenta solicitudes propuestas: cincuenta intenciones factibles y veinte fuera de alcance. La asesora está designada como experta externa al desarrollo, según lo declarado por el tesista. No se han recibido todavía sus referencias, correcciones ni las cien paráfrasis humanas requeridas. La admisibilidad y estabilidad se medirán después de preservar y congelar su primera entrega; las propuestas asistidas por IA no se presentan como anotaciones independientes.",
        "En F2 se redactó el protocolo TRP 1.0.0": "En F2 se redactó el protocolo TRP 1.0.0 y posteriormente se migraron los identificadores a la versión 1.0.1, sin modificar umbrales ni tamaños. Sus veintiún indicadores tienen medición, denominador, criterio y regla de reporte. El apartado A.16 conserva el diseño; la campaña técnica y las enmiendas operativas se documentan en A.25 y evaluation/trp/campaign-20261012/. El registro local por Git y hash no se presenta como prerregistro externo.",
        "Estos umbrales son metas, no resultados ni valores avalados": "Estos umbrales son metas, no resultados ni valores avalados por las herramientas. El protocolo separa desarrollo y reserva por intención, sesión y familia, y fija repeticiones, caídas de servicio, exclusiones e incertidumbre. La asesora y el modelo gpt-6-sol fueron elegidos por el autor; dos laboratorios AWS y el acceso efectivo al modelo quedaron comprobados técnicamente. La referencia humana, las paráfrasis y la congelación científica aplicable permanecen pendientes.",
        "Se mantienen pendientes la autenticación externa de las fuentes": "STRPsearch dispone de una ruta admitida de detección, y SIFTS y modelos predichos cuentan con adaptadores en el alcance descrito. Continúan pendientes referencias humanas, autenticación externa de las fuentes y cobertura independiente del dominio. Los informes distinguen controles no evaluables y las garantías locales de las remotas. La verificación de CSV exige identidad, límites, número de unidades, valores finitos, escala TM-score, relleno inicial y resúmenes etiquetados.",
        "La admisión compara capacidad, demanda y presupuesto.": "La admisión compara capacidad, demanda y presupuesto. Un inventario ausente, incompleto, ilegible o con más de cinco minutos no concede admisión. Se reobserva después de aprobar y antes del análisis real. La ruta Linux x64 dispone de ejecución local y de un adaptador SSH/Slurm verificado en AWS Academy; los contenedores usan Docker en el nodo de ejecución. El inventario remoto distingue controlador, trabajador elegible y cada nodo obligado por la propuesta.",
        "En la ruta ordinaria, el inventario representa capacidad compartida": "En la ruta ordinaria, el inventario representa capacidad compartida limitada por cgroups heredados. La asignación local estricta distingue presupuesto completo de consumo actual. La ruta Slurm comprueba capacidad de controlador y trabajos por nodo, sin agrupar memoria entre trabajadores. Imagen y Nextflow se verifican aparte. Las llamadas y el coste del proveedor no forman parte de ese contador; el presupuesto autorizado del modelo es US$100 y su facturación no se infiere del coste cero del complemento OAuth.",
        "El contador distingue los canales de entrada de las tareas ejecutables": "El contador distingue canales y tareas: dos simuladas y dos científicas, sin reintentos automáticos. En local las llamadas científicas remotas son cero; en la ruta Slurm se registran las dos tareas científicas enviadas a infraestructura remota. Las trazas contrastan esos conteos y conservan los comandos de control observados. La conversación del proveedor, los sondeos de monitorización y el consumo monetario de API se reportan por separado y no se confunden con el número de tareas.",
        "El registro cuenta la instantánea de mensajes": "El registro cuenta la instantánea de mensajes proporcionada a la herramienta; las respuestas de la interfaz de aprobación se conservan separadamente en los eventos. Otros significa que no se encontró una señal reconocida, no ausencia demostrada de intervención. Las pruebas usan ejemplos de desarrollo y no sustituyen etiquetas externas. El acuerdo externo permanece sin calcular hasta recibir primeras etiquetas independientes de los turnos elegibles de T-TURNS; no se asigna un kappa ficticio.",
        "El control de plausibilidad física permaneció no evaluable en 78/78": "La inspección del 1 de octubre conservó el control de plausibilidad física no evaluable en 78/78 modelos: cobertura física 0% y detección conservadora 0/5 para los ejemplos publicados. La extensión del 12 de octubre añadió un puntaje estérico, áreas descriptivas de superficie y treinta referencias experimentales con anotación revisada de RepeatsDB, documentados en este capítulo. Esa anotación no demuestra ausencia de todo fallo físico y no completa una clase negativa validada. Sensibilidad física y especificidad siguen sin calcular; se mantienen las metas F2 de 80%, 90% y 90% para sensibilidad, especificidad y cobertura, sin declarar cumplimiento. Coordenadas y PAE originales dejaron de ser el bloqueo.",
        "NOTA PARA EL AUTOR. Los originales de la Tabla S1 ya fueron recuperados": "NOTA PARA EL AUTOR. Los originales de la Tabla S1 fueron recuperados y el diagnóstico estérico posterior se registra separadamente. Marcar 78/78 por confianza no demuestra discriminación; hallar contactos tampoco completa un veredicto físico. Las treinta referencias revisadas requieren una interpretación de etiquetas pertinente y un control validado antes de medir R3.8. Conservar los casos empleados para diseño como desarrollo, sin reutilizarlos como reserva intacta.",
        "La configuración limita cada tarea a dos CPU, 2 GB y tres minutos": "La configuración histórica de F3 limitó cada tarea a dos CPU, 2 GB y tres minutos, sin reintentos ni red. Esa referencia local no demostraba clúster. La campaña posterior en AWS Academy verifica trabajos reales de Helix sobre Slurm y documenta sus límites por nodo en A.25. La anotación independiente continúa pendiente; se mantiene julio de 2027 para la sustentación y el 4 de junio como objetivo del borrador completo.",
        "F4 completa una primera implementación de admisión": "F4 construyó admisión y proveniencia para la ruta geométrica local, y su cierre R2.2 añadió cuota y límites de controlador/tareas con siete contrastes. Las incorporaciones posteriores incluyen STRPsearch, mapeos SIFTS y una ruta predicha; la campaña de octubre añade ejecución real en Slurm. Persisten la evaluación reservada y los contratos de dominio no admitidos. Se mantienen julio de 2027 y el 4 de junio como mes de sustentación y objetivo del borrador.",
        "La segunda fase verificó localmente la recuperación de una estructura PDB": "La segunda fase verificó recuperación PDB y geometría GeomeTRe; fases posteriores admitieron STRPsearch e incorporaron correspondencias SIFTS y modelos predichos. En octubre se verificó Helix sobre un clúster Slurm de AWS Academy y acceso al modelo elegido. La asesora está designada, pero referencias y etiquetas independientes siguen sin recibir. ReUPred y el contrato de loci de RepeatsDB conservan límites técnicos; la obtención de anotaciones revisadas para un comparador no equivale a admitir todas sus conversiones.",
        "NOTA PARA EL AUTOR. Escenario de trabajo mientras se confirman recursos": "NOTA PARA EL AUTOR. Los escenarios de costo de este anexo son planificación histórica. Ahora hay dos cuentas Academy de US$50 y un modelo elegido con US$100 autorizados, sin una factura final inferida. Las etiquetas externas siguen pendientes. La infraestructura y sus limitaciones efectivamente observadas se documentan en A.25.",
        "R-E. Clúster no disponible.": "R-E. Restricciones o vencimiento del laboratorio. Síntoma: sesión caducada, nodo detenido, crédito agotado o recurso no permitido. La contingencia inicial de falta de clúster se resolvió técnicamente con AWS Academy. Mitigación actual: comprobar saldo y tiempo, fijar recursos permitidos, renovar por mecanismos autorizados, conservar evidencia y detener cómputo ocioso. Un nodo aislado no sustituye una ejecución verificada en Slurm; más cuentas no eliminan un límite de RAM por instancia.",
        "La utilización de clúster se contempla como recurso condicionado": "El clúster se implementó y ejecutó en dos laboratorios AWS Academy independientes. Cada inventario conserva las capacidades y condiciones reales de su ejecución; el tamaño permitido de las instancias y el vencimiento de sesión limitan el alcance. A.25 registra la topología manual Slurm, almacenamiento, control temporal y reproducción, sin sustituir esos registros por especificaciones supuestas.",
        "Antes de F6 se congelarán commit, protocolo, catálogo": "Antes de cada campaña reservada se congelarán commit, protocolo, catálogo, inventario y casos, fuentes, licencias, modelo/revisión, instrucciones, parámetros de muestreo, límites de tokens y llamadas, imágenes, dependencias, hardware y presupuesto. Se registrarán seudónimo, experiencia y acuerdo de la anotadora. Un dato aplicable pendiente impide iniciar la medición dependiente. El acceso a Slurm y gpt-6-sol tiene comprobación técnica y la experta fue designada; las etiquetas y paráfrasis humanas siguen sin recibir. Las campañas técnicas fechadas no se presentan como inferencia reservada realizada en F2.",
        "NOTA PARA EL AUTOR. Antes de F6 resolver anotador, modelo, presupuesto": "NOTA PARA EL AUTOR. Antes de la inferencia reservada recibir y congelar referencias, paráfrasis y acuerdo de uso de etiquetas; conservar la configuración efectiva del modelo y sus límites. El clúster y el acceso a gpt-6-sol ya tienen comprobación técnica. Se mantienen sustentación en julio de 2027 y borrador completo objetivo al 4 de junio. Las ilustraciones finales deben derivar de los datos conservados, sin suplir referencias humanas con ejemplos sintéticos.",
        "Permanecen pendientes ampliación del catálogo, mapeos SIFTS/UniProt": "STRPsearch está admitido en el catálogo 1.2.0 y los mapeos SIFTS/UniProt y la ruta predicha se incorporaron en el alcance documentado. Siguen pendientes ReUPred, contratos restantes y evaluación independiente del dominio. F4 y A.20 conservan la gobernanza local estricta; A.25 documenta la ruta remota y sus límites distintos. No se extiende una garantía por la sola existencia de un adaptador.",
        "R2.1 y R2.3 cuentan con mecanismos verificados en la ruta local.": "R2.1 y R2.3 cuentan con mecanismos locales y remotos verificados en desarrollo. R2.2 conserva su contraste local estricto de siete casos; el margen y una cota dura de almacenamiento remoto no se dan por establecidos. R2.4 necesita decisiones de flujos contrastadas con factibilidad observada, y R3.3 necesita turnos y primeras etiquetas independientes. La cobertura de puertas de R3.2 se verificó en la referencia remota, sin una afirmación de cobertura completa de sesiones. Modelo, experta y AWS tienen decisiones registradas; esas decisiones no sustituyen anotaciones terminadas.",
        "C9. Plausibilidad física.": "C9. Plausibilidad física. Pratt et al. (2025) muestran problemas que confianza alta no descarta. El control incorpora diagnósticos opcionales mediante Reduce2/Probe2 y FreeSASA, identificados por versiones y hashes, con contactos atómicos, clashscore y áreas de superficie. No hay un clasificador validado de validez física de la molécula: C9 conserva no evaluable y la validez biológica no establecida. La exposición medida no establece protonación ni compensación de cargas. Los observables y sus referencias experimentales se presentan separados de sensibilidad y especificidad.",
        "La evaluación reservada de F6 conserva el protocolo, las particiones": "La evaluación reservada conserva protocolo, particiones y referencias independientes. La asesora está designada y el acceso a gpt-6-sol y a Slurm fue comprobado técnicamente; no hay referencias humanas recibidas ni congelación final de T-LANG/T-TURNS. Los originales de rango 1 de Pratt se recuperaron y el diagnóstico estérico se incorporó como extensión exploratoria, sin validar un veredicto físico general. Los casos 2xqh y P69905 continúan excluidos de la reserva.",
        "Los resultados se conservan con valor, umbral y estado: 78/78": "La inspección histórica conserva 78/78 alarmas en el perfil principal y 77/78 en el central, incluidos los cinco ejemplos publicados. El control físico general sigue no evaluable. La campaña posterior añade valores estéricos en 77/78 originales y 28/30 referencias experimentales dentro de su perfil temporal, con tres límites de tiempo conservados. Las referencias revisadas no son automáticamente negativos físicos. Los otros 73 originales no se etiquetan retrospectivamente como correctos o fallidos; no hay rangos 2 a 5 ni todos los modelos preliminares de las figuras. Sensibilidad física y especificidad requieren una regla y etiquetas pertinentes independientes.",
    }


def conclusion_changes(data):
    counts = None if data["workflow"] is None else data["workflow"]["counts"]
    workflow_note = ("Las variantes técnicas observadas se conservan sin presentar un lote incompleto como terminado."
                     if counts is None else
                     f"Se verificaron {counts['unique_cases_verified']}/50 IDs técnicos tras conservar {counts['first_attempt_succeeded']} primeras tentativas satisfactorias, {counts['first_attempt_failed']} fallos y {counts['retry_attempts']} tentativas adicionales; son variantes de una sola proteína.")
    return {
        "La continuación técnica amplía el alcance verificable: incorpora detección STRPsearch": "La implementación integra un catálogo inicial, detección STRPsearch, correspondencias SIFTS, geometría sobre modelos predichos y ejecución aprobada con evidencia portable. La campaña de octubre demuestra que Helix puede enviar y recuperar trabajos reales de Slurm en la infraestructura permitida de AWS Academy y reproducir la referencia geométrica bajo condiciones fijadas. Los diagnósticos estérico y de superficie añaden observables independientes de pLDDT/PAE, contrastados con los adaptadores reales de Helix, sin validar por sí solos la plausibilidad completa del pliegue. La anotación externa y las métricas reservadas permanecen pendientes.",
        "Las cinco fases desarrolladas construyen una base verificable": "Los resultados técnicos sostienen la separación entre propuesta, aprobación, decisiones mecánicas y evidencia. La ruta local dispone de la asignación estricta documentada; la ruta remota aporta trabajos nativos, observaciones de límites de contenedores y verificación sin red. Sus garantías no son idénticas: no se demostró cuota dura de disco ni límite duro del controlador remoto. La infraestructura disponible permite continuar evaluación técnica sin atribuirle validación humana o biológica.",
        "Respecto del OE1, se implementaron el catálogo inicial": f"Respecto del OE1, el motor transforma una especificación aprobada y validada en un flujo ejecutable local o en Slurm para las rutas admitidas. La referencia reprodujo el CSV y las composiciones adversariales permitieron contrastar rechazos estáticos. {workflow_note} El contraste público coincidió con expectativas de fuentes separadas en 11751 correspondencias label/autor y treinta parses SIFTS; admitió 28 preparaciones con 11215 residuos y conservó dos rechazos correctos por ausencia de CA. No valida límites biológicos ni casos reales con inserciones, ausentes del conjunto. El piloto real de cuatro solicitudes no tiene puntuación semántica independiente. La admisibilidad del lenguaje, su estabilidad ante paráfrasis y la tasa sobre cincuenta especificaciones externas no pueden concluirse sin las referencias humanas previstas.",
        "Respecto del OE2, se implementaron inventarios fechados": "Respecto del OE2, existen inventarios fechados, conteos reproducibles y negativas tipificadas. Los cuarenta contrastes independientes demostraron límites de capacidad y contención del laboratorio, con recursos considerados por nodo. No constituyen una matriz de acierto y falso rechazo de flujos bioinformáticos, por lo que ese resultado conserva su evaluación pendiente. Respecto del OE3, el paquete remoto y los métodos derivados permiten verificar integridad y decisiones registradas sin el modelo ni la infraestructura que ejecutó el análisis. El kappa y la sensibilidad/especificidad física requieren sus referencias independientes.",
        "NOTA PARA EL AUTOR. Conclusiones provisionales de avance.": "NOTA PARA EL AUTOR. Estas conclusiones se apoyan en las mediciones técnicas del Capítulo 4. El clúster y el modelo dejaron de ser dependencias de acceso, pero las referencias humanas, el corpus de turnos y una regla física validada siguen abiertos. No presentar el cierre técnico como cumplimiento de los tres objetivos ni trasladar estos requisitos a trabajos futuros para dar por terminada la tesis.",
    }


def primary_method_citations(writer, body):
    """Add verified methodology references outside protected Chapters 1 to 3."""
    entries = [
        ("10.1002/pro.3330", "Wratten, L.,", "Williams, C. J., Headd, J. J., Moriarty, N. W., Prisant, M. G., Videau, L. L., Deis, L. N., Verma, V., Keedy, D. A., Hintze, B. J., Chen, V. B., Jain, S., Lewis, S. M., Arendall, W. B., III, Snoeyink, J., Adams, P. D., Lovell, S. C., Richardson, J. S., & Richardson, D. C. (2018). MolProbity: More and better reference data for improved all-atom structure validation. Protein Science, 27(1), 293–315. https://doi.org/10.1002/pro.3330"),
        ("10.12688/f1000research.7931.1", "Mozaffari, S.,", "Mitternacht, S. (2016). FreeSASA: An open source C library for solvent accessible surface area calculations. F1000Research, 5, 189. https://doi.org/10.12688/f1000research.7931.1"),
    ]
    added = {}
    for doi, prefix, citation in entries:
        added[doi] = False
        if any(doi in text(item) for item in body):
            continue
        after = next((p for p in body if text(p).startswith(prefix)), None)
        p = writer.paragraph(citation)
        if after is not None:
            ppr = p.find(q("pPr"))
            if ppr is not None:
                p.remove(ppr)
            existing_pr = after.find(q("pPr"))
            if existing_pr is not None:
                p.insert(0, deepcopy(existing_pr))
            writer.insert_before(after, [p])
        else:
            anchor = next(item for item in body if text(item) == "Anexo A: Plan de Proyecto")
            writer.insert_before(anchor, [p])
        added[doi] = True
    return added


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--target", type=Path, default=TARGET)
    parser.add_argument("--checks", type=Path, default=BASE / "document/checks.json")
    parser.add_argument("--require-structural-summary", action="store_true")
    parser.add_argument("--require-workflow-summary", action="store_true")
    args = parser.parse_args()
    if args.source.resolve() == args.target.resolve() or args.target.resolve() == SOURCE.resolve():
        raise ValueError("This generator writes a candidate only; root installs separately")
    data = evidence()
    source_hash_at_start = sha(args.source)
    if args.require_structural_summary and data["structural"] is None:
        raise ValueError("Final structural summary not yet available; no projected results")
    if args.require_workflow_summary and data["workflow"] is None:
        raise ValueError("Final workflow summary not yet available; no projected results")
    changed = []
    with ZipFile(args.source) as archive:
        original = archive.read("word/document.xml")
        doc = E.fromstring(original, E.XMLParser(resolve_entities=False, no_network=True, remove_blank_text=False))
        body = doc.find(q("body"))
        items = list(body)
        boundary = next(i for i, item in enumerate(items) if text(item) == "Presentación de los resultados esperados")
        if any(text(item) == SECTION_TITLE or text(item) == ANNEX_TITLE for item in body):
            raise ValueError("Candidate sections already exist; regenerate from unchanged original Word")
        protected = [E.tostring(item) for item in items[:boundary]]
        writer = Writer(body)
        map_current = replacements()
        map_conclusions = conclusion_changes(data)
        conclusion = next(item for item in body if text(item) == "Conclusiones y trabajos futuros")
        references = next(item for item in body if text(item) == "Referencias")
        conclusion_index, reference_index = list(body).index(conclusion), list(body).index(references)
        for index, item in enumerate(items[boundary:], start=boundary):
            for p in item.iter(q("p")):
                before = text(p)
                candidates = map_conclusions if conclusion_index < index < reference_index else map_current
                for prefix, value in candidates.items():
                    if before.startswith(prefix):
                        replace_text(p, value)
                        changed.append({"before": before, "after": value})
                        break
        writer.insert_before(conclusion, measured_campaign(writer, data) + structural_sections(writer, data) + result_table(writer, data))
        added_citations = primary_method_citations(writer, body)
        section = body.find(q("sectPr"))
        if section is None:
            raise ValueError("Original section properties missing")
        writer.insert_before(section, annex(writer, data))
        if [E.tostring(item) for item in list(body)[:boundary]] != protected:
            raise ValueError("Protected Chapters1–3 body XML changed")
        serialized = E.tostring(doc, encoding="utf-8", xml_declaration=True)
        # Validate the serialized candidate, not merely the in-memory objects.
        candidate = E.fromstring(serialized)
        candidate_items = list(candidate.find(q("body")))
        if [E.tostring(item) for item in candidate_items[:boundary]] != protected:
            raise ValueError("Protected XML changed during serialization")
        args.target.parent.mkdir(parents=True, exist_ok=True)
        with ZipFile(args.target, "w", ZIP_DEFLATED) as out:
            for entry in archive.infolist():
                out.writestr(copy(entry), serialized if entry.filename == "word/document.xml" else archive.read(entry.filename))
        with ZipFile(args.target) as written:
            unchanged_parts = all(written.read(name) == archive.read(name) for name in archive.namelist() if name != "word/document.xml")
            if not unchanged_parts:
                raise ValueError("Non-document ZIP parts were changed")
    rows = candidate.find(q("body")).findall(q("tbl"))
    result_tables = [t for t in rows if text(t).startswith("IDEvidencia observadaEstado y alcance pendiente")]
    if len(result_tables) != 1 or len(result_tables[0].findall(q("tr"))) != 22:
        raise ValueError("Expected 21 result rows plus header")
    expected_ids = [row["id"] for row in data["protocol"]["metrics"]]
    table_ids = [text(tr.find(q("tc"))) for tr in result_tables[0].findall(q("tr"))[1:]]
    if table_ids != expected_ids:
        raise ValueError("Result table identifiers changed")
    if sha(args.source) != source_hash_at_start:
        raise ValueError("Author Word changed while generating the candidate")
    checks = {
        "schema": "thesis-academy-docx-checks/1.0", "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": str(args.source), "source_sha256": source_hash_at_start, "candidate": str(args.target),
        "candidate_sha256": sha(args.target), "original_word_overwritten": False,
        "chapters_1_to_3_xml_preserved": True, "protected_body_elements": boundary,
        "protected_body_sha256": hashlib.sha256(b"".join(protected)).hexdigest(),
        "all_other_zip_parts_preserved": unchanged_parts, "result_ids": table_ids,
        "replaced_paragraphs": changed, "source_evidence": data["source_records"],
        "structural_summary_included": data["structural"] is not None,
        "additional_cloud_summaries": data["additional_cloud_summaries"],
        "failed_cloud_cases": data["failed_cloud_cases"],
        "final_workflow_summary_included": data["workflow"] is not None,
        "final_workflow_counts": None if data["workflow"] is None else data["workflow"]["counts"],
        "expert_workbook_current_snapshot": data["expert"],
        "primary_citation_added": any(added_citations.values()),
        "primary_citations_added": added_citations,
        "surface_profile_included": {"cases": 108, "residue_observations": data["sasa_residue_total"], "incomplete_charged_sidechains": 29, "incomplete_charged_structures": data["sasa_incomplete_charged_cases"], "any_heavy_missing_structures": data["sasa_missing_heavy_cases"], "physical_classifier": None},
        "model_pilot_included": {"cases": len(data["model_pilot"]["cases"]), "usage": data["model_pilot"]["usage_totals"], "api_equivalent_usd": data["model_pilot"]["published_standard_api_equivalent_usd"], "actual_bill_available": False},
        "clean_cancellation_included": {"native_job": data["cancel_clean_terminal"]["nativeJob"], "before": "RUNNING", "after": data["cancel_clean_terminal"]["nativeAfter"], "code": data["cancel_clean_terminal"]["nativeExitCode"], "automatic_package": data["cancel_clean_terminal"]["automaticFinalization"]},
        "mapped_reference_included": {"units": data["mapped_terminal"]["mapping"]["mappedUnits"], "residues": data["mapped_terminal"]["mapping"]["mappedResidues"], "native_jobs": data["mapped_terminal"]["nativeTasks"]["native_ids"], "portable_files": data["mapped_terminal"]["portable"]["files"], "numerical_equal": data["mapped_terminal"]["numerical"]["equal"], "global_memory_peak_claimed": False},
        "public_mapping_included": {"chains": data["public_mapping"]["selectedChains"], "label_positions": data["public_mapping"]["labelPositions"], "label_mapped": data["public_mapping"]["labelMapped"], "sifts_parser_chains": data["public_mapping"]["siftsParserMappedChains"], "prepared_chains": data["public_mapping"]["preparedMappedChains"], "prepared_residues": data["public_mapping"]["preparedMappedResidues"], "expected_rejected_chains": data["public_mapping"]["preparedRejectedChains"], "unobserved_sifts_residues": data["public_mapping"]["unobservedSiftsAccessionRows"], "insertion_cases_observed": data["public_mapping"]["sourceInsertionRows"], "biological_validation": False, "verification": data["public_mapping_verification"]},
        "default_regression_included": data["regression"],
        "r24_empirical_rate_included": True,
        "r24_head_workspace_scope": {"original_cases": 40, "attempts": 42, "feasible": 26, "infeasible": 14, "false_rejections": 6, "false_rejection_rate": 6/26, "accuracy": 34/40, "separate_posthoc_extension": 6, "aggregate_client_and_remote": False, "scientific_metric": None},
        "negative_events_included": {"cases": 4, "eligible": 13, "matched": 13, "actor": "synthetic permission/UI callbacks", "human_labels": 0},
        "citation_sources": ["https://pmc.ncbi.nlm.nih.gov/articles/PMC5734394/", "https://pubmed.ncbi.nlm.nih.gov/29067766/", "https://github.com/cctbx/cctbx_project/blob/master/mmtbx/programs/clashscore2.py", "https://f1000research.com/articles/5-189/v1", "https://freesasa.github.io/doxygen/CLI.html"],
        "writing_review": {"pass_1": "Numbers checked against saved evidence; current identifiers, null scientific metrics and independent-label dependencies retained.",
                           "pass_2": "Current-state prose condensed; historical failures and bounded claims preserved; no invented figure or whole-thesis completion."},
    }
    args.checks.parent.mkdir(parents=True, exist_ok=True)
    args.checks.write_text(json.dumps(checks, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"candidate": str(args.target), "protected_xml_preserved": True, "result_rows": len(table_ids),
                      "changed_paragraphs": len(changed), "structural_summary_included": checks["structural_summary_included"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
