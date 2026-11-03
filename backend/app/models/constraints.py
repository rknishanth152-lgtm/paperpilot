"""Allowed values shared by the ORM models and the database CHECK constraints.

Defined once here so code and database cannot disagree (docs/design/schema.md).
"""

DOCUMENT_STATUSES = ("pending", "processing", "parsed", "failed")

# Stored on failed documents (docs/design/schema.md §6). Upload rejections
# (not_pdf, empty_file, file_too_large) never create a document, so they are
# not here.
FAILURE_REASONS = (
    "parser_unreachable",
    "parser_disconnected",
    "parser_timeout",
    "parser_busy",
    "unreadable_pdf",
    "no_text_layer",
    "document_too_long",
    "parser_error",
    "malformed_tei",
    "empty_parse",
    "storage_error",
    "interrupted",
)

PASSAGE_REGIONS = ("abstract", "body", "caption", "back")

METADATA_SOURCES = ("grobid",)


def one_of(column: str, values: tuple[str, ...]) -> str:
    """SQL for a CHECK that `column` is one of `values`."""
    quoted = ", ".join(f"'{value}'" for value in values)
    return f"{column} IN ({quoted})"
