"""File storage behind a small interface (AD-002): save, read and delete by key.

Keys are always generated here, never derived from client filenames
(NFR-SEC-002): `pdf/<uuid7 hex>.pdf` for uploaded papers and
`tei/<uuid7 hex>.tei.xml` for GROBID output. Only keys of exactly that shape
are accepted, so a key can never point outside the storage folder.

Source documents are never deleted automatically (DR-008): `delete` exists
only to remove a file whose document row was never committed.
"""

import os
import re
import uuid
from functools import lru_cache
from pathlib import Path
from typing import BinaryIO, Protocol

from app.config import get_settings

_SUFFIXES = {"pdf": ".pdf", "tei": ".tei.xml"}
_KEY = re.compile(r"^(?:pdf/[0-9a-f]{32}\.pdf|tei/[0-9a-f]{32}\.tei\.xml)$")


class StorageError(Exception):
    """A file could not be stored, read or deleted. Messages contain no paths."""


class StorageKeyNotFoundError(StorageError):
    """No file exists for a well-formed key."""


class InvalidStorageKeyError(StorageError, ValueError):
    """The key is not one this storage generated."""


class Storage(Protocol):
    def save(self, data: bytes, *, kind: str) -> str: ...

    def read(self, key: str) -> bytes: ...

    def delete(self, key: str) -> None: ...


def _new_id() -> str:
    return uuid.uuid7().hex


def _write_all(handle: BinaryIO, data: bytes) -> int:
    written = handle.write(data)
    handle.flush()
    os.fsync(handle.fileno())
    return written


class LocalStorage:
    """Files in a local folder (default `data/storage`, git-ignored)."""

    def __init__(self, root: Path) -> None:
        self._root = root.resolve()

    def save(self, data: bytes, *, kind: str) -> str:
        """Store `data` unmodified under a new key and return the key."""
        if kind not in _SUFFIXES:
            raise ValueError(
                f"unknown storage kind {kind!r}; expected one of {sorted(_SUFFIXES)}"
            )
        if not data:
            raise ValueError("refusing to store empty content")
        key = f"{kind}/{_new_id()}{_SUFFIXES[kind]}"
        path = self._path(key)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            # "x": create only; an existing file (key collision) is never overwritten.
            with path.open("xb") as handle:
                _write_all(handle, data)
        except FileExistsError:
            raise StorageError(
                "storage key collision; nothing was overwritten"
            ) from None
        except OSError as exc:
            path.unlink(missing_ok=True)
            raise StorageError(
                f"file could not be stored ({type(exc).__name__})"
            ) from None
        return key

    def read(self, key: str) -> bytes:
        path = self._path(key)
        try:
            return path.read_bytes()
        except FileNotFoundError:
            raise StorageKeyNotFoundError("no stored file for this key") from None
        except OSError as exc:
            raise StorageError(
                f"file could not be read ({type(exc).__name__})"
            ) from None

    def delete(self, key: str) -> None:
        path = self._path(key)
        try:
            path.unlink()
        except FileNotFoundError:
            raise StorageKeyNotFoundError("no stored file for this key") from None
        except OSError as exc:
            raise StorageError(
                f"file could not be deleted ({type(exc).__name__})"
            ) from None

    def _path(self, key: str) -> Path:
        """Path for a generated key; anything else is refused."""
        if not _KEY.match(key):
            raise InvalidStorageKeyError("not a storage key")
        path = (self._root / key).resolve()
        if not path.is_relative_to(
            self._root
        ):  # second guard; the pattern already forbids it
            raise InvalidStorageKeyError("not a storage key")
        return path


@lru_cache
def get_storage() -> Storage:
    """The application's storage, rooted at `STORAGE_DIR`."""
    return LocalStorage(get_settings().storage_dir)
