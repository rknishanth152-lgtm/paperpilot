"""Phase 1 throwaway script (P1-T4): measure GROBID TEI against the roadmap checklist.

Not application code. Run from the repository root after grobid_experiment.py:

    uv run python scripts/inspect_tei.py

Reads data/grobid-output/*.tei.xml and writes data/grobid-output/inspection.json.
Prints counts and short flags only, no paragraph text (NFR-PRI-002).
"""

import json
import re
import statistics
from pathlib import Path
from xml.etree import ElementTree

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = REPO_ROOT / "data" / "grobid-output"
NS = {"tei": "http://www.tei-c.org/ns/1.0"}
SHORT_PARAGRAPH_CHARS = 60
TERMINAL = (".", "?", "!", ":", ")", "]", '"', "”")


def text_of(element: ElementTree.Element) -> str:
    return " ".join("".join(element.itertext()).split())


def coord_pages(element: ElementTree.Element) -> list[int]:
    """Page numbers from a `coords` attribute: boxes 'page,x,y,w,h;...'."""
    coords = element.get("coords")
    if not coords:
        return []
    return sorted({int(box.split(",")[0]) for box in coords.split(";") if box})


def inspect(path: Path) -> dict[str, object]:
    root = ElementTree.parse(path).getroot()
    header = root.find("tei:teiHeader", NS)
    body = root.find("tei:text/tei:body", NS)
    back = root.find("tei:text/tei:back", NS)
    assert header is not None and body is not None

    title = header.find("tei:fileDesc/tei:titleStmt/tei:title", NS)
    authors = header.findall(
        "tei:fileDesc/tei:sourceDesc/tei:biblStruct/tei:analytic/tei:author/tei:persName",
        NS,
    )
    abstract_ps = header.findall("tei:profileDesc/tei:abstract//tei:p", NS)
    doi = header.find(
        "tei:fileDesc/tei:sourceDesc/tei:biblStruct/tei:idno[@type='DOI']", NS
    )

    divs = body.findall("tei:div", NS)
    heads = body.findall("tei:div/tei:head", NS)
    paragraphs = body.findall("tei:div/tei:p", NS)
    texts = [text_of(p) for p in paragraphs]
    lengths = [len(t) for t in texts]
    pages = [coord_pages(p) for p in paragraphs]

    figures = body.findall("tei:figure", NS)
    tables = [f for f in figures if f.get("type") == "table"]
    table_rows = [len(f.findall("tei:table/tei:row", NS)) for f in tables]
    total_pages = len(root.findall("tei:facsimile/tei:surface", NS))

    references = (
        back.findall(".//tei:listBibl/tei:biblStruct", NS) if back is not None else []
    )
    raw_references = [
        r
        for r in references
        if r.find("tei:note[@type='raw_reference']", NS) is not None
    ]
    back_heads = (
        [text_of(h) for h in back.findall(".//tei:head", NS)]
        if back is not None
        else []
    )

    return {
        "file": path.name,
        "pages": total_pages,
        "header": {
            "title_present": title is not None and bool(text_of(title)),
            "authors": len(authors),
            "abstract_paragraphs": len(abstract_ps),
            "doi_present": doi is not None and bool(text_of(doi)),
        },
        "body": {
            "sections": len(divs),
            "nested_sections": len(body.findall("tei:div/tei:div", NS)),
            "headings": len(heads),
            "numbered_headings": sum(1 for h in heads if h.get("n")),
            "divs_without_heading": sum(
                1 for d in divs if d.find("tei:head", NS) is None
            ),
            "paragraphs": len(paragraphs),
            "paragraph_chars_min_median_max": (
                [min(lengths), int(statistics.median(lengths)), max(lengths)]
                if lengths
                else None
            ),
            "short_paragraphs": sum(1 for n in lengths if n < SHORT_PARAGRAPH_CHARS),
            "ending_without_terminal_punctuation": sum(
                1 for t in texts if t and not t.endswith(TERMINAL)
            ),
            "starting_lowercase": sum(1 for t in texts if t and t[0].islower()),
            "paragraphs_with_page": sum(1 for p in pages if p),
            "paragraphs_spanning_pages": sum(1 for p in pages if len(p) > 1),
            "headings_with_page": sum(1 for h in heads if coord_pages(h)),
            "bare_number_paragraphs": sum(
                1 for t in texts if re.fullmatch(r"\d{1,4}", t)
            ),
            "footnotes": len(body.findall("tei:note", NS)),
            "formulas": len(body.findall(".//tei:formula", NS)),
        },
        "figures_tables": {
            "figures": len(figures) - len(tables),
            "tables": len(tables),
            "tables_with_rows": sum(1 for n in table_rows if n),
            "figures_with_page": sum(1 for f in figures if coord_pages(f)),
        },
        "back": {
            "references": len(references),
            "references_with_raw_string": len(raw_references),
            "references_with_page": sum(1 for r in references if coord_pages(r)),
            "back_section_headings": back_heads,
        },
    }


def main() -> None:
    results = [inspect(p) for p in sorted(OUTPUT_DIR.glob("*.tei.xml"))]
    (OUTPUT_DIR / "inspection.json").write_text(
        json.dumps(results, indent=2), encoding="utf-8"
    )
    for r in results:
        print(json.dumps(r))


if __name__ == "__main__":
    main()
