#!/usr/bin/env python3
"""Independent bounded Nextflow oracle, one prospectively frozen case on head.

Requires an already provisioned, new XFS project-quota mount exported at the
same absolute path on both workers. This never changes NFS, the existing
positive campaign, Helix production or cloud instances. Run as root only after
the operator has verified the mount and the production decision is archived.
Supervisor observations live outside the quota; the complete staged/run/log/
portable-copy footprint lives inside the quota. This is a head-workspace
development contrast, not a total remote plus actual local-client budget claim.
"""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import pwd
import re
import shutil
import subprocess
import time


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
    temporary.replace(path)


def command(argv, **kwargs):
    return subprocess.run(argv, text=True, capture_output=True, **kwargs)


def quota(mount, project):
    value = command(["xfs_quota", "-x", "-c", "report -p -b -n", str(mount)], check=True).stdout
    found = re.search(rf"^#{project}\s+(\d+)\s+(\d+)\s+(\d+)\s", value, re.M)
    if not found:
        raise RuntimeError("Project quota observation missing")
    state = command(["xfs_quota", "-x", "-c", "state -p", str(mount)], check=True).stdout
    if "Accounting: ON" not in state or "Enforcement: ON" not in state:
        raise RuntimeError("Project quota is not enforced")
    return {"usedBytes": int(found[1])*1024, "hardBytes": int(found[3])*1024, "raw": value, "state": state}


def owned_jobs(comment):
    ids = command(["squeue", "--noheader", "--format=%i|%k"], check=True).stdout.splitlines()
    return [row.split("|", 1)[0] for row in ids if "|" in row and row.split("|", 1)[1] == comment]


def cancel(comment):
    ids = owned_jobs(comment)
    if ids:
        command(["scancel", *ids], check=True)
    deadline = time.monotonic()+15
    while owned_jobs(comment) and time.monotonic() < deadline:
        time.sleep(.25)
    return {"requested": ids, "remaining": owned_jobs(comment)}


def controller(package, item, workspace):
    """Executed unprivileged inside the independently verified service cap."""
    os.chdir(workspace)
    os.environ.update(NXF_OFFLINE="true", NXF_DISABLE_CHECK_LATEST="true")
    args = ["nextflow", "-C", "nextflow.config", "run", "main.nf", "-ansi-log", "false", "-with-trace", "trace.tsv"]
    dry = workspace / "dry-run"
    dry.mkdir(mode=0o711)
    for name in item["files"]:
        shutil.copyfile(workspace/name, dry/name)
        (dry/name).chmod(0o600)
    for directory, argv in [(dry, args+["-stub-run"]), (workspace, args)]:
        with (directory/"oracle.stdout").open("wb") as out, (directory/"oracle.stderr").open("wb") as err:
            subprocess.run(argv, cwd=directory, stdout=out, stderr=err, check=True, timeout=480)
    actual = workspace / "results/geometry.csv"
    if digest(actual) != item["goldCsvSha256"] or actual.read_bytes() != (package/item["goldCsvPath"]).read_bytes():
        raise RuntimeError("Same-input numerical comparator differs")
    # Materialize links as the portable exporter does. Keep this duplicate
    # inside the same project; never compare logical bytes with quota blocks.
    portable = workspace / "portable-run"
    portable.mkdir(mode=0o711)
    for file in list(workspace.rglob("*")):
        relative = file.relative_to(workspace)
        if relative.parts[0] == "portable-run" or not file.is_file():
            continue
        target = portable/relative
        target.parent.mkdir(parents=True, exist_ok=True, mode=0o711)
        shutil.copyfile(file, target, follow_symlinks=True)
    write(workspace/"oracle-success.json", {"csvSha256": digest(actual), "numericalEqual": True})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", required=True, type=Path)
    parser.add_argument("--case", required=True)
    parser.add_argument("--mount", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--decision", type=Path)
    parser.add_argument("--user", default="ubuntu")
    parser.add_argument("--controller-workspace", type=Path)
    args = parser.parse_args()
    package = args.package.resolve()
    plan = json.loads((package/"freeze.json").read_text())
    own_source = "evaluation/trp/campaign-20261012/trace/run_r24_extension.py"
    if digest(Path(__file__).resolve()) != plan["sources"][own_source]:
        raise ValueError("Independent runner changed after source freeze")
    item = next(row for row in plan["cases"] if row["id"] == args.case)
    for name, expected in item["files"].items():
        if digest(package/item["inputDirectory"]/name) != expected:
            raise ValueError("Frozen input changed: " + name)
    if digest(package/item["goldCsvPath"]) != item["goldCsvSha256"]:
        raise ValueError("Frozen comparator changed")
    if args.controller_workspace is not None:
        controller(package, item, args.controller_workspace.resolve())
        return
    if os.geteuid() != 0 or not all([args.mount, args.output, args.decision]):
        parser.error("Root supervisor requires --mount, --output and archived --decision")
    output = args.output.resolve()
    if output.exists():
        raise ValueError("Preserve every attempt; output must be a new directory")
    output.mkdir(parents=True)
    decision = json.loads(args.decision.read_text())
    if decision["case"] != item["id"] or decision["planSha256"] != digest(package/"freeze.json"):
        raise ValueError("Admission decision belongs to another frozen case")
    mount = args.mount.resolve()
    state = command(["findmnt", "-n", "-T", str(mount), "-o", "FSTYPE,OPTIONS"], check=True).stdout
    if "xfs" not in state or "prjquota" not in state:
        raise ValueError("An independently provisioned XFS project-quota mount is required")
    deadline_utc = datetime.fromisoformat(plan["globalDeadlineUtc"].replace("Z", "+00:00"))
    remaining = (deadline_utc-datetime.now(timezone.utc)).total_seconds()
    if remaining < 90:
        raise ValueError("Global cancellation checkpoint too close; do not start")
    account = pwd.getpwnam(args.user)
    project = plan["operationalAmendment"]["projectIdBase"]+plan["executionOrder"].index(item["id"])
    workspace = mount/plan["operationalAmendment"]["workspaceNamespace"]/item["id"]
    workspace.parent.mkdir(mode=0o711, exist_ok=True)
    if workspace.exists():
        raise ValueError("Existing case workspace must not be reused")
    workspace.mkdir(mode=0o711)
    os.chown(workspace, account.pw_uid, account.pw_gid)
    command(["xfs_quota", "-x", "-c", f"project -s -p {workspace} {project}", str(mount)], check=True)
    command(["xfs_quota", "-x", "-c", f"limit -p bhard={item['budget']['workBytes']//1024}k {project}", str(mount)], check=True)
    unit = plan["operationalAmendment"]["unitPrefix"]+item["id"].lower()
    started = time.monotonic()
    samples = []
    result = {"case": item["id"], "graphId": item["graphId"], "planSha256": digest(package/"freeze.json"),
              "helixDecision": decision, "budget": item["budget"], "physicalFeasibilityLabel": None,
              "scope": plan["scope"], "storageUnit": plan["storageUnit"], "scientificR24Complete": False}
    process = None
    try:
        before = quota(mount, project)
        if before["hardBytes"] != item["budget"]["workBytes"]:
            raise ValueError("Kernel quota differs from approved scenario budget")
        for name in item["files"]:
            target = workspace/name
            target.write_bytes((package/item["inputDirectory"]/name).read_bytes())
            target.chmod(0o600)
            os.chown(target, account.pw_uid, account.pw_gid)
        seconds = min(item["budget"]["wallSeconds"], int(remaining)-20)
        argv = ["systemd-run", "--unit="+unit, "--uid="+args.user, "--gid="+args.user, "--wait",
                "--property=CPUQuota=100%", "--property=MemoryMax=2G", "--property=MemorySwapMax=0",
                "--property=RuntimeMaxSec="+str(seconds), "--property=KillMode=control-group",
                "--property=WorkingDirectory="+str(workspace),
                "--property=StandardOutput=file:"+str(workspace/"controller.stdout"),
                "--property=StandardError=file:"+str(workspace/"controller.stderr"),
                "python3", str(Path(__file__).resolve()), "--package", str(package), "--case", item["id"],
                "--controller-workspace", str(workspace)]
        process = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        while process.poll() is None:
            sample = {"elapsedSeconds": time.monotonic()-started, "quota": quota(mount, project)}
            group = command(["systemctl", "show", unit, "--property=ControlGroup", "--value"]).stdout.strip()
            if group:
                base = Path("/sys/fs/cgroup")/group.lstrip("/")
                sample["controllerCgroup"] = {name: (base/name).read_text().strip() for name in
                    ["cpu.max", "memory.max", "memory.swap.max", "memory.current", "memory.peak"] if (base/name).exists()}
            samples.append(sample)
            if datetime.now(timezone.utc) >= deadline_utc:
                result["globalCheckpointReached"] = True
                command(["systemctl", "stop", unit])
                break
            time.sleep(.25)
        stdout, stderr = process.communicate(timeout=20)
        result.update(controllerExitCode=process.returncode, supervisorStdout=stdout, supervisorStderr=stderr)
        caps = [sample["controllerCgroup"] for sample in samples if sample.get("controllerCgroup")]
        valid_caps = any(c.get("cpu.max") == "100000 100000" and c.get("memory.max") == "2147483648" and c.get("memory.swap.max") == "0" for c in caps)
        result["controllerLimitsObserved"] = valid_caps
        if process.returncode == 0 and (workspace/"oracle-success.json").is_file() and valid_caps:
            traces = []
            native = []
            runtime = []
            for stage in [workspace/"dry-run", workspace]:
                with (stage/"trace.tsv").open() as stream:
                    traces.extend(csv.DictReader(stream, delimiter="\t"))
            for row in traces:
                native.append(command(["scontrol", "show", "job", row["native_id"], "--oneliner"], check=True).stdout)
            for file in (workspace/"work").glob("*/*/.command.out"):
                for line in file.read_text().splitlines():
                    if line.startswith("HELIX_RUNTIME:"):
                        runtime.append(json.loads(line.split(":",1)[1]))
            exact_tasks = len(traces) == 4 and len({r["native_id"] for r in traces}) == 4 and all(r["status"] == "COMPLETED" and r["exit"] == "0" for r in traces)
            exact_native = all("JobState=COMPLETED" in row and "ExitCode=0:0" in row and
                               "Comment="+item["runComment"] in row for row in native)
            exact_runtime = len(runtime) == 2 and all(r["cpuMax"] == "200000 100000" and r["memoryMax"] == "2147483648" and r["swapMax"] == "0" and r["numericalProfile"] == "Haswell" and r["threads"] == "1" for r in runtime)
            result.update(traces=traces,native=native,runtime=runtime)
            if exact_tasks and exact_native and exact_runtime:
                result["physicalFeasibilityLabel"] = True
                result["oracleStatus"] = "exact-output-under-observed-limits"
            else:
                result["oracleStatus"] = "unknown-incomplete-runtime-evidence"
        else:
            errors = "\n".join(file.read_text(errors="replace") for file in workspace.rglob("*")
                               if file.is_file() and (file.name.endswith((".stderr", ".stdout")) or file.name == ".nextflow.log"))
            result["oracleError"] = errors[-12000:]
            if any(s in errors for s in ["Disk quota exceeded", "No space left on device"]):
                result["physicalFeasibilityLabel"] = False
                result["oracleStatus"] = "infeasible-observed-workspace-quota"
            else:
                result["oracleStatus"] = "unknown-other-execution-failure"
    except OSError as error:
        result.update(oracleError=str(error),errno=error.errno)
        if error.errno in (28,122):
            result.update(physicalFeasibilityLabel=False,oracleStatus="infeasible-observed-staging-quota")
        else:
            result["oracleStatus"]="unknown-operator-or-io-failure"
    except Exception as error:
        result.update(oracleStatus="unknown-supervisor-failure",oracleError=str(error))
    finally:
        command(["systemctl", "stop", unit])
        try:
            result["nativeCleanup"] = cancel(item["runComment"])
        except Exception as error:
            result["nativeCleanup"] = {"confirmed": False, "error": str(error)}
        try:
            result["finalQuota"] = quota(mount, project)
        except Exception as error:
            result["quotaObservationError"] = str(error)
        result["elapsedSeconds"] = time.monotonic()-started
        result["samples"] = samples
        write(output/"oracle-result.json", result)
        # Evidence is copied after execution and measurements, outside the
        # project. Copy-back storage is explicitly excluded from the oracle.
        shutil.copytree(workspace, output/"retained-workspace", symlinks=True)
        write(output/"export-ready.json", {"case":item["id"],"oracleResultSha256":digest(output/"oracle-result.json"),"copiedBeforePublication":True})
    print(json.dumps({k: result.get(k) for k in ["case","oracleStatus","physicalFeasibilityLabel","elapsedSeconds"]}))


if __name__ == "__main__":
    main()
