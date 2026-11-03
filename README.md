# PaperPilot

An evidence-first research intelligence and scientific-reproducibility platform. It turns academic papers into structured, searchable knowledge in which every derived statement links to a stored source passage.

**Status:** Phase 0 (environment setup). No application code exists yet. What is actually done and verified is recorded in [`progress.md`](progress.md).

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

Python tooling (uv, Python 3.14) is decided but not yet installed (P0-T4).

## Running the project

Not available yet. Commands for starting PostgreSQL and GROBID (P0-T3), installing dependencies, running tests and running the application are added here when each one has been run and verified. Do not use commands that are not listed here.

## Important limits

- **Local, single-user only.** There is no authentication. Do not expose PaperPilot to a shared or public network (`NFR-SEC-006`).
- **Only upload papers you are allowed to use**, including sending their text to the configured AI provider (`NFR-PRI-001`, `RISK-13`). Papers are never committed to this repository.
- **Never commit secrets.** Settings go in `.env`, which is ignored; `.env.example` lists placeholders only (`NFR-SEC-001`).
