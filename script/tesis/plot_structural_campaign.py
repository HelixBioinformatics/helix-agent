#!/usr/bin/env python3
"""Descriptive physical-observable figure; no fitted threshold or classifier."""
import csv
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "evaluation/trp/campaign-20261012/structural"
source = BASE / "outcomes.csv"
with source.open() as stream:
    rows = list(csv.DictReader(stream))
groups = [
    ("Referencias experimentales\nrevisadas", [r for r in rows if r["group"] != "pratt-original"], "#0072B2"),
    ("Pratt: sin etiqueta\nfísica", [r for r in rows if r["group"] == "pratt-original" and r["label"] != "published_problem"], "#666666"),
    ("Pratt: problemas\nilustrados", [r for r in rows if r["label"] == "published_problem"], "#D55E00"),
]
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.spines.top": False, "axes.spines.right": False, "pdf.fonttype": 42, "svg.fonttype": "none"})
fig, ax = plt.subplots(figsize=(7.5, 4.4))
rng = np.random.default_rng(20261012)
labels = []
for position, (label, cohort, color) in enumerate(groups, start=1):
    valid = [r for r in cohort if r["status"] == "evaluable"]
    values = [float(r["clashscore"]) for r in valid]
    labels.append(f"{label}\nn = {len(valid)}/{len(cohort)}")
    if not values:
        continue
    ax.boxplot([values], positions=[position], widths=0.40, showfliers=False, patch_artist=True,
               boxprops={"facecolor": "white", "edgecolor": color, "linewidth": 1.2},
               medianprops={"color": color, "linewidth": 1.8}, whiskerprops={"color": color}, capprops={"color": color})
    offsets = rng.uniform(-0.16, 0.16, len(valid))
    ax.scatter(position + offsets, values, s=24, color=color, alpha=0.72, zorder=3)
    if position == 3:
        placement = {"8b": (-25, 15), "12ab": (6, 6), "19r": (18, 12), "21r": (-38, -20), "22r": (22, -10)}
        for offset, row, value in zip(offsets, valid, values):
            ax.annotate(row["id"], (position + offset, value), xytext=placement[row["id"]], textcoords="offset points", fontsize=10, color=color,
                        arrowprops={"arrowstyle": "-", "color": color, "linewidth": 0.6}, bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.85, "pad": 0.5})
ax.set_xticks([1, 2, 3], labels)
ax.set_ylabel("Choques graves por 1000 átomos (clashscore)")
ax.set_ylim(bottom=-3)
ax.grid(axis="y", color="#dddddd", linewidth=0.6)
ax.set_axisbelow(True)
fig.tight_layout()
for suffix in ("png", "pdf", "svg"):
    fig.savefig(BASE / f"steric-distribution.{suffix}", dpi=300, bbox_inches="tight")
plt.close(fig)
caption = ("Distribución exploratoria del clashscore calculado por CCTBX Reduce2/Probe2. Cada punto corresponde a una cadena; las cajas muestran mediana y cuartiles. "
           "Los denominadores indican casos evaluables frente al total fijado. Los cinco problemas ilustrados conservan únicamente sus etiquetas publicadas; los restantes modelos de Pratt carecen de etiqueta física. "
           "Las referencias son cadenas experimentales de beta-solenoides con anotación revisada de RepeatsDB, sin certificar ausencia de todo error atómico. "
           "Los modelos AF2 originales no están relajados y las referencias experimentales fueron refinadas, lo que impide atribuir cualquier contraste exclusivamente a validez del pliegue. "
           "No se ajustó ni se dibujó un umbral de clasificación; esta figura no mide sensibilidad ni especificidad física.")
(BASE / "steric-distribution-caption.txt").write_text(caption + "\n")
(BASE / "figure-source.json").write_text(json.dumps({"source": "outcomes.csv", "sha256": hashlib.sha256(source.read_bytes()).hexdigest(), "scriptSha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), "kind": "descriptive distribution, no classifier", "groups": [{"label": label, "total": len(cohort), "evaluable": sum(r["status"] == "evaluable" for r in cohort)} for label, cohort, _ in groups]}, indent=2) + "\n")
print(json.dumps({"figure": str(BASE / "steric-distribution.png"), "sourceRows": len(rows)}))
