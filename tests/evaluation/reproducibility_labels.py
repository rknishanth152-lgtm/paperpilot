"""The labelling sheet for the reproducibility checklist (R5; FR-EVL-006).

From the repository folder, with PostgreSQL running and the corpus ingested:

    uv run python -m tests.evaluation.reproducibility_labels sheet

Writes a page to the git-ignored data/ folder, because it holds paper text. The
labels must be given before any model assesses these papers, so they stay
independent of it. Scoring is added once assessments exist (R8).
"""

import argparse
import html
import json
import sys
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Literal

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker
from tests.evaluation.claim_support import Name, ShownPassage, normalised_sha256
from tests.evaluation.code_state import REPO_ROOT
from tests.evaluation.dataset import load_evaluation_set
from tests.evaluation.retrieval_harness import load_corpus

from app.database import get_sessionmaker
from app.models import Passage
from app.services.reproducibility.checklist import (
    CHECKLIST,
    CHECKLIST_VERSION,
    ChecklistItem,
)

GUIDE = REPO_ROOT / "benchmarks" / "reproducibility_guide_v1.md"
LABELS = REPO_ROOT / "benchmarks" / "reproducibility_labels_v1.json"
SHEET = REPO_ROOT / "data" / "labelling" / "reproducibility-sheet.html"
DEFAULT_LABELLER = "RK Nishanth"
PAPERS: tuple[str, ...] = ("p1", "p4", "p5")

Status = Literal["reported", "partially_reported", "not_found", "needs_review"]
PaperKey = Literal["p1", "p4", "p5"]
_STATUS_TEXT: dict[str, str] = {
    "reported": "Reported",
    "partially_reported": "Partly reported",
    "not_found": "Not found in the text shown",
    "needs_review": "Needs review",
}


class Label(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    paper: PaperKey
    item: str
    status: Status


class Labels(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    labeller: Name
    labelled_on: date
    guide_sha256: str
    checklist_version: str
    labels: tuple[Label, ...]


@dataclass(frozen=True)
class ShownPaper:
    key: str
    title: str
    passages: tuple[ShownPassage, ...]


def check_labels(labels: Labels, *, guide_sha256: str) -> None:
    """Refuse labels that do not cover exactly these papers and items."""
    if labels.guide_sha256 != guide_sha256:
        raise ValueError("the guide changed since the labels were made")
    if labels.checklist_version != CHECKLIST_VERSION:
        raise ValueError("the labels are for another checklist version")
    seen = [(label.paper, label.item) for label in labels.labels]
    expected = {(paper, item.key) for paper in PAPERS for item in CHECKLIST}
    repeated = sorted({pair for pair in seen if seen.count(pair) > 1})
    missing = sorted(expected - set(seen))
    unknown = sorted(set(seen) - expected)
    if repeated or missing or unknown:
        raise ValueError(
            f"labels do not cover the sheet: repeated {repeated}, "
            f"missing {missing}, unknown {unknown}"
        )


def load_paper(
    sessions: sessionmaker[Session], key: str, title: str, document: uuid.UUID
) -> ShownPaper:
    with sessions() as session:
        rows = session.execute(
            select(Passage.text, Passage.section_path, Passage.page_start)
            .where(Passage.document_id == document)
            .order_by(Passage.ordinal)
        ).all()
    return ShownPaper(
        key,
        title,
        tuple(ShownPassage(r.text, r.section_path, r.page_start) for r in rows),
    )


_STYLE = """
:root { --bg:#f6f7f9; --surface:#fff; --ink:#1c2430; --muted:#5b6675; --line:#dbe0e7; --accent:#1f3a68; }
* { box-sizing:border-box; }
body { margin:0; background:var(--bg); color:var(--ink); font:16px/1.55 system-ui,sans-serif; }
main { max-width:1280px; margin:0 auto; padding:24px 16px 64px; }
h1 { font-size:1.5rem; margin:0 0 8px; }
h2 { font-size:1.25rem; margin:32px 0 12px; }
code { overflow-wrap:anywhere; }
.paper { display:grid; gap:16px; grid-template-columns:minmax(0,1fr); }
@media (min-width:960px) { .paper { grid-template-columns:minmax(0,3fr) minmax(0,2fr); } }
.text { background:var(--surface); border:1px solid var(--line); border-radius:8px; padding:16px; max-height:85vh; overflow-y:auto; }
.where { color:var(--muted); font-size:.875rem; margin:12px 0 2px; }
.text p.body { margin:0; }
.items { display:grid; gap:12px; align-content:start; }
.item { background:var(--surface); border:1px solid var(--line); border-radius:8px; padding:16px; }
.item h3 { font-size:1rem; margin:0 0 4px; }
.def { color:var(--muted); font-size:.9rem; margin:4px 0; }
fieldset { border:0; padding:0; margin:8px 0 0; }
legend { position:absolute; width:1px; height:1px; overflow:hidden; clip-path:inset(50%); }
label { display:block; padding:2px 0; }
.finish { background:var(--surface); border:1px solid var(--line); border-radius:8px; padding:16px; margin-top:32px; }
.who input { font:inherit; padding:6px 8px; border:1px solid var(--line); border-radius:6px; margin-right:12px; }
textarea { width:100%; height:72px; font:12px/1.4 monospace; margin-top:8px; }
button { font:inherit; color:#fff; background:var(--accent); border:0; border-radius:6px; padding:8px 16px; cursor:pointer; }
button:disabled { opacity:.5; cursor:not-allowed; }
"""

_SCRIPT = """
const PAIRS = __PAIRS__;
const GUIDE = "__GUIDE__";
const CHECKLIST = "__CHECKLIST__";
const output = document.getElementById("output");
const status = document.getElementById("status");
const copy = document.getElementById("copy");
function update() {
  const labels = [];
  let missing = 0;
  for (const [paper, item] of PAIRS) {
    const chosen = document.querySelector(`input[name="${paper}-${item}"]:checked`);
    if (chosen) labels.push({ paper, item, status: chosen.value });
    else missing += 1;
  }
  const labeller = document.getElementById("labeller").value.trim();
  const on = document.getElementById("labelled_on").value;
  const done = missing === 0 && labeller && on;
  status.textContent = missing
    ? `${missing} of ${PAIRS.length} items still need a status.`
    : done ? "All labelled. Copy the text below into the chat." : "Enter your name and the date.";
  output.value = done
    ? JSON.stringify({ labeller, labelled_on: on, guide_sha256: GUIDE, checklist_version: CHECKLIST, labels })
    : "";
  copy.disabled = !done;
}
copy.addEventListener("click", async () => {
  output.select();
  try {
    await navigator.clipboard.writeText(output.value);
    status.textContent = "Copied. Paste it into the chat.";
  } catch {
    status.textContent = "The text is selected. Press Ctrl+C to copy it.";
  }
});
document.addEventListener("input", update);
update();
"""


def _passage(passage: ShownPassage) -> str:
    section = html.escape(passage.section) if passage.section else "section unknown"
    page = f"page {passage.page}" if passage.page is not None else "page unknown"
    return (
        f'<p class="where">{section}, {page}</p>'
        f'<p class="body">{html.escape(passage.text)}</p>'
    )


def _item(paper: str, item: ChecklistItem) -> str:
    name = f"{paper}-{item.key}"
    choices = "".join(
        f'<label><input type="radio" name="{name}" value="{value}"> {text}</label>'
        for value, text in _STATUS_TEXT.items()
    )
    return (
        f'<section class="item"><h3>{html.escape(item.title)}</h3>'
        f"<p>{html.escape(item.question)}</p>"
        f'<p class="def"><strong>Reported:</strong> {html.escape(item.reported)}</p>'
        f'<p class="def"><strong>Partly:</strong> '
        f"{html.escape(item.partially_reported)}</p>"
        f"<fieldset><legend>Status</legend>{choices}</fieldset></section>"
    )


def _paper(paper: ShownPaper) -> str:
    text = "".join(_passage(passage) for passage in paper.passages)
    items = "".join(_item(paper.key, item) for item in CHECKLIST)
    return (
        f"<h2>{html.escape(paper.key)}: {html.escape(paper.title)}</h2>"
        f'<div class="paper"><div class="text" tabindex="0">{text}</div>'
        f'<div class="items">{items}</div></div>'
    )


def render_sheet(
    papers: Sequence[ShownPaper], *, guide_sha256: str, today: date
) -> str:
    """One page. Every paper-derived value is escaped; paper text is untrusted."""
    pairs = [[paper.key, item.key] for paper in papers for item in CHECKLIST]
    script = (
        _SCRIPT.replace("__PAIRS__", json.dumps(pairs))
        .replace("__GUIDE__", guide_sha256)
        .replace("__CHECKLIST__", CHECKLIST_VERSION)
    )
    body = "".join(_paper(paper) for paper in papers)
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>Reproducibility labels</title><style>{_STYLE}</style></head><body><main>"
        "<h1>Reproducibility labels</h1>"
        "<p>Read <code>benchmarks/reproducibility_guide_v1.md</code> first. Use only the "
        "text shown, and no AI tool. Your browser's find (Ctrl+F) helps in the longer "
        "paper. <strong>Not found</strong> means not found in the text shown. It is not a "
        "judgement about the paper.</p>"
        f"{body}"
        '<div class="finish"><p class="who">'
        f'<label>Labeller <input id="labeller" value="{DEFAULT_LABELLER}"></label> '
        f'<label>Date <input id="labelled_on" type="date" value="{today.isoformat()}">'
        "</label></p>"
        '<p id="status" role="status"></p>'
        '<button id="copy" type="button">Copy labels</button>'
        '<textarea id="output" readonly aria-label="Labels to copy"></textarea></div>'
        f"</main><script>{script}</script></body></html>"
    )


def sheet() -> None:
    evaluation = load_evaluation_set()
    sessions = get_sessionmaker()
    documents, _ = load_corpus(sessions, evaluation)
    titles = {paper.key: paper.title for paper in evaluation.corpus}
    papers = [load_paper(sessions, key, titles[key], documents[key]) for key in PAPERS]
    page = render_sheet(
        papers,
        guide_sha256=normalised_sha256(GUIDE),
        today=datetime.now(UTC).date(),
    )
    SHEET.parent.mkdir(parents=True, exist_ok=True)
    SHEET.write_text(page, encoding="utf-8")
    print(f"Sheet: {SHEET}")
    print(f"Items to label: {len(PAPERS) * len(CHECKLIST)}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("sheet")
    parser.parse_args()
    sheet()


if __name__ == "__main__":
    main()
