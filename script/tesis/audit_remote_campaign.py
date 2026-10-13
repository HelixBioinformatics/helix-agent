#!/usr/bin/env python3
"""Independently audit actual Helix SSH/Slurm evidence without cloud access.

The trusted repository verifier is loaded, never the executable bundled with
the evidence. Native scheduler records, effective runtime observations,
approval/transfer bindings, method claims and optional case-specific numerical
references are checked independently. No model, network or SSH is used.
"""
import argparse
from collections import Counter
import csv
from datetime import datetime
import hashlib
import io
import json
import math
from pathlib import Path
import re
import runpy
import subprocess

ROOT = Path(__file__).resolve().parents[2]
TRUSTED = ROOT / "packages/helix/src/trp/verify_bundle.py.txt"
BACKEND = "trp-slurm-ssh/1.0.0"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def js_json(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def record(directory, name):
    # Parse through the trusted duplicate-key/non-finite-number rejection code.
    parser = runpy.run_path(str(TRUSTED), run_name="trusted_parser")["parse"]
    return parser((directory / name).read_bytes())


def records(directory, name):
    parser = runpy.run_path(str(TRUSTED), run_name="trusted_parser")["parse"]
    return [parser(line) for line in (directory / name).read_bytes().splitlines() if line.strip()]


def native_fields(text):
    return dict(re.findall(r"(\w+)=([^\s]+)", text))


def timestamp(value):
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("Timestamp lacks timezone")
    return result


def check_methods(run):
    methods = record(run, "methods.json")
    by_name = {}
    for item in methods["fields"]:
        if item["name"] in by_name:
            raise ValueError("Duplicate methods field: " + item["name"])
        by_name[item["name"]] = item
        artifact = item["artifact"]
        if not re.fullmatch(r"[a-zA-Z0-9_.-]+", artifact):
            raise ValueError("Methods pointer leaves run root")
        value = record(run, artifact)
        for key in item["pointer"]:
            value = value[key]
        if value != item["value"]:
            raise ValueError("Unbacked methods field: " + item["name"])
    required = {"protein", "chain", "model", "units", "insertions", "coordinate contract",
                "GeomeTRe revision", "parameter contract", "input hash", "engine", "image",
                "command", "counts", "storage estimate", "status", "execution backend",
                "remote infrastructure", "numerical profile"}
    if not required <= by_name.keys():
        raise ValueError("Required remote method claims missing: " + repr(sorted(required - by_name.keys())))
    if by_name["execution backend"]["value"] != BACKEND:
        raise ValueError("Methods do not declare actual remote backend")
    software = record(run, "software.json") if (run / "software.json").is_file() else None
    if software is not None and "Nextflow version output" not in by_name:
        raise ValueError("Observed software version omitted from methods")
    spec, execution = record(run, "specification.json"), record(run, "execution.json")
    catalogue, admission = record(run, "catalogue.json"), record(run, "admission.json")
    geometre = next(entry for entry in catalogue["entries"] if entry["id"] == "geometre.geometry")
    status = record(run, "run.json")["status"]
    expected = [
        "# Métodos de la ejecución registrada", "",
        f"Se procesó {spec['structure']['value']['pdb']}, cadena autora {spec['chain']['value']}, modelo {spec['model']['value']}, con {len(spec['units']['value']['ranges'])} unidades suministradas. La entrada se identifica mediante SHA-256 {spec['structure']['value']['sha256']}.", "",
        f"El adaptador {execution['engine']} generó la orden {js_json(execution['run'])} y fijó la imagen {execution['container']}. La revisión de GeomeTRe es {geometre['source']['revision']}; su contrato de parámetros es {js_json(geometre['parameters'])}. Se planificaron dos tareas simuladas y dos reales, sin reintentos; tareas científicas en infraestructura remota: {admission['demand']['counts']['remoteScientificCalls']}. Estado registrado: {status}.", "",
        f"Salida observada de la consulta de versión de Nextflow: {js_json(software['nextflowVersionOutput'])}." if software else "No se dispone de una consulta de versión de Nextflow completada correctamente.", "",
        f"La reserva estimada de almacenamiento fue {admission['demand']['workBytes']} bytes. Los campos y sus fuentes se encuentran en methods.json; el inventario, el presupuesto, las decisiones y los eventos se conservan en archivos separados.", "",
        *["- " + item for item in methods["limitations"]], "",
    ]
    if (run / "methods.md").read_text() != "\n".join(expected):
        raise ValueError("Methods markdown differs from deterministic source-backed template")
    required_limitations = [
        "Author-PDB numbering; supplied units, not repeat detection; experimental B-factor is not pLDDT.",
        "The first-unit geometry zeros are placeholders. Remote Slurm execution is recorded for this run; external annotation and held-out scientific evaluation remain separate requirements.",
        "Slurm requests resources per job; container observations record effective CPU, memory and swap limits. Controller resources and aggregate storage use estimates and admission, without a hard controller limit or disk quota. Memory is not pooled between workers.",
        "Offline verification checks bytes and declared links, not scientific truth or an authenticated human identity.",
        "Agent provider/model/cost are not observed by this workflow; task software is identified by the pinned catalogue reference and image.",
    ]
    if methods["limitations"] != required_limitations:
        raise ValueError("Remote limitations differ from the declared deterministic template")
    expected_unavailable = [] if software else ["Nextflow version probe did not complete successfully; see run.json and process records"]
    if methods.get("unavailable") != expected_unavailable:
        raise ValueError("Unknown software availability not explicitly reported")
    return {"fields_checked": len(by_name), "required_fields": len(required),
            "markdown_reproduced_from_sources": True,
            "unavailable_fields": methods.get("unavailable", [])}


def check_events(run, success, oracle=None):
    data = records(run, "events.jsonl")
    sources = [(e["source"], e["outcome"]) for e in data]
    digest = record(run, "run.json")["digest"]
    for i, event in enumerate(data):
        if event["sequence"] != i or event["previous"] != (sha(canonical(data[i-1]).encode()) if i else None):
            raise ValueError("Event chain not contiguous")
        timestamp(event["at"])
        if isinstance(event.get("detail"), dict) and "digest" in event["detail"] and event["detail"]["digest"] != digest:
            raise ValueError("Event references a different approved bundle")
    required = []
    if success:
        protocol = record(run, "protocol.json")
        required = [("admission", "accepted-for-review"),
                    ("protocol", "checked" if protocol["check"]["committed"] else "not-committed"),
                    ("permission", "requested"), ("permission", "returned-allowed"),
                    ("approval", "requested"), ("approval", "answered"),
                    ("admission", "recheck-accepted"), ("execution", "remote-started"),
                    ("admission", "analysis-accepted"), ("execution", "completed")]
        missing = [pair for pair in required if pair not in sources]
        if missing:
            raise ValueError("Independent successful-path event oracle missing: " + repr(missing))
        indices = [sources.index(pair) for pair in required]
        if indices != sorted(indices) or len(set(indices)) != len(indices):
            raise ValueError("Approval/admission/execution gate order differs")
    elif ("execution", "failed-or-rejected") not in sources:
        raise ValueError("Failed path omitted failure event")
    oracle_count = None
    if oracle is not None:
        independent = json.loads(oracle.read_text())
        expected = independent["expected"]
        counted = Counter(sources)
        for item in expected:
            if counted[(item["source"], item["outcome"])] != item.get("count", 1):
                raise ValueError("External action oracle/event count mismatch")
        oracle_count = sum(item.get("count", 1) for item in expected)
    return {"recorded_events": len(data), "source_counts": dict(Counter(e["source"] for e in data)),
            "independent_success_path_gate_events": len(required),
            "external_action_oracle_expected_events": oracle_count,
            "limitation": "Mandatory path coverage only unless an independent action oracle is supplied; not full-session human coverage or protocol-violation sensitivity."}


def check_bindings(bundle, run):
    manifest = record(bundle, "manifest.json")
    execution, budget = record(run, "execution.json"), record(run, "budget.json")
    target = record(run, "remote_target.json")
    if execution.get("backend") != BACKEND or target != execution["target"]:
        raise ValueError("Remote target/backend binding differs")
    if target.get("hostKeyVerification") != "strict" or target.get("credentialBytes") != "excluded":
        raise ValueError("SSH trust/secrets exclusion absent")
    if any(key in target for key in ("identityFile", "knownHostsFile", "password", "privateKey")):
        raise ValueError("Secret/operator private paths exported in target")
    approved = record(run, "remote-approved.json")
    if (approved["digest"] != manifest["bundle"]["digest"] or approved["target"] != target
            or approved["budget"] != budget or approved["files"] != manifest["bundle"]["files"]):
        raise ValueError("Remote-approved snapshot differs from human-reviewed bundle")
    approval = record(run, "approval.json")
    if approval["digest"] != approved["digest"] or approval["channel"] != "Question.Service" or approval["answer"] != "Aprobar y ejecutar":
        raise ValueError("Scientific approval is absent or bound to another proposal")
    config = (run / "nextflow.config").read_text()
    for fragment in ("process.executor = 'slurm'", "process.queue = '" + target["partition"] + "'",
                     "--comment=helix:" + approved["id"], "--cpus 2", "--memory=2g", "--memory-swap=2g"):
        if fragment not in config:
            raise ValueError("Approved remote configuration missing " + fragment)
    transferred = record(run, "remote-transfer.json")
    if transferred["digest"] != approved["digest"]:
        raise ValueError("Transfer belongs to another proposal")
    seen = set()
    for item in transferred["files"]:
        name = item["path"]
        if not re.fullmatch(r"[a-zA-Z0-9_.-]+(?:/[a-zA-Z0-9_.-]+)*", name) or any(p in (".", "..") for p in name.split("/")) or name in seen:
            raise ValueError("Transfer path duplicate/unsafe")
        raw = (run / name).read_bytes()
        if len(raw) != item["bytes"] or sha(raw) != item["sha256"]:
            raise ValueError("Transferred bytes differ")
        seen.add(name)
    if not manifest["bundle"]["files"].keys() <= seen:
        raise ValueError("Transferred set omits immutable approved inputs")
    terminal = record(run, "remote-terminal.json")
    if terminal["digest"] != approved["digest"] or terminal["id"] != approved["id"]:
        raise ValueError("Terminal record belongs to another native execution")
    if terminal["status"] == "succeeded":
        admission = record(run, "analysis-admission.json")
        acknowledgement = record(run, "remote-analysis-approval.json")
        if acknowledgement["decision"] != admission["decision"] or not acknowledgement["decision"]["accepted"]:
            raise ValueError("Head did not acknowledge the same accepted pre-scientific admission")
        timestamp(acknowledgement["acceptedAt"])
    return {"run_id": approved["id"], "digest": approved["digest"],
            "bound_files": len(approved["files"]), "transferred_files": len(seen),
            "target_fingerprint": target["fingerprint"], "terminal_status": terminal["status"],
            "approval_actor": "Question.Service answer; actor provenance must be disclosed by the campaign driver."}


def check_native_jobs(run):
    approved, target = record(run, "remote-approved.json"), record(run, "remote_target.json")
    native = {}
    snapshots = records(run, "remote-native-jobs.jsonl")
    for snapshot in snapshots:
        timestamp(snapshot["at"])
        for job in snapshot["records"]:
            raw = native_fields(job["source"])
            if raw.get("JobId") != job["id"] or raw.get("Comment") != "helix:" + approved["id"]:
                raise ValueError("Native scheduler ID/ownership differs")
            if raw.get("JobState") != job["state"] or raw.get("NodeList") != job["nodes"]:
                raise ValueError("Normalized native fields disagree with raw scheduler record")
            if job["state"] == "COMPLETED":
                if raw.get("ExitCode") != "0:0" or raw.get("NumNodes") != "1" or raw.get("NumCPUs") != "2":
                    raise ValueError("Completed Slurm allocation/exit differs from task request")
                native[job["id"]] = job
    tasks, ids = [], set()
    spec = record(run, "specification.json")
    select = next(n["id"].upper() for n in spec["graph"]["nodes"] if n["operation"] == "pdb.select")
    geometry = next(n["id"].upper() for n in spec["graph"]["nodes"] if n["operation"] == "geometre.geometry")
    for traversal, trace in (("scientific", "trace.tsv"), ("stub", "dry-run/trace.tsv")):
        rows = list(csv.DictReader(io.StringIO((run / trace).read_text()), delimiter="\t"))
        if len(rows) != 2:
            raise ValueError("Expected two tasks in each traversal")
        names = set()
        for row in rows:
            identifier, name = row["native_id"], row.get("process", row["name"])
            if not re.fullmatch(r"[0-9]+", identifier) or identifier in ids or identifier not in native:
                raise ValueError("Native task ID absent/reused/non-native")
            if row["status"] != "COMPLETED" or row["exit"] != "0":
                raise ValueError("Task is not completed successfully")
            if name not in (select, geometry):
                raise ValueError("Unexpected process in trace: " + name)
            expected_node = target.get("selectNode" if name == select else "geometryNode")
            node = native[identifier]["nodes"]
            if expected_node is not None and node != expected_node:
                raise ValueError("Native worker placement differs from approved target")
            ids.add(identifier)
            names.add(name)
            tasks.append({"traversal": traversal, "process": name, "native_id": identifier,
                          "node": node, "state": native[identifier]["state"]})
        if names != {select, geometry}:
            raise ValueError("Missing required process in traversal")
    if record(run, "run.json")["measuredTasks"] != {"scientificTasks": 2, "stubTasks": 2}:
        raise ValueError("Reported measured task counts differ")
    return {"tasks": tasks, "native_ids": sorted(ids, key=int),
            "nodes": sorted({task["node"] for task in tasks}), "unique_native_jobs": len(ids)}


def check_runtime(run):
    runtime = record(run, "remote-task-runtime.json")
    observations = runtime["records"]
    if len(observations) != 2:
        raise ValueError("Expected two scientific runtime observations")
    paths = set()
    for row in observations:
        source = row["source"]
        if not re.fullmatch(r"work/[a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+/\.command\.out", source) or source in paths:
            raise ValueError("Runtime source missing/duplicate/unsafe")
        paths.add(source)
        markers = [line.split(":", 1)[1] for line in (run / source).read_text().splitlines() if line.startswith("HELIX_RUNTIME:")]
        expected = {k: v for k, v in row.items() if k != "source"}
        if len(markers) != 1 or json.loads(markers[0]) != expected:
            raise ValueError("Runtime claims not reproduced from captured container output")
        quota, period = map(int, row["cpuMax"].split())
        if period <= 0 or quota / period != 2 or int(row["memoryMax"]) != 2147483648 or int(row["swapMax"]) != 0 or row["threads"] != "1":
            raise ValueError("Effective CPU/memory/swap/thread limit differs")
        if record(run, "execution.json")["numericalProfile"] == "haswell-single-thread":
            if row["numericalProfile"] != "Haswell" or not any(x.get("architecture") == "Haswell" and x.get("num_threads") == 1 for x in row["blas"]):
                raise ValueError("Observed numerical profile differs")
    return {"observations": len(observations), "cpus_per_task": 2, "memory_bytes_per_task": 2147483648,
            "swap_bytes_per_task": 0, "cpu_quota_is_exclusive_cores": False,
            "hard_controller_limit_verified": False, "hard_aggregate_disk_quota_verified": False}


def check_numerical(run, reference):
    spec = record(run, "specification.json")
    raw = (run / "results/geometry.csv").read_bytes()
    rows = list(csv.DictReader(io.StringIO(raw.decode())))
    units = spec["units"]["value"]["ranges"]
    expected_header = ["pdb_id", "chain", "unit_start", "unit_end", "curvature", "twist", "twist_hand", "pitch", "pitch_hand", "tmscore", "yaw"]
    if not rows or list(rows[0]) != expected_header or len(rows) != len(units) + 2:
        raise ValueError("CSV schema or per-input row count differs")
    for i, row in enumerate(rows):
        if row["pdb_id"] != spec["structure"]["value"]["pdb"] or row["chain"] != spec["chain"]["value"]:
            raise ValueError("CSV protein/chain differs")
        if i < len(units) and (row["unit_start"] != str(units[i]["start"]) or row["unit_end"] != str(units[i]["end"])):
            raise ValueError("CSV boundaries differ from this case")
        values = [float(row[name]) for name in expected_header[4:]]
        if any(not math.isfinite(value) for value in values):
            raise ValueError("CSV contains non-finite values")
        if i < len(units) and not 0 <= float(row["tmscore"]) <= 1:
            raise ValueError("TM-score is outside its declared scale")
    if any(float(rows[0][name]) != 0 for name in expected_header[4:]):
        raise ValueError("First-unit zero placeholder differs")
    if [row["unit_start"] for row in rows[-2:]] != ["mean", "std"]:
        raise ValueError("Summary rows are not explicitly labelled")
    result = {"rows": len(rows), "units": len(units), "sha256": sha(raw), "reference_comparison": "not_evaluable"}
    if reference is not None:
        reference_spec = record(reference, "specification.json")
        for field in ("chain", "model", "units", "insertions"):
            if spec[field]["value"] != reference_spec[field]["value"]:
                raise ValueError("Reference belongs to different input settings: " + field)
        if spec["structure"]["value"]["pdb"] != reference_spec["structure"]["value"]["pdb"] or sha((run / "source.pdb").read_bytes()) != sha((reference / "source.pdb").read_bytes()):
            raise ValueError("Reference source structure differs")
        golden = (reference / "results/geometry.csv").read_bytes()
        if raw != golden:
            raise ValueError("CSV differs byte for byte from matched-input numerical reference")
        result.update(reference_comparison="byte_identical", reference_run=str(reference), reference_sha256=sha(golden))
    return result


def partial_diagnostics(run, terminal, cancellation):
    tasks = []
    for traversal, name in (("scientific", "trace.tsv"), ("stub", "dry-run/trace.tsv")):
        if not (run / name).is_file():
            continue
        for row in csv.DictReader(io.StringIO((run / name).read_text()), delimiter="\t"):
            tasks.append({"traversal": traversal, "process": row.get("process", row.get("name")),
                          "native_id": row.get("native_id"), "state": row.get("status"),
                          "exit": row.get("exit")})
    errors = []
    for directory in (run / "work", run / "dry-run/work"):
        if not directory.is_dir():
            continue
        for file in sorted(directory.glob("*/*/.command.err")):
            text = file.read_text(errors="replace")
            if text.strip():
                errors.append({"artifact": file.relative_to(run).as_posix(), "sha256": sha(file.read_bytes()),
                               "excerpt": text[-8192:]})
    mount_denial = any("creating mount source path" in item["excerpt"] and "permission denied" in item["excerpt"].lower() for item in errors)
    no_owned_jobs = bool(cancellation and cancellation.get("confirmed") and cancellation.get("remaining") == [])
    return {"terminal": terminal, "native_tasks_observed_in_traces": tasks,
            "scientific_tasks_completed": sum(t["traversal"] == "scientific" and t["state"] == "COMPLETED" and t["exit"] == "0" for t in tasks),
            "captured_task_errors": errors, "docker_mount_permission_denial_observed": mount_denial,
            "native_cancellation": cancellation, "no_owned_active_jobs_after_failure_confirmed": no_owned_jobs,
            "running_job_cancellation_demonstrated": bool(no_owned_jobs and any(item.get("state") == "RUNNING" for item in cancellation.get("requested", []))),
            "limitation": "Trace native IDs do not establish actual node placement without matching native scheduler records. Empty cancellation requests show no owned active jobs, not cancellation of a running task."}


def audit(args):
    bundle = args.bundle.resolve(strict=True)
    run = bundle / "run"
    report = {"schema": "helix-remote-campaign-audit/1.0", "bundle": str(bundle),
              "externally_recorded_manifest_sha256": args.sha256, "expected_outcome": args.expected_outcome,
              "trusted_verifier_sha256": sha(TRUSTED.read_bytes()), "checks": [],
              "scope": "Actual recorded remote engineering execution and source-backed methods; no independent human agreement or physical specificity."}

    def check(name, action):
        try:
            value = action()
        except (OSError, ValueError, KeyError, TypeError, StopIteration, RecursionError) as error:
            report["checks"].append({"name": name, "passed": False, "error": str(error)})
            return None
        report["checks"].append({"name": name, "passed": True, "result": value})
        return value

    verify = runpy.run_path(str(TRUSTED), run_name="trusted_verifier")["verify"]
    cold = check("portable_integrity_and_cold_counts", lambda: verify(bundle, args.sha256))
    if cold is None:
        report["verified"] = False
        return report
    actual = record(run, "run.json")
    terminal = record(run, "remote-terminal.json") if (run / "remote-terminal.json").exists() else None
    outcome = terminal["status"] if terminal else ("rejected" if actual["status"] == "failed" else actual["status"])
    check("expected_outcome", lambda: {"outcome": outcome} if outcome == args.expected_outcome else (_ for _ in ()).throw(ValueError("Actual outcome " + outcome + " differs")))
    succeeded = actual["status"] == "succeeded"
    check("source_backed_methods_and_template", lambda: check_methods(run))
    check("event_chain_and_independent_gate_oracle", lambda: check_events(run, succeeded, args.event_oracle))
    if terminal is not None:
        check("approval_configuration_and_transfer_bindings", lambda: check_bindings(bundle, run))
    if succeeded:
        check("four_native_jobs_and_worker_placement", lambda: check_native_jobs(run))
        check("effective_container_runtime_from_captured_output", lambda: check_runtime(run))
        check("input_specific_numerical_reference", lambda: check_numerical(run, args.reference_run))
        if args.require_reference and args.reference_run is None:
            check("required_reference_supplied", lambda: (_ for _ in ()).throw(ValueError("No input-specific reference supplied")))
    elif terminal is not None:
        cancellation = record(run, "remote-job-cancellation.json") if (run / "remote-job-cancellation.json").exists() else None
        if args.expected_outcome == "cancelled":
            check("native_cancellation_confirmed", lambda: cancellation if cancellation and cancellation["confirmed"] and not cancellation["remaining"] else (_ for _ in ()).throw(ValueError("Native cancellation not independently confirmed")))
        report["partial_execution"] = partial_diagnostics(run, terminal, cancellation)
    if args.fault_injection:
        injection_path = args.output.with_name(args.output.stem + "-fault-injection.json")
        command = ["python", str(ROOT / "script/tesis/audit_trp_bundle.py"), str(bundle), str(injection_path)]
        process = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, timeout=600)
        check("per_artifact_cold_fault_injection", lambda: json.loads(injection_path.read_text()) if process.returncode == 0 else (_ for _ in ()).throw(ValueError(process.stderr[-4000:] or process.stdout[-4000:])))
    report["verified"] = all(item["passed"] for item in report["checks"])
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--sha256", required=True, help="Manifest hash recorded outside the exported bundle")
    parser.add_argument("--expected-outcome", choices=("succeeded", "failed", "cancelled", "rejected"), default="succeeded")
    parser.add_argument("--reference-run", type=Path, help="Matching manual/local run with specification.json, source.pdb and results/geometry.csv")
    parser.add_argument("--require-reference", action="store_true")
    parser.add_argument("--event-oracle", type=Path, help="Independent expected action/event count JSON; not labels derived from the same ledger")
    parser.add_argument("--fault-injection", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"[0-9a-f]{64}", args.sha256):
        parser.error("Expected SHA-256 must be 64 lowercase hexadecimal characters")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    try:
        result = audit(args)
    except (OSError, ValueError, KeyError, TypeError, StopIteration, subprocess.TimeoutExpired) as error:
        result = {"schema": "helix-remote-campaign-audit/1.0", "verified": False, "error": str(error)}
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    temporary.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    temporary.replace(args.output)
    print(json.dumps({"verified": result["verified"],
                      "checks": [{"name": item["name"], "passed": item["passed"], "error": item.get("error")} for item in result.get("checks", [])]}, ensure_ascii=False))
    return 0 if result["verified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
