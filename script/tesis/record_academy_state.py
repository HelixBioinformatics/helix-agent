#!/usr/bin/env python3
"""Record fresh EC2 lifecycle observations without credentials or private keys."""
import argparse
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lab", choices=("183928", "185395"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--require-stopped", action="store_true")
    args = parser.parse_args()
    spec = importlib.util.spec_from_file_location("academy", ROOT / "script/tesis/aws_academy_cluster.py")
    academy = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(academy)
    academy.configure_lab(args.lab)
    state = academy.refresh(academy.ec2_client(), academy.load())
    report = {
        "schema": "helix-academy-lifecycle-observation/1.0",
        "observed_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": "Fresh EC2 DescribeInstances response, with verified deployment ownership tags",
        "lab": args.lab,
        "region": state["region"],
        "deployment": state["deployment"],
        "nodes": state["nodes"],
        "all_stopped": all(node["state"] == "stopped" for node in state["nodes"]),
        "stopped_compute_does_not_remove_storage": True,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"lab": args.lab, "all_stopped": report["all_stopped"], "nodes": len(report["nodes"])}))
    if args.require_stopped and not report["all_stopped"]:
        raise SystemExit("EC2 has not confirmed that all owned nodes are stopped")


if __name__ == "__main__":
    main()
