#!/usr/bin/env python3
"""Offline action oracle. Expectations are frozen before producer observation.

Reads actual callback observations, run ledger or preparation refusal records.
It never connects to AWS, submits science, invokes a model or changes a package.
"""
import argparse
import collections
import datetime
import hashlib
import json
from pathlib import Path
import subprocess


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def load(path):
    return json.loads(Path(path).read_text())


def check_case(directory, expected, freeze_hash, trusted_verifier):
    case = load(directory / "case.json")
    actions = load(directory / "actions.json")
    if not case["actionOracleBeforeProducerRead"] or case["sourceFreezeSha256"] != freeze_hash:
        raise ValueError("Action observation or freeze not bound")
    if not case["terminalFailed"] or case["forbiddenExternalLaunchAttempts"] != 0:
        raise ValueError("Negative gate failed to stop before process dispatch")
    for index, action in enumerate(actions):
        if action["order"] != index:
            raise ValueError("Independent action order changed")
        datetime.datetime.fromisoformat(action["at"].replace("Z", "+00:00"))
    permission = [x for x in actions if x["source"] == "permission"]
    approval = [x for x in actions if x["source"] == "approval"]
    guards = [x for x in actions if x["source"] == "protocol" and x["outcome"] == "guard-returned"]
    if len(permission) != expected["expectedPermissionActions"]:
        raise ValueError("Independent permission callback count differs")
    if len(approval) != expected["expectedApprovalActions"]:
        raise ValueError("Independent Question.Service count differs")
    if len(guards) != expected["expectedProtocolGuards"]:
        raise ValueError("Actual protocol guard count differs")
    observed = [x for x in actions if x["source"] == "inventory" and x["outcome"] == "observed"]
    if len(observed) != 1 or observed[0]["detail"]["host"] == "synthetic-test-host":
        raise ValueError("Real fresh local host inventory absent")
    eligible = collections.Counter()
    coverage = collections.Counter()
    files = [directory / "case.json", directory / "actions.json"]
    cold = None
    if case["runDirectory"]:
        run = directory / case["runDirectory"]
        events_path = run / "events.jsonl"
        events = [json.loads(x) for x in events_path.read_text().splitlines()]
        if [{"source": x["source"], "outcome": x["outcome"]} for x in events] != expected["expectedEvents"]:
            raise ValueError("Exact prospective event types/count/order differs")
        for index, event in enumerate(events):
            prev = hashlib.sha256(canonical(events[index - 1]).encode()).hexdigest() if index else None
            if event["sequence"] != index or event["previous"] != prev:
                raise ValueError("Producer ledger chain differs")
        # Independent callbacks are observed separately from the producer ledger.
        callback_projection = [
            (x["source"], {"denied": "denied-or-error", "allowed": "returned-allowed",
                              "question-asked": "requested", "question-replied": "answered"}.get(x["outcome"], x["outcome"]))
            for x in actions if x["source"] in {"permission", "approval"}
        ]
        ledger_projection = [(x["source"], x["outcome"]) for x in events if x["source"] in {"permission", "approval"}]
        if callback_projection != ledger_projection:
            raise ValueError("Observed permission/UI actions and producer records differ")
        if any("detail" not in x for x in events):
            raise ValueError("Decision cause/detail absent")
        if events[-1]["outcome"] != "failed-or-rejected" or not events[-1]["detail"].get("error"):
            raise ValueError("Automatic terminal/cause absent")
        admission = load(run / "admission.json")
        if admission["accepted"] != expected["expectedAdmissionDecision"]:
            raise ValueError("Initial admission decision differs")
        for event in expected["expectedEvents"]:
            if event["source"] in {"admission", "protocol", "permission", "approval"}:
                eligible[event["source"]] += 1
                coverage[event["source"]] += 1
        anchor = load(run / "evidence-location.json")
        process = subprocess.run(["python3", str(trusted_verifier), str(run / "evidence"),
                                  "--sha256", anchor["manifestSha256"]], capture_output=True, text=True, timeout=60)
        if process.returncode:
            raise ValueError("Cold automatic failure bundle rejected: " + process.stderr[:200])
        cold = json.loads(process.stdout)
        files.extend([events_path, run / "run.json", run / "admission.json", run / "protocol.json", run / "evidence-location.json"])
    else:
        rejected = list((directory / "producer" / "trp").glob("rejected-*.json"))
        if len(rejected) != 1:
            raise ValueError("Preparation refusal record absent/ambiguous")
        record = load(rejected[0])
        target = expected["expectedPreparationRecord"]
        admission = record["admission"]
        if admission["accepted"] != target["admissionAccepted"]:
            raise ValueError("Preparation admission decision differs")
        datetime.datetime.fromisoformat(admission["decidedAt"].replace("Z", "+00:00"))
        eligible["admission"] += 1
        coverage["admission"] += 1
        if expected["id"] == "admission-rejected":
            if not any(all(r.get(k) == target[k] for k in ["code", "resource", "demand", "available"]) for r in admission["rejections"]):
                raise ValueError("Actual typed budget rejection/cause differs")
        else:
            protocol = record["protocol"]
            refusal = protocol["ledger"]["refusals"]
            if not protocol["check"]["refused"] or len(refusal) != 1:
                raise ValueError("Committed protocol refusal omitted")
            if target["constraintId"] not in refusal[0]["constraintIds"] or not refusal[0]["constraintTexts"]:
                raise ValueError("Protocol refusal cause/reference omitted")
            if not guards[0]["detail"]["result"]["refused"]:
                raise ValueError("Independent actual guard result differs")
            datetime.datetime.fromisoformat(refusal[0]["at"].replace("Z", "+00:00"))
            eligible["protocol"] += 1
            coverage["protocol"] += 1
        files.append(rejected[0])
    return {"id": expected["id"], "verified": True,
            "independently_observed_permission_actions": len(permission),
            "independently_observed_question_actions": len(approval),
            "independently_observed_protocol_guards": len(guards),
            "eligible_records_by_source": dict(eligible), "matched_records_by_source": dict(coverage),
            "record_route": "run.events.jsonl" if case["runDirectory"] else "preparation.rejected.json/protocol.refusals",
            "automatic_failure_bundle_cold_verification": cold,
            "records": [{"path": str(p), "sha256": sha(p)} for p in files]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[4]
    plan = load(args.protocol)
    verifier = root / "packages/helix/src/trp/verify_bundle.py.txt"
    records = [check_case(args.cases / x["id"], x, sha(args.protocol), verifier) for x in plan["cases"]]
    totals = collections.Counter()
    for row in records:
        totals.update(row["eligible_records_by_source"])
    result = {"schema": "helix-negative-independent-action-audit/1.0",
              "auditedAtUtc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "verified": True, "cases": records, "unique_gate_cases": len(records),
              "eligible_records_by_source": dict(totals), "matched_records_by_source": dict(totals),
              "source_coverage": {k: {"matched": v, "eligible": v, "proportion": 1.0} for k, v in totals.items()},
              "protocolSha256": sha(args.protocol), "verifierSha256": sha(verifier), "auditorSha256": sha(__file__),
              "scope": "Four deterministic local engineering refusal sessions; real production service/host observer and Question.Service, synthetic permission/UI actor. Exact prospective action count/type/order and causes checked independently. Preparation refusals are explicit records, not fabricated run ledger events.",
              "human_labels": 0, "model_calls": 0, "aws_operations": 0, "kappa": None,
              "reserved_scientific_metrics": None}
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"verified": True, "cases": len(records), "eligibleBySource": dict(totals), "output": str(args.output)}))


if __name__ == "__main__":
    main()
