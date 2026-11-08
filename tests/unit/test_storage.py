"""Tests for the storage interface and local-filesystem storage (P3-T1).

FR-ING-002 (store unmodified under a generated key), NFR-SEC-002 (never use
client filenames as paths), AD-002 (save/read/delete by key).
"""

import hashlib
import re
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

import app.storage as storage_module
from app.storage import (
    InvalidStorageKeyError,
    LocalStorage,
    StorageError,
    StorageKeyNotFoundError,
)

PDF_BYTES = b"%PDF-1.4\nsynthetic test bytes\n%%EOF\n"
KEY_PATTERN = re.compile(r"^(pdf/[0-9a-f]{32}\.pdf|tei/[0-9a-f]{32}\.tei\.xml)$")


@pytest.fixture
def store(tmp_path: Path) -> LocalStorage:
    return LocalStorage(tmp_path / "storage")


def files_under(root: Path) -> list[Path]:
    return sorted(p for p in root.rglob("*") if p.is_file())


# --- save and read --------------------------------------------------------------


def test_saved_bytes_read_back_unchanged(store: LocalStorage) -> None:
    key = store.save(PDF_BYTES, kind="pdf")

    data = store.read(key)

    assert data == PDF_BYTES
    assert hashlib.sha256(data).hexdigest() == hashlib.sha256(PDF_BYTES).hexdigest()


@pytest.mark.parametrize(
    ("kind", "prefix", "suffix"), [("pdf", "pdf/", ".pdf"), ("tei", "tei/", ".tei.xml")]
)
def test_keys_are_generated_with_kind_prefix_and_suffix(
    store: LocalStorage, kind: str, prefix: str, suffix: str
) -> None:
    key = store.save(b"x", kind=kind)

    assert KEY_PATTERN.match(key)
    assert key.startswith(prefix)
    assert key.endswith(suffix)


def test_same_content_gets_a_new_key_each_time(store: LocalStorage) -> None:
    keys = {store.save(PDF_BYTES, kind="pdf") for _ in range(20)}

    assert len(keys) == 20


def test_files_stay_inside_the_storage_root(
    store: LocalStorage, tmp_path: Path
) -> None:
    store.save(PDF_BYTES, kind="pdf")
    store.save(b"<TEI/>", kind="tei")

    for path in files_under(tmp_path):
        assert path.is_relative_to(tmp_path / "storage")


def test_root_folder_is_created_if_missing(tmp_path: Path) -> None:
    root = tmp_path / "does" / "not" / "exist"

    LocalStorage(root).save(b"x", kind="pdf")

    assert root.is_dir()


def test_unknown_kind_is_rejected(store: LocalStorage) -> None:
    with pytest.raises(ValueError, match="kind"):
        store.save(b"x", kind="exe")


def test_empty_content_is_rejected(store: LocalStorage, tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="empty"):
        store.save(b"", kind="pdf")
    assert files_under(tmp_path) == []


# --- keys that are not generated keys -------------------------------------------


@pytest.mark.parametrize(
    "key",
    [
        "",
        "../secret.pdf",
        "pdf/../../secret.pdf",
        "pdf/../tei/0123456789abcdef0123456789abcdef.tei.xml",
        "/etc/passwd",
        "C:\\Windows\\win.ini",
        "pdf\\0123456789abcdef0123456789abcdef.pdf",
        "PDF/0123456789ABCDEF0123456789ABCDEF.pdf",
        "pdf/0123456789abcdef0123456789abcdef.exe",
        "pdf/0123456789abcdef0123456789abcdef.tei.xml",
        "pdf/short.pdf",
        "pdf/0123456789abcdef0123456789abcdef.pdf/../x",
        "pdf/paper title from the client.pdf",
        " pdf/0123456789abcdef0123456789abcdef.pdf",
        "pdf/0123456789abcdef0123456789abcdef.pdf\n",
    ],
)
def test_read_and_delete_refuse_anything_but_a_generated_key(
    store: LocalStorage, tmp_path: Path, key: str
) -> None:
    outside = tmp_path / "secret.pdf"
    outside.write_bytes(b"must not be touched")

    with pytest.raises(InvalidStorageKeyError):
        store.read(key)
    with pytest.raises(InvalidStorageKeyError):
        store.delete(key)

    assert outside.read_bytes() == b"must not be touched"


def test_a_valid_key_does_not_depend_on_how_the_system_resolves_paths(
    store: LocalStorage, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Windows can return a `\\\\?\\` form of a path while its folder is being created."""
    monkeypatch.setattr(Path, "resolve", lambda self, strict=False: Path("elsewhere"))

    key = store.save(PDF_BYTES, kind="pdf")

    assert store.read(key) == PDF_BYTES


def test_concurrent_saves_into_a_new_folder_all_succeed(tmp_path: Path) -> None:
    """Regression test: this failed for 1 to 3% of saves on Windows."""
    workers = 12

    def save_all(store: LocalStorage, barrier: threading.Barrier) -> str:
        barrier.wait()
        return store.save(PDF_BYTES, kind="pdf")

    with ThreadPoolExecutor(max_workers=workers) as pool:
        for attempt in range(60):
            store = LocalStorage(tmp_path / f"attempt-{attempt}" / "storage")
            barrier = threading.Barrier(workers)
            futures = [pool.submit(save_all, store, barrier) for _ in range(workers)]
            keys = {future.result() for future in futures}
            assert len(keys) == workers


def test_reading_a_missing_key_is_an_explicit_error(store: LocalStorage) -> None:
    with pytest.raises(StorageKeyNotFoundError):
        store.read("pdf/0123456789abcdef0123456789abcdef.pdf")


# --- delete -----------------------------------------------------------------------


def test_delete_removes_the_file(store: LocalStorage, tmp_path: Path) -> None:
    key = store.save(PDF_BYTES, kind="pdf")

    store.delete(key)

    assert files_under(tmp_path) == []
    with pytest.raises(StorageKeyNotFoundError):
        store.read(key)


def test_deleting_a_missing_key_is_an_explicit_error(store: LocalStorage) -> None:
    with pytest.raises(StorageKeyNotFoundError):
        store.delete("tei/0123456789abcdef0123456789abcdef.tei.xml")


# --- failures --------------------------------------------------------------------


def test_key_collision_fails_without_overwriting(
    store: LocalStorage, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixed = "0123456789abcdef0123456789abcdef"
    monkeypatch.setattr(storage_module, "_new_id", lambda: fixed)
    key = store.save(b"first", kind="pdf")

    with pytest.raises(StorageError, match="collision"):
        store.save(b"second", kind="pdf")

    assert store.read(key) == b"first"


def test_write_failure_leaves_no_partial_file(
    store: LocalStorage, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail_write(self: object, data: bytes) -> int:
        raise OSError("disk full (simulated)")

    monkeypatch.setattr(storage_module, "_write_all", fail_write)

    with pytest.raises(StorageError, match="could not be stored"):
        store.save(PDF_BYTES, kind="pdf")

    assert files_under(tmp_path) == []


def test_storage_errors_do_not_reveal_paths(
    store: LocalStorage, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Messages may reach API responses: no file-system paths (NFR-SEC-005)."""

    def fail_write(self: object, data: bytes) -> int:
        raise OSError(f"cannot write {tmp_path}")

    monkeypatch.setattr(storage_module, "_write_all", fail_write)

    with pytest.raises(StorageError) as error:
        store.save(PDF_BYTES, kind="pdf")

    assert str(tmp_path) not in str(error.value)
