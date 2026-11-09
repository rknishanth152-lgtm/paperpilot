"""Assess the labelled papers and score them against the labels (R8; FR-EVL-006).

From the repository folder, with PostgreSQL running and the corpus ingested:

    uv run python -m tests.evaluation.score_assessment --pause 30

A manual real-model run: retrieved passages from the three labelled papers are
sent to the configured provider. Saves one new dated file with statuses and
counts, no paper text. Each run also adds new assessments, and earlier ones stay.
"""

import argparse
import json
import sys
import time
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TypeVar

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from tests.evaluation.claim_support import normalised_sha256
from tests.evaluation.code_state import REPO_ROOT, CodeState, code_state
from tests.evaluation.dataset import load_evaluation_set
from tests.evaluation.reproducibility_labels import (
    GUIDE,
    LABELS,
    PAPERS,
    Labels,
    check_labels,
)
from tests.evaluation.retrieval_harness import load_corpus

from app.config import get_settings
from app.database import get_sessionmaker
from app.models.constraints import REPRODUCIBILITY_STATUSES
from app.schemas.answer import MalformedAnswerError
from app.services.llm import ModelError, ModelUnavailableError
from app.services.llm_factory import build_language_model
from app.services.reproducibility.assessment import Assessor, assessment_limits
from app.services.reproducibility.checklist import CHECKLIST_VERSION
from app.services.reproducibility.records import AssessmentRecord, get_assessment
from app.services.retrieval.selection import build_retriever

RESULTS = REPO_ROOT / "benchmarks" / "results"
DEFAULT_PAUSE = 30.0
OUTAGE_RETRIES = 3
OUTAGE_WAIT = 60.0
_T = TypeVar("_T")
LIMITS = (
    "18 items from 3 papers, one labeller, one model. It shows agreement with that "
    "person on the text PaperPilot stored, not whether the papers can be reproduced, "
    "and is a coarse baseline (RISK-15)."
)
# Strength of what is claimed. `needs_review` claims nothing, so it is not ranked.
_STRENGTH = {"not_found": 0, "partially_reported": 1, "reported": 2}


@dataclass(frozen=True)
class Pair:
    paper: str
    item: str
    labelled: str
    assessed: str


def assess_with_retries(
    assess: Callable[[], _T],
    *,
    retries: int,
    wait: float,
    sleep: Callable[[float], None] = time.sleep,
) -> _T:
    """Retry only a brief provider outage. Anything else stops the run."""
    for _ in range(retries):
        try:
            return assess()
        except ModelUnavailableError:
            sleep(wait)
    return assess()


def _ratio(part: int, whole: int) -> float | None:
    return round(part / whole, 4) if whole else None


def score(pairs: Sequence[Pair]) -> dict[str, Any]:
    """Agreement overall, per status, and where the two disagree."""
    if not pairs:
        raise ValueError("there is nothing to score")
    labelled = Counter(pair.labelled for pair in pairs)
    assessed = Counter(pair.assessed for pair in pairs)
    agreed = Counter(pair.labelled for pair in pairs if pair.labelled == pair.assessed)
    confusion = {
        row: {
            column: sum(p.labelled == row and p.assessed == column for p in pairs)
            for column in REPRODUCIBILITY_STATUSES
        }
        for row in REPRODUCIBILITY_STATUSES
    }
    commonest = max(REPRODUCIBILITY_STATUSES, key=lambda status: labelled[status])
    ranked = [
        (_STRENGTH[p.labelled], _STRENGTH[p.assessed])
        for p in pairs
        if p.labelled in _STRENGTH and p.assessed in _STRENGTH
    ]
    return {
        "items": len(pairs),
        "agreements": sum(agreed.values()),
        "agreement_rate": _ratio(sum(agreed.values()), len(pairs)),
        "majority_baseline": {
            "label": commonest,
            "agreements": labelled[commonest],
            "rate": _ratio(labelled[commonest], len(pairs)),
        },
        "per_status": {
            status: {
                "labelled": labelled[status],
                "assessed": assessed[status],
                "agreed": agreed[status],
                "recall": _ratio(agreed[status], labelled[status]),
                "precision": _ratio(agreed[status], assessed[status]),
            }
            for status in REPRODUCIBILITY_STATUSES
        },
        "confusion": confusion,
        "not_found_vs_needs_review": {
            "labelled_not_found_assessed_needs_review": confusion["not_found"][
                "needs_review"
            ],
            "labelled_needs_review_assessed_not_found": confusion["needs_review"][
                "not_found"
            ],
            "measurable": labelled["not_found"] > 0 and labelled["needs_review"] > 0,
        },
        "overstated": sum(machine > human for human, machine in ranked),
        "understated": sum(machine < human for human, machine in ranked),
    }


def pairs_from(labels: Labels, assessed: Mapping[str, AssessmentRecord]) -> list[Pair]:
    """Each label beside the assessed status. A missing item is a KeyError."""
    by_item = {
        paper: {item.key: item.status for item in record.items}
        for paper, record in assessed.items()
    }
    return [
        Pair(label.paper, label.item, label.status, by_item[label.paper][label.item])
        for label in labels.labels
    ]


def score_record(
    pairs: Sequence[Pair],
    *,
    rows: Sequence[Mapping[str, Any]],
    labels_sha256: str,
    guide_sha256: str,
    checklist_version: str,
    model: str | None,
    prompt_version: str | None,
    retrieval_method: str | None,
    labeller: str,
    labelled_on: str,
    run_at: datetime,
    state: CodeState,
) -> dict[str, Any]:
    return {
        "kind": "manual real-model run, reproducibility checklist",
        "run_at": run_at.isoformat(),
        "code_revision": state.revision,
        "working_tree_clean": state.clean,
        "labels_sha256": labels_sha256,
        "guide_sha256": guide_sha256,
        "checklist_version": checklist_version,
        "model": model,
        "prompt_version": prompt_version,
        "retrieval_method": retrieval_method,
        "labeller": labeller,
        "labelled_on": labelled_on,
        "limits": LIMITS,
        "result": score(pairs),
        "items": list(rows),
    }


def write_score(record: Mapping[str, Any], directory: Path) -> Path:
    """Save to a new dated file. An existing result is never overwritten."""
    stamp = datetime.fromisoformat(record["run_at"]).strftime("%Y%m%dT%H%M%SZ")
    name = f"reproducibility-score-{stamp}-{record['code_revision'][:7]}.json"
    path = directory / name
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(record, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    return path


def _rows(
    pairs: Sequence[Pair], assessed: Mapping[str, AssessmentRecord]
) -> list[dict[str, Any]]:
    """Statuses and counts for each item. Holds no quotes or explanations."""
    details = {
        (paper, item.key): item
        for paper, record in assessed.items()
        for item in record.items
    }
    return [
        {
            "paper": pair.paper,
            "item": pair.item,
            "labelled": pair.labelled,
            "assessed": pair.assessed,
            "review_reason": details[(pair.paper, pair.item)].review_reason,
            "evidence_quotes": len(details[(pair.paper, pair.item)].evidence),
            "passages_examined": details[(pair.paper, pair.item)].passages_examined,
        }
        for pair in pairs
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pause", type=float, default=DEFAULT_PAUSE)
    options = parser.parse_args()

    labels = Labels.model_validate_json(LABELS.read_text(encoding="utf-8"))
    guide_hash = normalised_sha256(GUIDE)
    check_labels(labels, guide_sha256=guide_hash)
    state = code_state()
    settings = get_settings()
    sessions = get_sessionmaker()
    documents, _ = load_corpus(sessions, load_evaluation_set())
    assessor = Assessor(
        sessions,
        build_language_model(settings),
        assessment_limits(settings),
        build_retriever(settings, sessions),
    )
    assessed: dict[str, AssessmentRecord] = {}
    try:
        for index, paper in enumerate(PAPERS):
            if index:
                time.sleep(options.pause)
            document = documents[paper]
            assessment_id = assess_with_retries(
                lambda: assessor.assess(document),
                retries=OUTAGE_RETRIES,
                wait=OUTAGE_WAIT,
            )
            assessed[paper] = get_assessment(sessions, assessment_id)
            print(f"{paper} assessed", flush=True)
    except (ModelError, MalformedAnswerError) as error:
        print(f"Stopped: {error.code}. Nothing was scored.", file=sys.stderr)
        return 1

    pairs = pairs_from(labels, assessed)
    first = assessed[PAPERS[0]]
    record = score_record(
        pairs,
        rows=_rows(pairs, assessed),
        labels_sha256=normalised_sha256(LABELS),
        guide_sha256=guide_hash,
        checklist_version=CHECKLIST_VERSION,
        model=first.model,
        prompt_version=first.prompt_version,
        retrieval_method=first.retrieval_method,
        labeller=labels.labeller,
        labelled_on=labels.labelled_on.isoformat(),
        run_at=datetime.now(UTC),
        state=state,
    )
    path = write_score(record, RESULTS)
    print(json.dumps(record["result"], indent=2))
    print(f"Saved {path.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
