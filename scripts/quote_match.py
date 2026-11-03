"""Phase 1 throwaway script (P1-T4, OQ-013): can GROBID text be found in the PDF text layer?

Not application code. Needs data/grobid-output/*.tei.xml and data/pdfalto/*.alto.xml
(pdfalto run inside the GROBID container). Run from the repository root:

    uv run python scripts/quote_match.py

For each body sentence of at least MIN_CHARS characters, checks whether it occurs
in the PDF text under three normalisation levels. Prints rates and a few short
failure snippets; writes data/grobid-output/quote-match.json.
"""

import json
import re
import sys
import unicodedata
from collections.abc import Callable
from pathlib import Path
from xml.etree import ElementTree

REPO_ROOT = Path(__file__).resolve().parents[1]
TEI_DIR = REPO_ROOT / "data" / "grobid-output"
ALTO_DIR = REPO_ROOT / "data" / "pdfalto"
TEI = {"tei": "http://www.tei-c.org/ns/1.0"}
MIN_CHARS = 40
LIGATURES = {
    "ﬀ": "ff",
    "ﬁ": "fi",
    "ﬂ": "fl",
    "ﬃ": "ffi",
    "ﬄ": "ffl",
    "ﬅ": "st",
    "ﬆ": "st",
}


def alto_text(path: Path) -> str:
    """Text lines in reading order; a line-final hyphen (ALTO HYP) is kept as '-' + newline."""
    lines: list[str] = []
    for element in ElementTree.parse(path).iter():
        tag = element.tag.rsplit("}", 1)[-1]
        if tag == "TextLine":
            words: list[str] = []
            for child in element:
                child_tag = child.tag.rsplit("}", 1)[-1]
                if child_tag == "String":
                    words.append(child.get("CONTENT", ""))
                elif child_tag == "HYP":
                    words.append("-")
            lines.append(
                " ".join(words).replace(" -", "-")
                if words and words[-1] == "-"
                else " ".join(words)
            )
    return "\n".join(lines)


def level0(text: str) -> str:
    """Whitespace collapsed only."""
    return " ".join(text.split())


def level1(text: str) -> str:
    """Plus Unicode NFKC, ligatures, line-end hyphenation joined, and 'fi nding'-style splits."""
    text = unicodedata.normalize("NFKC", text)
    for ligature, letters in LIGATURES.items():
        text = text.replace(ligature, letters)
    text = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", text)
    text = re.sub(r"\b(fi|fl|ff|ffi|ffl) (?=[a-z])", r"\1", text)
    return " ".join(text.split())


def level2(text: str) -> str:
    """Upper bound: level 1 with all whitespace and hyphens removed, lower-cased."""
    return re.sub(r"[\s\-‐‑–]", "", level1(text)).lower()


LEVELS: list[tuple[str, Callable[[str], str]]] = [
    ("whitespace", level0),
    ("ligatures_hyphenation", level1),
    ("no_spaces_no_hyphens", level2),
]


def sentences(tei_path: Path) -> list[str]:
    body = ElementTree.parse(tei_path).getroot().find("tei:text/tei:body", TEI)
    assert body is not None
    found: list[str] = []
    for paragraph in body.findall("tei:div/tei:p", TEI):
        text = " ".join("".join(paragraph.itertext()).split())
        found.extend(
            s for s in re.split(r"(?<=[.?!])\s+(?=[A-Z])", text) if len(s) >= MIN_CHARS
        )
    return found


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    report: list[dict[str, object]] = []
    for tei_path in sorted(TEI_DIR.glob("*.tei.xml")):
        stem = tei_path.name.removesuffix(".tei.xml")
        pdf_text = alto_text(ALTO_DIR / f"{stem}.alto.xml")
        sents = sentences(tei_path)
        row: dict[str, object] = {"paper": stem, "sentences": len(sents)}
        for name, normalise in LEVELS:
            haystack = normalise(pdf_text)
            misses = [s for s in sents if normalise(s) not in haystack]
            row[name] = round(1 - len(misses) / len(sents), 3) if sents else None
            if name == "ligatures_hyphenation":
                row["examples_missed_at_level1"] = [m[:80] for m in misses[:3]]
        report.append(row)
        print(json.dumps(row, ensure_ascii=False))
    (TEI_DIR / "quote-match.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
