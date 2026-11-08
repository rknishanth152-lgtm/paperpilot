"""Phase 5 measurement (P5-T6, OQ-013): which quote-matching rules accept true quotes
and reject altered ones? Not application code. Read-only. Run from the repository root
with PostgreSQL running and the five papers ingested:

    uv run python scripts/quote_rules.py

Prints counts only, never passage text, and writes data/grobid-output/quote-rules.json
(git-ignored). Needs pdftotext (shipped with Git for Windows).

A model sees stored passage text but may tidy it when quoting, so "true quotes" are
stored sentences written as they appear in the PDF as well as exactly as stored.
"""

import json
import random
import re
import shutil
import subprocess
import sys
import unicodedata
from collections import Counter
from collections.abc import Callable
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from sqlalchemy import text

from app.database import get_engine

PAPERS = REPO_ROOT / "data" / "papers"
OUTPUT = REPO_ROOT / "data" / "grobid-output" / "quote-rules.json"
PDFTOTEXT = (
    shutil.which("pdftotext") or r"C:\Program Files\Git\mingw64\bin\pdftotext.exe"
)
MIN_CHARS = 40
DASHES = re.compile("[\u2010-\u2015\u2212]")
QUOTES = str.maketrans({"\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"'})
SPLIT = re.compile(r"(fi|fl|ff) (?=[a-z])")
SPLIT_WORD = re.compile(r"\b([A-Za-z]*(?:fi|fl|ff)) ([a-z]+)")


def folded(value: str) -> str:
    return DASHES.sub("-", unicodedata.normalize("NFKC", value)).translate(QUOTES)


def rule_a(value: str) -> str:
    """Typography and whitespace only."""
    return " ".join(folded(value).split())


def rule_b(value: str) -> str:
    """Provisional OQ-013: A plus a space removed after fi, fl or ff."""
    return SPLIT.sub(r"\1", rule_a(value))


def rule_c(value: str) -> str:
    """Every space ignored."""
    return "".join(folded(value).split())


RULES: dict[str, Callable[[str], str]] = {
    "A typography, whitespace": rule_a,
    "B plus split ligatures": rule_b,
    "C ignore all spaces": rule_c,
}


def sentences(passage: str) -> list[str]:
    found = re.split(r"(?<=[.!?])\s+(?=[A-Z])", passage)
    return [s for s in found if len(s) >= MIN_CHARS]


def page_text(pdf: Path) -> str:
    done = subprocess.run([PDFTOTEXT, str(pdf), "-"], capture_output=True, check=True)
    return " ".join(folded(done.stdout.decode("utf-8", "replace")).split())


def as_in_pdf(sentence: str, pdf: str, squeezed: str, offsets: list[int]) -> str | None:
    """The sentence as the PDF spells it, or None if it cannot be located."""
    wanted = "".join(folded(sentence).split())
    start = squeezed.find(wanted)
    if start < 0:
        return None
    return pdf[offsets[start] : offsets[start + len(wanted) - 1] + 1]


def alterations(sentence: str, rng: random.Random) -> dict[str, str]:
    words = sentence.split()
    out: dict[str, str] = {}
    middle = rng.randrange(1, len(words) - 1) if len(words) > 2 else 0
    out["word dropped"] = " ".join(words[:middle] + words[middle + 1 :])
    out["word replaced"] = " ".join(
        words[:middle] + ["substitute"] + words[middle + 1 :]
    )
    out["not inserted"] = " ".join(words[:middle] + ["not"] + words[middle:])
    if digit := re.search(r"\d", sentence):
        changed = str((int(digit.group()) + 1) % 10)
        out["number changed"] = (
            sentence[: digit.start()] + changed + sentence[digit.end() :]
        )
    letters = [i for i, c in enumerate(sentence) if c.isalpha()]
    position = rng.choice(letters)
    swap = "x" if sentence[position] != "x" else "y"
    out["letter changed"] = sentence[:position] + swap + sentence[position + 1 :]
    return out


def main() -> None:
    with get_engine().connect() as connection:
        rows = connection.execute(
            text(
                "SELECT left(d.original_filename, 2), d.original_filename, p.text "
                "FROM passages p JOIN documents d ON d.id = p.document_id"
            )
        ).all()

    pdfs: dict[str, tuple[str, str, list[int]]] = {}
    for _, name, _ in rows:
        if name not in pdfs:
            pdf = page_text(PAPERS / name)
            offsets = [i for i, c in enumerate(pdf) if not c.isspace()]
            pdfs[name] = (pdf, "".join(c for c in pdf if not c.isspace()), offsets)

    rng = random.Random(20261108)
    true_counts: Counter[str] = Counter()
    false_counts: Counter[str] = Counter()
    joined_words: Counter[str] = Counter()
    joined_by_paper: Counter[str] = Counter()
    altered_total = 0
    stored_total = differs_total = 0

    for paper, name, body in rows:
        for match in SPLIT_WORD.finditer(body):
            joined_by_paper[paper] += 1
            if paper != "p3":
                joined_words[match.group(1).lower()] += 1
        for sentence in sentences(body):
            stored_total += 1
            pdf, squeezed, offsets = pdfs[name]
            spelled = as_in_pdf(sentence, pdf, squeezed, offsets)
            variants = {"exact": sentence}
            if spelled is not None and rule_a(spelled) != rule_a(sentence):
                differs_total += 1
                variants["as in the PDF, differs from stored"] = spelled
            for rule, normalize in RULES.items():
                haystack = normalize(body)
                for kind, quote in variants.items():
                    true_counts[f"{rule} | {kind}"] += normalize(quote) in haystack
            altered = alterations(sentence, rng)
            altered_total += len(altered)
            for kind, quote in altered.items():
                for rule, normalize in RULES.items():
                    if normalize(quote) in normalize(body):
                        false_counts[f"{rule} | {kind}"] += 1

    report = {
        "sentences": stored_total,
        "sentences_differing_from_pdf": differs_total,
        "alterations": altered_total,
        "true_quotes_accepted": dict(sorted(true_counts.items())),
        "altered_quotes_accepted": dict(sorted(false_counts.items())),
        "fi_fl_ff_then_space_by_paper": dict(sorted(joined_by_paper.items())),
        "words_joined_outside_p3": joined_words.most_common(15),
    }
    OUTPUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
