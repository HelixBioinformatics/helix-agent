#!/usr/bin/env python3
"""Run deterministic TUI behavior fixtures against frozen and active sources.

Only mocked HTTP/events are used. State and generated evidence stay in tmp/.
"""
import argparse
import concurrent.futures
import io
import json
import os
import pathlib
import shutil
import subprocess
import tarfile
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
WORK = ROOT / "tmp" / "tui-identity"
HERE = pathlib.Path(__file__).resolve().parent
FLOWS = [
    "permission-once", "permission-always", "permission-reject", "permission-mouse",
    "question-select", "question-custom", "question-reject", "dialog-select",
    "dialog-mouse", "dialog-prompt", "prompt-unicode", "prompt-paste",
    "prompt-ime-flush", "copy-selection", "interrupt",
]


def bun_path():
    found = shutil.which("bun")
    fallback = pathlib.Path.home() / ".bun" / "bin" / "bun"
    if found:
        return found
    if fallback.is_file():
        return str(fallback)
    raise SystemExit("Bun is required; use the repository's installed dependencies.")


def prepare_baseline(revision, baseline):
    if baseline.exists():
        raise SystemExit("Baseline already exists; it will not be replaced: " + str(baseline))
    baseline.parent.mkdir(parents=True, exist_ok=True)
    commit = subprocess.check_output(["git", "rev-parse", revision], cwd=ROOT, text=True).strip()
    archive = subprocess.check_output([
        "git", "archive", "--format=tar", commit,
        "packages/tui/src", "packages/tui/test", "packages/tui/package.json", "packages/tui/tsconfig.json",
        "packages/tui/bunfig.toml", "packages/tui/sst-env.d.ts",
    ], cwd=ROOT)
    with tempfile.TemporaryDirectory(prefix="baseline-", dir=WORK) as staging:
        staging = pathlib.Path(staging)
        with tarfile.open(fileobj=io.BytesIO(archive)) as source:
            for member in source.getmembers():
                target = (staging / member.name).resolve()
                if staging.resolve() not in target.parents or member.issym() or member.islnk():
                    raise SystemExit("Unexpected path/link in git archive: " + member.name)
            source.extractall(staging)
        shutil.move(str(staging / "packages" / "tui"), baseline)
    (baseline.parent / "source-revision.txt").write_text(commit + "\n")
    print("Prepared commit-only baseline:", baseline)
    print("This does not reproduce any uncommitted changes in the original frozen worktree.")


def ensure_dependency_link(path):
    target = ROOT / "packages" / "tui" / "node_modules"
    if not target.is_dir():
        raise SystemExit("Missing packages/tui/node_modules; install the repository dependencies first.")
    if path.exists():
        return
    if path.is_symlink():
        raise SystemExit("Broken dependency link must be repaired explicitly: " + str(path))
    path.symlink_to(target, target_is_directory=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=["before", "after", "both"], default="both")
    parser.add_argument("--flows", default=",".join(FLOWS), help="Comma-separated fixture flows")
    parser.add_argument("--sizes", default="120x40,60x20")
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--baseline", default="tmp/tui-identity/baseline/source")
    parser.add_argument("--prepare-baseline", metavar="REVISION", help="Create a missing commit-only baseline and exit")
    parser.add_argument("--audit-only", action="store_true")
    parser.add_argument("--report-only", action="store_true")
    parser.add_argument("--skip-report", action="store_true", help="Keep the existing comparison report during a smoke run")
    args = parser.parse_args()
    baseline = (ROOT / args.baseline).resolve()
    WORK.mkdir(parents=True, exist_ok=True)
    if args.prepare_baseline:
        prepare_baseline(args.prepare_baseline, baseline)
        return
    if not (baseline / "src").is_dir():
        raise SystemExit("Missing baseline; see docs/design/tui-identity-verification.md")
    bun = bun_path()
    ensure_dependency_link(WORK / "node_modules")
    ensure_dependency_link(baseline / "node_modules")
    shutil.copy2(HERE / "verification.test.tsx", WORK / "verification.test.tsx")
    flows = args.flows.split(",")
    if not flows or any(flow not in FLOWS for flow in flows):
        raise SystemExit("Unknown flow; choose from " + ",".join(FLOWS))
    try:
        sizes = [tuple(map(int, size.split("x"))) for size in args.sizes.split(",")]
        if any(len(size) != 2 or min(size) < 1 for size in sizes):
            raise ValueError()
    except ValueError:
        raise SystemExit("Sizes must look like 120x40,60x20")
    if args.workers < 1:
        raise SystemExit("workers must be positive")
    env = os.environ.copy()
    env.update(VERIFY_FLOWS=",".join(flows), VERIFY_SIZES=args.sizes)
    for kind in ["data", "cache", "config", "state"]:
        path = WORK / "environment" / kind
        path.mkdir(parents=True, exist_ok=True)
        env["XDG_" + kind.upper() + "_HOME"] = str(path)
    if not args.audit_only and not args.report_only:
        phases = ["before", "after"] if args.phase == "both" else [args.phase]
        jobs = [(phase, flow, width, height) for phase in phases for flow in flows for width, height in sizes]

        def run(job):
            phase, flow, width, height = job
            job_env = env.copy()
            job_env.update(VERIFY_SOURCE=str(baseline if phase == "before" else ROOT / "packages" / "tui"),
                           VERIFY_PHASE=phase, VERIFY_FLOW=flow, VERIFY_WIDTH=str(width), VERIFY_HEIGHT=str(height))
            output = WORK / "verification" / phase
            output.mkdir(parents=True, exist_ok=True)
            command = [bun, "--conditions=browser", "test", str(WORK / "verification.test.tsx"),
                       "--preload", "@opentui/solid/preload", "--timeout", "65000"]
            try:
                process = subprocess.run(command, cwd=ROOT / "packages" / "tui", env=job_env,
                                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=90)
                code, log = process.returncode, process.stdout
            except subprocess.TimeoutExpired as error:
                code, log = 124, str(error)
            result = dict(phase=phase, flow=flow, width=width, height=height, exit=code, log=log)
            (output / f"{flow}-{width}x{height}-run.json").write_text(json.dumps(result, indent=2))
            print(json.dumps({key: value for key, value in result.items() if key != "log"}), flush=True)
            return result

        with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
            results = list(pool.map(run, jobs))
        for phase in phases:
            report = WORK / "verification" / phase / "run-results.json"
            previous = json.loads(report.read_text()) if report.exists() else []
            updated = {(item["flow"], item["width"], item["height"]): item for item in previous}
            updated.update({(item["flow"], item["width"], item["height"]): item
                            for item in results if item["phase"] == phase})
            report.write_text(json.dumps(list(updated.values()), indent=2))
        if any(result["exit"] for result in results):
            raise SystemExit("A fixture failed; inspect tmp/tui-identity/verification/<phase>/*-run.json")
    audit_env = env.copy()
    audit_env["VERIFY_SOURCE"] = str(baseline)
    subprocess.run([bun, str(HERE / "verification-diff.tsx")], cwd=ROOT, env=audit_env, check=True)
    if not args.skip_report and not args.audit_only:
        subprocess.run([bun, str(HERE / "verification-compare.tsx")], cwd=ROOT, env=audit_env, check=True)


if __name__ == "__main__":
    main()
