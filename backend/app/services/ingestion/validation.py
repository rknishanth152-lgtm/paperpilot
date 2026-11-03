"""Upload validation (P3-T2, FR-ING-001).

Runs before anything is stored. A rejected upload creates no document; the
upload endpoint returns the rejection as a structured API error
(docs/design/schema.md §6). The file type is decided by content, never by the
filename or the client's declared media type (NFR-SEC-002).
"""

import hashlib
import re
from dataclasses import dataclass

PDF_SIGNATURE = b"%PDF-"
MAX_FILENAME_CHARS = 255  # documents.original_filename CHECK

# Plain-language messages shown to users (FR-UI-001). They never repeat the
# client's filename.
MESSAGES = {
    "empty_file": "The file is empty.",
    "file_too_large": "The file is larger than the upload limit.",
    "not_pdf": "The file is not a PDF. Only PDF files can be uploaded.",
}


class UploadRejectedError(Exception):
    """An upload failed validation. `code` is stable; `message` is for people."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code
        self.message = MESSAGES[code]


@dataclass(frozen=True)
class ValidatedUpload:
    content: bytes
    sha256: str
    size_bytes: int
    original_filename: str | None  # display only, never used as a path


def validate_upload(
    data: bytes, filename: str | None, *, max_bytes: int
) -> ValidatedUpload:
    """Accept `data` if it is a non-empty PDF within `max_bytes`, else raise.

    Checks run in a fixed order: empty, size, PDF signature.
    """
    if max_bytes <= 0:
        raise ValueError("max_bytes must be positive")
    if not data:
        raise UploadRejectedError("empty_file")
    if len(data) > max_bytes:
        raise UploadRejectedError("file_too_large")
    if not data.startswith(PDF_SIGNATURE):
        raise UploadRejectedError("not_pdf")
    return ValidatedUpload(
        content=data,
        sha256=hashlib.sha256(data).hexdigest(),
        size_bytes=len(data),
        original_filename=display_filename(filename),
    )


_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def display_filename(raw: str | None) -> str | None:
    """A safe name to show people: last path part, no control characters.

    Both `/` and `\\` count as separators, so a Windows path from any client is
    reduced to its file name. Returns None when nothing usable remains.
    """
    if raw is None:
        return None
    name = re.split(r"[\\/]", raw)[-1]
    name = _CONTROL.sub("", name)
    name = " ".join(name.split())
    if name in {"", ".", ".."}:
        return None
    return name[:MAX_FILENAME_CHARS]
