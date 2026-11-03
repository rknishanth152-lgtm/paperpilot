"""Phase 1 throwaway script (P1-T3): send each paper to GROBID and save the raw TEI.

Not application code. Run from the repository root with the services up:

    $env:PYTHONPATH = "backend"; uv run python scripts/grobid_experiment.py

Reads PDFs from data/papers/, writes TEI and a JSON run record to
data/grobid-output/ (git-ignored). Prints no paper text (NFR-PRI-002).
"""

import hashlib
import json
import time
from datetime import UTC, datetime
from pathlib import Path
from xml.etree import ElementTree

import httpx

from app.config import REPO_ROOT, get_settings

PAPERS_DIR = REPO_ROOT / "data" / "papers"
OUTPUT_DIR = REPO_ROOT / "data" / "grobid-output"
TIMEOUT_SECONDS = 300.0
TEI_NS = "{http://www.tei-c.org/ns/1.0}"

# One fixed configuration for every paper. consolidateHeader defaults to 1 in
# GROBID and would send extracted metadata to CrossRef, so all consolidation
# is switched off (docs/experiments/grobid-feasibility.md §2.3).
# A list value sends the field once per item, as GROBID expects for teiCoordinates.
FORM_FIELDS: dict[str, str | list[str]] = {
    "consolidateHeader": "0",
    "consolidateCitations": "0",
    "consolidateFunders": "0",
    "includeRawCitations": "1",
    "generateIDs": "1",
    "teiCoordinates": ["p", "head", "figure", "biblStruct"],
}


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def page_count(tei: bytes) -> int | None:
    """Pages listed in GROBID's <facsimile>, or None if absent or unparsable."""
    try:
        root = ElementTree.fromstring(tei)
    except ElementTree.ParseError:
        return None
    surfaces = root.findall(f"{TEI_NS}facsimile/{TEI_NS}surface")
    return len(surfaces) or None


def process(client: httpx.Client, url: str, pdf: Path) -> dict[str, object]:
    record: dict[str, object] = {
        "file": pdf.name,
        "sha256": sha256_of(pdf),
        "bytes": pdf.stat().st_size,
    }
    started = time.perf_counter()
    try:
        with pdf.open("rb") as handle:
            response = client.post(
                f"{url}/api/processFulltextDocument",
                data=FORM_FIELDS,
                files={"input": (pdf.name, handle, "application/pdf")},
            )
    except httpx.TransportError as exc:
        record.update(status=None, error=type(exc).__name__)
        record["seconds"] = round(time.perf_counter() - started, 2)
        return record

    record["seconds"] = round(time.perf_counter() - started, 2)
    record["status"] = response.status_code
    if response.status_code == 200:
        out = OUTPUT_DIR / f"{pdf.stem}.tei.xml"
        out.write_bytes(response.content)
        record.update(
            tei_file=out.name,
            tei_bytes=len(response.content),
            pages=page_count(response.content),
        )
    else:
        # GROBID error messages describe the failure, not the paper's content.
        record["error"] = response.text[:300]
    return record


def main() -> None:
    url = str(get_settings().grobid_url).rstrip("/")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    pdfs = sorted(PAPERS_DIR.glob("*.pdf"))
    if not pdfs:
        raise SystemExit(f"No PDFs in {PAPERS_DIR}")

    with httpx.Client(timeout=TIMEOUT_SECONDS) as client:
        version = client.get(f"{url}/api/version").json()
        results = [process(client, url, pdf) for pdf in pdfs]

    run = {
        "started_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "grobid_version": version,
        "endpoint": "/api/processFulltextDocument",
        "form_fields": FORM_FIELDS,
        "client_timeout_seconds": TIMEOUT_SECONDS,
        "results": results,
    }
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    run_file = OUTPUT_DIR / f"run-{stamp}.json"
    run_file.write_text(json.dumps(run, indent=2), encoding="utf-8")

    print(f"GROBID {version.get('version')} at {url}; run record: {run_file.name}")
    for r in results:
        print(
            f"{r['file']:<34} status={r['status']} seconds={r['seconds']} "
            f"pages={r.get('pages')} tei_bytes={r.get('tei_bytes')} error={r.get('error')}"
        )


if __name__ == "__main__":
    main()
