#!/usr/bin/env python3
"""Preserve the welcome-field revision without replacing the initial captures."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[2]
WORK = ROOT / "tmp" / "tui-identity"
SOURCE = WORK / "captures" / "field-revision"
DEST = ROOT / "docs" / "design" / "tui-identity" / "field-revision"


def copy(source, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def main():
    results = json.loads((SOURCE / "capture-results.json").read_text())
    comparison = json.loads((WORK / "verification" / "behavioral-comparison.json").read_text())
    if len(results) != 16 or any(item["exit"] for item in results):
        raise SystemExit("Expected sixteen successful field capture cases.")
    if comparison["cases"] != 30 or not comparison["allPassed"]:
        raise SystemExit("Expected thirty successful interaction comparisons.")
    for path, digest in comparison["sourceHashes"].items():
        if hashlib.sha256((ROOT / path).read_bytes()).hexdigest() != digest:
            raise SystemExit("Source changed after comparison: " + path)
    changed = subprocess.check_output(["git", "diff", "--name-only"], cwd=ROOT, text=True).splitlines()
    protected = [path for path in changed if path.startswith(("packages/core/", "packages/sdk/", "packages/helix/",
                 "docs/tesis/", "script/tesis/", "evaluation/")) or path.endswith(("package.json", "bun.lock"))]
    if protected:
        raise SystemExit("Protected changes require separate review: " + str(protected))
    subprocess.run(["git", "diff", "--check"], cwd=ROOT, check=True)
    for item in results:
        directory = SOURCE / item["case"]
        for file in directory.iterdir():
            if file.suffix in [".txt", ".json", ".png", ".gif"]:
                copy(file, DEST / item["case"] / file.name)
        copy(SOURCE / (item["case"] + ".log"), DEST / (item["case"] + ".log"))
    copy(SOURCE / "capture-results.json", DEST / "capture-results.json")
    for name in ["field-tui-tests.log", "field-typecheck.log", "field-format.log", "field-lint.json",
                 "field-lint-comparison.json"]:
        copy(WORK / "checks" / name, DEST / "checks" / name)
    for name in ["behavioral-comparison.json", "behavioral-source-audit.json"]:
        copy(WORK / "verification" / name, DEST / "checks" / name)
    manifest = {
        "scope": "Welcome-only ambient genome field revision; initial captures are preserved separately.",
        "nativeCaptureCases": len(results), "interactionComparisons": comparison["cases"],
        "allPassed": True, "sourceHashes": comparison["sourceHashes"], "protectedPathsModified": protected,
        "files": {str(file.relative_to(DEST)): hashlib.sha256(file.read_bytes()).hexdigest()
                  for file in sorted(DEST.rglob("*")) if file.is_file() and file.name != "manifest.json"},
    }
    (DEST / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"nativeCaptureCases": len(results), "interactionComparisons": comparison["cases"],
                      "preservedFiles": len(manifest["files"]), "protectedPathsModified": protected}, indent=2))


if __name__ == "__main__":
    main()
