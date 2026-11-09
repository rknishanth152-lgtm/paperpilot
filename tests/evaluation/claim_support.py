"""Human labels for claim support (P6-T3, FR-EVL-004, AD-008).

From the repository folder, with PostgreSQL running and the corpus ingested:

    uv run python -m tests.evaluation.claim_support draw benchmarks/results/answers-X.json
    uv run python -m tests.evaluation.claim_support sheet
    uv run python -m tests.evaluation.claim_support report

`draw` fixes the sample and writes a labelling sheet to the git-ignored data/
folder, because the sheet holds passage text. `sheet` writes that page again from
the fixed sample. `report` checks the labels against
the sample and guide, then saves a new dated result. Neither calls a model.
"""

import argparse
import hashlib
import html
import json
import random
import sys
import uuid
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Annotated, Any, Literal, get_args

from pydantic import BaseModel, ConfigDict, StringConstraints

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker
from tests.evaluation.code_state import CodeState, code_state

from app.database import get_sessionmaker
from app.models import Passage

BENCHMARKS = REPO_ROOT / "benchmarks"
RESULTS = BENCHMARKS / "results"
GUIDE = BENCHMARKS / "claim_support_guide_v1.md"
SAMPLE = BENCHMARKS / "claim_support_sample_v1.json"
LABELS = BENCHMARKS / "claim_support_labels_v1.json"
SHEET = REPO_ROOT / "data" / "labelling" / "claim-support-sheet.html"
SEED = 20261109
DEFAULT_LABELLER = "rknishanth152-lgtm"
LIMITS = (
    "Small sample: one run of one model, labelled by one labeller, who had already "
    "read notes on q06, q12 and q19. It shows agreement with that person, not "
    "scientific truth, and is a coarse baseline (RISK-15)."
)

ClaimSupport = Literal["supported", "partly_supported", "not_supported", "cannot_judge"]
AnswersQuestion = Literal["yes", "partly", "no", "cannot_judge"]
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class SampleCitation(_Strict):
    alias: str
    quote: str | None
    passage_id: uuid.UUID


class SampleItem(_Strict):
    item: str
    question_id: str
    statement_index: int
    question: str
    statement: str
    citations: tuple[SampleCitation, ...]


class Sample(_Strict):
    version: int
    seed: int
    guide_sha256: str
    source: dict[str, Any]
    statements_in_source: int
    items: tuple[SampleItem, ...]


class Label(_Strict):
    item: str
    claim_support: ClaimSupport
    answers_question: AnswersQuestion


class Labels(_Strict):
    labeller: Name
    labelled_on: date
    guide_sha256: str
    labels: tuple[Label, ...]


@dataclass(frozen=True)
class ShownPassage:
    text: str
    section: str | None
    page: int | None


def normalised_sha256(path: Path) -> str:
    """A text file's hash, the same whichever line endings git has given it."""
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def write_new(content: Mapping[str, Any], path: Path) -> None:
    """Write JSON to a new file. An existing file is never replaced."""
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(content, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def _item_citations(
    row: Mapping[str, Any], statement: Any
) -> tuple[SampleCitation, ...]:
    citations = []
    for citation in statement["citations"]:
        if citation["passage_id"] is None:
            raise ValueError(f"{row['id']}: a citation has no passage to show")
        citations.append(
            SampleCitation(
                alias=citation["alias"],
                quote=citation["quote"],
                passage_id=citation["passage_id"],
            )
        )
    return tuple(citations)


def draw_items(
    rows: Sequence[Mapping[str, Any]], *, seed: int
) -> tuple[SampleItem, ...]:
    """Every statement in the run, in a shuffled order fixed by the seed."""
    found = [
        (row, index, statement)
        for row in rows
        for index, statement in enumerate(row.get("statements", []))
    ]
    random.Random(seed).shuffle(found)
    return tuple(
        SampleItem(
            item=f"S{number:02d}",
            question_id=row["id"],
            statement_index=index,
            question=row["question"],
            statement=statement["text"],
            citations=_item_citations(row, statement),
        )
        for number, (row, index, statement) in enumerate(found, start=1)
    )


def load_passages(
    sessions: sessionmaker[Session], passage_ids: Iterable[uuid.UUID]
) -> dict[uuid.UUID, ShownPassage]:
    wanted = set(passage_ids)
    with sessions() as session:
        rows = session.execute(
            select(
                Passage.id, Passage.text, Passage.section_path, Passage.page_start
            ).where(Passage.id.in_(wanted))
        ).all()
    found = {
        row.id: ShownPassage(row.text, row.section_path, row.page_start) for row in rows
    }
    missing = wanted - set(found)
    if missing:
        raise LookupError(f"passages not found: {sorted(map(str, missing))}")
    return found


_STYLE = """
:root { --bg:#f6f7f9; --surface:#fff; --ink:#1c2430; --muted:#5b6675; --line:#dbe0e7; --accent:#1f3a68; }
* { box-sizing:border-box; }
body { margin:0; background:var(--bg); color:var(--ink); font:16px/1.55 system-ui,sans-serif; }
main { max-width:780px; margin:0 auto; padding:24px 16px 64px; }
h1 { font-size:1.5rem; margin:0 0 8px; }
.item { background:var(--surface); border:1px solid var(--line); border-radius:8px; padding:20px; margin:16px 0; }
.id, .where { color:var(--muted); font-size:.875rem; }
.statement { font-weight:600; font-size:1.0625rem; }
blockquote { margin:8px 0 16px; padding:12px 16px; background:var(--bg); border-left:3px solid var(--line); }
fieldset { border:0; padding:0; margin:12px 0 0; }
legend { font-weight:600; padding:0; }
label { display:block; padding:3px 0; }
.finish { background:var(--surface); border:1px solid var(--line); border-radius:8px; padding:16px; }
.who input { font:inherit; padding:6px 8px; border:1px solid var(--line); border-radius:6px; margin-right:12px; }
textarea { width:100%; height:72px; font:12px/1.4 monospace; margin-top:8px; }
button { font:inherit; color:#fff; background:var(--accent); border:0; border-radius:6px; padding:8px 16px; cursor:pointer; }
button:disabled { opacity:.5; cursor:not-allowed; }
"""

_SCRIPT = """
const ITEMS = __ITEMS__;
const GUIDE = "__GUIDE__";
const output = document.getElementById("output");
const status = document.getElementById("status");
const copy = document.getElementById("copy");
const read = (name) => {
  const chosen = document.querySelector(`input[name="${name}"]:checked`);
  return chosen ? chosen.value : null;
};
function update() {
  const labels = [];
  let missing = 0;
  for (const item of ITEMS) {
    const claim = read(`${item}-claim_support`);
    const answer = read(`${item}-answers_question`);
    if (claim && answer) {
      labels.push({ item, claim_support: claim, answers_question: answer });
    } else {
      missing += 1;
    }
  }
  const labeller = document.getElementById("labeller").value.trim();
  const on = document.getElementById("labelled_on").value;
  const done = missing === 0 && labeller && on;
  status.textContent = missing
    ? `${missing} of ${ITEMS.length} statements still need both labels.`
    : done ? "All labelled. Copy the text below into the chat." : "Enter your name and the date.";
  output.value = done
    ? JSON.stringify({ labeller, labelled_on: on, guide_sha256: GUIDE, labels })
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

_CLAIM_TEXT: dict[str, str] = {
    "supported": "Supported",
    "partly_supported": "Partly supported",
    "not_supported": "Not supported",
    "cannot_judge": "Cannot judge",
}
_ANSWER_TEXT: dict[str, str] = {
    "yes": "Yes",
    "partly": "Partly",
    "no": "No",
    "cannot_judge": "Cannot judge",
}


def _options(name: str, legend: str, values: Mapping[str, str]) -> str:
    choices = "".join(
        f'<label><input type="radio" name="{name}" value="{value}"> {text}</label>'
        for value, text in values.items()
    )
    return f"<fieldset><legend>{legend}</legend>{choices}</fieldset>"


def _passage(passage: ShownPassage) -> str:
    section = html.escape(passage.section) if passage.section else "section unknown"
    page = f"page {passage.page}" if passage.page is not None else "page unknown"
    return (
        f'<p class="where">{section}, {page}</p>'
        f"<blockquote>{html.escape(passage.text)}</blockquote>"
    )


def _card(item: SampleItem, passages: Mapping[uuid.UUID, ShownPassage]) -> str:
    shown = "".join(_passage(passages[c.passage_id]) for c in item.citations)
    claim = _options(
        f"{item.item}-claim_support",
        "1. Does the cited evidence support the statement?",
        _CLAIM_TEXT,
    )
    answer = _options(
        f"{item.item}-answers_question",
        "2. Does the statement answer the question?",
        _ANSWER_TEXT,
    )
    return (
        f'<section class="item"><p class="id">{item.item}</p>'
        f"<p>Question: {html.escape(item.question)}</p>"
        f'<p class="statement">{html.escape(item.statement)}</p>'
        f"{shown}{claim}{answer}</section>"
    )


def render_sheet(
    sample: Sample, passages: Mapping[uuid.UUID, ShownPassage], *, today: date
) -> str:
    """One page. Every paper-derived value is escaped; paper text is untrusted."""
    cards = "".join(_card(item, passages) for item in sample.items)
    script = _SCRIPT.replace(
        "__ITEMS__", json.dumps([item.item for item in sample.items])
    ).replace("__GUIDE__", sample.guide_sha256)
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>Claim-support labels</title><style>{_STYLE}</style></head><body><main>"
        "<h1>Claim-support labels</h1>"
        "<p>Use only the passage text shown. Read "
        "<code>benchmarks/claim_support_guide_v1.md</code> first. Give the two labels "
        "separately. Small extraction glitches, such as a word broken in two, are not "
        "a reason for a lower label.</p>"
        f"{cards}"
        '<div class="finish"><p class="who">'
        f'<label>Labeller <input id="labeller" value="{DEFAULT_LABELLER}"></label> '
        f'<label>Date <input id="labelled_on" type="date" value="{today.isoformat()}">'
        "</label></p>"
        '<p id="status" role="status"></p>'
        '<button id="copy" type="button">Copy labels</button>'
        '<textarea id="output" readonly aria-label="Labels to copy"></textarea></div>'
        f"</main><script>{script}</script></body></html>"
    )


def check_labels(sample: Sample, labels: Labels, *, guide_sha256: str) -> None:
    """Refuse labels that do not cover this sample under this guide, exactly."""
    if labels.guide_sha256 != guide_sha256 or sample.guide_sha256 != guide_sha256:
        raise ValueError("the guide changed since the sample or labels were made")
    given = Counter(label.item for label in labels.labels)
    expected = {item.item for item in sample.items}
    repeated = sorted(name for name, count in given.items() if count > 1)
    missing = sorted(expected - set(given))
    unknown = sorted(set(given) - expected)
    if repeated or missing or unknown:
        raise ValueError(
            f"labels do not match the sample: repeated {repeated}, "
            f"missing {missing}, unknown {unknown}"
        )


def _measure(
    values: Sequence[str], options: tuple[str, ...], counted: str
) -> dict[str, Any]:
    counts = Counter(values)
    return {
        "counts": {option: counts[option] for option in options},
        "rate": round(counts[counted] / len(values), 4) if values else None,
    }


def claim_support_result(sample: Sample, labels: Labels) -> dict[str, Any]:
    """Claim support is supported ÷ all labelled, so cannot-judge stays in."""
    return {
        "sample_size": len(sample.items),
        "claim_support": _measure(
            [label.claim_support for label in labels.labels],
            get_args(ClaimSupport),
            "supported",
        ),
        "answers_question": _measure(
            [label.answers_question for label in labels.labels],
            get_args(AnswersQuestion),
            "yes",
        ),
        "supported_but_not_fully_answering": sum(
            label.claim_support == "supported"
            and label.answers_question in ("partly", "no")
            for label in labels.labels
        ),
    }


def claim_support_record(
    *,
    sample: Sample,
    labels: Labels,
    sample_sha256: str,
    labels_sha256: str,
    state: CodeState,
    run_at: datetime,
) -> dict[str, Any]:
    return {
        "kind": "claim support, human labels",
        "run_at": run_at.isoformat(),
        "code_revision": state.revision,
        "working_tree_clean": state.clean,
        "labeller": labels.labeller,
        "labelled_on": labels.labelled_on.isoformat(),
        "sample_size": len(sample.items),
        "seed": sample.seed,
        "guide_sha256": sample.guide_sha256,
        "sample_sha256": sample_sha256,
        "labels_sha256": labels_sha256,
        "source": sample.source,
        "limits": LIMITS,
        "result": claim_support_result(sample, labels),
    }


def draw(answers: Path) -> None:
    source = json.loads(answers.read_bytes())
    items = draw_items(source["questions"], seed=SEED)
    sample = Sample(
        version=1,
        seed=SEED,
        guide_sha256=normalised_sha256(GUIDE),
        source={
            "file": answers.name,
            "sha256": normalised_sha256(answers),
            "model": source["requested_model"],
            "prompt_version": source["prompt_version"],
            "code_revision": source["code_revision"],
        },
        statements_in_source=len(items),
        items=items,
    )
    page = _sheet_page(sample)
    write_new(sample.model_dump(mode="json"), SAMPLE)
    _save_sheet(page)
    print(f"Sample: {len(items)} statements. Sheet: {SHEET}")


def _sheet_page(sample: Sample) -> str:
    passages = load_passages(
        get_sessionmaker(),
        (c.passage_id for item in sample.items for c in item.citations),
    )
    return render_sheet(sample, passages, today=datetime.now(UTC).date())


def _save_sheet(page: str) -> None:
    SHEET.parent.mkdir(parents=True, exist_ok=True)
    SHEET.write_text(page, encoding="utf-8")


def sheet() -> None:
    """Render the page again from the fixed sample, which stays unchanged."""
    sample = Sample.model_validate_json(SAMPLE.read_text(encoding="utf-8"))
    _save_sheet(_sheet_page(sample))
    print(f"Sheet: {SHEET}")


def report() -> None:
    sample = Sample.model_validate_json(SAMPLE.read_text(encoding="utf-8"))
    labels = Labels.model_validate_json(LABELS.read_text(encoding="utf-8"))
    check_labels(sample, labels, guide_sha256=normalised_sha256(GUIDE))
    state = code_state()
    now = datetime.now(UTC)
    record = claim_support_record(
        sample=sample,
        labels=labels,
        sample_sha256=normalised_sha256(SAMPLE),
        labels_sha256=normalised_sha256(LABELS),
        state=state,
        run_at=now,
    )
    path = RESULTS / f"claim-support-{now:%Y%m%dT%H%M%SZ}-{state.revision[:7]}.json"
    write_new(record, path)
    print(json.dumps(record["result"], indent=2))
    print(f"Saved {path.name}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("draw").add_argument("answers", type=Path)
    commands.add_parser("sheet")
    commands.add_parser("report")
    options = parser.parse_args()
    if options.command == "draw":
        draw(options.answers)
    elif options.command == "sheet":
        sheet()
    else:
        report()


if __name__ == "__main__":
    main()
