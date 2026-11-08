"""Is a quote really in a stored passage? (P5-T6; FR-CIT-002, OQ-013)

Compared after Unicode NFKC (which expands ligature characters), folding curly
quotes and dashes to ASCII, and ignoring all whitespace. Case is kept.

Whitespace is ignored because PDF extraction moves it around without changing
the text: `fi ndings`, `BERT BASE`, `2015;Peters`. On the five papers, the
narrower rule of only repairing split ligatures would reject 126 of 209 true
quotes (progress.md §6.14).

A match shows the words are in the passage. It says nothing about whether the
passage supports the statement (AD-008).
"""

import re
import unicodedata

_DASHES = re.compile("[‐-―−]")
_QUOTES = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"'})


def _normalized(text: str) -> str:
    folded = _DASHES.sub("-", unicodedata.normalize("NFKC", text)).translate(_QUOTES)
    return "".join(folded.split())


def quote_in_passage(quote: str, passage_text: str) -> bool:
    wanted = _normalized(quote)
    return bool(wanted) and wanted in _normalized(passage_text)
