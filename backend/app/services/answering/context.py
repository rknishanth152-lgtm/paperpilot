"""The context given to the model (P5-T4; FR-QA-002, FR-QA-007, AD-007).

The user message is one JSON document holding the question and the labelled
passages. Paper text is therefore a JSON string value: quotes and newlines are
escaped, so text inside a passage cannot end its own field or add new ones.
Instructions live only in the system prompt, outside this data. This limits
prompt injection but is not a complete defence (RISK-08).

Passages are referred to by prompt-local aliases (`P1`, `P2`), mapped back in
code. Page numbers and database ids are not given to the model, so it has
nothing to repeat or invent from them.

Truncation: passages are taken in rank order and whole. At the first one that
does not fit, it and all later ones are dropped. Passages are never cut,
because a cited quote must exist in the stored text.
"""

import json
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from app.services.retrieval.keyword import RetrievedPassage


@dataclass(frozen=True)
class AnswerContext:
    user_message: str
    aliases: Mapping[str, RetrievedPassage]  # shown to the model
    dropped: Mapping[str, RetrievedPassage]  # retrieved, not shown

    @property
    def passages_dropped(self) -> int:
        return len(self.dropped)


def _serialized(entry: Mapping[str, Any]) -> str:
    return json.dumps(entry, ensure_ascii=False)


def build_context(
    question: str,
    passages: Sequence[RetrievedPassage],
    *,
    paper_titles: Mapping[uuid.UUID, str | None],
    max_chars: int,
) -> AnswerContext:
    """The message for `passages`, best first. `max_chars` bounds the passages."""
    if max_chars < 1:
        raise ValueError("max_chars must be positive")

    aliases: dict[str, RetrievedPassage] = {}
    dropped: dict[str, RetrievedPassage] = {}
    entries: list[dict[str, Any]] = []
    paper_numbers: dict[uuid.UUID, int] = {}
    used = 0

    for position, passage in enumerate(passages, 1):
        alias = f"P{position}"
        if dropped:
            dropped[alias] = passage
            continue
        number = paper_numbers.get(passage.paper_id, len(paper_numbers) + 1)
        entry = {
            "alias": alias,
            "paper": f"Paper {number}",
            "paper_title": paper_titles.get(passage.paper_id),
            "section": passage.section,
            "text": passage.text,
        }
        size = len(_serialized(entry))
        if used + size > max_chars:
            dropped[alias] = passage
            continue
        used += size
        paper_numbers[passage.paper_id] = number
        aliases[alias] = passage
        entries.append(entry)

    return AnswerContext(
        user_message=_serialized({"question": question, "passages": entries}),
        aliases=aliases,
        dropped=dropped,
    )
