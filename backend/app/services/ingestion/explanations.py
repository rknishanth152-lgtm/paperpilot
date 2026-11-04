"""Plain-language explanations of failure reasons (FR-UI-001, NFR-SEC-005).

Shown to users instead of the stored `failure_message`, which is written for
developers. Every reason in `FAILURE_REASONS` has an entry (unit-tested).
"""

FAILURE_EXPLANATIONS = {
    "parser_unreachable": "The PDF parser (GROBID) could not be reached. Check that it "
    "is running, then retry.",
    "parser_disconnected": "The PDF parser closed the connection before it finished. "
    "Retry the document.",
    "parser_timeout": "The PDF parser took too long to respond. Retry the document.",
    "parser_busy": "The PDF parser was busy with other documents. Retry in a moment.",
    "unreadable_pdf": "The PDF could not be read. It may be damaged or incomplete.",
    "no_text_layer": "No text was found in the PDF. It may be a scanned or image-only "
    "file, which is not supported.",
    "document_too_long": "The document is longer than the parser can handle.",
    "parser_error": "The PDF parser reported an error for this document.",
    "malformed_tei": "The parser's output could not be read.",
    "empty_parse": "No body text was found in the parser's output.",
    "storage_error": "A file could not be stored or read on the server.",
    "interrupted": "Processing was interrupted because the server stopped. Retry the "
    "document.",
}
