#!/usr/bin/env python3
"""Hash retained resource evidence and its public execution/audit sources."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[4]
HERE=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument("--include",type=Path,action="append",default=[]);p.add_argument("--output",type=Path,required=True);p.add_argument("--verify",action="store_true");a=p.parse_args()
 output=a.output.resolve()
 if a.verify:
  manifest=json.loads(output.read_text());anchor=json.loads(output.with_name(output.name+".anchor.json").read_text())
  if sha(output)!=anchor["manifestSha256"]:raise ValueError("External manifest anchor differs")
  for row in manifest["files"]:
   candidate=ROOT/row["path"]
   file=candidate.resolve()
   if not file.is_relative_to(ROOT) or candidate.is_symlink() or not file.is_file() or file.stat().st_size!=row["bytes"] or sha(file)!=row["sha256"]:
    raise ValueError("Retained source/evidence mismatch: "+row["path"])
  print(json.dumps({"verified":True,"files":len(manifest["files"]),"bytes":sum(r["bytes"]for r in manifest["files"]),"manifestSha256":sha(output)}));return
 if not a.include:p.error("At least one final evidence directory is required")
 paths=set()
 for folder in a.include:
  folder=folder.resolve()
  if not folder.is_dir() or not folder.is_relative_to(ROOT):raise ValueError("Only repository evidence directories may be packaged")
  for file in folder.rglob("*"):
   if file.is_file() and not file.is_symlink() and file.suffix!=".tmp":paths.add(file)
 for file in HERE.iterdir():
  if file.is_file() and file.suffix in {".py",".ts",".md"} and ("r24" in file.name.lower() or file.name.startswith("R24")):paths.add(file)
 for name in ["script/tesis/aws_academy_cluster.py","script/tesis/aws_academy_prepare_remote.py","script/tesis/resume_r24_workspace.py"]:paths.add(ROOT/name)
 for name in ["r24-summary.json","r24-final-quiescence.json"]:
  final=ROOT/"evaluation/trp/campaign-20261012/cloud/lab2"/name
  if final.is_file():paths.add(final)
 paths.discard(output);paths.discard(output.with_name(output.name+".anchor.json"))
 rows=[{"path":str(file.relative_to(ROOT)),"bytes":file.stat().st_size,"sha256":sha(file)}for file in sorted(paths)]
 value={"schema":"helix-r24-retained-evidence-manifest/1.0","createdAtUtc":datetime.now(timezone.utc).isoformat(),
  "scope":"Original and operationally continued head-workspace development resource experiment; separate extension where included. No private AWS credentials and no independent biological labels.",
  "files":rows,"fileCount":len(rows),"bytes":sum(r["bytes"]for r in rows),"packagerSourceSha256":sha(Path(__file__))}
 output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(value,indent=2)+"\n")
 output.with_name(output.name+".anchor.json").write_text(json.dumps({"manifestSha256":sha(output),"createdAtUtc":datetime.now(timezone.utc).isoformat(),"anchorScope":"External sidecar outside every included original run. Integrity is distinct from empirical truth."},indent=2)+"\n")
 print(json.dumps({"manifest":str(output),"files":len(rows),"bytes":value["bytes"],"manifestSha256":sha(output)}))


if __name__=="__main__":main()
