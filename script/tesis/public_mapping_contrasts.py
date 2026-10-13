#!/usr/bin/env python3
"""Freeze and independently characterize public SIFTS/CIF/PDB mapping contrasts.

The oracle reads public source rows, never the Helix-produced mapping. All
selected chains and unsupported residues remain in their original denominators.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import gzip
import hashlib
import json
import math
from pathlib import Path
import re
import statistics
import subprocess
import os
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "evaluation/trp/campaign-20261012/mapping-public-contrasts"
COHORT = ROOT / "evaluation/trp/campaign-20261012/structural/cases.json"
CODE = ["packages/helix/src/trp/coordinates.ts", "packages/helix/src/trp/sifts_residues.py.txt",
        "packages/helix/src/trp/inspect_structure.py.txt", "packages/helix/src/trp/structural.ts",
        "packages/helix/src/trp/specification.ts", "packages/helix/src/trp/catalog.json",
        "script/tesis/public_mapping_contrasts.py", "script/tesis/run_public_mapping_contrasts.ts"]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path):
    return json.loads(Path(path).read_text())


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


def prepare():
    import gemmi
    if (BASE / "protocol.json").exists():
        raise ValueError("prospective protocol already exists")
    chosen = [c for c in load(COHORT) if c["group"] == "experimental-reviewed-beta-solenoid"]
    assert len(chosen) == 30 and all(c["pdb"] != "2xqh" and len(c["uniprot"]) == 1 for c in chosen)
    cases = [{"id": c["id"], "pdb": c["pdb"], "chain": c["chain"], "accession": c["uniprot"][0],
              "cifUrl": f"https://files.rcsb.org/download/{c['pdb'].upper()}.cif",
              "pdbUrl": f"https://files.rcsb.org/download/{c['pdb'].upper()}.pdb",
              "siftsUrl": f"https://ftp.ebi.ac.uk/pub/databases/msd/sifts/xml_remediated/{c['pdb']}.xml.gz",
              "siftsAvailabilityFallbackUrl": f"https://ftp.ebi.ac.uk/pub/databases/msd/sifts/xml/{c['pdb']}.xml.gz"} for c in chosen]
    protocol = {"version": "public-mapping-development/1.0.0", "createdUTC": datetime.now(timezone.utc).isoformat(),
                "selection": "Exactly the thirty existing reviewed experimental beta-solenoid PDB/author-chain/accession identities; no 2XQH, private author models, replacements or held-out claims.",
                "cases": cases, "sourceCohortSha256": sha(COHORT),
                "sourcePolicy": "Current official RCSB CIF and PDB plus EBI remediated SIFTS XML. Legacy official XML only after HTTP404 of remediated source, recorded explicitly. One request per URL with a 30s transport limit and 20MB input cap; source failures stay in the thirty-chain denominator.",
                "oracle": "Independent raw CIF atom_site CA rows plus fixed-column official PDB CA records and namespace-aware XML residue cross-reference joins. No segment endpoint interpolation, sequence alignment or producer-generated mapping is used as an expectation. Shared Gemmi lexical CIF parser is disclosed; join/identity logic is separate.",
                "comparisons": ["All residue rows from production SIFTS parser versus raw XML expectation", "Real mapUnits for every unique observed label position versus independently joined CIF/PDB expectations", "Real Coordinates.prepare for all observed numeric UniProt positions in maximal consecutive intervals (split a single interval into two probes to satisfy the existing adapter contract)"],
                "granularity": "Intervals are engineering numbering probes, not independent biological repeat boundaries. The label primitive is also tested with one-residue intervals and each unsupported position is retained.",
                "scope": "First model; fixed author chain; observed CA positions. Full XML unobserved positions, no-cross-reference positions, insertions, noninteger/negative author positions, alternate or duplicate identities, mismatches and missing coordinates are retained and classified as unmappable or unsupported. No physical or language verdict.",
                "coordinateToleranceAngstrom": 0.0011, "bFactorToleranceAngstromSquared": 0.011,
                "runtime": {"gemmi": gemmi.__version__, "workers": 1, "maximumAttempts": 1, "perChainSeconds": 180},
                "sources": ["https://www.ebi.ac.uk/pdbe/docs/sifts/quick.html", "https://www.ebi.ac.uk/pdbe/docs/sifts/efamily.html", "https://www.rcsb.org/docs/programmatic-access/file-download-services"],
                "missingHumanReference": True, "reservedScientificEvaluation": False,
                "software": [{"path": name, "sha256": sha(ROOT / name)} for name in CODE],
                "gemmiModuleSha256": sha(Path(gemmi.__file__).parent / next(p.name for p in Path(gemmi.__file__).parent.glob("gemmi_ext*.so")))}
    save(BASE / "protocol.json", protocol)
    print(json.dumps({"frozenChains": len(cases), "privateAuthorInputs": 0, "comparisonsStarted": False}))


def verify_protocol():
    protocol = load(BASE / "protocol.json")
    assert sha(COHORT) == protocol["sourceCohortSha256"]
    for entry in protocol["software"]:
        assert sha(ROOT / entry["path"]) == entry["sha256"], entry["path"]
    return protocol


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Helix thesis public mapping verification/1.0"})
    with urllib.request.urlopen(req, timeout=30) as response:
        raw = response.read(20_000_001)
        if len(raw) > 20_000_000:
            raise ValueError("official source exceeds fixed20MB cap")
        return raw, {"finalUrl": response.url, "lastModified": response.headers.get("Last-Modified"), "contentType": response.headers.get("Content-Type")}


def acquire_one(case):
    directory = BASE / "sources" / case["id"]
    directory.mkdir(parents=True, exist_ok=True)
    records = []
    for kind, url in (("cif", case["cifUrl"]), ("pdb", case["pdbUrl"]), ("sifts", case["siftsUrl"])):
        try:
            fallback = False
            try:
                raw, headers = fetch(url)
            except urllib.error.HTTPError as error:
                if kind != "sifts" or error.code != 404:
                    raise
                url, fallback = case["siftsAvailabilityFallbackUrl"], True
                raw, headers = fetch(url)
            extension = "xml.gz" if kind == "sifts" else kind
            file = directory / (case["pdb"] + "." + extension)
            file.write_bytes(raw)
            record = {"kind": kind, "url": url, "retrievedUTC": datetime.now(timezone.utc).isoformat(), "headers": headers,
                      "path": file.relative_to(ROOT).as_posix(), "sha256": sha(file), "bytes": len(raw), "availabilityFallback": fallback, "status": "available"}
            if kind == "sifts":
                xml = gzip.decompress(raw)
                if len(xml) > 20_000_000:
                    raise ValueError("decompressed XML exceeds cap")
                decoded = directory / (case["pdb"] + ".xml")
                decoded.write_bytes(xml)
                record.update(xmlPath=decoded.relative_to(ROOT).as_posix(), xmlSha256=sha(decoded), xmlBytes=len(xml))
            records.append(record)
        except Exception as error:
            records.append({"kind": kind, "url": url, "status": "unavailable", "error": type(error).__name__ + ": " + str(error)})
    save(directory / "acquisition.json", {"case": case, "records": records})
    return {"case": case, "records": records}


def acquire():
    protocol = verify_protocol()
    if (BASE / "acquisition.json").exists():
        raise ValueError("source acquisition already completed")
    # Independent read-only requests; the scientific worker remains sequential.
    with ThreadPoolExecutor(max_workers=3) as pool:
        rows = list(pool.map(acquire_one, protocol["cases"]))
    save(BASE / "acquisition.json", rows)
    print(json.dumps({"chains": len(rows), "allSourcesAvailable": sum(all(r["status"] == "available" for r in row["records"]) for row in rows)}))


def clean(value):
    import gemmi
    return None if value in ("?", ".", "") else gemmi.cif.as_string(value)


def cif_rows(path, chain):
    import gemmi
    block = gemmi.cif.read_file(str(path)).sole_block()
    names = ["label_atom_id", "label_seq_id", "auth_seq_id", "auth_asym_id", "label_comp_id", "label_alt_id",
             "pdbx_PDB_ins_code", "pdbx_PDB_model_num", "Cartn_x", "Cartn_y", "Cartn_z", "B_iso_or_equiv"]
    table = block.find("_atom_site.", names)
    raw = [dict(zip(names, [clean(value) for value in row])) for row in table]
    first_model = raw[0]["pdbx_PDB_model_num"] if raw else None
    rows = []
    for atom in raw:
        if atom["label_atom_id"] != "CA" or atom["auth_asym_id"] != chain or atom["pdbx_PDB_model_num"] != first_model or atom["label_seq_id"] is None:
            continue
        rows.append({"label": int(atom["label_seq_id"]), "author": atom["auth_seq_id"], "residue": atom["label_comp_id"],
                     "insertion": atom["pdbx_PDB_ins_code"] or "", "alt": atom["label_alt_id"] or "",
                     "xyz": [float(atom["Cartn_" + a]) for a in "xyz"], "b": float(atom["B_iso_or_equiv"])})
    return rows


def pdb_rows(path, chain):
    rows, ordinal, current = [], 0, 1
    for line in Path(path).read_text().splitlines():
        if line.startswith("MODEL "):
            ordinal += 1
            current = ordinal
        if line.startswith("ENDMDL"):
            current = 0
        if current != 1 or line[:6] not in ("ATOM  ", "HETATM") or line[21:22] != chain or line[12:16].strip() != "CA":
            continue
        rows.append({"author": line[22:26].strip(), "residue": line[17:20].strip(), "insertion": line[26:27].strip(),
                     "alt": line[16:17].strip(), "xyz": [float(line[p:p + 8]) for p in (30, 38, 46)], "b": float(line[60:66])})
    return rows


def xml_rows(path, case):
    root = ET.fromstring(Path(path).read_bytes())
    tag = lambda name: name.rsplit("}", 1)[-1]
    assert root.attrib["dbAccessionId"].lower() == case["pdb"]
    all_rows, observed, unobserved = [], [], []
    for item in root.iter():
        if tag(item.tag) != "residue":
            continue
        refs = [node.attrib for node in item if tag(node.tag) == "crossRefDb"]
        pdb = [r for r in refs if r.get("dbSource") == "PDB" and r.get("dbChainId") == case["chain"] and r.get("dbAccessionId", "").lower() == case["pdb"]]
        if not pdb:
            continue
        uni = [r for r in refs if r.get("dbSource") == "UniProt" and r.get("dbAccessionId") == case["accession"]]
        not_observed = any(tag(node.tag) == "residueDetail" and (node.text or "").strip().casefold() == "not_observed" for node in item)
        record = {"pdbReferences": pdb, "uniprotReferences": uni, "notObserved": not_observed, "details": [(node.text or "").strip() for node in item if tag(node.tag) == "residueDetail"]}
        all_rows.append(record)
        if not uni:
            continue
        (unobserved if not_observed else observed).append(record)
    rows, error = [], None
    for record in observed:
        p, u = record["pdbReferences"], record["uniprotReferences"]
        if len(p) != 1 or len(u) != 1:
            error = "ambiguous-sifts-residue"
            break
        if not re.fullmatch(r"[0-9]+", p[0].get("dbResNum", "")) or not re.fullmatch(r"[0-9]+", u[0].get("dbResNum", "")):
            error = "unsupported-sifts-numbering"
            break
        rows.append({"author": int(p[0]["dbResNum"]), "uniprot": int(u[0]["dbResNum"]), "residue": p[0].get("dbResName"), "uniprotResidue": u[0].get("dbResName")})
    if error is None and not rows:
        error = "no-observed-sifts-residues"
    if error is None and (len({r["author"] for r in rows}) != len(rows) or len({r["uniprot"] for r in rows}) != len(rows)):
        error = "nonbijective-sifts-mapping"
    positions = sorted({int(r["uniprotReferences"][0]["dbResNum"]) for r in observed if len(r["uniprotReferences"]) == 1 and r["uniprotReferences"][0].get("dbResNum", "").isdigit()})
    return {"rawChainRows": all_rows, "observedWithAccession": observed, "unobservedWithAccession": unobserved,
            "expectedRows": rows if error is None else None, "expectedParserError": error, "uniprotPositions": positions,
            "release": root.attrib.get("date")}


def intervals(positions):
    ranges = []
    for value in sorted(set(positions)):
        if ranges and value == ranges[-1]["end"] + 1:
            ranges[-1]["end"] = value
        else:
            ranges.append({"start": value, "end": value})
    if len(ranges) == 1 and ranges[0]["end"] > ranges[0]["start"]:
        start, end = ranges[0]["start"], ranges[0]["end"]
        midpoint = (start + end) // 2
        ranges = [{"start": start, "end": midpoint}, {"start": midpoint + 1, "end": end}]
    return ranges


def expected_label_rows(source, target):
    rows = []
    for label in sorted({r["label"] for r in source}):
        candidates = [r for r in source if r["label"] == label]
        reason, mapping = None, None
        if len(candidates) != 1:
            reason = "ambiguous-label"
        else:
            row = candidates[0]
            others = [r for r in target if r["author"] == row["author"]]
            if not re.fullmatch(r"[1-9][0-9]*", row["author"] or ""):
                reason = "unsupported-author-numbering"
            elif len(others) != 1:
                reason = "missing-or-ambiguous-author"
            elif row["alt"] or row["insertion"] or others[0]["alt"] or others[0]["insertion"] or row["residue"] != others[0]["residue"]:
                reason = "identity-or-insertion"
            elif any(not math.isfinite(x) or not math.isfinite(y) or abs(x - y) > 0.0011 for x, y in zip(row["xyz"], others[0]["xyz"])):
                reason = "coordinate-mismatch"
            elif not math.isfinite(row["b"]) or not math.isfinite(others[0]["b"]) or abs(row["b"] - others[0]["b"]) > 0.011:
                reason = "displacement-mismatch"
            else:
                mapping = {"label": label, "author": int(row["author"]), "residue": row["residue"]}
        rows.append({"label": label, "expectedMapping": mapping, "unmappableReason": reason})
    return rows


def oracle():
    verify_protocol()
    if (BASE / "oracle-freeze.json").exists():
        raise ValueError("oracle expectations already frozen; no post-output adjustments")
    acquisitions, results = load(BASE / "acquisition.json"), []
    for acquired in acquisitions:
        case = acquired["case"]
        if not all(r["status"] == "available" for r in acquired["records"]):
            results.append({"case": case, "status": "sources_unavailable", "sources": acquired["records"]})
            continue
        records = {r["kind"]: r for r in acquired["records"]}
        source, target = cif_rows(ROOT / records["cif"]["path"], case["chain"]), pdb_rows(ROOT / records["pdb"]["path"], case["chain"])
        sifts = xml_rows(ROOT / records["sifts"]["xmlPath"], case)
        labels = expected_label_rows(source, target)
        # End-to-end expected chain uses all observed UniProt rows; no unit
        # boundary is chosen from actual producer outputs or endpoint offsets.
        expected_chain, chain_error = [], sifts["expectedParserError"]
        if chain_error is None:
            by_author = {}
            for row in source:
                by_author.setdefault(row["author"], []).append(row)
            for row in sifts["expectedRows"]:
                matches = by_author.get(str(row["author"]), [])
                if len(matches) != 1 or matches[0]["residue"] != row["residue"]:
                    chain_error = "sifts-identity"
                    break
                match = next(r for r in labels if r["label"] == matches[0]["label"])
                if match["expectedMapping"] is None:
                    chain_error = match["unmappableReason"]
                    break
                expected_chain.append({**match["expectedMapping"], "uniprot": row["uniprot"]})
        ranges = intervals(sifts["uniprotPositions"])
        ordered_chain = sorted(expected_chain, key=lambda r: r["uniprot"])
        if chain_error is None:
            for unit in ranges:
                own = [r for r in ordered_chain if unit["start"] <= r["uniprot"] <= unit["end"]]
                if any(b["label"] != a["label"] + 1 or b["author"] != a["author"] + 1 for a, b in zip(own, own[1:])):
                    chain_error = "noncontiguous-interval"
                    break
        result = {"case": case, "status": "oracle_ready", "sources": records, "rawCifCaRows": source, "rawPdbCaRows": target,
                  "labelRows": labels, "sifts": sifts, "uniprotIntervals": ranges, "expectedPreparedMapping": ordered_chain if chain_error is None else None,
                  "expectedPreparedError": chain_error,
                  "probeLabelPositions": [r["label"] for r in source[:2]],
                  "probeAuthorPositions": [int(r["author"]) for r in target[:2]]}
        save(BASE / "oracle" / (case["id"] + ".json"), result)
        results.append({"case": case, "status": "oracle_ready", "oraclePath": (BASE / "oracle" / (case["id"] + ".json")).relative_to(ROOT).as_posix()})
    save(BASE / "oracle-index.json", results)
    sources = [{"path": p.relative_to(ROOT).as_posix(), "sha256": sha(p), "bytes": p.stat().st_size} for p in sorted(BASE.rglob("*")) if p.is_file()]
    save(BASE / "oracle-freeze.json", {"createdUTC": datetime.now(timezone.utc).isoformat(), "producerOutputsObserved": False, "files": sources})
    print(json.dumps({"chains": len(results), "oracleReady": sum(r["status"] == "oracle_ready" for r in results), "frozenBeforeProducer": True}))


def verify_sources():
    verify_protocol()
    for entry in load(BASE / "oracle-freeze.json")["files"]:
        path = ROOT / entry["path"]
        assert path.stat().st_size == entry["bytes"] and sha(path) == entry["sha256"], entry["path"]


def run():
    verify_sources()
    if (BASE / "run-summary.json").exists():
        raise ValueError("producer contrast already completed")
    rows = []
    for entry in load(BASE / "oracle-index.json"):
        case = entry["case"]
        if entry["status"] != "oracle_ready":
            rows.append({"id": case["id"], "status": "sources_unavailable"})
            continue
        attempt = BASE / "attempts" / (case["id"] + ".json")
        if attempt.exists():
            raise ValueError("attempt exists; never silently retry")
        save(attempt, {"id": case["id"], "startedUTC": datetime.now(timezone.utc).isoformat(), "status": "running"})
        try:
            result = subprocess.run(["bun", str(ROOT / "script/tesis/run_public_mapping_contrasts.ts"), case["id"]],
                                    text=True, capture_output=True, timeout=180,
                                    env=dict(os.environ, HELIX_TRP_PYTHON=sys.executable, HELIX_TRP_STERIC_PYTHON="", HELIX_TRP_SURFACE_PYTHON=""))
            row = {"id": case["id"], "status": "completed" if result.returncode == 0 else "runtime_failed", "exitCode": result.returncode}
            (attempt.with_suffix(".log")).write_text(result.stdout + "\n" + result.stderr)
        except subprocess.TimeoutExpired:
            row = {"id": case["id"], "status": "runtime_timeout", "timeoutSeconds": 180}
        save(attempt, row)
        rows.append(row)
        save(BASE / "progress.json", {"completed": len(rows), "total": 30, "rows": rows})
        print(json.dumps(row), flush=True)
    save(BASE / "run-summary.json", {"cases": 30, "rows": rows, "modelCalls": 0, "awsInstances": 0})
    verify_sources()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["prepare", "acquire", "oracle", "verify-sources", "run"])
    action = parser.parse_args().action.replace("-", "_")
    globals()[action]()
