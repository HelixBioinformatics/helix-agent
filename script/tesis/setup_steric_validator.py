#!/usr/bin/env python3
"""Install the pinned optional steric validator and verify public chemistry data.

No original author model is downloaded or redistributed by this helper.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "evaluation/trp/campaign-20261012/structural"


def install(state):
    state.mkdir(parents=True, exist_ok=True, mode=0o700)
    venv = state / "venv"
    python = venv / "bin/python"
    env = dict(os.environ, UV_NO_PROGRESS="1")
    if not python.exists():
        subprocess.run(["uv", "venv", "--python", "3.12", str(venv)], check=True, env=env)
    packages = json.loads((EVIDENCE / "freeze.json").read_text())["packages"]
    subprocess.run(["uv", "pip", "install", "--python", str(python), *[name + "==" + version for name, version in packages.items()]], check=True, env=env)
    for name, manifest in (("geostd", "geostd-library-complete.json"), ("chemical_components", "chemical-components.json")):
        target = state / name
        records = json.loads((EVIDENCE / manifest).read_text())["files"]
        for record in records:
            relative = Path(record["path"])
            if relative.is_absolute() or ".." in relative.parts:
                raise ValueError("unsafe chemistry resource path")
            path = target / relative
            if path.exists():
                data = path.read_bytes()
            else:
                with urllib.request.urlopen(record["url"], timeout=60) as response:
                    data = response.read(10_000_001)
                if len(data) > 10_000_000:
                    raise ValueError("chemistry resource exceeds limit")
                if len(data) != record["bytes"] or hashlib.sha256(data).hexdigest() != record["sha256"]:
                    raise ValueError("public chemistry source changed: " + record["path"])
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
            if len(data) != record["bytes"] or hashlib.sha256(data).hexdigest() != record["sha256"]:
                raise ValueError("installed chemistry resource changed: " + record["path"])
        link = venv / name
        if os.path.lexists(link):
            if not link.is_symlink() or link.resolve() != target.resolve():
                raise ValueError("existing CCTBX resource path differs: " + str(link))
        else:
            link.symlink_to(target.resolve(), target_is_directory=True)
    print(json.dumps({"ok": True, "operatorSetting": "HELIX_TRP_STERIC_PYTHON", "python": str(python), "resources": "official pinned geostd and wwPDB CCD", "scope": "steric observable, no fold classifier"}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", type=Path, default=Path.home() / ".local/state/helix/structural-20261012")
    args = parser.parse_args()
    install(args.state)
