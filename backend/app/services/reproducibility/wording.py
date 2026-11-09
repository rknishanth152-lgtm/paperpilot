"""The words every client shows for a status (R7; FR-REP-004, RISK-12).

Kept on the server so no client can word `not_found` as a finding about the
paper. Statements here describe what was examined, never the work itself.
"""

_PLAIN: dict[str, tuple[str, str]] = {
    "reported": (
        "Reported",
        "The passages examined state this. A quote is shown as evidence.",
    ),
    "partially_reported": (
        "Partly reported",
        "The passages examined state part of this. A quote is shown as evidence.",
    ),
    "not_found": (
        "Not found in the material examined",
        (
            "The passages examined do not contain this. It does not mean the paper "
            "leaves it out, because tables, figures, supplements and other passages "
            "were not examined."
        ),
    ),
}

_REVIEW: dict[str, str] = {
    "parse_incomplete": (
        "This paper was not fully processed, so this item could not be checked."
    ),
    "evidence_unverified": (
        "The evidence could not be verified against the stored text, so no "
        "status is given. Check the paper directly."
    ),
    "model_uncertain": (
        "The passages examined did not settle this, or point to a table, figure "
        "or supplement. Check the paper directly."
    ),
}


def status_text(status: str, review_reason: str | None) -> tuple[str, str]:
    """(label, description) for a stored status."""
    if status == "needs_review" and review_reason is not None:
        return "Needs review", _REVIEW[review_reason]
    return _PLAIN[status]
