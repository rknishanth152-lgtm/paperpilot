# PaperPilot

An evidence-first research intelligence and scientific-reproducibility platform. It turns academic papers into structured, searchable knowledge in which every derived statement links to a stored source passage.

**Status:** Phase 0 (environment setup); local services run. No application code exists yet. What is actually done and verified is recorded in [`progress.md`](progress.md).

## Documents

| Document | Purpose |
|---|---|
| [`PRD.md`](PRD.md) | Requirements, decisions, open questions |
| [`docs/implementation-roadmap.md`](docs/implementation-roadmap.md) | Phase order, tasks, exit criteria |
| [`progress.md`](progress.md) | Verified state, decisions log, verification log |
| [`CLAUDE.md`](CLAUDE.md) | Rules for development with Claude Code |
| [`docs/design-system.md`](docs/design-system.md) | Design and motion system (proposed) |

`notes/` holds learning notes. They are not requirements.

## Prerequisites

Verified on the developer's machine on 2026-11-03 (see `progress.md` §7):

- Docker Desktop with the WSL 2 backend
- Git
- Node.js 24 with npm (frontend)

- uv 0.13 and Python 3.14 (below)

## Python environment

The project uses [uv](https://docs.astral.sh/uv/) with Python 3.14 (pinned in `.python-version`). Tools: pytest, ruff, mypy (`pyproject.toml`).

**One-time machine setup** (done on the developer's machine 2026-11-03):

```bash
winget install --id astral-sh.uv -e --scope user
```

Set two user environment variables so uv keeps Python and its cache on E: (C: is short of space, and the Claude desktop app cannot use uv's default AppData location): `UV_PYTHON_INSTALL_DIR=E:\uv\python` and `UV_CACHE_DIR=E:\uv\cache`. Open a new terminal afterwards. Then:

```bash
uv python install 3.14
```

**In the repository** (verified 2026-11-03):

```bash
uv sync
```

```bash
uv run ruff check .
```

```bash
uv run ruff format --check .
```

```bash
uv run pytest
```

This runs the unit tests only: fast and offline. Tests that need PostgreSQL or GROBID live in `tests/integration` and run only when asked, with the services started (`docker compose up -d --wait`). If a service is down they fail with instructions rather than being skipped:

```bash
uv run pytest -m integration
```

Schema tests never touch your development database: they create a temporary database (`<POSTGRES_DB>_test`) on the same server, migrate it with Alembic, and drop it afterwards.

Test folders: `tests/unit` (default), `tests/integration` (marker `integration`), `tests/evaluation` (marker `evaluation`, from Phase 4). Markers are applied by folder in `tests/conftest.py`.

```bash
uv run mypy .
```

## Database migrations

The schema is managed with Alembic (migrations in `backend/migrations/`). The database connection comes from `.env` through `backend/app/config.py`; `alembic.ini` holds only logging settings. Run from the repository folder with PostgreSQL running (verified 2026-11-03):

```bash
uv run alembic upgrade head
```

```bash
uv run alembic current
```

`uv run alembic check` reports whether the models and the migrations disagree. Alembic reads its settings from `pyproject.toml` in the current folder, so run these commands from the repository folder.

## Configuration

All settings are read in one place, `backend/app/config.py`, from environment variables and `.env`. `.env.example` lists every setting with a placeholder; the same `POSTGRES_*` values configure Docker Compose and the backend. The backend refuses to start with a missing or invalid value.

## Local services (PostgreSQL and GROBID)

Defined in [`compose.yaml`](compose.yaml). Both are reachable from this computer only (`127.0.0.1`).

| Service | Image | Address |
|---|---|---|
| PostgreSQL 18 (pgvector available, not enabled) | `pgvector/pgvector:0.8.7-pg18-trixie` | `127.0.0.1:5432` |
| GROBID 0.9.1 (CPU, CRF models) | `grobid/grobid:0.9.1-crf` | `http://127.0.0.1:8070` |

GROBID uses about 3 GB of memory while running.

**First time:** create `.env` from `.env.example` and set `POSTGRES_PASSWORD` to a value of your own. `.env` is never committed.

Run from the repository folder (verified 2026-11-03, see `progress.md` §7):

```bash
docker compose up -d --wait
```

```bash
docker compose ps
```

```bash
curl.exe http://127.0.0.1:8070/api/isalive
```

The last command prints `true` when GROBID is ready. In Windows PowerShell, type `curl.exe`, not `curl` (which is a different PowerShell command).

`compose.yaml` fixes the Docker project name to `paperpilot`. A second checkout of this repository on the same computer therefore controls the **same** containers and database volume. To run a separate copy (for example a fresh-clone check), stop the first one and set `COMPOSE_PROJECT_NAME` to another name in that terminal.

Stop the services (database data is kept in the `paperpilot_postgres-data` volume):

```bash
docker compose down
```

## Running the backend

The backend has a health endpoint and the document API (upload, status, structure, retry). It reads `.env` at startup and refuses to start if a setting is missing or invalid. Run from the repository folder (verified 2026-11-03):

```bash
uv run uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

Run **one** server process (uvicorn's default; do not pass `--workers`). At startup the server marks every document still `processing` as `failed` with reason `interrupted`, because only a crash can leave one there; this assumes no other process is ingesting (`AD-010`). If PostgreSQL is unreachable, startup fails.

Check it in another terminal; it prints `{"status":"ok"}`:

```bash
curl.exe http://127.0.0.1:8000/health
```

The health endpoint only says the API process is running. It does not check PostgreSQL or GROBID. Always keep `--host 127.0.0.1` (`NFR-SEC-006`). Stop the server with Ctrl+C.

### Document API (verified 2026-11-04)

PostgreSQL and GROBID must be running. Upload sends the PDF bytes as the request body (not a form); the optional `X-Filename` header carries the file name, percent-encoded, for display only. Processing runs after the response; poll the status until it is `parsed` or `failed`.

```bash
curl.exe -X POST http://127.0.0.1:8000/documents --data-binary "@paper.pdf" -H "Content-Type: application/pdf" -H "X-Filename: paper.pdf"
```

| Method and path | Result |
|---|---|
| `POST /documents` | `202` and a new `pending` document, or `200` and the existing document for an identical file (`created: false`; it is not processed again) |
| `GET /documents/{id}` | Status, `failure_reason` and a plain-language `failure_explanation` |
| `GET /documents/{id}/structure` | Metadata and passages in order with section and page (`null` = unknown); `409 document_not_parsed` with status and reason otherwise |
| `POST /documents/{id}/retry` | `202` and processing again for a `failed` (or stuck `pending`) document; `409 document_not_retryable` otherwise |
| `POST /answers` | Body: `question` and `document_ids` and/or `paper_ids`. A checked answer with `validation_status`, per-citation validity and evidence passages. Without a configured model this returns `503 model_not_configured` |

Every error is `{"error": {"code", "message", "details"?}}` with no internal details. Upload rejections create nothing: `empty_file` (400), `file_too_large` (413, reading stops at `MAX_UPLOAD_MB`), `not_pdf` (415, decided by content). The interactive API docs are at `http://127.0.0.1:8000/docs`.

## Running the frontend

The frontend is in `frontend/` (React, TypeScript, Vite). Run these from that folder (verified 2026-11-08). First time only:

```bash
npm ci
```

```bash
cp .env.example .env
```

With the backend running on port 8000, start the dev server and open `http://127.0.0.1:5173`:

```bash
npm run dev
```

The dev server forwards `/api` to `API_PROXY_TARGET` in `frontend/.env`, and refuses to start if that is not set. Checks:

```bash
npm test
```

```bash
npm run typecheck
```

```bash
npm run build
```

Commands are added here only after they have been run and verified.

## Trying it end to end

Verified 2026-11-08 with five real papers. In three terminals, from the repository folder:

```bash
docker compose up -d --wait
```

```bash
uv run uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

```bash
npm --prefix frontend run dev
```

Open `http://127.0.0.1:5173`, upload a PDF, and wait for it to reach `Parsed` or `Failed`. There is no list of uploaded documents yet: to get back to one, keep its address, or upload the same file again, which opens the existing document without processing it again.

Parser limits you will see in the structure view are recorded in `progress.md` §6.12. Passages are shown exactly as stored, including the parser's mistakes.

## Connecting an AI model

Uploading, parsing and search need no AI model; answering questions does. Set these in `.env` (never commit it), then restart the backend.

**Google Gemini, free tier.** Create a key at <https://aistudio.google.com/apikey>; no billing is needed.

```text
LLM_PROVIDER=gemini
LLM_MODEL=gemini-3.5-flash-lite
LLM_API_KEY=your-key-here
```

**Use the free tier only with open-access papers.** Google's terms say free-tier content is used to improve its products and that human reviewers may read it, and advise against submitting sensitive or confidential material. You must be 18 or older.

**Anthropic Claude (paid).** Create a key at <https://platform.claude.com/settings/keys>, and use `LLM_PROVIDER=anthropic` with `LLM_MODEL=claude-haiku-5-5`. Anthropic's commercial API data is not used for training by default.

## Reporting checklist

A parsed paper's page has a **Reporting checklist** panel. It checks what the paper states about six reporting items and shows a status in words, with quoted evidence and its section and page. It gives no score or verdict, and **Not found in the material examined** is not a judgement about the paper.

Running it sends passages found in the paper to the configured provider, once per item. `GET /documents/{id}/assessment` returns the latest result and `POST` runs a new one. Earlier results are kept.

## Embeddings

Questions are answered with semantic retrieval by default, because it was measured to find more of the expected passages (`docs/experiments/retrieval-comparison.md`). It needs an embedding for each stored passage, made with `gemini-embedding-2` using the same `LLM_API_KEY`. New uploads are not embedded automatically: until they are, a question on them uses keyword search, and the answer names the method used. See how many are missing without sending anything:

```bash
uv run python scripts/embed_passages.py --check
```

Create the missing ones. This sends the text of those passages to Google, so use it only with papers you may send there. It is safe to run again, and continues after a rate limit:

```bash
uv run python scripts/embed_passages.py
```

## Important limits

- **Local, single-user only.** There is no authentication. Do not expose PaperPilot to a shared or public network (`NFR-SEC-006`).
- **Only upload papers you are allowed to use**, including sending their text to the configured AI provider (`NFR-PRI-001`, `RISK-13`). Papers are never committed to this repository.
- **Question answering sends text to an outside service (Phase 5).** With an API key configured, your question and the retrieved passages are sent to the provider you chose (`NFR-PRI-001`); PDFs are not. Running `scripts/embed_passages.py` also sends the text of every stored passage once. Nothing is sent without a key, and uploading and parsing stay on your machine. The terms differ a lot by provider, so read "Connecting an AI model" above and check the current terms before using papers that are not open access.
- **Never commit secrets.** Settings go in `.env`, which is ignored; `.env.example` lists placeholders only (`NFR-SEC-001`).
