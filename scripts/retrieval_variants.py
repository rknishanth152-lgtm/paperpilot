"""Phase 4 exploratory script (P4-T7): compare search settings on the fixed evaluation set.

Not application code, and not the evaluation harness: its figures are exploratory
comparisons and are never reported as metrics. Read-only. Needs a baseline result
in benchmarks/results/. Run from the repository root:

    uv run python scripts/retrieval_variants.py

Writes benchmarks/results/variants-<time>-<revision>.json.
"""

import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from sqlalchemy import text

from app.database import get_engine

RESULTS = REPO_ROOT / "benchmarks" / "results"
BASELINE = "retrieval-20261108T173245Z-368fd83.json"

OR_QUERY = "replace(plainto_tsquery('english', :q)::text, ' & ', ' | ')::tsquery"
AND_QUERY = "plainto_tsquery('english', :q)"
STORED = "p.search_vector"
REPAIR = r"regexp_replace({}, '(fi|fl|ff) (?=[a-z])', '\1', 'g')"
REPAIRED = f"to_tsvector('english', {REPAIR.format('p.text')})"
WITH_SECTION = "to_tsvector('english', coalesce(p.section_title, '') || ' ' || p.text)"
REPAIRED_QUERY = OR_QUERY.replace(":q", REPAIR.format(":q"))

# name: (vector, query, ranking)
VARIANTS = {
    "baseline: ts_rank, words ORed": (STORED, OR_QUERY, "ts_rank(v, q)"),
    "words ANDed": (STORED, AND_QUERY, "ts_rank(v, q)"),
    "ts_rank_cd": (STORED, OR_QUERY, "ts_rank_cd(v, q)"),
    "ts_rank, normalisation 1": (STORED, OR_QUERY, "ts_rank(v, q, 1)"),
    "ts_rank, normalisation 2": (STORED, OR_QUERY, "ts_rank(v, q, 2)"),
    "ts_rank_cd, normalisation 1": (STORED, OR_QUERY, "ts_rank_cd(v, q, 1)"),
    "split-ligature repair": (REPAIRED, REPAIRED_QUERY, "ts_rank(v, q)"),
    "section title in the vector": (WITH_SECTION, OR_QUERY, "ts_rank(v, q)"),
}


def git(*arguments: str) -> str:
    return subprocess.run(
        ["git", *arguments],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def main() -> None:
    baseline: dict[str, Any] = json.loads(
        (RESULTS / BASELINE).read_text(encoding="utf-8")
    )
    evaluation: dict[str, Any] = json.loads(
        (REPO_ROOT / "benchmarks" / "retrieval_eval_v1.json").read_text(
            encoding="utf-8"
        )
    )
    questions = {q["id"]: q for q in evaluation["questions"]}
    rows = [row for row in baseline["questions"] if row["answerable"]]
    output: list[dict[str, Any]] = []
    reference: dict[str, bool] | None = None

    with get_engine().connect() as connection:
        documents = {
            row[0]: row[1]
            for row in connection.execute(
                text("SELECT left(original_filename, 2), id::text FROM documents")
            )
        }
        for name, (vector, query, ranking) in VARIANTS.items():
            statement = text(
                f"WITH t AS (SELECT p.id::text i, p.document_id::text d, {vector} v, "
                f"{query} q FROM passages p) "
                f"SELECT i, d FROM t WHERE v @@ q ORDER BY {ranking} DESC, i"
            )
            hits: dict[str, bool] = {}
            own_paper = 0
            for row in rows:
                question = questions[row["id"]]
                expected = set(row["expected_passage_ids"])
                ranked = connection.execute(
                    statement, {"q": question["question"]}
                ).all()
                paper = documents[question["papers"][0]]
                hits[row["id"]] = bool(expected & {r[0] for r in ranked[:5]})
                own = [r[0] for r in ranked if r[1] == paper][:5]
                own_paper += bool(expected & set(own))
            reference = reference or hits
            output.append(
                {
                    "variant": name,
                    "hits_all_papers": sum(hits.values()),
                    "hits_question_paper": own_paper,
                    "evaluated": len(rows),
                    "gained": [k for k in hits if hits[k] and not reference[k]],
                    "lost": [k for k in hits if reference[k] and not hits[k]],
                }
            )

    now = datetime.now(UTC)
    revision = git("rev-parse", "HEAD")
    record = {
        "kind": "exploratory comparison, not an evaluation metric",
        "run_at": now.isoformat(),
        "code_revision": revision,
        "working_tree_clean": git("status", "--porcelain") == "",
        "baseline_result": BASELINE,
        "variants": output,
    }
    path = RESULTS / f"variants-{now:%Y%m%dT%H%M%SZ}-{revision[:7]}.json"
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(record, handle, indent=2)
        handle.write("\n")
    print(f"Saved {path.relative_to(REPO_ROOT)}")
    for item in output:
        print(item)


if __name__ == "__main__":
    main()
