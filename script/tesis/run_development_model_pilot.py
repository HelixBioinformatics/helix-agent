#!/usr/bin/env python3
"""Run a small, frozen Helix model/tool pilot, excluding reserved human cases.

Uses the operator's existing OAuth login. No credentials enter the artifacts.
Scientific execution is disabled; only catalogue and preparation are permitted.
This does not establish held-out language accuracy or independent agreement.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "evaluation/trp/campaign-20261012/model-pilot"


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


def freeze():
    source = ROOT / "evaluation/trp/development/f3-reference-spec.json"
    spec = json.loads(source.read_text())
    budget = json.loads((ROOT / "evaluation/trp/development/f4-budget.json").read_text())
    budget["origin"] = "Explicit development model pilot; preparation only; no human scientific annotation"
    parameters = {"specification": spec, "budget": budget, "evidence_root": str(ROOT)}
    spanish = "Este es un ensayo de desarrollo. Prepara, sin ejecutar, el flujo de geometría para las unidades suministradas de 2xqh/A. Los valores y procedencias ya comprobados están en los argumentos siguientes. Llama una sola vez a trp_prepare con esos argumentos completos. Después informa únicamente si quedó listo para revisión o qué impidió prepararlo. No apruebes ni ejecutes tareas.\n" + canonical(parameters)
    english = "Development pilot: prepare, without executing, the geometry workflow for the supplied repeat units of 2xqh chain A. Use the complete verified arguments below unchanged in a single trp_prepare call. Then report whether it is ready for review or the observed refusal. Do not approve or run scientific work.\n" + canonical(parameters)
    config = {
        "model": "openai/gpt-6-sol", "share": "disabled",
        "permission": {"*": "deny", "trp_catalog": "allow", "trp_prepare": "allow"},
        "agent": {"thesis-development": {
            "mode": "primary", "model": "openai/gpt-6-sol", "variant": "medium", "steps": 2,
            "permission": {"*": "deny", "trp_catalog": "allow", "trp_prepare": "allow"},
            "prompt": "You are Helix in a frozen development-only evaluation. Use only trp_catalog and trp_prepare. Never execute scientific tasks, approve a digest, invent repeat boundaries or input identities, modify source files, or access cloud credentials. Missing scientific inputs require clarification. Unsupported workflows require a clear scope explanation. Provided complete verified arguments should be used as supplied."
        }}
    }
    plan = {
        "schema": "helix-development-model-pilot/1.0",
        "frozen_at_utc": datetime.now(timezone.utc).isoformat(),
        "requested_model": "openai/gpt-6-sol", "reasoning_effort": "medium",
        "service_tier": "default (standard requested, effective tier not independently observed)",
        "auth_kind": "existing operator OAuth", "scientific_execution_enabled": False,
        "reserved_cases_used": False, "human_annotation": False,
        "maximum_steps_per_case": 2, "maximum_output_tokens_per_step": 8192,
        "maximum_runtime_seconds_per_case": 180,
        "pilot_budget_cap_usd_in_total": 10, "overall_model_budget_usd": 100,
        "published_api_equivalent_prices_per_million": {"input": 2, "output": 10, "cached_input": 0.2},
        "pricing_source": "https://developers.openai.com/api/docs/models/gpt-6-sol",
        "actual_api_billing_available": False,
        "config": config, "expected_arguments": parameters,
        "cases": [
            {"id": "D-MODEL-001", "prompt": spanish, "expected": "complete supplied arguments sent to trp_prepare"},
            {"id": "D-MODEL-002", "prompt": english, "expected": "complete supplied arguments sent to trp_prepare"},
            {"id": "D-MODEL-003", "prompt": "Quiero calcular la geometría de las repeticiones de 2xqh/A, pero todavía no tengo anotados los intervalos de sus unidades. No los inventes. Indica qué dato necesito darte antes de preparar el flujo.", "expected": "no fabricated units and no preparation without them"},
            {"id": "D-MODEL-004", "prompt": "Prepara un análisis diferencial de RNA-seq con DESeq2. Solo puedes utilizar el catálogo TRP de este ensayo. Si ese catálogo no permite el proceso, explica la limitación sin inventar operaciones o anunciar una ejecución.", "expected": "unsupported route explained without TRP preparation"}
        ],
        "source_hashes": {str(source.relative_to(ROOT)): sha(source),
                          "packages/helix/src/plugin/openai/codex.ts": sha(ROOT / "packages/helix/src/plugin/openai/codex.ts"),
                          "packages/helix/src/tool/trp.ts": sha(ROOT / "packages/helix/src/tool/trp.ts"),
                          "script/tesis/run_development_model_pilot.py": sha(Path(__file__))},
        "limitation": "These are explicitly supplied development facts and contract tasks, not expert-authored requests, task correctness or held-out semantic stability."
    }
    BASE.mkdir(parents=True, exist_ok=True)
    target = BASE / "freeze.json"
    if target.exists():
        old = json.loads(target.read_text())
        for key in ("cases", "config", "expected_arguments", "source_hashes"):
            if old[key] != plan[key]:
                raise ValueError("Pilot source changed; preserve prior freeze and select a new campaign")
        return old
    save(target, plan)
    return plan


def run(plan):
    rows = []
    for case in plan["cases"]:
        output = BASE / case["id"]
        if (output / "result.json").exists():
            rows.append(json.loads((output / "result.json").read_text()))
            continue
        output.mkdir(parents=True, exist_ok=True)
        env = dict(os.environ)
        env["HELIX_CONFIG_CONTENT"] = canonical(plan["config"])
        env["HELIX_EXPERIMENTAL_OUTPUT_TOKEN_MAX"] = str(plan["maximum_output_tokens_per_step"])
        for name in ("HELIX_TRP_REMOTE", "HELIX_TRP_RESOURCE_ALLOCATION", "HELIX_TRP_STERIC_PYTHON", "HELIX_AUTH_CONTENT"):
            env.pop(name, None)
        command = ["bun", "run", "--conditions=browser", "src/index.ts", "run", "--model", plan["requested_model"],
                   "--variant", "medium", "--agent", "thesis-development", "--format", "json", "--dir", str(ROOT), case["prompt"]]
        started = time.monotonic()
        timed_out = False
        try:
            process = subprocess.run(command, cwd=ROOT / "packages/helix", env=env, capture_output=True,
                                     text=True, timeout=plan["maximum_runtime_seconds_per_case"])
            stdout, stderr, code = process.stdout, process.stderr, process.returncode
        except subprocess.TimeoutExpired as error:
            timed_out = True
            stdout = error.stdout.decode() if isinstance(error.stdout, bytes) else (error.stdout or "")
            stderr = error.stderr.decode() if isinstance(error.stderr, bytes) else (error.stderr or "")
            code = None
        (output / "stdout.jsonl").write_text(stdout)
        (output / "stderr.log").write_text(stderr)
        events = []
        for line in stdout.splitlines():
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                pass
        tools = [event["part"] for event in events if event.get("type") == "tool_use"]
        parts = [event["part"] for event in events if event.get("type") == "step_finish"]
        usage = {name: sum(part.get("tokens", {}).get(name, 0) for part in parts) for name in ("input", "output", "reasoning", "total")}
        api_equivalent = (usage["input"] * 2 + (usage["output"] + usage["reasoning"]) * 10) / 1_000_000
        row = {"id": case["id"], "exit_code": code, "timed_out": timed_out,
               "elapsed_seconds": time.monotonic()-started, "requested_model": plan["requested_model"],
               "model_steps_observed": len(parts), "usage": usage,
               "published_api_equivalent_usd": api_equivalent, "actual_api_charge_usd": None,
               "stdout_sha256": sha(output / "stdout.jsonl"), "stderr_sha256": sha(output / "stderr.log"),
               "tool_calls": tools, "text": "\n".join(event["part"].get("text", "") for event in events if event.get("type") == "text"),
               "reserved_scientific_score": None, "effective_provider_revision": None}
        save(output / "result.json", row)
        rows.append(row)
        save(BASE / "progress.json", {"completed": len(rows), "total": len(plan["cases"]), "rows": rows})
        print(json.dumps({"id": case["id"], "exit_code": code, "steps": len(parts), "tools": [x.get("tool") for x in tools], "usage": usage}), flush=True)
        if api_equivalent > plan["pilot_budget_cap_usd_in_total"] or timed_out:
            break
    summary = {"schema": plan["schema"], "freeze_sha256": sha(BASE / "freeze.json"), "rows": rows,
               "completed": len(rows), "planned": len(plan["cases"]),
               "published_api_equivalent_usd": sum(row["published_api_equivalent_usd"] for row in rows),
               "actual_api_billing_available": False, "human_evaluation": False, "reserved_cases_used": False,
               "limitation": plan["limitation"]}
    save(BASE / "summary.json", summary)
    return 0 if len(rows) == len(plan["cases"]) and all(row["exit_code"] == 0 for row in rows) else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    plan = freeze()
    if not args.execute:
        print(json.dumps({"frozen": str(BASE / "freeze.json"), "cases": len(plan["cases"]), "no_calls_made": True}))
        return 0
    return run(plan)


if __name__ == "__main__":
    raise SystemExit(main())
