#!/usr/bin/env python3
"""Preserve a compact selection of native captures and verified reports in docs/."""
import hashlib
import json
from pathlib import Path
import shutil

from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[2]
WORK = ROOT / "tmp" / "tui-identity"
DEST = ROOT / "docs" / "design" / "tui-identity"
CAPTURES = WORK / "captures"


def read(path):
    return json.loads(path.read_text())


def copy(source, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def main():
    behavior = read(WORK / "verification" / "behavioral-comparison.json")
    if behavior["cases"] != 30 or not behavior["allPassed"]:
        raise SystemExit("Expected the complete successful 30-case comparison.")
    for name, digest in behavior["sourceHashes"].items():
        if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != digest:
            raise SystemExit("Source changed after verification: " + name)

    counts = {}
    for phase, count in [("before", 52), ("after", 52), ("before-default", 2),
                         ("after-default", 2), ("after-extras", 19)]:
        source = CAPTURES / phase / "capture-results.json"
        results = read(source)
        if len(results) != count or any(item["exit"] for item in results):
            raise SystemExit("Incomplete capture matrix: " + phase)
        counts[phase] = count
        copy(source, DEST / "captures" / phase / source.name)

    selection = []
    for phase in ["before-default", "after-default"]:
        selection += [(phase, f"{scene}-120x40-dark") for scene in ["home", "session"]]
    stems = ["home-80x24-dark", "home-60x20-dark", "session-160x48-dark",
             "session-60x20-dark", "session-120x40-light", "permission-80x24-dark",
             "question-80x24-dark", "menu-120x40-dark", "theme-menu-120x40-light",
             "selector-60x20-dark", "confirm-120x40-light", "prompt-80x24-dark",
             "error-80x24-dark"]
    selection += [(phase, stem) for phase in ["before", "after"] for stem in stems]
    for case in ["ascii-home", "system-session", "limited16", "motion", "quiet-typing",
                 "draft-six-lines", "resize-home", "idle-home", "idle-session",
                 "before-idle-home", "before-idle-session"]:
        directory = CAPTURES / "after-extras" / case
        frames = [p for p in directory.glob("*.json") if not p.name.endswith(".meta.json")]
        if len(frames) != 1:
            raise SystemExit("Expected one native frame for " + case)
        selection.append(("after-extras/" + case, frames[0].stem))
    for phase, stem in selection:
        for suffix in [".txt", ".json", ".meta.json", ".png"]:
            copy(CAPTURES / phase / (stem + suffix), DEST / "captures" / phase / (stem + suffix))

    # Retain thirty-seven native rows in both crops, without scaling or moving cells.
    # Only the after crop skips three rows containing the compact identity header.
    for phase, first_row in [("before-default", 0), ("after-default", 3)]:
        source = DEST / "captures" / phase / "session-120x40-dark.png"
        with Image.open(source) as frame:
            mono = ImageOps.grayscale(frame)
            mono.save(source.with_name(source.stem + "-mono.png"))
            body = mono.crop((0, 16 + first_row * 20, frame.width, 16 + (first_row + 37) * 20))
            body.save(source.with_name(source.stem + "-body-mono.png"))

    for name in ["behavioral-comparison.json", "behavioral-source-audit.json"]:
        copy(WORK / "verification" / name, DEST / "verification" / name)
    for name in ["baseline-provenance.json", "lint-comparison.json", "lint-before.json",
                 "lint-after.json", "typecheck.log", "tui-tests.log", "format.log"]:
        copy(WORK / "checks" / name, DEST / "verification" / name)
    manifest = {
        "baselineRevision": "1de7c76718b19125b3d8598f73c11f25305714b6",
        "captureCounts": counts,
        "selectedFrames": len(selection),
        "interactionComparisons": behavior["cases"],
        "sourceHashes": behavior["sourceHashes"],
        "files": {str(path.relative_to(DEST)): hashlib.sha256(path.read_bytes()).hexdigest()
                  for path in sorted(DEST.rglob("*")) if path.is_file() and path.name != "manifest.json"},
    }
    (DEST / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"selectedFrames": len(selection), "captureCounts": counts,
                      "interactionComparisons": behavior["cases"]}, indent=2))


if __name__ == "__main__":
    main()
