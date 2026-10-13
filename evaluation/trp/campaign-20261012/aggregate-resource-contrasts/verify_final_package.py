#!/usr/bin/env python3
"""Verify raw bytes and reproduce selected audits against frozen sources.

Does not run Helix, rewrite any case interpretation, modify a database, or
contact AWS. The historical trusted verifier comes from the externally hashed
source archive, so later production repairs do not replace the campaign code.
"""
import hashlib, json, runpy, sqlite3, statistics
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
SNAPSHOT = HERE / "source-snapshots/frozen-original40"

def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def load(path):
    return json.loads(path.read_text())

def main():
    summary = load(HERE / "summary.json")
    checks = []
    def require(name, ok, detail=None):
        checks.append({"name":name,"ok":bool(ok),"detail":detail})
        if not ok:
            raise ValueError(name + ": " + str(detail))
    sources = load(HERE / "campaign-inputs/freeze.json")["sourceHashes"]
    for path, digest in sources.items():
        require("frozen-source:" + path, sha(SNAPSHOT / path) == digest)
    require("original-auditor-restored", sha(HERE / "audit_cases.py") == sources[str((HERE / "audit_cases.py").relative_to(ROOT))])
    expected_unknowns = {"AGG-08-small", "AGG-18-small", "AGG-13-generous", "AGG-14-generous"}
    observed_unknowns = set()
    rows = []
    for group, inputs_name, outcomes_name in [
        ("original", "campaign-inputs", "campaign-outcomes"),
        ("boundary", "boundary-inputs", "boundary-outcomes"),
        ("extension", "extension-inputs", "extension-outcomes")]:
        inputs, outcomes = HERE / inputs_name, HERE / outcomes_name
        freeze = load(inputs / "freeze.json")
        require("freeze-anchor:" + group, sha(inputs / "freeze.json") == summary[group]["freezeSha256"])
        require("all-terminal:" + group, load(outcomes / "terminal.json")["allFrozenCasesObserved"])
        for path, digest in freeze["sourceHashes"].items():
            source = SNAPSHOT / path
            if not source.exists():
                source = ROOT / path
            require("prospective-source:" + group + ":" + path, sha(source) == digest)
        group_rows = {r["case"]:r for r in summary[group]["rows"]}
        for item in freeze["cases"]:
            case, local = item["id"], outcomes / item["id"]
            require("unlabeled-before-output:" + case, item["physicalFeasibilityLabel"] is None and item["helixDecision"] is None)
            require("case-equals-freeze:" + case, load(inputs / (case + ".json")) == item)
            graph = inputs / item["graphId"]
            require("source-input:" + case, sha(graph / "source.pdb") == item["sourceInputSha256"])
            require("own-input-gold:" + case, sha(graph / "geometry.csv") == item["goldCsvSha256"])
            planning_bundle = load(graph / "unbound-bundle.json")
            for name, digest in item["unboundFileHashes"].items():
                require("planning-bundle:" + case + ":" + name, hashlib.sha256(planning_bundle["files"][name].encode()).hexdigest() == digest)
            r = group_rows[case]
            for path_key, digest_key in [
                ("auditPath", "auditSha256"), ("firstAuditPath", "firstAuditSha256"),
                ("resolutionReviewPath", "resolutionReviewSha256"),
                ("fdReviewPath", "fdReviewSha256")]:
                if path_key in r:
                    require("interpretation-anchor:" + case + ":" + path_key, sha(ROOT / r[path_key]) == r[digest_key])
            selected = load(ROOT / r["auditPath"])
            first = load(ROOT / r["firstAuditPath"])
            if r.get("selectedInterpretation") == "fatal-descriptor-review":
                auditor = HERE / "audit_cases_fd.py"
                require("review-source:" + case, sha(auditor) == selected["reviewSourceSha256"])
                require("review-lineage:" + case, selected["frozenAuditSha256"] == r["firstAuditSha256"])
                require("review-amendment:" + case, sha(HERE / "auditor-fd-amendment.json") == selected["amendmentSha256"])
            elif r.get("selectedInterpretation") == "causal-resolution-review":
                auditor = HERE / "audit_cases_resolution.py"
                require("review-source:" + case, sha(auditor) == selected["reviewSourceSha256"])
            else:
                auditor = HERE / "audit_cases.py"
            # Only the frozen ROOT lookup is rebound. This is an offline source
            # resolver, not a runtime admission or physical-limit override.
            namespace = runpy.run_path(str(auditor), run_name="historical_audit")
            namespace["audit"].__globals__["ROOT"] = SNAPSHOT
            reproduced = namespace["audit"](local, item)
            extras = {"frozenAuditSha256", "reviewSourceSha256", "amendmentSha256"}
            require("selected-audit-reproduced:" + case, reproduced == {k:v for k,v in selected.items() if k not in extras})
            require("summary-label:" + case, r["physicalFeasibilityLabel"] is selected["physicalFeasibilityLabel"])
            require("summary-decision:" + case, r["actualDecision"] == selected["actualDecision"])
            recovery = load(local / "recovery.json")
            require("archive-anchor:" + case, sha(local / "actual-allocation-and-supervisor.tar") == recovery["archiveSha256"] == selected["retainedArchiveSha256"])
            require("dispatch-anchor:" + case, sha(local / "dispatch-intent.json") == r["dispatchIntentSha256"])
            require("recovery-anchor:" + case, sha(local / "recovery.json") == r["recoverySha256"])
            if selected["physicalFeasibilityLabel"] is None:
                observed_unknowns.add(case)
            if selected["physicalFeasibilityLabel"] is True:
                guest = Path(load(local / "dispatch-intent.json")["guest"]).name
                db = local / "recovered" / guest / "retained-allocation/state/data/helix/helix-local.db"
                before = sha(db)
                with sqlite3.connect(db.resolve().as_uri() + "?mode=ro&immutable=1", uri=True) as connection:
                    healthy = connection.execute("PRAGMA quick_check").fetchall() == [("ok",)]
                    projects = connection.execute("SELECT COUNT(*) FROM project").fetchone()[0]
                require("actual-sqlite-cold:" + case, healthy and projects >= 1 and sha(db) == before)
            rows.append({"case":case,"group":group,"label":selected["physicalFeasibilityLabel"],
                         "firstLabel":first["physicalFeasibilityLabel"],"accepted":selected["actualDecision"]["accepted"],
                         "selectedAuditSha256":r["auditSha256"],"firstAuditSha256":r["firstAuditSha256"],
                         "reproducedWithFrozenSource":True})
            print(json.dumps({"case":case,"verified":True}),flush=True)
    require("unknown-identifiers-preserved", observed_unknowns == expected_unknowns)
    require("one-dispatch-each", len(rows) == 50 and len({r["case"] for r in rows}) == 50)
    require("science-unestimated", summary["scientificR24Rate"] is None and summary["uniqueProteins"] == 1)
    require("final-quiescence", load(HERE / "final-quiescence.json")["readyForParentSourceChangesAndLifecycle"])
    report = {"schema":"helix-aggregate-final-cold-reproduction/1.0","verified":True,
              "at":datetime.now(timezone.utc).isoformat(),"cases":rows,"checks":checks,
              "checksPassed":len(checks),"summarySha256":sha(HERE / "summary.json"),
              "observerSha256":sha(Path(__file__)),"quiescenceSha256":sha(HERE / "final-quiescence.json"),
              "sourceArchive":"source-snapshots/frozen-original40",
              "scientificR24Rate":None,"cloudCalls":0,"caseFilesMutated":False,
              "scope":"All fifty raw archives and selected interpretations rechecked offline; selected physical audits rerun with the exact frozen producer/resources/verifier source, preserving every original interpretation."}
    (HERE / "final-package-verification.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({"verified":True,"cases":len(rows),"checks":len(checks)}),flush=True)

if __name__ == "__main__":
    main()
