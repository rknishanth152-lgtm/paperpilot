"""Plain-language explanations of failure reasons (FR-UI-001, NFR-SEC-005).

Shown to users instead of the stored `failure_message`, which is written for
developers. Every reason in `FAILURE_REASONS` has an entry (unit-tested).
"""

FAILURE_EXPLANATIONS = {
    "parser_unreachable": "The paper reader isn't running. Start it, then try again.",
    "parser_disconnected": "Reading stopped before it finished. Try again.",
    "parser_timeout": "This paper took too long to read. Try again.",
    "parser_busy": "PaperPilot was busy with other papers. Try again in a moment.",
    "unreadable_pdf": "This PDF couldn't be opened. It may be damaged or incomplete.",
    "no_text_layer": "This PDF has no text to read. It may be a scan or a set of images, "
    "which PaperPilot can't read yet.",
    "document_too_long": "This paper is too long for PaperPilot to read.",
    "parser_error": "Something went wrong while reading this paper. Try again.",
    "malformed_tei": "Something went wrong while reading this paper. Try again.",
    "empty_parse": "No main text was found in this paper.",
    "storage_error": "This file couldn't be saved or opened on this computer.",
    "interrupted": "Reading stopped because PaperPilot was closed. Try again.",
}
