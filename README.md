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
- Node.js 24 (frontend, later phases)

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

```bash
uv run mypy .
```

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

Stop the services (database data is kept in the `paperpilot_postgres-data` volume):

```bash
docker compose down
```

## Running the application

Not available yet. Commands for installing dependencies, running tests and running the application are added here when each one has been run and verified. Do not use commands that are not listed here.

## Important limits

- **Local, single-user only.** There is no authentication. Do not expose PaperPilot to a shared or public network (`NFR-SEC-006`).
- **Only upload papers you are allowed to use**, including sending their text to the configured AI provider (`NFR-PRI-001`, `RISK-13`). Papers are never committed to this repository.
- **Never commit secrets.** Settings go in `.env`, which is ignored; `.env.example` lists placeholders only (`NFR-SEC-001`).
