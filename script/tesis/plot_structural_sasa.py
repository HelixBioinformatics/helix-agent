#!/usr/bin/env python3
"""Export per-residue observations and draw an explicitly descriptive figure."""
import csv
import hashlib
import json
from pathlib import Path
import statistics

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "evaluation/trp/campaign-20261012/structural/freesasa"
cases = json.loads((BASE / "freeze.json").read_text())["cases"]
with (BASE / "outcomes.csv").open() as stream:
    outcomes = list(csv.DictReader(stream))
reports = {case["id"]: json.loads((BASE / "reports" / case["group"] / (case["id"] + ".json")).read_text()) for case in cases if next(row for row in outcomes if row["id"] == case["id"])["status"] == "evaluable"}
observations = []
for case in cases:
    if case["id"] not in reports:
        continue
    for row in reports[case["id"]]["residueObservations"]:
        observations.append({"case": case["id"], "group": case["group"], "published_label": case["label"],
                             "chain": row["chain"], "residue": row["residue"], "residue_name": row["residueName"],
                             **{f"{key}_area_A2": value for key, value in row["areaAngstromSquared"].items()},
                             **{f"relative_{key}_area": value for key, value in row["relativeArea"].items()},
                             "observed_heavy_atoms": row["observedAtomCount"], "missing_heavy_atoms": " ".join(row["missingExpectedHeavyAtoms"]),
                             "charged_identity": row["chargedResidueIdentity"], "charged_sidechain_complete": row["chargedSidechainComplete"],
                             "missing_charged_sidechain_atoms": " ".join(row["missingChargedSidechainAtoms"] or []),
                             "interpretable_charged_sidechain_relative_area": row["interpretableChargedSidechainRelativeArea"]})
for name, selected in (("residue-observations.csv", observations), ("charged-residue-observations.csv", [r for r in observations if r["charged_identity"]])):
    with (BASE / name).open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(observations[0]))
        writer.writeheader()
        writer.writerows(selected)

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
                     "pdf.fonttype": 42, "svg.fonttype": "none"})
fig, (ax, detail) = plt.subplots(1, 2, figsize=(10.3, 4.2), gridspec_kw={"width_ratios": [1, 1.15]})
groups = [("Referencias\nexperimentales", [r for r in outcomes if r["group"] != "pratt-original"], "#0072B2"),
          ("Pratt: sin\netiqueta física", [r for r in outcomes if r["group"] == "pratt-original" and r["label"] != "published_problem"], "#666666"),
          ("Pratt: problemas\nilustrados", [r for r in outcomes if r["label"] == "published_problem"], "#D55E00")]
rng = np.random.default_rng(20261012)
labels = []
for x, (label, rows, color) in enumerate(groups, 1):
    selected = [r for r in rows if r["charged_sidechain_relative_area_median"]]
    values = [float(r["charged_sidechain_relative_area_median"]) for r in selected]
    labels.append(f"{label}\nn = {len(selected)}/{len(rows)}")
    ax.boxplot([values], positions=[x], widths=0.4, showfliers=False, patch_artist=True,
               boxprops={"facecolor": "white", "edgecolor": color}, medianprops={"color": color},
               whiskerprops={"color": color}, capprops={"color": color})
    offsets = rng.uniform(-0.15, 0.15, len(values))
    ax.scatter(x + offsets, values, s=23, color=color, alpha=0.74, zorder=3)
    if x == 3:
        placements = {"19r": (7, 8), "12ab": (-25, -8), "22r": (10, -3), "21r": (8, 8)}
        for offset, value, row in zip(offsets, values, selected):
            ax.annotate(row["id"], (x + offset, value), xytext=placements[row["id"]], textcoords="offset points", color=color, fontsize=9,
                        arrowprops={"arrowstyle": "-", "color": color, "linewidth": 0.6},
                        bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.85, "pad": 0.5})
ax.set_xticks([1, 2, 3], labels)
ax.set_ylabel("Mediana de rSA lateral de D/E/K/R por cadena")
ax.set_ylim(-0.04, 1.14)
ax.text(-0.12, 1.04, "A", transform=ax.transAxes, fontweight="bold", fontsize=12)
ax.grid(axis="y", color="#dddddd", linewidth=0.6)
ax.set_axisbelow(True)

# Repeat grouping is a verifiable sequence identity, not a newly assigned fold
# or failure label. 22r comprises the exact same 22-residue unit ten times.
sequence = [r["residueName"] for r in reports["22r"]["residueObservations"]]
assert len(sequence) == 220 and all(sequence[i:i + 22] == sequence[:22] for i in range(0, 220, 22))
detail_rows = reports["22r"]["residueObservations"]
traces = []
for position, name, color, marker in ((3, "Lys3", "#000000", "s"), (6, "Asp6", "#0072B2", "o"),
                                     (10, "Asp10", "#D55E00", "^"), (18, "Asp18", "#009E73", "D")):
    selected = [detail_rows[position - 1 + 22 * i] for i in range(10)]
    assert all(r["chargedSidechainComplete"] for r in selected)
    values = [r["interpretableChargedSidechainRelativeArea"] for r in selected]
    detail.plot(range(1, 11), values, color=color, marker=marker, markersize=4, linewidth=1, label=name)
    traces.append({"positionInRepeat": position, "name": name, "values": values, "median": statistics.median(values)})
detail.set_xlabel("Repetición de 22r, orden en la secuencia")
detail.set_ylabel("rSA lateral respecto de Ala-X-Ala (ProtOr)")
detail.set_xticks(range(1, 11))
detail.set_ylim(-0.04, 1.14)
detail.text(-0.12, 1.04, "B", transform=detail.transAxes, fontweight="bold", fontsize=12)
detail.legend(frameon=False, fontsize=9, loc="upper right")
detail.grid(axis="y", color="#dddddd", linewidth=0.6)
detail.set_axisbelow(True)
fig.tight_layout(w_pad=2.0)
for suffix in ("png", "pdf", "svg"):
    fig.savefig(BASE / ("surface-exposure." + suffix), dpi=300, bbox_inches="tight")
plt.close(fig)
caption = ("Accesibilidad al solvente descriptiva, calculada con FreeSASA/ProtOr, Lee y Richards, sonda de 1.4 Å y 20 cortes. "
           "A: cada punto representa la mediana del área lateral relativa (rSA) de los residuos Asp/Glu/Lys/Arg con todos sus átomos laterales esperados; las cajas muestran mediana y cuartiles de las cadenas. "
           "Los denominadores distinguen cadenas con un observable aplicable frente a todas las cadenas fijadas. Veintinueve modelos de Pratt, incluido 8b, carecen de estos residuos y no se representan como valores cero. "
           "Los 29 residuos laterales incompletos de las referencias conservan sus mediciones parciales, pero se excluyen del resumen interpretable. "
           "B: rSA de cuatro posiciones laterales de la unidad de 22 residuos repetida diez veces en 22r, enlazado con la Figura 3B de Pratt et al. "
           "El área se normaliza con el tripéptido Ala-X-Ala extendido de ProtOr y puede superar 1. Las líneas unen mediciones de una misma posición de la secuencia; no representan trayectorias temporales. "
           "Se analiza la cadena aislada y se omiten otros componentes del ensamblaje. No se fija un umbral de enterramiento, no se determina la protonación o compensación de cargas y no se clasifica la validez física del pliegue.")
(BASE / "surface-exposure-caption.txt").write_text(caption + "\n")
digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
(BASE / "figure-source.json").write_text(json.dumps({"scriptSha256": digest(Path(__file__).resolve()), "sourceOutcomeSha256": digest(BASE / "outcomes.csv"),
                                                     "source22rSha256": digest(BASE / "reports/pratt-original/22r.json"), "groups": [{"label": label, "total": len(rows), "applicable": sum(bool(r["charged_sidechain_relative_area_median"]) for r in rows)} for label, rows, _ in groups],
                                                     "22rSequenceRepeatLength": 22, "22rRepeats": 10, "traces": traces,
                                                     "figureKind": "descriptive continuous surface exposure; no burial threshold or classifier"}, ensure_ascii=False, indent=2) + "\n")
print(json.dumps({"residueRows": len(observations), "chargedRows": sum(r["charged_identity"] for r in observations), "figure": str(BASE / "surface-exposure.png")}))
