#!/usr/bin/env python3
"""Hash the complete preserved campaign without embedding its raw bytes."""
import argparse, hashlib, json
from pathlib import Path

HERE = Path(__file__).resolve().parent
MANIFEST = HERE / "analysis-manifest.json"
ANCHOR = HERE / "analysis-manifest.sha256"
EXCLUDED = {MANIFEST.name, ANCHOR.name, "manifest-verification.json"}

def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def files():
    return [p for p in sorted(HERE.rglob("*")) if p.is_file() and not p.is_symlink()
            and "__pycache__" not in p.parts and p.suffix != ".pyc"
            and str(p.relative_to(HERE)) not in EXCLUDED]

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--verify", action="store_true")
    args = p.parse_args()
    if args.verify:
        expected = ANCHOR.read_text().split()[0]
        if sha(MANIFEST) != expected:
            raise ValueError("External manifest SHA changed")
        manifest = json.loads(MANIFEST.read_text())
        for name, record in manifest["files"].items():
            path = HERE / name
            if not path.is_file() or path.stat().st_size != record["bytes"] or sha(path) != record["sha256"]:
                raise ValueError("Campaign artifact changed: " + name)
        actual = {str(path.relative_to(HERE)) for path in files()}
        if actual != set(manifest["files"]):
            raise ValueError("Manifest does not cover the actual regular-file set")
        result = {"verified":True,"manifestSha256":expected,"files":len(actual),
                  "bytes":sum(r["bytes"] for r in manifest["files"].values()),
                  "cloudCalls":0,"rawEvidenceMutated":False}
        (HERE / "manifest-verification.json").write_text(json.dumps(result,indent=2)+"\n")
        print(json.dumps(result))
        return
    records = {str(path.relative_to(HERE)):{"bytes":path.stat().st_size,"sha256":sha(path)} for path in files()}
    manifest = {"schema":"helix-preserved-full-client-resource-campaign/1.0",
                "files":records,"regularFileCount":len(records),
                "bytes":sum(r["bytes"] for r in records.values()),
                "summarySha256":sha(HERE / "summary.json"),
                "frozenOriginalAuditorSha256":sha(HERE / "audit_cases.py"),
                "finalColdAuditSha256":sha(HERE / "final-package-verification.json"),
                "producerCommit":"ecfab67","uniqueProteins":1,
                "scientificR24Rate":None,
                "scope":"Preserved raw archives, extracted ordinary files, original and amended interpretations, failures, source snapshots, operational amendments, derived tables and figures. Raw archive symlinks are retained in tar plus symlink-records; Python caches and this manifest's external anchor are excluded."}
    MANIFEST.write_text(json.dumps(manifest,indent=2,allow_nan=False)+"\n")
    ANCHOR.write_text(sha(MANIFEST)+"  analysis-manifest.json\n")
    print(json.dumps({"manifestSha256":sha(MANIFEST),"files":len(records),"bytes":manifest["bytes"]}))

if __name__ == "__main__":
    main()
