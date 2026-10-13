#!/usr/bin/env python3
"""Check the rendered Academy thesis against the author's preserved source.

Uses standard Python, pdftotext and the actual DOCX/PDF. Preserves prose,
references and original images independently of the document generator.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
from xml.etree import ElementTree as E
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[2]
NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
CHAPTER4 = "Presentación de los resultados esperados"
CHAPTER5 = "Conclusiones y trabajos futuros"
CAMPAIGN = "Campaña técnica en AWS Academy y estado de la evaluación"
ANNEX = "A.25. Ejecución de Helix en AWS Academy y reproducción"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def text(node):
    return "".join(t.text or "" for t in node.findall(".//w:t", NS))


def is_toc(node):
    gallery = node.find(".//w:docPartGallery", NS)
    return gallery is not None and gallery.get("{" + NS["w"] + "}val") == "Table of Contents"


def extract(path):
    with ZipFile(path) as archive:
        root = E.fromstring(archive.read("word/document.xml"))
        body = root.find("w:body", NS)
        media = Counter(hashlib.sha256(archive.read(name)).hexdigest()
                        for name in archive.namelist() if name.startswith("word/media/"))
    items = list(body)
    boundary = next(i for i, node in enumerate(items) if text(node) == CHAPTER4)
    protected = [text(node) for node in items[:boundary] if not is_toc(node)]
    paragraphs = [text(node) for node in body.findall("w:p", NS)]
    references = paragraphs[paragraphs.index("Referencias") + 1:paragraphs.index("Anexos")]
    references = [value for value in references if value.strip() and not value.startswith("NOTA PARA EL AUTOR.")]
    return root, body, paragraphs, protected, references, media


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--source-sha256", required=True)
    parser.add_argument("--rendered", required=True, type=Path)
    parser.add_argument("--pdf", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if sha(args.source) != args.source_sha256:
        raise ValueError("Author source changed; do not overwrite it")
    old, oldbody, oldps, oldprotected, oldrefs, oldmedia = extract(args.source)
    root, body, paragraphs, protected, refs, media = extract(args.rendered)
    checks = {}

    def check(name, condition, details=None):
        checks[name] = {"passed": bool(condition), "details": details}
        if not condition:
            raise ValueError("Rendered document check failed: " + name)

    check("chapters_1_to_3_text_preserved_excluding_updated_toc", protected == oldprotected,
          {"original_blocks": len(oldprotected), "rendered_blocks": len(protected)})
    check("all_original_images_preserved", not (oldmedia - media),
          {"original": sum(oldmedia.values()), "rendered": sum(media.values())})
    check("section_count_preserved", len(root.findall(".//w:sectPr", NS)) == len(old.findall(".//w:sectPr", NS)))
    iterator = iter(refs)
    check("original_bibliography_order_and_text_preserved", all(any(candidate == value for candidate in iterator) for value in oldrefs),
          {"original_entries": len(oldrefs), "rendered_entries": len(refs)})
    for title in (CHAPTER4, CHAPTER5, CAMPAIGN, ANNEX):
        check("heading_" + title, paragraphs.count(title) == 1)
    expected = [row["id"] for row in json.loads((ROOT / "evaluation/trp/protocol.json").read_text())["metrics"]]
    tables = [node for node in body.findall("w:tbl", NS) if text(node).startswith("IDEvidencia observadaEstado y alcance pendiente")]
    check("one_current_result_table", len(tables) == 1)
    rows = tables[0].findall("w:tr", NS)
    ids = [text(row.find("w:tc", NS)) for row in rows[1:]]
    check("all_21_result_rows_in_current_order", ids == expected and len(rows) == 22, ids)
    toc_nodes = [node for node in body.findall("w:sdt", NS) if is_toc(node)]
    check("one_refreshed_toc", len(toc_nodes) == 1)
    toc = text(toc_nodes[0])
    check("current_chapter_titles_in_toc", CHAPTER4 in toc and CHAPTER5 in toc)
    check("all_current_ids_once_in_toc", all(toc.count(identifier + ".") == 1 for identifier in expected))
    check("new_annex_once_in_toc", toc.count("A.25.") == 1)
    original_texts = set(text(node) for node in oldbody.iter("{" + NS["w"] + "}p"))
    newnotes = 0
    for node in body.iter("{" + NS["w"] + "}p"):
        value = text(node)
        if value in original_texts:
            continue
        check("no_em_dash_" + str(newnotes) + "_" + hashlib.sha256(value.encode()).hexdigest()[:10], "\u2014" not in value)
        if not value.startswith("NOTA PARA EL AUTOR."):
            continue
        colors = [color.get("{" + NS["w"] + "}val") for color in node.findall(".//w:color", NS)]
        check("red_italic_new_note_" + str(newnotes), "FF0000" in colors and bool(node.findall(".//w:i", NS)))
        newnotes += 1
    pdf = subprocess.run(["pdftotext", "-layout", str(args.pdf), "-"], check=True, capture_output=True, text=True).stdout
    pages = pdf.split("\f")[:-1]
    footer_counts = set(re.findall(r"Página\s+\d+\s+de\s+(\d+)", pdf))
    check("footer_total_matches_pdf", footer_counts == {str(len(pages))}, {"pdf_pages": len(pages), "footer_totals": sorted(footer_counts)})
    check("all_result_ids_visible_in_pdf", all(identifier in pdf for identifier in expected))
    report = {
        "schema": "helix-rendered-thesis-audit/1.0", "verified": True,
        "observed_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": str(args.source), "source_sha256": args.source_sha256,
        "rendered": str(args.rendered), "rendered_sha256": sha(args.rendered),
        "pdf": str(args.pdf), "pdf_sha256": sha(args.pdf), "pdf_pages": len(pages),
        "new_red_italic_notes": newnotes, "checks": checks,
        "scope": "Text, package images, identifiers, bibliography and rendered page fields. Separate visual inspection remains required.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"verified": True, "checks": len(checks), "pages": len(pages), "new_notes": newnotes}))


if __name__ == "__main__":
    main()
