#!/usr/bin/env python3
"""Provision a fresh, isolated guest XFS/NFS workspace for resource contrasts.

No new EC2 or EBS resources are created. Existing /shared/helix is untouched.
Refuses existing experiment paths and active Helix jobs rather than reformatting
or interrupting them. Credentials and SSH keys remain in operator private state.
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
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.configure_lab(args.lab)
    state = module.refresh(module.ec2_client(), module.load())
    if any(node["state"] != "running" for node in state["nodes"]):
        raise RuntimeError("Every cluster node must be running for verified setup")
    head = next(node for node in state["nodes"] if node["role"] == "head")
    workers = [node for node in state["nodes"] if node["role"] != "head"]
    report = {"schema": "helix-r24-guest-workspace-setup/1.0", "lab": args.lab,
              "started_at_utc": datetime.now(timezone.utc).isoformat(),
              "mount": "/shared/helix-r24", "new_ec2_instances": 0, "new_ebs_volumes": 0,
              "existing_positive_workspace_modified": False, "steps": []}
    args.output.mkdir(parents=True, exist_ok=True)

    def ssh(node, command, timeout=120):
        result = subprocess.run(["ssh", *module.ssh_options(node), "ubuntu@"+node["public_ip"],
                                 "bash -lc "+shlex.quote(command)], capture_output=True, text=True, timeout=timeout)
        report["steps"].append({"node": node["name"], "command": command, "exit_code": result.returncode,
                                 "stdout": result.stdout, "stderr": result.stderr})
        (args.output / "setup.json").write_text(json.dumps(report, indent=2)+"\n")
        if result.returncode:
            raise RuntimeError("Setup failed on "+node["name"]+": "+result.stderr[-1500:])
        return result.stdout

    queue = ssh(head, "squeue --noheader --format='%i|%k'")
    if any("|helix:" in line for line in queue.splitlines()):
        raise RuntimeError("A Helix job is active; preserve it and wait for its authoritative terminal state")
    for node in state["nodes"]:
        ssh(node, "test ! -e /shared/helix-r24 && test ! -e /srv/helix-r24-store")
    free = ssh(head, "df -B1 --output=avail /srv/helix | tail -1")
    if int(free.strip()) < 4*1024**3:
        raise RuntimeError("Insufficient free disk for isolated 2GiB workspace and evidence reserve")
    # All potentially destructive format commands operate only on the new file
    # whose absence was independently checked on all nodes above.
    setup = "\n".join([
        "set -euo pipefail", "sudo apt-get install -y xfsprogs",
        "sudo install -d -m 0755 /srv/helix-r24-store /shared/helix-r24",
        "sudo fallocate -l 2G /srv/helix-r24-store/disk.img",
        "sudo chmod 0600 /srv/helix-r24-store/disk.img",
        "sudo mkfs.xfs -f -q /srv/helix-r24-store/disk.img",
        "sudo mount -o loop,prjquota,allocsize=4k /srv/helix-r24-store/disk.img /shared/helix-r24",
        *["sudo exportfs -o rw,sync,no_subtree_check,root_squash "+shlex.quote(node["private_ip"]+":/shared/helix-r24") for node in workers],
        "sudo xfs_quota -x -c 'state -p' /shared/helix-r24",
        "sudo exportfs -v", "findmnt -n -T /shared/helix-r24 -o FSTYPE,OPTIONS",
        "sudo install -d -o ubuntu -g ubuntu -m 0711 /shared/helix-r24/operator-witness",
        "printf '%s\\n' 'HELIX_R24_SHARED_WITNESS' > /shared/helix-r24/operator-witness/source.txt",
        "sha256sum /shared/helix-r24/operator-witness/source.txt",
    ])
    ssh(head, setup, timeout=240)
    for node in workers:
        setup = "\n".join([
            "set -euo pipefail", "sudo install -d -m 0755 /shared/helix-r24",
            "sudo mount -t nfs4 "+shlex.quote(head["private_ip"]+":/shared/helix-r24")+" /shared/helix-r24",
            "findmnt -n -t nfs4 -T /shared/helix-r24 -o SOURCE,FSTYPE,OPTIONS",
            "sha256sum /shared/helix-r24/operator-witness/source.txt",
            "printf '%s\\n' '"+node["name"]+"' > /shared/helix-r24/operator-witness/"+node["name"]+".txt",
        ])
        ssh(node, setup)
    ssh(head, "sha256sum /shared/helix-r24/operator-witness/*.txt")
    report.update(completed_at_utc=datetime.now(timezone.utc).isoformat(), ready=True)
    (args.output / "setup.json").write_text(json.dumps(report, indent=2)+"\n")
    print(json.dumps({"lab": args.lab, "ready": True, "mount": report["mount"], "nodes": len(state["nodes"])}))


if __name__ == "__main__":
    main()
