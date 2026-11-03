"""DOI normalisation (P2-T4).

Used to recognise the same paper across uploads (PRD §8.3, FR-ING-008) and,
later, across discovery results (FR-DIS-002). A pure function: no I/O.
"""

import re

# Resolver prefixes and the "doi:" label, compared case-insensitively.
_PREFIX = re.compile(r"^(?:(?:https?://)?(?:dx\.)?doi\.org/|doi:\s*)", re.IGNORECASE)

# Crossref's recommended pattern for modern DOIs: "10." + registrant code of
# 4-9 digits + "/" + a suffix without whitespace.
_DOI = re.compile(r"^10\.\d{4,9}/\S+$")


def normalize_doi(raw: str | None) -> str | None:
    """Return the DOI in canonical form, or None if `raw` is not a DOI.

    Canonical form: surrounding whitespace removed, one resolver prefix or
    "doi:" label removed, lower-cased (DOIs are case-insensitive). Values that
    do not look like a DOI give None, never a guess (FR-ING-006). Trailing
    punctuation is kept because it can be part of a real DOI.
    """
    if raw is None:
        return None
    candidate = _PREFIX.sub("", raw.strip(), count=1).lower()
    return candidate if _DOI.match(candidate) else None
