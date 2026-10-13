#!/usr/bin/env python3
"""Remount the existing R24 XFS image and NFS exports after a guest restart.

Never formats, recreates, truncates, or resets quotas. Only operates on the
recorded Academy deployment, after confirming no Helix Slurm jobs are active.
"""
import argparse
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import shlex
import subprocess

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lab", choices=("183928", "185395"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    spec = importlib.util.spec_from_file_location("academy", ROOT / "script/tesis/aws_academy_cluster.py")
    academy = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(academy)
    academy.configure_lab(args.lab)
    state = academy.refresh(academy.ec2_client(), academy.load())
    if any(node["state"] != "running" for node in state["nodes"]):
        raise RuntimeError("All three recorded nodes must be running")
    head = next(node for node in state["nodes"] if node["role"] == "head")
    workers = [node for node in state["nodes"] if node["role"] != "head"]
    args.output.mkdir(parents=True, exist_ok=True)
    report = {
        "schema": "helix-r24-workspace-resume/1.0", "lab": args.lab,
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "format_performed": False, "quotas_reset": False,
        "steps": [],
    }

    def ssh(node, command, timeout=90):
        options = ["StrictHostKeyChecking=yes" if value == "StrictHostKeyChecking=accept-new" else value
                   for value in academy.ssh_options(node)]
        result = subprocess.run(["ssh", *options, "ubuntu@" + node["public_ip"],
                                 "bash -lc " + shlex.quote(command)],
                                capture_output=True, text=True, timeout=timeout)
        report["steps"].append({"node": node["name"], "command": command,
                                "exit_code": result.returncode, "stdout": result.stdout,
                                "stderr": result.stderr})
        (args.output / "resume.json").write_text(json.dumps(report, indent=2) + "\n")
        if result.returncode:
            raise RuntimeError("Resume failed on " + node["name"] + ": " + result.stderr[-1500:])
        return result.stdout

    queue = ssh(head, "squeue --noheader --format='%i|%k'")
    if any("|helix:" in line for line in queue.splitlines()):
        raise RuntimeError("Helix jobs remain active; preserve their original invocation")
    image = "/srv/helix-r24-store/disk.img"
    mount = "/shared/helix-r24"
    command = "\n".join([
        "set -euo pipefail",
        "test -d /shared/helix-r24",
        "sudo test -f " + image,
        "sudo test ! -L " + image,
        "test \"$(sudo stat -c '%U:%G:%a:%s' " + image + ")\" = 'root:root:600:2147483648'",
        "sudo blkid -p -o export " + image,
        "if ! mountpoint -q " + mount + "; then sudo mount -o loop,prjquota,allocsize=4k " + image + " " + mount + "; fi",
        "test \"$(findmnt -n -M " + mount + " -o FSTYPE)\" = xfs",
        "source=\"$(findmnt -n -M " + mount + " -o SOURCE)\"",
        "test \"$(sudo losetup --noheadings --output BACK-FILE \"$source\")\" = " + image,
        "findmnt -n -M " + mount + " -o SOURCE,FSTYPE,OPTIONS",
        "sudo losetup -j " + image,
        "sudo xfs_quota -x -c 'state -p' " + mount,
        *["sudo exportfs -o rw,sync,no_subtree_check,root_squash " + shlex.quote(node["private_ip"] + ":" + mount) for node in workers],
        "sudo exportfs -v",
        "sha256sum " + mount + "/operator-witness/*.txt",
    ])
    head_output = ssh(head, command)
    if "TYPE=xfs" not in head_output or "prjquota" not in head_output:
        raise RuntimeError("Existing XFS type and project-quota mount were not observed")
    for node in workers:
        command = "\n".join([
            "set -euo pipefail", "test -d " + mount,
            "if ! mountpoint -q " + mount + "; then sudo mount -t nfs4 " +
            shlex.quote(head["private_ip"] + ":" + mount) + " " + mount + "; fi",
            "test \"$(findmnt -n -M " + mount + " -o FSTYPE)\" = nfs4",
            "test \"$(findmnt -n -M " + mount + " -o SOURCE)\" = " + shlex.quote(head["private_ip"] + ":" + mount),
            "findmnt -n -M " + mount + " -o SOURCE,FSTYPE,OPTIONS",
            "sha256sum " + mount + "/operator-witness/*.txt",
        ])
        ssh(node, command)
    report.update(ready=True, completed_at_utc=datetime.now(timezone.utc).isoformat())
    (args.output / "resume.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"lab": args.lab, "ready": True, "existing_image_preserved": True}))


if __name__ == "__main__":
    main()
