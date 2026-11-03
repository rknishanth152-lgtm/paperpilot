"""Phase 1 throwaway script (P1-T5): how does GROBID respond to bad or extreme input?

Not application code. Run from the repository root with the services up:

    $env:PYTHONPATH = "backend"; uv run python scripts/grobid_failures.py inputs
    $env:PYTHONPATH = "backend"; uv run python scripts/grobid_failures.py service

`inputs` generates synthetic test files in data/failure-inputs/ (git-ignored)
and sends each to GROBID. `service` stops GROBID with Docker Compose to test an
unreachable service and a request interrupted mid-flight, restarts it, then
sends concurrent requests to look for 503. Results go to
data/grobid-output/failures-<mode>-<time>.json. No paper text is printed.
"""

import json
import os
import random
import subprocess
import sys
import threading
import time
import zlib
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from xml.etree import ElementTree

import httpx

from app.config import REPO_ROOT, get_settings

INPUT_DIR = REPO_ROOT / "data" / "failure-inputs"
PAPERS_DIR = REPO_ROOT / "data" / "papers"
OUTPUT_DIR = REPO_ROOT / "data" / "grobid-output"
TEI = {"tei": "http://www.tei-c.org/ns/1.0"}
TIMEOUT_SECONDS = 600.0
FORM_FIELDS: dict[str, str | list[str]] = {
    "consolidateHeader": "0",
    "consolidateCitations": "0",
    "consolidateFunders": "0",
}


# --- Minimal PDF writer (standard library only) -----------------------------


def build_pdf(
    page_contents: list[bytes], image: tuple[int, int, bytes] | None = None
) -> bytes:
    """A valid PDF: one content stream per page, Helvetica, optional gray image."""
    objects: list[bytes] = []

    def add(body: bytes) -> int:
        objects.append(body)
        return len(objects)

    catalog = add(b"")  # filled in below
    pages = add(b"")
    font = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    image_ref = None
    if image is not None:
        width, height, pixels = image
        data = zlib.compress(pixels, 1)
        image_ref = add(
            b"<< /Type /XObject /Subtype /Image /Width %d /Height %d /ColorSpace /DeviceGray "
            b"/BitsPerComponent 8 /Filter /FlateDecode /Length %d >>\nstream\n"
            % (width, height, len(data))
            + data
            + b"\nendstream"
        )
    kids = []
    for content in page_contents:
        stream = add(
            b"<< /Length %d >>\nstream\n" % len(content) + content + b"\nendstream"
        )
        xobject = b" /XObject << /Im1 %d 0 R >>" % image_ref if image_ref else b""
        kids.append(
            add(
                b"<< /Type /Page /Parent %d 0 R /MediaBox [0 0 612 792] "
                b"/Resources << /Font << /F1 %d 0 R >>%s >> /Contents %d 0 R >>"
                % (pages, font, xobject, stream)
            )
        )
    objects[catalog - 1] = b"<< /Type /Catalog /Pages %d 0 R >>" % pages
    objects[pages - 1] = b"<< /Type /Pages /Kids [%s] /Count %d >>" % (
        b" ".join(b"%d 0 R" % k for k in kids),
        len(kids),
    )

    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % number + body + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    out += b"".join(b"%010d 00000 n \n" % o for o in offsets)
    out += b"trailer\n<< /Size %d /Root %d 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (
        len(objects) + 1,
        catalog,
        xref,
    )
    return bytes(out)


def text_page(page: int, lines: int = 40) -> bytes:
    """Synthetic sentences, one per line (no real paper text)."""
    rows = [
        f"({f'Synthetic test sentence {n} on page {page} for the parser experiment.'}) Tj T*"
        for n in range(1, lines + 1)
    ]
    return ("BT /F1 11 Tf 14 TL 72 740 Td " + " ".join(rows) + " ET").encode("ascii")


def generate_inputs() -> list[Path]:
    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    rng = random.Random(42)
    p1 = (PAPERS_DIR / "p1-devlin2019-bert.pdf").read_bytes()
    p2 = (PAPERS_DIR / "p2-errington2021-elife.pdf").read_bytes()
    image_page = b"q 612 0 0 792 0 0 cm /Im1 Do Q"
    gradient = bytes((x + y) % 256 for y in range(1100) for x in range(850))
    noise_side = 8000
    cases: dict[str, bytes] = {
        "f01-text-renamed.pdf": b"This is a plain text file, not a PDF.\n" * 20,
        "f02-empty.pdf": b"",
        "f03-header-then-garbage.pdf": b"%PDF-1.4\n" + rng.randbytes(50_000),
        "f04-truncated-p1-50pct.pdf": p1[: len(p1) // 2],
        "f05-truncated-p2-10pct.pdf": p2[: len(p2) // 10],
        "f06-synthetic-text-1-page.pdf": build_pdf([text_page(1)]),
        "f07-image-only-1-page.pdf": build_pdf([image_page], (850, 1100, gradient)),
        "f08-blank-1-page.pdf": build_pdf([b""]),
        "f09-text-300-pages.pdf": build_pdf([text_page(p) for p in range(1, 301)]),
        "f10-text-3000-pages.pdf": build_pdf([text_page(p) for p in range(1, 3001)]),
        "f11-large-image-64mb.pdf": build_pdf(
            [image_page], (noise_side, noise_side, os.urandom(noise_side * noise_side))
        ),
    }
    paths = []
    for name, content in cases.items():
        path = INPUT_DIR / name
        path.write_bytes(content)
        paths.append(path)
    return paths


# --- Sending -----------------------------------------------------------------


def body_paragraphs(tei: bytes) -> int | None:
    try:
        root = ElementTree.fromstring(tei)
    except ElementTree.ParseError:
        return None
    return len(root.findall("tei:text/tei:body/tei:div/tei:p", TEI))


def send(client: httpx.Client, url: str, path: Path) -> dict[str, object]:
    record: dict[str, object] = {"file": path.name, "bytes": path.stat().st_size}
    started = time.perf_counter()
    try:
        with path.open("rb") as handle:
            response = client.post(
                f"{url}/api/processFulltextDocument",
                data=FORM_FIELDS,
                files={"input": (path.name, handle, "application/pdf")},
            )
    except httpx.HTTPError as exc:
        record.update(status=None, error=f"{type(exc).__name__}: {str(exc)[:200]}")
    else:
        record["status"] = response.status_code
        if response.status_code == 200:
            record["body_paragraphs"] = body_paragraphs(response.content)
            record["tei_bytes"] = len(response.content)
        else:
            record["error"] = response.text[:300]
    record["seconds"] = round(time.perf_counter() - started, 2)
    return record


def compose(*args: str) -> None:
    subprocess.run(
        ["docker", "compose", *args], cwd=REPO_ROOT, check=True, capture_output=True
    )


def wait_until_alive(client: httpx.Client, url: str, limit: float = 180.0) -> float:
    started = time.perf_counter()
    while time.perf_counter() - started < limit:
        try:
            if client.get(f"{url}/api/isalive", timeout=5.0).text.strip() == "true":
                return round(time.perf_counter() - started, 1)
        except httpx.HTTPError:
            pass
        time.sleep(2)
    raise SystemExit("GROBID did not come back within the limit")


def run_inputs(client: httpx.Client, url: str) -> list[dict[str, object]]:
    results = []
    for path in generate_inputs():
        result = send(client, url, path)
        print(json.dumps(result)[:400], flush=True)
        results.append(result)
    return results


def run_service(client: httpx.Client, url: str) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    small = PAPERS_DIR / "p5-alsheikhali2011-plosone.pdf"
    long_input = INPUT_DIR / "f10-text-3000-pages.pdf"
    try:
        # 1. Service stopped before the request.
        compose("stop", "grobid")
        results.append({"case": "service stopped", **send(client, url, small)})
        compose("start", "grobid")
        results.append(
            {"case": "restart", "seconds_until_alive": wait_until_alive(client, url)}
        )

        # 2. Service stopped while a long request is in flight.
        holder: dict[str, dict[str, object]] = {}
        worker = threading.Thread(
            target=lambda: holder.update(r=send(client, url, long_input))
        )
        worker.start()
        time.sleep(5)
        compose("stop", "grobid")
        worker.join()
        results.append({"case": "stopped mid-request (after 5 s)", **holder["r"]})
    finally:
        compose("start", "grobid")
        results.append(
            {"case": "restart", "seconds_until_alive": wait_until_alive(client, url)}
        )

    # 3. Concurrent requests: look for 503 when all threads are busy.
    medium = PAPERS_DIR / "p2-errington2021-elife.pdf"
    with ThreadPoolExecutor(max_workers=25) as pool:
        burst = list(pool.map(lambda _: send(client, url, medium), range(25)))
    statuses: dict[str, int] = {}
    for r in burst:
        statuses[str(r["status"])] = statuses.get(str(r["status"]), 0) + 1
    results.append(
        {
            "case": "25 concurrent requests (p2)",
            "status_counts": statuses,
            "seconds_min_max": [
                min(float(str(r["seconds"])) for r in burst),
                max(float(str(r["seconds"])) for r in burst),
            ],
            "error_example": next(
                (r.get("error") for r in burst if r["status"] != 200), None
            ),
        }
    )
    for r in results:
        print(json.dumps(r)[:400], flush=True)
    return results


def main() -> None:
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if mode not in {"inputs", "service"}:
        raise SystemExit("usage: grobid_failures.py inputs|service")
    url = str(get_settings().grobid_url).rstrip("/")
    with httpx.Client(timeout=TIMEOUT_SECONDS) as client:
        results = (
            run_inputs(client, url) if mode == "inputs" else run_service(client, url)
        )
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    out = OUTPUT_DIR / f"failures-{mode}-{stamp}.json"
    out.write_text(
        json.dumps({"form_fields": FORM_FIELDS, "results": results}, indent=2),
        encoding="utf-8",
    )
    print(f"saved {out.name}")


if __name__ == "__main__":
    main()
