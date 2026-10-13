#!/usr/bin/env python3
"""Read-only review from a separate agent, including prospective causes/UI links."""
import collections, hashlib, json, runpy
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
CAMPAIGN = ROOT / "evaluation/trp/campaign-20261012/event-negative-contrasts"
OUTPUT = Path(__file__).with_name("event-negative-independent-agent-review.json")

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def load(path):
    return json.loads(path.read_text())

def stamp(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))

def main():
    protocol = load(CAMPAIGN / "protocol.json")
    checks = []
    def require(name, condition):
        checks.append({"name":name,"ok":bool(condition)})
        if not condition:
            raise ValueError(name)
    for item in protocol["sources"]:
        require("prospective-source:" + item["path"], sha(CAMPAIGN / "source-snapshot" / item["path"]) == item["sha256"])
    trusted = ROOT / "evaluation/trp/campaign-20261012/aggregate-resource-contrasts/source-snapshots/frozen-original40/packages/helix/src/trp/verify_bundle.py.txt"
    require("archived-trusted-verifier", sha(trusted) == "86aec3f5034483c94fd814bf39df62e237f26ac91ea90d37dd0617872f80a3f5")
    # Reuse the separately written byte/chain checker, then add checks omitted
    # from its generic cause-nonempty test. No totals are copied from audit.json.
    checker = runpy.run_path(str(CAMPAIGN / "audit.py"),run_name="reviewed_action_checker")["check_case"]
    rows, totals = [], collections.Counter()
    for expected in protocol["cases"]:
        folder = CAMPAIGN / "primary" / expected["id"]
        case = load(folder / "case.json")
        actions = load(folder / "actions.json")
        require("expectations-precede-actions:" + expected["id"], all(stamp(a["at"]) >= stamp(protocol["frozenAtUtc"]) for a in actions))
        require("declared-synthetic-scope:" + expected["id"], case["syntheticCallbacks"] and case["modelCalls"] == case["awsOperations"] == case["humanLabels"] == case["scientificTasksLaunched"] == 0)
        require("preparation-stage:" + expected["id"], case["preparationSucceeded"] == bool(case["runDirectory"]))
        if expected.get("causeCode"):
            require("specific-failure-code:" + expected["id"], case["failureCode"] == expected["causeCode"])
        else:
            require("specific-permission-cause:" + expected["id"], expected["causeContains"] in case["cause"])
        if expected["id"] == "approval-rejected":
            asked = [a for a in actions if a["source"] == "approval" and a["outcome"] == "question-asked"]
            replied = [a for a in actions if a["source"] == "approval" and a["outcome"] == "question-replied"]
            require("actual-question-request-response-link", len(asked) == len(replied) == 1 and asked[0]["detail"]["data"]["id"] == replied[0]["detail"]["data"]["requestID"])
            require("actual-ui-rejection-value", replied[0]["detail"]["data"]["answers"] == [["Rechazar"]])
            run = folder / case["runDirectory"]
            ledger = [json.loads(line) for line in (run / "events.jsonl").read_text().splitlines()]
            answered = [e for e in ledger if e["source"] == "approval" and e["outcome"] == "answered"]
            require("ledger-ui-answer-equality", len(answered) == 1 and answered[0]["detail"]["channel"] == "Question.Service" and answered[0]["detail"]["answers"] == replied[0]["detail"]["data"]["answers"])
        row = checker(folder,expected,sha(CAMPAIGN / "protocol.json"),trusted)
        totals.update(row["eligible_records_by_source"])
        rows.append(row)
    require("exact-observed-record-denominators", dict(totals) == {"admission":4,"protocol":3,"permission":4,"approval":2})
    report = {"schema":"helix-independent-agent-negative-events-review/1.0","verified":True,
              "reviewerAgent":"/root/evaluation_audit","at":datetime.now(timezone.utc).isoformat(),
              "cases":rows,"recordCounts":dict(totals),"checks":checks,
              "protocolSha256":sha(CAMPAIGN / "protocol.json"),"reviewSourceSha256":sha(Path(__file__)),
              "trustedArchivedVerifierSha256":sha(trusted),"sourceCasesMutated":False,
              "cloudCalls":0,"humanLabels":0,"kappa":None,
              "independence":"Reviewed by a different agent from the harness author. Frozen expectations precede all recorded actions; callbacks are observed separately from the producer ledger. The permission and approval actors remain synthetic and the process-launch service is deliberately forbidden, so zero launch attempts demonstrates the gating route only.",
              "limitations":["Four development gate cases, not population-wide event coverage.",
                              "Action observations are interleaved with producer events, not all earlier than ledger creation.",
                              "Approval callback instrumentation is not an independent human annotation or agreement metric.",
                              "Reruns after harness-only errors remain separate attempts of four unique cases.",
                              "Cold failed-bundle verification establishes recorded integrity, not biological correctness."]}
    OUTPUT.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({"verified":True,"cases":len(rows),"records":sum(totals.values()),"checks":len(checks),"output":str(OUTPUT)}))

if __name__ == "__main__":
    main()
