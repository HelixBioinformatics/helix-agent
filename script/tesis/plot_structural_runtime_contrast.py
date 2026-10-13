#!/usr/bin/env python3
"""Render the secondary runtime profile separately from primary evidence."""
import csv
import hashlib
import json
from pathlib import Path
import statistics

ROOT = Path(__file__).resolve().parents[2]
PRIMARY = ROOT / "evaluation/trp/campaign-20261012/structural"
BASE = PRIMARY / "runtime-600"
with (PRIMARY / "outcomes.csv").open() as stream:
    primary = list(csv.DictReader(stream))
with (BASE / "outcomes.csv").open() as stream:
    secondary = {row["id"]: row for row in csv.DictReader(stream)}
expanded = [{**row, **secondary.get(row["id"], {})} for row in primary]
with (BASE / "expanded-outcomes.csv").open("w", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=list(primary[0]))
    writer.writeheader()
    writer.writerows(expanded)
summary = json.loads((BASE / "summary.json").read_text())
for group, record in summary["expandedProfile"].items():
    own = [row for row in expanded if row["group"] == group]
    valid = [row for row in own if row["status"] == "evaluable"]
    scores = [float(row["clashscore"]) for row in valid]
    if record["cases"] != len(own) or record["evaluable"] != len(valid) or record["coverage"] != len(valid) / len(own):
        raise ValueError("expanded denominator differs")
    if record["clashscoreMedian"] != statistics.median(scores) or record["clashscoreMin"] != min(scores) or record["clashscoreMax"] != max(scores):
        raise ValueError("expanded statistics differ")

# Reuse the visually reviewed scientific plotting template. The only effective
# code changes select the secondary destination and its explicitly merged CSV.
# Preserve both template and effective-source hashes rather than hiding this.
template_path = ROOT / "script/tesis/plot_structural_campaign.py"
template = template_path.read_text()
old_base = 'BASE = ROOT / "evaluation/trp/campaign-20261012/structural"'
old_source = 'source = BASE / "outcomes.csv"'
if template.count(old_base) != 1 or template.count(old_source) != 1:
    raise ValueError("plotting template changed")
effective = template.replace(old_base, 'BASE = ROOT / "evaluation/trp/campaign-20261012/structural/runtime-600"').replace(old_source, 'source = BASE / "expanded-outcomes.csv"')
exec(compile(effective, str(template_path), "exec"), {"__file__": str(template_path)})
source = json.loads((BASE / "figure-source.json").read_text())
source.update(driverSha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), effectiveSourceSha256=hashlib.sha256(effective.encode()).hexdigest(),
              templateSha256=hashlib.sha256(template.encode()).hexdigest(), profile="secondary600s, primary180s outputs preserved", primaryCsvSha256=hashlib.sha256((PRIMARY / "outcomes.csv").read_bytes()).hexdigest(), secondaryCsvSha256=hashlib.sha256((BASE / "outcomes.csv").read_bytes()).hexdigest())
(BASE / "figure-source.json").write_text(json.dumps(source, indent=2) + "\n")
caption = (BASE / "steric-distribution-caption.txt").read_text().strip()
caption += (" Esta figura corresponde exclusivamente al perfil técnico ampliado: los 105 resultados del primario de 180 segundos se conservan y los tres casos no evaluables se recuperaron con una tentativa adicional, secuencial, de hasta 600 segundos. "
            "Las coordenadas, parámetros, etiquetas y recursos del método permanecieron idénticos. La comparación cambia también de dos trabajadores a uno, por lo que no atribuye las diferencias de tiempo exclusivamente al límite. "
            "El caso experimental recuperado 1ea0-A tiene un clashscore de 71,55, superior al de cuatro de los cinco problemas ilustrados. El solapamiento no permite convertir esta medida en un clasificador físico validado.")
(BASE / "steric-distribution-caption.txt").write_text(caption + "\n")
print(json.dumps({"verifiedExpandedRows": len(expanded), "primaryUntouched": True, "secondaryFigure": str(BASE / "steric-distribution.png")}))
