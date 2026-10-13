#!/usr/bin/env python3
"""Recompute model usage and audit frozen development tool actions offline."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "evaluation/trp/campaign-20261012/model-pilot"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    freeze = json.loads((BASE / "freeze.json").read_text())
    rows = []
    for case in freeze["cases"]:
        target = BASE / case["id"]
        result = json.loads((target / "result.json").read_text())
        if sha(target / "stdout.jsonl") != result["stdout_sha256"] or sha(target / "stderr.log") != result["stderr_sha256"]:
            raise ValueError("Captured model output changed: " + case["id"])
        events = [json.loads(line) for line in (target / "stdout.jsonl").read_text().splitlines() if line.strip().startswith("{")]
        steps = [event["part"] for event in events if event.get("type") == "step_finish"]
        calls = [event["part"] for event in events if event.get("type") == "tool_use"]
        usage = {key: sum(part.get("tokens", {}).get(key, 0) for part in steps) for key in ("input", "output", "reasoning", "total")}
        usage.update(cache_read=sum(part.get("tokens", {}).get("cache", {}).get("read", 0) for part in steps),
                     cache_write=sum(part.get("tokens", {}).get("cache", {}).get("write", 0) for part in steps))
        if usage["total"] != sum(value for key, value in usage.items() if key != "total"):
            raise ValueError("Token totals do not reproduce the recorded components")
        # Helix subtracts cache tokens from input and reasoning from output;
        # pricing therefore includes each component exactly once.
        equivalent = (2*usage["input"] + .2*usage["cache_read"] + 2.5*usage["cache_write"] + 10*(usage["output"]+usage["reasoning"]))/1_000_000
        prepared = [call for call in calls if call["tool"] == "trp_prepare"]
        checks = {"process_completed": result["exit_code"] == 0 and not result["timed_out"],
                  "configured_step_cap_observed": len(steps) <= freeze["maximum_steps_per_case"],
                  "output_token_cap_observed": all(part["tokens"]["output"] + part["tokens"]["reasoning"] <= freeze["maximum_output_tokens_per_step"] for part in steps),
                  "only_authorized_preparation_tools": all(call["tool"] in ("trp_catalog", "trp_prepare") for call in calls),
                  "no_scientific_run_tool_called": not any(call["tool"] == "trp_run" for call in calls),
                  "tools_completed": all(call["state"]["status"] == "completed" for call in calls)}
        digest = None
        if case["id"] in ("D-MODEL-001", "D-MODEL-002"):
            checks["one_preparation_call"] = len(prepared) == 1
            checks["complete_supplied_arguments_preserved"] = len(prepared) == 1 and prepared[0]["state"]["input"] == freeze["expected_arguments"]
            if prepared and prepared[0]["state"]["status"] == "completed":
                output = json.loads(prepared[0]["state"]["output"])
                checks["actual_resource_admission"] = output["admission"]["accepted"] is True
                checks["actual_graph_validation"] = output["validation"]["valid"] is True
                digest = output["digest"]
        else:
            checks["no_preparation_with_missing_or_unsupported_inputs"] = len(prepared) == 0
        rows.append({"id": case["id"], "checks": checks, "verified": all(checks.values()),
                     "usage": usage, "published_standard_api_equivalent_usd": equivalent,
                     "actual_charge_usd": None, "preparation_digest": digest,
                     "elapsed_seconds": result["elapsed_seconds"],
                     "source_output_sha256": sha(target / "stdout.jsonl"),
                     "text": result["text"], "semantic_correctness_independently_annotated": False})
    totals = {key: sum(row["usage"][key] for row in rows) for key in rows[0]["usage"]}
    report = {"schema": "helix-development-model-pilot-audit/1.0", "audited_at_utc": datetime.now(timezone.utc).isoformat(),
              "freeze_sha256": sha(BASE / "freeze.json"), "verified": all(row["verified"] for row in rows),
              "cases": rows, "usage_totals": totals,
              "published_standard_api_equivalent_usd": sum(row["published_standard_api_equivalent_usd"] for row in rows),
              "pricing_source": freeze["pricing_source"], "actual_api_billing_available": False,
              "requested_model": freeze["requested_model"], "configured_reasoning_effort": freeze["reasoning_effort"],
              "effective_provider_revision": None, "reserved_scientific_metrics": None,
              "scope": "Two supplied-argument preparations and two scope/missing-data development probes. Automatic action audit; no independent language score or scientific task execution.",
              "usage_accounting_note": "Raw driver API-equivalent estimates omitted cache reads; this audit recomputes all components directly from captured output. Neither estimate establishes a real OAuth/API bill."}
    output = BASE / "audit.json"
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False)+"\n")
    print(json.dumps({"verified": report["verified"], "usage": totals, "published_api_equivalent_usd": report["published_standard_api_equivalent_usd"]}))
    return 0 if report["verified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
