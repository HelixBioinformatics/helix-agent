#!/usr/bin/env python3
"""Independent stdlib verifier for frozen descriptive solvent-exposure evidence."""
import csv
import hashlib
import json
import math
from pathlib import Path
import statistics

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "evaluation/trp/campaign-20261012/structural/freesasa"


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def approximately(actual, expected):
    assert math.isclose(actual, expected, abs_tol=1e-7, rel_tol=1e-10)


def verify():
    freeze = read(BASE / "freeze.json")
    protocol = read(BASE / "protocol.json")
    assert digest(BASE / "protocol.json") == freeze["protocolSha256"]
    for source in freeze["sources"]:
        path = Path(source["path"])
        assert path.stat().st_size == source["bytes"] and digest(path) == source["sha256"]
    for entry in read(BASE / "manifest.json")["files"]:
        path = BASE / entry["path"]
        assert path.stat().st_size == entry["bytes"] and digest(path) == entry["sha256"]
    cohort = read(BASE.parent / "cases.json")
    assert sorted(c["id"] for c in cohort) == sorted(c["id"] for c in freeze["cases"])
    with (BASE / "outcomes.csv").open() as stream:
        outcomes = {r["id"]: r for r in csv.DictReader(stream)}
    assert len(outcomes) == 108
    summary = read(BASE / "summary.json")
    observed = []
    for case in freeze["cases"]:
        path = Path(case["scoreInputPath"])
        assert digest(path) == case["scoreInputSha256"]
        row = outcomes[case["id"]]
        assert row["group"] == case["group"] and row["label"] == case["label"]
        if row["status"] != "evaluable":
            assert row["error"] and not row["total_area_angstrom_squared"]
            observed.append((case, None))
            continue
        report = read(BASE / "reports" / case["group"] / (case["id"] + ".json"))
        assert report["inputSha256"] == case["scoreInputSha256"]
        assert report["parameters"] == protocol["parameters"]
        assert report["classifier"] == protocol["classifier"]
        assert report["parserOptions"] == protocol["parserOptions"]
        assert report["physicalFoldVerdict"] == "not_established"
        assert report["burialThreshold"] is None and report["confidenceScoresUsed"] is False
        input_atoms = {}
        excluded_h = 0
        for line in path.read_text().splitlines():
            if line[:6] != "ATOM  ":
                continue
            if line[76:78].strip() in {"H", "D"}:
                excluded_h += 1
                continue
            identity = (line[21], line[22:27].strip())
            atom_name = line[12:16].strip()
            names = input_atoms.setdefault(identity, {"name": line[17:20].strip(), "atoms": []})
            assert names["name"] == line[17:20].strip() and atom_name not in names["atoms"]
            names["atoms"].append(atom_name)
        assert excluded_h == report["excludedAtoms"]["hydrogen"]
        assert len(input_atoms) == case["residues"] == report["residues"]
        assert sum(len(v["atoms"]) for v in input_atoms.values()) == report["atoms"]
        residue_areas = report["residueObservations"]
        assert len(residue_areas) == len(input_atoms)
        complete_values = []
        charged_total = incomplete_total = 0
        for residue in residue_areas:
            identity = (residue["chain"], residue["residue"])
            raw = input_atoms[identity]
            assert raw["name"] == residue["residueName"]
            assert raw["atoms"] == [a["name"] for a in residue["atoms"]]
            assert len(raw["atoms"]) == residue["observedAtomCount"]
            absolute = residue["areaAngstromSquared"]
            assert all(math.isfinite(v) and v >= 0 for v in absolute.values())
            approximately(absolute["total"], sum(a["area"] for a in residue["atoms"]))
            approximately(absolute["total"], absolute["polar"] + absolute["apolar"])
            approximately(absolute["total"], absolute["mainChain"] + absolute["sideChain"])
            for component in ("polar", "apolar"):
                approximately(absolute[component], sum(a["area"] for a in residue["atoms"] if a["polarity"].lower() == component))
            for component, reference in protocol["referenceAreasAngstromSquared"][raw["name"]].items():
                relative = residue["relativeArea"][component]
                if reference > 0:
                    assert relative is not None and math.isfinite(relative) and relative >= 0
                    approximately(absolute[component], relative * reference)
            expected_missing = sorted(set(protocol["standardResidueExpectedHeavyAtoms"][raw["name"]]) - set(raw["atoms"]))
            assert residue["missingExpectedHeavyAtoms"] == expected_missing
            if raw["name"] in protocol["chargedSidechainExpectedHeavyAtoms"]:
                charged_total += 1
                missing = sorted(set(protocol["chargedSidechainExpectedHeavyAtoms"][raw["name"]]) - set(raw["atoms"]))
                assert residue["chargedResidueIdentity"] and residue["missingChargedSidechainAtoms"] == missing
                assert residue["chargedSidechainComplete"] == (not missing)
                if missing:
                    incomplete_total += 1
                    assert residue["interpretableChargedSidechainRelativeArea"] is None
                else:
                    assert residue["interpretableChargedSidechainRelativeArea"] == residue["relativeArea"]["sideChain"]
                    complete_values.append(residue["relativeArea"]["sideChain"])
            else:
                assert not residue["chargedResidueIdentity"] and residue["interpretableChargedSidechainRelativeArea"] is None
        assert report["chargedResidues"] == charged_total
        assert report["incompleteChargedSidechains"] == incomplete_total
        assert report["completeChargedSidechains"] == len(complete_values)
        assert report["residuesWithMissingExpectedHeavyAtoms"] == sum(bool(r["missingExpectedHeavyAtoms"]) for r in residue_areas)
        for key, fn in (("Median", statistics.median), ("Min", min), ("Max", max)):
            expected = fn(complete_values) if complete_values else None
            assert report["chargedSidechainRelativeArea" + key] == expected
        for component, total in report["areaAngstromSquared"].items():
            approximately(total, sum(r["areaAngstromSquared"][component] for r in residue_areas))
        approximately(report["libraryTotalArea"], report["areaAngstromSquared"]["total"])
        approximately(report["apolarAreaFraction"] + report["polarAreaFraction"], 1)
        approximately(float(row["total_area_angstrom_squared"]), report["libraryTotalArea"])
        for field, key in (("charged_residues", "chargedResidues"), ("complete_charged_sidechains", "completeChargedSidechains"),
                           ("incomplete_charged_sidechains", "incompleteChargedSidechains"), ("residues_with_missing_heavy_atoms", "residuesWithMissingExpectedHeavyAtoms")):
            assert int(row[field]) == report[key]
        observed.append((case, report))
    for group, declared in summary["groups"].items():
        own = [(c, r) for c, r in observed if c["group"] == group]
        reports = [r for _, r in own if r is not None]
        available = [r for r in reports if r["chargedSidechainRelativeAreaMedian"] is not None]
        actual = {"cases": len(own), "sasaEvaluable": len(reports), "sasaCoverage": len(reports) / len(own),
                  "casesWithInterpretableChargedSidechains": len(available), "casesWithoutChargedResidues": sum(r["chargedResidues"] == 0 for r in reports),
                  "chargedResidues": sum(r["chargedResidues"] for r in reports), "completeChargedSidechains": sum(r["completeChargedSidechains"] for r in reports),
                  "incompleteChargedSidechains": sum(r["incompleteChargedSidechains"] for r in reports),
                  "casesWithMissingHeavyAtoms": sum(r["residuesWithMissingExpectedHeavyAtoms"] > 0 for r in reports),
                  "medianOfCaseChargedSidechainRelativeAreaMedians": statistics.median(r["chargedSidechainRelativeAreaMedian"] for r in available) if available else None}
        assert declared == actual
    assert summary["physicalSensitivity"] is None and summary["physicalSpecificity"] is None
    assert summary["classifierValidated"] is False and summary["biologicalThreshold"] is None
    assert summary["primaryStericEvidencePreserved"] is True
    result = {"ok": True, "cases": len(observed), "evaluable": sum(r is not None for _, r in observed),
              "verifier": str(Path(__file__).resolve()), "verifierSha256": digest(__file__),
              "coreManifestSha256": digest(BASE / "manifest.json"), "groupSummaryRecomputed": True,
              "residueIdentityAndAreaChecked": True, "missingAtomsRemainExplicit": True,
              "primaryAndRuntime600SourceHashesPreserved": True, "biologicalClassifier": None}
    print(json.dumps(result))


if __name__ == "__main__":
    verify()
