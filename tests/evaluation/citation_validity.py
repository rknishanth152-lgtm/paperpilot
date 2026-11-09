"""The citation reference-validity rate over saved answers (P6-T2, FR-EVL-003).

From the repository folder, on a result saved by the answer evaluation:

    uv run python -m tests.evaluation.citation_validity benchmarks/results/answers-X.json

Reads only that file, calls no model, and saves a new dated file in
benchmarks/results/.
"""

import argparse
import hashlib
import json
import sys
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, get_args

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from tests.evaluation.code_state import CodeState, code_state

from app.services.answering.citations import CitationFailure

RESULTS = REPO_ROOT / "benchmarks" / "results"
SCOPE = (
    "Structural correctness only: each valid citation points to a real, in-scope "
    "passage containing any quote. This does not show that a passage supports a "
    "statement (AD-008). Answers without statements are excluded from the answer "
    "rate because they pass validation automatically."
)


def _rate(part: int, whole: int) -> float | None:
    """`None` when there is nothing to measure: 0 and 100% would both mislead."""
    return round(part / whole, 4) if whole else None


def _reason(citation: Mapping[str, Any]) -> str | None:
    """The failure reason, after refusing a citation that contradicts itself."""
    reason: str | None = citation["reason"]
    if citation["valid"] != (reason is None):
        raise ValueError(f"citation is inconsistent: valid and reason {reason!r}")
    if reason is not None and reason not in get_args(CitationFailure):
        raise ValueError(f"citation has an unknown failure reason: {reason!r}")
    return reason


def citation_validity(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Counted per citation and per answer, as the PRD allows either (§ metrics)."""
    reasons = dict.fromkeys(get_args(CitationFailure), 0)
    valid = total = uncited = 0
    produced = [row for row in rows if row["error"] is None]
    stated = [row for row in produced if row["statements"]]
    for row in stated:
        for statement in row["statements"]:
            uncited += not statement["citations"]
            for citation in statement["citations"]:
                total += 1
                reason = _reason(citation)
                if reason is None:
                    valid += 1
                else:
                    reasons[reason] += 1
    validated = sum(row["validation_status"] == "validated" for row in stated)
    return {
        "citations": {"valid": valid, "total": total, "rate": _rate(valid, total)},
        "failure_reasons": reasons,
        "uncited_statements": uncited,
        "answers_with_statements": {
            "validated": validated,
            "total": len(stated),
            "rate": _rate(validated, len(stated)),
        },
        "answers_without_statements": len(produced) - len(stated),
        "answers_not_produced": len(rows) - len(produced),
    }


def validity_record(
    *,
    source: Mapping[str, Any],
    source_name: str,
    source_sha256: str,
    state: CodeState,
    run_at: datetime,
) -> dict[str, Any]:
    return {
        "kind": "citation reference validity",
        "run_at": run_at.isoformat(),
        "code_revision": state.revision,
        "working_tree_clean": state.clean,
        "scope": SCOPE,
        "source": {
            "file": source_name,
            "sha256": source_sha256,
            "model": source["requested_model"],
            "prompt_version": source["prompt_version"],
            "code_revision": source["code_revision"],
            "working_tree_clean": source["working_tree_clean"],
            "stopped_early": source["stopped_early"],
            "answers": len(source["questions"]),
        },
        "result": citation_validity(source["questions"]),
    }


def write_validity(record: Mapping[str, Any], directory: Path) -> Path:
    """Save to a new dated file. An existing result is never overwritten."""
    stamp = datetime.fromisoformat(record["run_at"]).strftime("%Y%m%dT%H%M%SZ")
    name = f"{stamp}-{record['code_revision'][:7]}-{record['source']['sha256'][:8]}"
    path = directory / f"citation-validity-{name}.json"
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(record, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("answers", type=Path, help="a saved answer result file")
    options = parser.parse_args()

    raw = options.answers.read_bytes()
    record = validity_record(
        source=json.loads(raw),
        source_name=options.answers.name,
        source_sha256=hashlib.sha256(raw).hexdigest(),
        state=code_state(),
        run_at=datetime.now(UTC),
    )
    path = write_validity(record, RESULTS)
    print(json.dumps(record["result"], indent=2))
    print(f"Saved {path.name}")


if __name__ == "__main__":
    main()
