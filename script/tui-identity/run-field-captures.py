#!/usr/bin/env python3
"""Capture the revised welcome-only ambient genome field with native OpenTUI."""
import concurrent.futures
import importlib.util
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("helix_capture", HERE / "run-captures.py")
capture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(capture)

BASE = {
    "CAPTURE_SOURCE": "../../packages/tui", "CAPTURE_SCENARIO": "home",
    "CAPTURE_WIDTH": "120", "CAPTURE_HEIGHT": "40", "CAPTURE_THEME": "dark",
    "CAPTURE_ANIMATIONS": "1", "CAPTURE_OPTIONAL_PLUGINS": "0",
}
CASES = {
    "welcome-80": {"CAPTURE_WIDTH": "80", "CAPTURE_HEIGHT": "24", "CAPTURE_MOTION_SECONDS": "1"},
    "welcome-120": {"CAPTURE_MOTION_SECONDS": "1"},
    "welcome-160": {"CAPTURE_WIDTH": "160", "CAPTURE_HEIGHT": "48", "CAPTURE_MOTION_SECONDS": "1"},
    "welcome-60": {"CAPTURE_WIDTH": "60", "CAPTURE_HEIGHT": "20"},
    "welcome-light": {"CAPTURE_THEME": "light", "CAPTURE_MOTION_SECONDS": "1"},
    "rest": {"CAPTURE_MOTION_SECONDS": "4"},
    "motion": {"CAPTURE_FRAME_SERIES": "1"},
    "typing": {"CAPTURE_INPUT": "Inspect paired inputs", "CAPTURE_MOTION_SECONDS": "1"},
    "menu": {"CAPTURE_SCENARIO": "menu", "CAPTURE_HOME_DIALOG": "1", "CAPTURE_MOTION_SECONDS": "1"},
    "off": {"CAPTURE_ANIMATIONS": "0", "CAPTURE_IDLE_PROBE": "1"},
    "256": {"CAPTURE_COLOR": "256", "COLORTERM": "", "CAPTURE_MOTION_SECONDS": "1"},
    "16": {"CAPTURE_COLOR": "16", "COLORTERM": "", "CAPTURE_MOTION_SECONDS": "1"},
    "resize": {"CAPTURE_FROM_WIDTH": "160", "CAPTURE_FROM_HEIGHT": "48", "CAPTURE_WIDTH": "80", "CAPTURE_HEIGHT": "24", "CAPTURE_MOTION_SECONDS": "1"},
    "session": {"CAPTURE_SCENARIO": "session", "CAPTURE_MOTION_SECONDS": "1"},
    "ascii": {"HELIX_ASCII": "1", "CAPTURE_MOTION_SECONDS": "1"},
    "wcwidth": {"CAPTURE_WIDTH_METHOD": "wcwidth", "CAPTURE_MOTION_SECONDS": "1"},
}


def main():
    names = sys.argv[1].split(",") if len(sys.argv) > 1 else list(CASES)
    if any(name not in CASES for name in names):
        raise SystemExit("Choose from " + ",".join(CASES))
    bun, env = capture.prepare_runtime()
    output = capture.WORK / "captures" / "field-revision"
    output.mkdir(parents=True, exist_ok=True)

    def run(name):
        settings = {**BASE, **CASES[name], "CAPTURE_PHASE": "field-revision/" + name}
        code = capture.run_case(bun, env, settings, output / (name + ".log"))
        result = {"case": name, "exit": code, "settings": settings}
        print(json.dumps(result), flush=True)
        return result

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(run, names))
    report = output / "capture-results.json"
    previous = json.loads(report.read_text()) if report.exists() else []
    updated = {item["case"]: item for item in previous}
    updated.update({item["case"]: item for item in results})
    report.write_text(json.dumps(list(updated.values()), indent=2) + "\n")
    raise SystemExit(1 if any(item["exit"] for item in results) else 0)


if __name__ == "__main__":
    main()
