# PaperPilot: Progress

This file records **what actually exists and has been verified**. It is not a plan (see `docs/implementation-roadmap.md`) and not a specification (see `PRD.md`). Update it only with facts. Rules for working are in `CLAUDE.md`.

## 1. Project status

| Field | Value |
|---|---|
| Project | PaperPilot |
| Current stage | Phases 0–5 complete. Papers can be uploaded, parsed and searched, and questions are answered with validated citations through the configured model. Phase 6 (evaluation and reliability) is in progress. |
| Overall status | `in_progress` |
| Last updated | 2026-11-09 |
| Current milestone | M8: Evaluation and reliability (`in_progress`: P6-T1 done). M7 `completed` 2026-11-09. M5 and M6 `completed` 2026-11-08; M1–M4 `completed` 2026-11-03. |
| Current phase | Phase 6, evaluation and reliability (`docs/implementation-roadmap.md`) |
| Next release target | VS-1 (see `PRD.md` §12.1) |

Generated documents and transcript analysis are **planning artefacts**. They are not implementation.

## 2. Milestone status

Milestones are proposals from the roadmap, not claims of completion. Statuses: `not_started`, `in_progress`, `blocked`, `completed`. A milestone becomes `completed` only with evidence in the "Evidence" column.

| ID | Milestone (Phase) | Status | Objective | Completion criteria (summary) | Evidence | Blockers / dependencies |
|---|---|---|---|---|---|---|
| M1 | Requirements and architecture documentation (0) | `completed` | Agreed PRD, rules, roadmap, status file | Developer has reviewed the four documents; `OQ-` triage recorded (roadmap P0-T1) | 2026-11-03: developer approved the architecture and incremental strategy; requested corrections applied and verified (§6.7 rows 8–9, §7); developer delegated the remaining Phase 0 decisions (§6.8); `OQ-` triage in §6.7 | None |
| M2 | Repository and development environment setup (0) | `completed` | Repo, Compose with PostgreSQL + GROBID, tooling, test conventions | A fresh clone plus README reproduces running services and a passing smoke test | 2026-11-03: fresh clone from GitHub plus README reproduced running services, passing unit and integration tests and the backend health check (§7); tooling decisions recorded with dates (§6.8) | None |
| M3 | GROBID parsing experiment (1) | `completed` | Learn real GROBID behaviour on 3–5 permitted papers | `docs/experiments/grobid-feasibility.md` with observations, failures, go/no-go | 2026-11-03: 5 papers processed and inspected; failure inputs attempted (real scanned paper impossible, reason recorded); answers in §7, limitations §8, representation `docs/design/parser-output.md`, decision go with limits (§9); PRD updated | M2 (minimal subset: P0-T2, P0-T3, Python environment) |
| M4 | Database schema and migrations (2) | `completed` | `papers`, `documents`, `passages` with constraints | Migration applies to an empty DB; constraint tests pass | 2026-11-03: migration `d2ea199dd3d3` applies to an empty database and reverses; all 38 named check/unique/foreign-key constraints have passing failing-case tests (62 integration tests); repeat-ingestion rules tested; immutability documented in `CLAUDE.md` and enforced by a trigger; only the three tables (plus `alembic_version`); `docs/design/schema.md` §10 | M3 |
| M5 | Paper ingestion and passage persistence (3) | `completed` | Upload → GROBID → passages, honest statuses | `AC-VS-01`..`AC-VS-04` evidenced | None | M4 |
| M6 | Keyword retrieval (4) | `completed` | PostgreSQL full-text retrieval; evaluation set; Recall@5 baseline | `AC-VS-05`; baseline file recorded | None | M5 |
| M7 | Evidence-backed question answering (5) | `completed` | Retrieval → structured answer → citation validation | `AC-VS-06`..`AC-VS-08` | None | M6; `OQ-011` |
| M8 | Evaluation harness (6) | `in_progress` | Repeatable evaluation; VS-1 acceptance | `AC-VS-09`, `AC-VS-10` | None | M7 |
| M9 | Structured extraction (7) | `not_started` | Datasets, metrics, limitations with evidence | `FR-EXT-*` criteria; baseline P/R/F1 | None | M7, M8; `OQ-006`, `OQ-009` |
| M10 | Semantic and hybrid retrieval (8) | `not_started` | Compare keyword/semantic/hybrid on the same set | `FR-RET-005..007`; recorded comparison | None | M6, M8; `OQ-012` |
| M11 | Academic paper discovery (9) | `not_started` | OpenAlex search, normalisation, duplicates | `FR-DIS-*` criteria | None | M4, M5; `OQ-007` |
| M12 | Cross-paper comparison (10) | `not_started` | Context-preserving matrices with comparability labels | `FR-CMP-*` criteria | None | M9; `OQ-008` |
| M13 | Reproducibility assessment (11) | `not_started` | Checklist with four statuses and evidence | `FR-REP-*` criteria | None | M5, M7, M8; `OQ-010` |
| M14 | Reliability and release readiness (gate) | `not_started` | Whole-system NFR, security, privacy, clean-environment check | All M14 tasks evidenced | None | M9–M13 |

Future extensions (Phase 12) are unscheduled.

## 3. Verified implementation inventory

Verification method and date are given for each line. "Not verified" means it could not be confirmed, not that it is absent.

### 3.1 Exists and verified

| Item | How verified | Date |
|---|---|---|
| Learning notes: `notes/architecture-notes-fullstack-rag.md`, `notes/architecture-notes-claude-code-rag.md`, `notes/implementation-notes.md`, `notes/claude-code-workflow.md`, `notes/knowledge-gaps.md` | Folder listing of the developer's connected folder | 2026-11-03 |
| Source transcripts: `transcripts/fullstack-rag.txt`, `transcripts/claude-code-rag.txt` | Same listing | 2026-11-03 |
| Planning documents: `PRD.md`, `CLAUDE.md`, `progress.md`, `docs/implementation-roadmap.md` | Created in this session; consistency scripts run on drafts (see §7) | 2026-11-03 |
| Git repository at `E:\dev\paperpilot` (branch `main`, first commit `e860441`), `.gitignore`, `.gitattributes`, `README.md` stub | `git check-ignore` tests and staged-content scan (see §7) | 2026-11-03 |
| Local services: `compose.yaml` (PostgreSQL 18 with pgvector available, GROBID 0.9.1 CRF), `.env.example` (compose settings only), local `.env` with a generated password (not committed); README commands | Started, queried and restarted (see §7) | 2026-11-03 |
| Python environment: uv 0.13.7, Python 3.14.10 on E: (`.python-version`), `pyproject.toml` with pytest/ruff/mypy, `uv.lock`; README and `CLAUDE.md` commands | Installed and run (see §7) | 2026-11-03 |
| Configuration: `backend/app/config.py` (`Settings`, `get_settings()`), complete `.env.example`, `tests/unit/test_config.py` (15 tests); dependencies pydantic and pydantic-settings | Tests, mutation check, lint and type check (see §7) | 2026-11-03 |
| Backend skeleton: `backend/app/main.py` (`create_app`, startup settings check), `api/health.py`, `schemas/health.py`; `tests/unit/test_health.py` (2 tests); dependencies fastapi, uvicorn; dev httpx | Tests, mutation check, real server run (see §7) | 2026-11-03 |
| Test conventions: `tests/conftest.py` (markers by folder), `tests/integration/` (GROBID fixture with loud failure, 2 tests), `tests/evaluation/README.md`; pytest `addopts` excludes `integration` and `evaluation` by default | Selection, failure-path and typo checks (see §7) | 2026-11-03 |
| `docs/experiments/grobid-feasibility.md` (P1-T1 to P1-T5); throwaway `scripts/grobid_experiment.py`, `scripts/inspect_tei.py`, `scripts/quote_match.py`, `scripts/grobid_failures.py`; TEI, pdfalto text, generated failure inputs and measurements in git-ignored `data/` | See §7 | 2026-11-03 |
| `docs/design/parser-output.md`: parser output contract (`ParsedDocument`, `ParsedPassage`), passage regions and rules, page rules, failure-reason mapping. Design only, not implemented | Rules checked against the five TEI outputs (see §7) | 2026-11-03 |
| `docs/design/schema.md`: `papers`, `documents`, `passages` columns, constraints, failure reasons, indexes, immutability trigger. Design only, not implemented | Key PostgreSQL features checked live (see §7) | 2026-11-03 |
| Database layer: `backend/app/database/` (engine, sessions), `backend/app/models/base.py` (naming convention), Alembic environment in `backend/migrations/` with settings in `pyproject.toml`; no tables yet; dependencies SQLAlchemy, Alembic, psycopg | Tests and Alembic commands (see §7) | 2026-11-03 |
| Core schema in PostgreSQL: `papers`, `documents`, `passages` (migration `d2ea199dd3d3`, models in `backend/app/models/`), immutability trigger on `passages` | Applied, inspected, downgraded and re-applied (see §7) | 2026-11-03 |
| DOI normalisation: `backend/app/services/doi.py` (`normalize_doi`), 31 unit tests | Tests and mutation check (see §7) | 2026-11-03 |
| Schema tests: `tests/integration/test_schema_migration.py` (2) and `test_schema_constraints.py` (51), on a throwaway database | Run and mutation-checked (see §7) | 2026-11-03 |
| File storage: `backend/app/storage.py` (save/read/delete by generated key, local folder `data/storage`), 28 unit tests | Tests, mutation check, probe (see §7) | 2026-11-03 |
| Upload validation: `backend/app/services/ingestion/validation.py` (empty, size, `%PDF-` signature by content; display-only filename), 34 unit tests | Tests, real-file run, mutation check (see §7) | 2026-11-03 |
| GROBID client: `backend/app/services/ingestion/grobid.py` (fixed privacy-safe request, timeout and 503 retries from settings, failure-reason mapping), 30 unit and 4 integration tests | Stub server, real GROBID, mutation check (see §7) | 2026-11-03 |
| TEI parsing: `backend/app/services/ingestion/tei.py` (`parse_tei`: metadata, four passage regions, pages from coordinates, rules R1/R2, `malformed_tei`/`empty_parse`), 38 unit tests | Tests, real-paper counts, mutation check (see §7) | 2026-11-03 |
| Ingestion pipeline: `backend/app/services/ingestion/pipeline.py` (register: store then create `pending`, cleanup on failure; process: `processing`, GROBID, store TEI, parse, one transaction for paper + passages + `parsed`; every expected failure `failed` with its reason; identical files return the existing document, also under concurrent uploads; `failed` documents can be retried; one `process` per document at a time), 24 integration tests | Tests, mutation check, real end-to-end run (see §7) | 2026-11-04 |
| Startup recovery: `backend/app/services/ingestion/recovery.py` (`recover_interrupted`: every `processing` document becomes `failed`/`interrupted`, start time kept; run from the app lifespan; startup fails if the database is unreachable), 6 integration and 4 unit tests | Tests, real server run, mutation check (see §7) | 2026-11-04 |
| Document API: `backend/app/api/documents.py` (upload as raw body with bounded reading, status, structure, retry; processing as a background task), `api/errors.py` (one error envelope, no internals), `schemas/documents.py`, read service `services/ingestion/documents.py`, `explanations.py`; 27 integration and 5 unit tests | Tests, mutation check, real server with GROBID (see §7) | 2026-11-04 |
| Frontend (P0-T8, P3-T9): `frontend/` with upload view and document view (real status with polling, failure explanation and Retry, metadata, section list, passages exactly as stored with page or "page unknown"), API client, design tokens; 24 tests | Tests, mutation check, browser run with real backend and GROBID (see §7) | 2026-11-08 |
| GitHub remote `origin`: https://github.com/rknishanth152-lgtm/paperpilot (private), `main` tracks `origin/main` | `gh repo view`, `git ls-remote` (see §7) | 2026-11-03 |
| Claude Code development skills (project-local, see §3.5) | Fresh headless Claude Code session listed all eight skills; see §7 | 2026-11-03 |
| `docs/design-system.md`, status **proposed**: motion principles, provisional motion tokens and patterns; visual tokens not yet defined | File created; nothing implemented or browser-tested | 2026-11-03 |

### 3.2 Not present (as of the listing above)

- Application code (backend, frontend), tests, migrations, `docker-compose.yml`, `.env.example`, `.gitignore`, `README.md`, `scripts/`, `benchmarks/`.
- No version-control repository was visible in the folder listing. This was **not verified by running a version-control command** (the listing may omit hidden entries).

### 3.3 Not verified

- Whether any other PaperPilot code exists elsewhere on the developer's computer.
- Whether Docker, Python, Node, PostgreSQL or GROBID are installed on the developer's machine.
- Whether the connected folder is intended to become the project repository or the project will live in a separate directory (see §6).

### 3.4 Tests and integrations

No application tests exist. No integration (GROBID, PostgreSQL, LLM provider, OpenAlex) has been set up or exercised.

### 3.5 Development tooling for Claude Code (not application code)

Installed 2026-11-03 after the developer approved the set. All of it is project-local, under `.claude/`. Each copied skill has its upstream `LICENSE` and a `SOURCE.md` giving the upstream commit and any local changes.

| Skill | Location | Source · licence | Role |
|---|---|---|---|
| `paperpilot-engineering` | `.claude/skills/paperpilot-engineering/` | Written for this project | Provenance, citation validity vs claim support, `not_found`/`needs_review`, comparison context, FastAPI/React checklists, UI page process, state testing, verification |
| `frontend-design` | Plugin `frontend-design@claude-plugins-official` v1.1.1, enabled in `.claude/settings.json`. The install record is per folder: after cloning or moving the repository, re-run `claude plugin install frontend-design@claude-plugins-official --scope project` there | Anthropic · Apache-2.0 | Visual direction, avoiding templated design |
| `ui-ux-pro-max` | `.claude/skills/ui-ux-pro-max/` | nextlevelbuilder @713eef5 · MIT | Searchable UX/accessibility/typography guidance (local Python script). GSAP output is overridden by `paperpilot-engineering` |
| `design-motion-principles` | `.claude/skills/design-motion-principles/` | kylezantos @4a9ca87 · MIT | Motion creation and audit |
| `test-driven-development`, `systematic-debugging`, `verification-before-completion` | `.claude/skills/<name>/` | obra/superpowers @2ce8aa1 · MIT | Process discipline. The rest of Superpowers was deliberately not installed (its startup hook conflicts with `CLAUDE.md` §12) |
| `playwright-cli` | `.claude/skills/playwright-cli/` | Microsoft `@playwright/cli` 0.1.23 · Apache-2.0 | Browser checks. Run as `npx -y @playwright/cli@0.1.23 <command>`; uses the installed Chrome. No global install and no project dependency |

Rejected: `ghalex/skills` (no licence file; requires auth, Redux and a monorepo layout, which conflicts with the PRD) and pedronauck `motion-react` (no longer in the repository; its origin is marked unresolved upstream). No npm/Python packages were added to the project. Motion for React is not installed (an `OQ-014` decision when the frontend starts).

## 4. Current work

| Field | Value |
|---|---|
| Task | Phase 6 (M8): evaluation and reliability. P6-T1 `completed`: one command, `tests/evaluation/run_evaluation.py`. Phases 3 to 5 are `completed`; their task record is in §5 and §7. |
| Inputs | `docs/design/parser-output.md`, `docs/design/schema.md`, PRD `FR-ING-001`..`FR-ING-010`, `NFR-SEC-002`, `AD-002` |
| Status | Phase 5 `completed`; Phase 6 `in_progress`: P6-T1 `completed`, **P6-T2** next. Phases 0 to 5 are `completed` (M1 to M7). |

Summary of what is done (details in §3, §6 and §7): planning documents reviewed and approved (P0-T1); repository on E:, private on GitHub (P0-T2); PostgreSQL 18 and GROBID 0.9.1 via Compose (P0-T3); Python 3.14 with uv, pytest, ruff, mypy (P0-T4); settings module (P0-T5); FastAPI skeleton with `/health` (P0-T6); test conventions (P0-T7); GROBID experiment, decision **go with limits** (Phase 1); parser-output contract and schema design notes; database layer and Alembic; tables `papers`, `documents`, `passages` with an immutability trigger; DOI normalisation; 112 tests (Phase 2). Standing rule: every GROBID request sends `consolidateHeader=0`.

## 5. Next actions

In dependency order (roadmap Phase 3).

1. ~~P3-T1~~ `completed`: `backend/app/storage.py`.
2. ~~P3-T2~~ `completed`: `backend/app/services/ingestion/validation.py`. The bounded reading carried from here was done in P3-T8.
3. ~~P3-T3~~ to ~~P3-T8~~ `completed`. TEI files from failed attempts stay in storage, unreferenced; nothing is deleted automatically (`DR-008`). A database failure in the final ingestion transaction leaves the document `processing` until the next startup marks it `interrupted` (P3-T7). Recovery assumes one server process; FR-ING-010's timeout alternative is not built (it needs a periodic job). Only WARNING-level log lines are visible under uvicorn's default logging (the per-document `interrupted` line shows; the `recovered=N` INFO summary does not); logging configuration is not yet set up.
4. ~~P0-T8~~ and ~~P3-T9~~ `completed`. ~~P3-T10~~ `completed`, M5 `completed`. ~~P4-T1~~ `completed`: interim full-text configuration in `docs/design/retrieval.md` (`OQ-004` stays open until P4-T7). ~~P4-T2~~ `completed`: `passages.search_vector` and its GIN index (migration `e3ab5ad233d7`). ~~P4-T3~~ `completed`: `search_passages` in `backend/app/services/retrieval/keyword.py`, setting `MAX_QUERY_CHARS`. ~~P4-T4~~ `completed`. ~~P4-T5~~ and ~~P4-T6~~ `completed`: reviewed set `benchmarks/retrieval_eval_v1.json`, harness `tests/evaluation/`. ~~P4-T7~~ `completed`: baseline Recall@5 8/16 across all papers, 9/16 within the question's paper, all 8 misses vocabulary mismatches (`docs/experiments/retrieval-baseline.md`). `OQ-004` stays interim; `OQ-002` rules stand, not proven by 16 questions. A retrieval score cannot decide "not enough evidence" (`FR-QA-004`). ~~P5-T1~~ `completed`: interim model Claude Haiku 5.5 (§6.13). ~~P5-T2~~ `completed`: `backend/app/services/llm.py` (shared by answering and later extraction, so outside any one capability; setting `LLM_TIMEOUT_SECONDS`). The Anthropic adapter, which maps its SDK's exceptions to these errors and applies the timeout, is not built: it comes with the real-model step and needs the `anthropic` dependency, to be confirmed then. ~~P5-T3~~ `completed`: `backend/app/schemas/answer.py`. Structure only: unknown aliases and uncited statements are parsed so the citation validator (P5-T7) can report them. ~~P5-T4~~ `completed`: `backend/app/services/answering/context.py` (new `answering` module, as the roadmap asks to record). ~~P5-T5~~ `completed`: `answering/pipeline.py` and `prompt.py`; retry policy: malformed output is resent unchanged, once by default, then an explicit error; provider errors are not retried here. ~~P5-T6~~ `completed`: `answering/quotes.py`, `OQ-013` resolved for VS-1 (§6.14). The retrieval harness keeps its own earlier matching rule, so the saved baseline stays comparable. ~~P5-T7~~ `completed`: `answering/citations.py`. ~~P5-T8~~ `completed`. Because any matching word retrieves a passage, an out-of-corpus question usually still reaches the model, which must then say `insufficient`; P5-T12 measures that. ~~P5-T9~~ `completed`: `Answering.answer` runs the whole chain; `schemas/answer_response.py`, `answering/response.py`. ~~P5-T10~~ `completed`: `tests/integration/test_answering_faults.py`, covering every roadmap case and `AC-VS-08`, with the fake model. ~~P5-T11~~ `completed`: `POST /answers`, `QuestionPanel` on the document view. Answers return `503 model_not_configured` until the provider adapter exists. **P5-T12** `in_progress`: the adapter is built and tested offline (`services/llm_anthropic.py`). The developer approved `anthropic` 2.6.0, then could not pay Anthropic's minimum and chose the Gemini free tier (§6.13); `services/llm_gemini.py` is built and tested offline. ~~P5-T12~~ `completed`: `docs/experiments/answer-baseline.md`. Interim model `gemini-3.5-flash-lite`; `OQ-011` stays interim because no model comparison finished. The developer's `.env` now names `gemini-3.5-flash-lite`. To compare models later, rerun `tests/evaluation/run_answers.py` on `gemini-3.6-flash` after Google's daily quota resets (midnight Pacific). The `anthropic` package and an API key are needed only from the real-model step; no paper text is sent before P5-T12, and that first send needs the developer's go-ahead then. Carried to P4-T5: do not use the six probe queries listed in `retrieval.md` §5. Broken ligatures and leaked figure text: baseline first, then a before/after in P4-T7 in the search representation only, never in `passages`.
5. P0-T9 (CI) remains deferred.
6. ~~P6-T1~~ `completed`: `run_evaluation.py`, `code_state.py`. Use the run at 9654929 for P6-T2 and P6-T3: it is the first complete run with a clean tree and its configuration recorded. **P6-T2** next.

## 6. Decisions and blockers

### 6.1 Decisions recorded in the PRD (reviewed and approved by the developer 2026-11-03, see §6.7)

`AD-001`..`AD-016` in `PRD.md` §4.3. The most consequential: modular monolith (`AD-001`), GROBID as initial parser pending the Phase 1 experiment (`AD-003`), paragraph-level passages as a hypothesis (`AD-004`), keyword retrieval before vectors (`AD-005`), plain RAG with no agent loop (`AD-006`), deterministic citation validation separate from claim support (`AD-008`), no authentication in the MVP (`AD-009`).

### 6.2 Open questions that block the next steps

| ID | Blocks | Note |
|---|---|---|
| OQ-017 | Resolved 2026-11-03 | Docker Desktop and WSL2 installed with program files and data on E:, verified (§7) |
| OQ-014 | Resolved | Python tooling installed; FastAPI and pydantic verified on 3.14 (§7). Frontend tools installed at P0-T8/P3 |
| OQ-015 | Resolved | Images pulled and running (§7) |
| OQ-001, OQ-002, OQ-003, OQ-005, OQ-013, OQ-016 | Answered by Phase 1 | Do not decide earlier |
| Others (`OQ-004`, `OQ-006`..`OQ-012`) | Later phases | See the PRD register |

### 6.3 Experiments needed

Phase 1 GROBID experiment; Phase 4 keyword baseline; Phase 8 retrieval comparison.

### 6.4 External dependencies

GROBID service; PostgreSQL (with pgvector available later); an LLM provider (undecided, `OQ-011`); OpenAlex (Phase 9). None has been set up or verified.

### 6.5 Known limitations of the planning documents

- Parts of the PRD are hypotheses from earlier tutorial-video analysis and tool documentation read during this project. GROBID endpoint details came from a documentation branch; pgvector limits came from a third-party summary. Both are marked for verification (`OQ-012`, `OQ-015`).
- Upload limit, timeouts and `k` values are placeholders.
- The documents were written without access to an existing codebase; they may need adjustment once the repository exists.

### 6.5a Pending decisions from the skills setup (2026-11-03)

- **PRD wording on UI quality.** Resolved 2026-11-03 by `NFR-UX-001` (§6.7 row 9).
- **`.gitignore` at P0-T2.** Running `playwright-cli` inside the project writes snapshots to `.playwright-cli/`, and `claude plugin` may write `.claude/settings.local.json`. Add both to `.gitignore`. Commit `.claude/settings.json` and `.claude/skills/`.

### 6.6 Repository location

**Decided 2026-11-03: `E:\dev\paperpilot`.** This replaces the earlier choice of `C:\dev\paperpilot` (P0-T1 review, same day). Reason for the change: C: has about 18 GB free and the developer cannot free space now; E: had about 232 GB free. The original reasons still apply: no OneDrive sync and no spaces in the path.

The **complete** learning folder is copied, including `notes/` and `transcripts/` (developer's choice; this replaces the earlier plan to leave them behind). The OneDrive original is kept until the developer deletes it. See §7 for the copy check.

### 6.7 P0-T1 review decisions (2026-11-03)

Findings were prepared by Claude, and the developer chose each resolution.

| # | Finding | Decision | Changed |
|---|---|---|---|
| 1 | Repository inside OneDrive, path contains a space | Move to `C:\dev\paperpilot` at P0-T2. **Superseded by row 10** | §6.6 |
| 2 | No Docker/WSL2; ~18 GB free on C: | Keep `AD-015`; developer frees space and installs WSL2 + Docker Desktop; check image size during P0-T3 | PRD `OQ-017` added |
| 3 | `FR-CIT-004` checked citations per answer, so uncited statements could pass | Every statement in a `sufficient`/`partial` answer needs ≥1 valid citation; `insufficient` answers have no statements | PRD `FR-CIT-004`, §9.1, `AC-VS-08`; roadmap P5-T10; skill |
| 4 | Answer persistence inconsistent (CLAUDE.md implied an answers table; PRD §8.2 had none) | Answers not persisted in VS-1; harness saves run artifacts | PRD §8.2, `DR-001` note; CLAUDE.md §4; skill |
| 5 | Wording: `FR-QA-001` cited §10.1 instead of §9.1; roadmap §2 listed P0-T1 as a Phase 1 prerequisite; `passages_dropped` missing from §9.1 | Fixed | PRD, roadmap |
| 6 | How a failed document is retried (re-upload vs explicit retry) is unspecified | Decided at P3-T8 (developer): explicit `POST /documents/{id}/retry`; re-uploading an identical file returns the document unchanged | §6.10 |
| 7 | UI-quality wording (§6.5a) | Resolved by row 9 | — |
| 8 | Second review: roadmap §2 diagram and Phase 0 row still listed P0-T1 as a Phase 1 prerequisite (header was already v0.2; Phase 1 row was already fixed) | Diagram and Phase 0 row corrected: Phase 1 needs P0-T2, P0-T3 and the Python environment; P0-T1 completes M1 only | Roadmap §2 |
| 9 | PRD did not state the expected UI quality; §5.10 says "minimal" | Added `NFR-UX-001` (interface quality). §5.10 notes that "minimal" means feature scope. No features added, no animation library mandated, no numerical targets. Reason: the developer explicitly wants a distinctive, high-quality frontend with polished, accessible motion, and a requirement makes that reviewable | PRD §5.10, §6, version 0.3; roadmap P3-T9, P5-T11, M14-T5; `docs/design-system.md`; skill |
| 10 | Developer cannot free space on C: | Repository location changed to `E:\dev\paperpilot`; complete folder copied; original kept | §6.6 |

Open-question triage: decide in Phase 0: `OQ-014` (Python subset), `OQ-015`, `OQ-017`. Answered by Phase 1: `OQ-001`, `002`, `003`, `005`, `013`, `016`. Later phases: as listed in the PRD register.

### 6.8 Phase 0 decisions (2026-11-03)

The developer asked Claude to settle the remaining Phase 0 questions with the best option for this product. Versions and facts below were read from official documentation on 2026-11-03. Nothing here is installed or verified yet unless §7 says so.

| Question | Decision | Reason | Revisit if |
|---|---|---|---|
| `OQ-017` local runtime | Keep `AD-015`. Developer installs WSL2 (`wsl --install --no-distribution`), then Docker Desktop with `--installation-dir=E:\Docker\DockerDesktop` and `--wsl-default-data-root=E:\Docker\wsl`. | Docker's docs list these installer flags; they keep program files and all images off C: (about 18 GB free). Firmware virtualization is on, a hypervisor is present, Windows 11 build 26300, LanmanServer is Automatic, 23.7 GB RAM. Docker Desktop is free for personal and educational use. | Installation fails, or Docker's resource use makes the laptop unusable |
| `OQ-015` GROBID image | `grobid/grobid:0.9.1-crf` (GROBID 0.9.1, latest stable). Port 8070 published as `127.0.0.1:8070` only. Run options from the docs: `--init --ulimit core=0`. | CPU-only laptop. GROBID docs recommend the lightweight CRF image when only full text is needed; about 0.5 GB versus 13.8 GB for the full deep-learning image, and the full image is much slower without a GPU. Full-text processing needs about 4 GB RAM. Binding to 127.0.0.1 meets `NFR-SEC-004`. | Phase 1 shows CRF output quality is inadequate; then test the `-full` image as a recorded experiment |
| `OQ-015` PostgreSQL image | `pgvector/pgvector:0.8.7-pg18-trixie` (PostgreSQL 18, latest stable major; pgvector 0.8.7). Port published as `127.0.0.1:5432` only. | Satisfies `AD-015`: plain PostgreSQL now; pgvector is installed in the image but stays unused until Phase 8 runs `CREATE EXTENSION vector`. Pinned tag for reproducibility. | A pgvector or PostgreSQL security release; update the pinned tag deliberately |
| `OQ-014` Python | Python 3.14, managed by **uv** and pinned in `.python-version` (not the system Python). | 3.14 is a supported bugfix release; cp314 Windows wheels were confirmed for SQLAlchemy 2.1.6, psycopg-binary 3.3.7, asyncpg 0.32.0, lxml 6.1.3, mypy 2.4.1. uv gives one tool for Python versions, virtual environments and a lock file. **FastAPI and pydantic support for 3.14 was not confirmed** (PyPI page blocked/truncated). | FastAPI or pydantic fails to install on 3.14 at P0-T4; then pin 3.13 with uv and record why |
| `OQ-014` backend libraries | FastAPI + Pydantic v2; SQLAlchemy 2.1 + Alembic (`AD-012`); **psycopg 3** (synchronous) as the driver; httpx for the GROBID client; lxml for TEI parsing. | Synchronous database access is easier to learn and debug; `AD-010` runs ingestion in-process, so async adds complexity without a measured need. psycopg 3 is the maintained PostgreSQL driver with Windows wheels. | Measured concurrency problems |
| `OQ-014` quality tools | pytest (test runner), ruff (lint and format), mypy (type check). | Widely used, maintained, Windows wheels available; ruff replaces several tools; matches `CLAUDE.md` §5 type-hint rule. | — |
| `OQ-014` frontend | Vite + React + TypeScript (strict). Package manager **npm** (changed from pnpm at P3-T9, see §6.11). Node 24 is already installed (Vite needs 20.19+ or 22.12+). **No component library, data-fetching library or animation library chosen now**: decided at P3-T9 against `NFR-UX-001`; Motion for React (`motion`, imported from `motion/react`) is the candidate if CSS transitions are not enough. | Avoids committing to libraries before the first page exists (`CLAUDE.md` §10). | — |
| Repository contents (P0-T2) | Commit `notes/` (the developer's own learning notes). Do **not** commit `transcripts/` (add to `.gitignore`). | Transcripts are third-party video content (`RISK-13`); notes are the developer's own writing. | — |
| OneDrive original folder | Left in place. The developer deletes it when satisfied. | Deleting the developer's data is the developer's call. | — |

### 6.9 PRD updates from Phase 1 (2026-11-03)

Developer approved recording the P1-T6 answers in the PRD (now v0.5). Reason: the open-questions register and `AD-004` should reflect evidence from the GROBID experiment (`docs/experiments/grobid-feasibility.md` §7) rather than pre-experiment assumptions.

| PRD item | Change |
|---|---|
| `OQ-001` | Answered: pages for every paragraph; flat sections; store `page_start` and `page_end` |
| `OQ-002` | Provisional: paragraph passages plus two repair rules; confirm with Recall@5 in Phase 4 |
| `OQ-003` | Answered: references are not passages in VS-1; back matter decided in P1-T7 |
| `OQ-005` | Answered: 50 MB default, configurable |
| `OQ-013` | Provisional: verify against passage text; normalisation rules tested in P5-T6 |
| `OQ-016` | Deferred: table cells to Phase 7; captions decided in P1-T7; tracing at Phase 6 |
| `AD-004` | Reason column notes that paragraph passages stand, with the two provisional repair rules |
| Appendix A.3 | Page/section assumption marked as checked; upload limit no longer a placeholder |
| `AD-003`, `FR-ING-003` (v0.7, P1-T8) | GROBID decision: go with limits, limits listed in `AD-003`; `FR-ING-003` points to the reason codes in the design note. Developer decided |
| `FR-ING-007`, §8.2 Passage (v0.6, P1-T7) | Passages come from abstract, body, captions and back matter (not references, footnotes or table cells), each with a region; a document is `parsed` only with at least one body passage. Developer chose the regions |

### 6.10 P3-T8 decisions (2026-11-04)

Developer chose both recommended options.

| Decision | Reason | Changed |
|---|---|---|
| Upload body is the raw PDF bytes, not multipart; optional `X-Filename` header (percent-encoded, display only) | No new dependency (`python-multipart`); the server stops reading once the body passes `MAX_UPLOAD_MB`, while multipart would spool the whole file first | PRD `FR-ING-001` input wording (v0.8) |
| Retry is explicit: `POST /documents/{id}/retry` for `failed` documents, and also `pending` ones (a stopped server can leave one `pending` before processing began; startup recovery only handles `processing`) | No hidden side effect on upload; the UI gets a Retry button | Closes §6.7 row 6 |
| Users see a plain-language `failure_explanation` per reason code, never the stored `failure_message` | `failure_message` is for developers (`NFR-SEC-005`, `FR-UI-001`) | `services/ingestion/explanations.py` |

### 6.11 P3-T9 decisions (2026-11-04 to 2026-11-08)

Developer decided each of these.

| Decision | Reason |
|---|---|
| Colour theme: cool neutrals (Mist, Frost, Ink), ink-blue accent, slate/ochre/moss/brick status pairs. The developer first asked for cooler neutrals than the warm proposal, then approved | `docs/design-system.md` §2 |
| npm instead of pnpm | pnpm on this machine is broken (answers `CommandNotFound`); npm ships with Node and needs no global install. `CLAUDE.md` §5 updated |
| IBM Plex Sans and Serif through `@fontsource` (OFL-1.1) | A matched pair for technical reading; self-hosted, so no font requests leave the machine |
| Dependencies: react, react-dom (MIT); vite, @vitejs/plugin-react, vitest, jsdom, Testing Library (react, dom, user-event), @types/react, @types/react-dom (MIT); typescript (Apache-2.0). Versions pinned exactly | No component, state, data-fetching, router or animation library: two views and CSS transitions do not need one |

### 6.12 P3-T10 manual run observations (2026-11-08)

Observations by Claude Code, from the development database and the running UI. The developer opened the app afterwards and reported on 2026-11-08: "everything is fine". No further detail was given, so the findings below are Claude Code's. Real papers: the Phase 1 set (CC BY), not committed. The GROBID model in use is the CRF image (`AD-003`).

| Paper | Upload to final status | Passages (abstract / body / caption / back) | Pages | Metadata |
|---|---|---|---|---|
| p1 BERT | 5.0 s | 128 (2 / 97 / 8 / 21) | 16 | Title and 4 authors correct. No DOI: the PDF prints none, so this is right |
| p2 eLife | 5.9 s | 104 (2 / 77 / 15 / 10) | 30 | Title, 7 authors, DOI correct |
| p3 PLoS Med | 2.0 s | 32 (1 / 24 / 6 / 1) | 6 | Title, author, DOI correct |
| p4 PLoS ONE | 2.0 s | 39 (1 / 29 / 6 / 3) | 5 | Title, 3 authors, DOI correct |
| p5 PLoS ONE | 1.8 s | 21 (3 / 12 / 2 / 4) | 4 | Title, 4 authors, DOI correct |

**What held up.** All five reached `parsed`. 324 passages, ordinals continuous, every passage has a page, no body page runs backwards, no body passage lacks a section.

**Page numbers against the PDFs.** Every passage was compared with `pdftotext` output for its stated page (315 checked; 9 had too little text to compare). The first and last 40 normalised characters were found on the stated pages for 291. For 23 of the other 24, most of the passage's text is still on its stated pages; the exact check failed on inline maths, footnote marks or leaked figure text. One is a real error: p1 passage 104 (caption of Table 2) mixes in body text from page 7 while recording only page 6.

**Parser limits seen (GROBID's output, shown as stored).**

| Limit | Where | Why it matters |
|---|---|---|
| Broken ligatures: `signifi cance`, `fi ndings`, `confl icts` | p3 only: 202 matches in 25 of 32 passages (regular-expression count). 0 in the other four | Keyword search for those words misses the passages (Phase 4) |
| Figure or table text taken as prose | p1 passages 15, 93 (end of a real paragraph), 122 (chart axis labels); p2 passage 100 (table cells, region `back`) | Noise in retrieval; could be cited as if it were prose |
| Caption mixed with body text | p1 passage 104 | Wrong content under a caption, and an incomplete page range |
| Text that is not a heading used as a section title | p3: `P` (a drop cap), two pull-quote sentences. p2: `Table 1 continued on next page`, `Papers Experiments Effects All outcomes`. p1: a sentence beginning `QNLI Question Natural...` | Section labels shown and later cited can be wrong; following passages inherit them |

None of these is a pipeline defect, and none is hidden: passages keep the parser's text unmodified (`DR-002`). Passages are immutable, so any correction is a decision about the parse step or the search index, not an edit.

### 6.13 P5-T1: model for answers (2026-11-08)

Developer's priority: a GitHub showcase, rarely used, free or minimal cost, with strong answers. **Decision (developer): Claude Haiku 5.5 (`claude-haiku-5-5`) as the interim default, plus one comparison run on the evaluation set against a stronger model at P5-T12.** The default changes if Haiku does clearly worse. The comparison model is confirmed at P5-T12; Claude Opus 5.5 is proposed. `OQ-011` stays interim until then. Claude Code is made by Anthropic and said so when presenting this.

Facts read from the providers' official pages on 2026-11-08. Costs per answer are **estimates** assuming 4,000 input and 1,500 output tokens; P5-T12 measures them.

| Model | $ per million tokens, input / output | Est. per answer | Answer format | Data use |
|---|---|---|---|---|
| Claude Opus 5.5 | 4 / 20 | $0.046 | Schema-enforced, except refusals, `max_tokens` and enum capitalisation | API inputs and outputs not used for training by default; deleted within 30 days, with exceptions |
| Claude Sonnet 5.5 | 2 / 10 | $0.023 | Same | Same |
| **Claude Haiku 5.5** | 0.10 / 0.50 (prompts up to 100,000 tokens) | $0.001 | Same | Same |
| GPT-6.1 Sol | 2 / 10 | $0.023 | Strict JSON schema | Not used for training by default; abuse logs up to 30 days |
| Gemini 3.8 Flash, paid | 0.75 / 3.75 until 2026-12-31, then 1.50 / 7.50 | $0.009 | JSON schema subset; docs advise checking values | Not used to improve products |
| Gemini, free tier | 0 | $0 | Same | Used to improve products; human reviewers may read it |

How paper text is shared (`NFR-PRI-001`): the question and the retrieved passages go to Anthropic's API; PDFs and full papers do not. Recorded in `README.md`. Not checked: Anthropic's minimum credit purchase, Gemini free-tier rate limits. Model quality on this task is unmeasured until P5-T12.

**Change, 2026-11-09 (developer):** Anthropic's minimum purchase of $5 was more than the developer could pay, so the interim provider is now the **Gemini free tier**, model `gemini-3.8-flash`. The developer confirmed sending the open-access evaluation papers to Google, with its conditions (18 or older, available region). The comparison at P5-T12 is against `gemini-3.5-flash-lite`, also free. From Google's pages, read 2026-11-09: both models are free of charge on the free tier; free-tier content is used to improve Google's products and human reviewers may read it; free-tier limits are shown only in AI Studio after sign-in. The Anthropic connector stays in the code for anyone with a paid account. Requests set `store: false`; Google's pages do not state its default or any retention period.

**Result, 2026-11-09:** `gemini-3.8-flash` was overloaded (503 and timeouts). `gemini-3.6-flash` gave 3 answers, then its free limit stopped it. `gemini-3.5-flash-lite` completed all 20, so it is the interim model. Real API responses confirmed the request format.

### 6.14 P5-T6: quote matching (`OQ-013`, 2026-11-08)

**Decision:** a quote matches if it is contained in the stored passage after Unicode NFKC, folding curly quotes and dashes, and ignoring all whitespace. Case is kept. This replaces the provisional rule, which only repaired splits after `fi`, `fl`, `ff`.

From `scripts/quote_rules.py` on the five papers (1,179 sentences) plus a follow-up check:

| Rule | Exact sentences | 17 hand-picked evaluation quotes | PDF spelling differs from stored (209) | Altered quotes accepted (of 5,251) |
|---|---|---|---|---|
| A: typography and whitespace | 1,179 | 15 | 0 | 5 |
| B: A plus split ligatures (provisional) | 1,179 | 17 | 83 | 5 |
| **C: ignore all whitespace** | 1,179 | 17 | 209 | 5 |

- **C's 209 is true by construction:** those sentences were located by ignoring spaces, so it shows the case is covered, not an independent score. The independent evidence is the 17 evaluation quotes and the 126 that B rejects, which were inspected: spacing only, such as `BERT BASE` / `BERTBASE` and `2018a;Radford` / `2018a; Radford`.
- **The 5 accepted alterations are not real misses:** dropping one dot from a dotted-leader row, or one part of a two-part fragment.
- **Known limit:** letters identical but spaced differently cannot be told apart. 68 distinct adjacent word pairs in these papers also form a word when joined, 497 of 29,630 pairs; most are harmless (`pre training`, `fi ndings`). One could change meaning: `not able` / `notable`, 2 occurrences. A test pins this. A match shows the words are present, never that they support a claim (`AD-008`).

## 7. Verification log

Only checks actually performed. Nothing in this log refers to application behaviour, because none exists.

| Date | Check | Result |
|---|---|---|
| 2026-11-03 | Listed the developer's connected folder recursively | `notes/` (5 files) and `transcripts/` (2 files) present; no `PRD.md`, `CLAUDE.md`, `progress.md`, `docs/` before this work |
| 2026-11-03 | Script check on the drafted PRD, CLAUDE.md and roadmap: every requirement/decision/question/risk/acceptance ID (`FR-`, `NFR-`, `AD-`, `OQ-`, `RISK-`, `DR-`, `AC-VS-`) referenced in any document is defined in the PRD; milestone numbers within M1–M14; Markdown code fences balanced; table rows have consistent column counts; relative links resolve | Passed on the three drafted files (PRD.md, CLAUDE.md, docs/implementation-roadmap.md) |
| 2026-11-03 | Same script re-run on all four files after `progress.md` was written | Passed: all referenced IDs defined, fences balanced, table columns consistent |
| 2026-11-03 | Cross-document script: milestone→phase mapping in roadmap vs this file; every `P<n>-T<m>` reference has a definition; every `FR-` ID defined in the PRD is mentioned in the roadmap | Passed (no mismatches; no uncovered requirement IDs) |

| 2026-11-03 | `claude plugin list` | `frontend-design@claude-plugins-official` 1.1.1, scope project, enabled |
| 2026-11-03 | Headless `claude -p` session in this folder asked to list its skills | Listed `paperpilot-engineering`, `ui-ux-pro-max`, `design-motion-principles`, `playwright-cli`, `test-driven-development`, `systematic-debugging`, `verification-before-completion`, `frontend-design:frontend-design` |
| 2026-11-03 | `python -I .claude/skills/ui-ux-pro-max/scripts/search.py "evidence citation panel focus" --domain ux` | Returned 3 results from local `ux-guidelines.csv` |
| 2026-11-03 | `npx -y @playwright/cli@0.1.23 open "data:text/html,<h1>ok</h1>"`, then `close`, run outside the project folder | Opened the page in the installed Chrome, returned a page snapshot, closed cleanly. No Playwright browser download |
| 2026-11-03 | Environment check for P0-T3: `docker` command, `wsl.exe --status`, free space on C:, physical memory | No Docker; WSL not installed; about 18 GB free on C: (95% used); about 23.7 GB RAM |
| 2026-11-03 | After the P0-T1 edits, a script check on PRD, CLAUDE.md, progress.md, roadmap, design-system.md and the project skill: every referenced `FR-`/`NFR-`/`DR-`/`AD-`/`OQ-`/`RISK-`/`AC-VS-` ID is defined in the PRD; code fences balanced; table rows in each table have consistent column counts | Passed (146 IDs defined, no problems). Structural only; it does not show the documents are correct |

| 2026-11-03 | Second review round: inspected `docs/implementation-roadmap.md` | Header was already v0.2 and the Phase 1 row was already fixed; the §2 diagram and the Phase 0 row still listed P0-T1 as a Phase 1 prerequisite. Both corrected and the edited lines re-read |
| 2026-11-03 | Cross-document script after the second round (PRD, CLAUDE.md, progress.md, roadmap, design-system.md, project skill): IDs defined, `P<n>-T<m>`/`M14-T<n>` references defined, every PRD `FR-` ID covered in the roadmap, milestone→phase mapping matches between roadmap and this file, fences balanced, table columns consistent, no `P0-T1..T3` or `0.1 (draft` left | Passed: 147 IDs, 103 tasks, 14 milestones compared, no problems. Re-run on the E: copy: same result |
| 2026-11-03 | Copied the complete folder from OneDrive to `E:\dev\paperpilot`; SHA-256 of every file compared | 118 files on each side, all hashes identical. Original left in OneDrive |
| 2026-11-03 | From `E:\dev\paperpilot`: headless Claude Code session asked for its skills | The seven `.claude/skills/` skills were listed; `frontend-design` was **missing** because its plugin install record was bound to the old folder path |
| 2026-11-03 | Re-ran `claude plugin install frontend-design@claude-plugins-official --scope project` from `E:\dev\paperpilot`, then asked a headless session again | Plugin registered for `E:\dev\paperpilot`; `.claude/settings.json` unchanged; session reported `frontend-design:frontend-design` |

| 2026-11-03 | Read-only system check for Docker: CPU virtualization, hypervisor, OS build, winget, LanmanServer, free space on E: | Virtualization enabled in firmware; hypervisor present; Windows 11 Home build 26300; winget 1.29; LanmanServer running, Automatic; E: 232.1 GB free |
| 2026-11-03 | Official docs read for `OQ-014`, `OQ-015`, `OQ-017` (Docker Desktop Windows install page; GROBID Docker and service docs and releases; pgvector README and Docker Hub; postgresql.org versioning; Python devguide; PyPI pages; uv, Vite, pnpm, Motion docs) | Facts recorded in §6.8. Gaps: FastAPI and pydantic PyPI pages not read; Motion version and licence not read |

| 2026-11-03 | Cross-document script on the E: copy after the Phase 0 decisions (same checks as above, plus milestone status values) | Passed: 147 IDs, 103 tasks, 14 milestones; M1 `completed`, M2 `not_started`; no problems |

| 2026-11-03 | Verification after the developer reported Docker installed: `wsl --version`, `wsl -l -v`, `docker version`, install folders, Downloads installer file, uninstall registry entries, services, last boot time | **Not installed.** WSL reports "not installed"; `docker` command not found; `E:\Docker` absent; no Docker or WSL uninstall entries; installer not in Downloads; no restart since 17:23 the same day. `OQ-017` stays open |

| 2026-11-03 | Second verification after the developer installed Docker Desktop (all-users, WSL 2): `wsl --version`, `wsl -l -v`, `docker version`, install folders | WSL 3.0.3.0 installed (kernel 6.18.54.1), no distributions yet. Docker Desktop program files at `E:\Docker\DockerDesktop`; nothing under `C:\Program Files\Docker`. Docker CLI 29.9.2 works, but the **engine is not running** (cannot connect to `docker_engine`) and `E:\Docker\wsl` does not exist yet. Data location and `hello-world` not yet verified |

| 2026-11-03 | Third verification, Docker Desktop engine running: `docker version`, `docker info`, `wsl -l -v`, location of WSL disk files, `docker run --rm hello-world`, free space | Engine 29.9.2 linux/amd64 (20 CPUs, about 12 GB memory available to Docker). WSL distribution `docker-desktop` running, version 2. Data disks on E: (`E:\Docker\wsl\disk\docker_data.vhdx`, `E:\Docker\wsl\main\ext4.vhdx`); none under `%LOCALAPPDATA%\Docker`. Docker's bin folder is on the system PATH. `hello-world` printed "Hello from Docker!" and exited 0; its image was then removed. (The first attempt failed only because the checking shell predated the install and lacked the new PATH.) Free space afterwards: C: 15.2 GB, E: 227.3 GB. **`OQ-017` resolved.** |

| 2026-11-03 | P0-T2: `git init -b main` in `E:\dev\paperpilot`; dummy `.env`, `.env.local`, `data/probe.txt`, `probe.pdf`, `.claude/settings.local.json`, `.venv/`, `node_modules/` created and checked with `git check-ignore -v` and `git status`, then deleted | All ignored by the intended `.gitignore` rule; `transcripts/` ignored; `notes/`, `README.md`, `.claude/settings.json`, skills and `.env.example` not ignored |
| 2026-11-03 | P0-T2: `git add -A` (staged, **not committed**); staged-file summary; `git grep --cached` for API-key, token, private-key and database-URL patterns | 116 files staged; no PDF, `.env` or transcript staged. One match: `token: 'mock-token'` in a Playwright skill documentation example (not a secret). No credentials found |

| 2026-11-03 | P0-T2 first commit: identity re-checked, staged set and secret scan re-run, `git commit`, then `git log` and `git ls-tree` | Commit `e860441` on `main`, author `rknishanth152-lgtm <rknishanth.152@gmail.com>`, 116 files; no PDF, `.env` or transcript in the commit. Secret-pattern hits were false positives ("task-based" in two documentation URLs). **P0-T2 `completed`** |

| 2026-11-03 | P0-T3: pulled `pgvector/pgvector:0.8.7-pg18-trixie` and `grobid/grobid:0.9.1-crf`; inspected image config | Size on disk 652 MB and 1.72 GB (larger than the compressed sizes in the docs). PostgreSQL image: `PGDATA=/var/lib/postgresql/18/docker`, volume `/var/lib/postgresql`. GROBID image includes `curl`; no built-in health check |
| 2026-11-03 | P0-T3: `docker compose config --quiet` (values not printed), then `docker compose up -d --wait` | Config valid (Compose v5.6.1). Both containers healthy after 22 s; ports `127.0.0.1:5432` and `127.0.0.1:8070` |
| 2026-11-03 | P0-T3: GROBID `GET /api/isalive`, `/api/version`, `/api/health` from the host | `true` (200); version 0.9.1; ready, 12 CRF (wapiti) models loaded, 0 failed |
| 2026-11-03 | P0-T3: PostgreSQL queries via `docker compose exec` | PostgreSQL 18.6; database and user `paperpilot`; `vector` 0.8.7 available, not installed; data directory `/var/lib/postgresql/18/docker` |
| 2026-11-03 | P0-T3: exposure checks (`NFR-SEC-004`) | Listeners only on `127.0.0.1` for 5432 and 8070; admin port 8071 not published; connections to 5432 and 8070 on the Wi-Fi address refused |
| 2026-11-03 | P0-T3: persistence check: created a marker table, `docker compose down`, `docker compose up -d --wait`, read it back, dropped it | Row present after restart; table dropped; both services healthy again |
| 2026-11-03 | P0-T3: `docker stats --no-stream` at idle | GROBID about 3.16 GiB, PostgreSQL about 73 MiB, of 11.24 GiB available to Docker. **P0-T3 `completed`** |

| 2026-11-03 | P0-T4: `winget install --id astral-sh.uv -e --scope user` | uv 0.13.7 installed; installer hash verified by winget; uv folder and `.local\bin` present in the real user PATH (read via WMI) |
| 2026-11-03 | P0-T4: `uv python install 3.14` with default settings | **Failed**: the Claude desktop app is a packaged app and Windows redirected its writes under `%APPDATA%` to the app's private folder, leaving uv's version link pointing at a missing directory. Broken install removed with `uv python uninstall 3.14`; a broken `python3.14.exe` shim it created in `.local\bin` was replaced |
| 2026-11-03 | P0-T4: reinstalled with `UV_PYTHON_INSTALL_DIR=E:\uv\python`, `UV_CACHE_DIR=E:\uv\cache`; then set both as user environment variables (developer approved) via WMI and read them back | Python 3.14.10 runs from E: (OpenSSL 3.5.9, `ssl`/`sqlite3`/`venv` import); both variables present in the real user registry |
| 2026-11-03 | P0-T4: `uv python pin 3.14`, `pyproject.toml` (dev group: pytest, ruff, mypy), `uv sync` | `.python-version` = 3.14; `.venv` created with CPython 3.14.10; pytest 9.2.0, ruff 0.17.3, mypy 2.4.1; `uv.lock` written |
| 2026-11-03 | P0-T4: `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy .`, `uv run pytest -q` | First ruff run found 53 issues, all in vendored `.claude/skills/ui-ux-pro-max/scripts`; `.claude` excluded. ruff 0.17 also formats Markdown code blocks, so ruff is limited to `*.py`/`*.pyi`. Then ruff check and format check pass (no Python files yet); mypy exit 2 (no Python files); pytest exit 5 (no tests). Expected before P0-T6 |
| 2026-11-03 | P0-T4: throwaway venv on E: with fastapi, pydantic, sqlalchemy, alembic, psycopg[binary], httpx, lxml, uvicorn; imported each; venv deleted | All install and import on Python 3.14.10: fastapi 0.162.0, pydantic 2.14.2 (core 2.50.2), SQLAlchemy 2.1.6, Alembic 1.20.1, psycopg 3.3.7 (binary implementation), httpx 0.28.1, lxml 6.1.3, uvicorn 0.54.0. Python 3.14 confirmed for `OQ-014`. **P0-T4 `completed`** |

| 2026-11-03 | P0-T5: `uv add pydantic pydantic-settings` (developer approved the new dependency) | pydantic 2.14.2, pydantic-settings 2.16.2 (MIT), plus python-dotenv 1.2.4 and two small helpers as their dependencies |
| 2026-11-03 | P0-T5: `uv run pytest` on `tests/unit/test_config.py` | 15 passed |
| 2026-11-03 | P0-T5: mutation check: removed `env_ignore_empty` and the empty-password check, ran the tests, restored the file (hash identical) | The two expected tests failed (`test_empty_password_is_rejected`, `test_values_are_read_from_env_file`); 15 passed after restore |
| 2026-11-03 | P0-T5: `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy .` (strict, pydantic mypy plugin) | All passed; mypy: no issues in 3 source files |
| 2026-11-03 | P0-T5: loaded the developer's real `.env` through `get_settings()`, printing only non-secret facts | Loaded; password present; GROBID URL default; storage `data/storage`; no LLM configured. **P0-T5 `completed`** |

| 2026-11-03 | GitHub: installed GitHub CLI 2.103.3 (`winget install --id GitHub.cli -e --scope user`); developer ran `gh auth login`; scanned all commits for `.env`, PDFs, transcripts and local settings; `gh repo create paperpilot --private --source . --remote origin --push`; `gh repo view` | Logged in as `rknishanth152-lgtm`. History clean (5 commits). Repository `rknishanth152-lgtm/paperpilot` created, visibility `PRIVATE`, default branch `main`; remote `main` = local `62b1233`. Developer asked for commits to be pushed after each verified step |

| 2026-11-03 | P0-T6: `uv add fastapi uvicorn`; `uv add --dev httpx` (FastAPI test client) | fastapi 0.162.0 (MIT), starlette 1.10.0, uvicorn 0.54.0, httpx 0.28.1 (BSD-3-Clause); FastAPI also pulls in `opentelemetry-api` 1.45.2 |
| 2026-11-03 | P0-T6: `uv run pytest` (config and health tests) | 17 passed. Warning: Starlette deprecates `httpx` for its test client and suggests `httpx2`; not acted on (provenance unchecked; httpx is also the chosen GROBID client). Revisit at P3-T3 |
| 2026-11-03 | P0-T6: mutation check: health route made to raise, smoke tests run, file restored (hash identical) | `test_health_returns_ok` failed as expected; all pass after restore |
| 2026-11-03 | P0-T6: `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy .` | All passed; mypy: no issues in 9 source files |
| 2026-11-03 | P0-T6: started `uv run uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000` with the real `.env`; `GET /health`, `GET /does-not-exist`; listener and Wi-Fi checks; stopped | Startup complete; `/health` 200 `{"status":"ok"}`; unknown route 404 `{"detail":"Not Found"}`; listening on 127.0.0.1 only; refused on the Wi-Fi address; port free after stop. **P0-T6 `completed`** |

| 2026-11-03 | P0-T7: pytest selections: `uv run pytest`, `-m integration`, `-m evaluation`, `--collect-only` | Default: 17 passed, 2 deselected. Integration: 2 passed (GROBID alive, version 0.9.1). Evaluation: no tests yet (exit 5). The two integration tests carry the marker from their folder |
| 2026-11-03 | P0-T7: stopped GROBID, ran `-m integration`, then the default run, restarted GROBID | Integration errored with "GROBID is not reachable at http://127.0.0.1:8070 (ConnectError). Start the services with `docker compose up -d --wait`."; the default run still passed offline (17); GROBID healthy again and integration 2 passed |
| 2026-11-03 | P0-T7: temporary test using an unregistered marker (`integrashun`), then removed | Rejected: "'integrashun' not found in `markers` configuration option" |
| 2026-11-03 | P0-T7: `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy .` | ruff passed; mypy first reported two modules named `conftest`; fixed with `explicit_package_bases`; then no issues in 12 source files. **P0-T7 `completed`** |

| 2026-11-03 | M2 fresh-clone check: `git clone` from GitHub into a new folder (`f5e9c32`, 134 files; no `.env`, `.venv`, `data/` or transcripts); `uv lock --check`; `uv sync --locked`; `.env` created from `.env.example` with a new password | Lock matches `pyproject.toml`; fresh `.venv` with Python 3.14.10 and 31 packages |
| 2026-11-03 | M2 fresh-clone check: original services stopped (volume kept); clone services started with `docker compose up -d --wait` under a throwaway project name (`COMPOSE_PROJECT_NAME=paperpilot-freshcheck`) so a new database volume was created | Both healthy after 22 s on 127.0.0.1; GROBID `isalive` true. Finding: the fixed project name means a second checkout would otherwise take over the same containers and volume; documented in README |
| 2026-11-03 | M2 fresh-clone check, in the clone: `uv run ruff check .`, `ruff format --check .`, `mypy .`, `pytest`, `pytest -m integration`, then uvicorn and `GET /health` | All exit 0: 17 unit passed, 2 integration passed, mypy no issues in 12 files; `/health` 200 `{"status":"ok"}` |
| 2026-11-03 | M2 fresh-clone check cleanup: `docker compose down -v` for the throwaway project; original `docker compose up -d --wait`; clone folder deleted | Throwaway containers, network and test volume removed; original services healthy with `paperpilot_postgres-data` intact; clone removed. **M2 `completed`** |

| 2026-11-03 | P1-T1: read the current GROBID service, consolidation, coordinates, configuration, docker, TEI and flavor documentation | Recorded in `docs/experiments/grobid-feasibility.md` §2 |
| 2026-11-03 | P1-T1: compared the docs with the running GROBID: image `grobid.yaml` key settings; `POST` with no file; `GET` on the full-text endpoint; outbound reach from the container to `api.crossref.org` | 400 and 405 as documented. Image config differs from docs: pdfalto `timeoutSec` 120 (docs 60), `blocksMax` 200000 (docs 100000). Consolidation service is CrossRef with no `mailto`, and the container can reach CrossRef: with the default `consolidateHeader=1` extracted metadata would leave the machine. **P1-T1 `completed`** |
| 2026-11-03 | UI direction from the developer: light theme, no dark/neon look, polished motion, colour theme explained before any UI is built | Recorded in `docs/design-system.md` §1 and the page-process skill reference |

| 2026-11-03 | P1-T2: licence checks on publisher pages for candidate papers | CC BY shown for ACL Anthology N19-1423, eLife 71601, PLOS Med e124, PLOS ONE e308 and e24357. Not CC BY: arXiv 2304.02643, 2010.11929, 1706.03762 (arXiv non-exclusive licence); JMLR v15 srivastava14a ("© JMLR 2014"). Excluded |
| 2026-11-03 | P1-T2: HEAD checks, then download of the 5 approved PDFs (developer approved, about 3.2 MB) into `data/papers/` | All 5 are `application/pdf`, start with `%PDF-`, and are git-ignored; sizes and SHA-256 in the experiment doc §3. The eLife signed download link returned HTML, so the eLife CDN URL was used. **P1-T2 `completed`**. No scanned PDF with a verified licence was found |

| 2026-11-03 | P1-T3: `scripts/grobid_experiment.py` checked with ruff and mypy (one mypy finding fixed: httpx form data must be a mapping); unit tests still 17 passed | Clean |
| 2026-11-03 | P1-T3: ran the script twice on the 5 papers (`consolidateHeader=0`, coordinates for p/head/figure/biblStruct) | All HTTP 200; pages 16/30/6/5/4; run 1 1.4–11.0 s (first request includes warm-up), run 2 1.4–2.9 s. Details in the experiment doc §4 |
| 2026-11-03 | P1-T3: compared TEI from two runs; searched TEI for consolidation markers and the GROBID log for CrossRef | Outputs identical after removing random `generateIDs` IDs and the `when` timestamp; `generateIDs` IDs are random per run. No consolidation markers; no CrossRef in the log. **P1-T3 `completed`** |

| 2026-11-03 | P1-T4: `scripts/inspect_tei.py` on the 5 TEI outputs (ruff, mypy clean) | Every body paragraph (242/242) and heading has a page from `coords`; 1–14 paragraphs per paper span two pages; sections always flat; no `<pb>`; running headers/footers go to body `note`, not paragraphs. Problems: paragraphs split mid-sentence at column/page breaks (0–3 per paper), BERT footnotes in body text, PLOS Medicine sidebar text as sections, several figure/table misclassifications, BERT appendix in `back` |
| 2026-11-03 | P1-T4: pdfalto 0.6.2 in the GROBID container extracted each PDF's text layer; `scripts/quote_match.py` searched GROBID body sentences in it at three normalisation levels | Found: 24–85% (whitespace only), 63–86% (ligatures, hyphenation), 78–93% (no spaces or hyphens). Causes of the remaining misses confirmed on examples: GROBID rewrites citation markers ("[9–11]" → "[9][10][11]"), mid-word ligature splits from the PDF itself ("confi rmation"), different text order. **P1-T4 `completed`** |

| 2026-11-03 | P1-T5: `scripts/grobid_failures.py inputs` (ruff, mypy clean): 11 generated inputs | Non-PDF, empty, corrupt and truncated: 500 `BAD_INPUT_DATA`. Image-only, blank, 64 MB image: 500 `NO_BLOCKS`. 3,000 pages: 500 `TOO_MANY_TOKENS` (2,883,000 tokens, limit 1,000,000). Synthetic 1- and 300-page text: **200 with an empty body** (text in `back`). Details in the experiment doc §6 |
| 2026-11-03 | P1-T5: `scripts/grobid_failures.py service` | GROBID stopped: `ConnectError`. Stopped mid-request: `RemoteProtocolError`. Restart to alive: 24.4 s and 22.7 s. 25 concurrent requests: 10 × 200, 15 × 503 (HTML body). GROBID healthy afterwards. **P1-T5 `completed`**. Not observed: 204, `TIMEOUT`, `TOO_MANY_BLOCKS`, encrypted PDF, real scanned paper |

| 2026-11-03 | P1-T6: extra checks on the TEI (note `place`, hyphen splits, curly quotes, back-matter `div` types, captions) and answers written in the experiment doc §7, limitations in §8 | Answered: `OQ-001` (pages for every paragraph; sections flat), `OQ-003` (references not passages in VS-1), `OQ-005` (keep 50 MB). Provisional: `OQ-002` (paragraph passages plus two repair rules, confirm with Recall@5), `OQ-013` (normalisation rules, test in P5-T6). Deferred: `OQ-016` (tables to Phase 7; tracing to Phase 6). **P1-T6 `completed`**. PRD not yet updated (needs developer approval) |

| 2026-11-03 | PRD v0.5: recorded Phase 1 answers (developer approved); cross-document consistency script on PRD, CLAUDE.md, progress.md, roadmap, README, design system, experiment doc and project skill | Passed: 147 IDs defined, 103 tasks, 14 milestones; references, fences and table columns consistent across 8 files |

| 2026-11-03 | P1-T7: checked the TEI shape of abstract, back matter and captions on the five papers | Abstract `abstract/div/p` with coordinates; back matter `back/div[@type]/div/p` with coordinates; captions `figure/figDesc` without coordinates but the enclosing `figure` always has them |
| 2026-11-03 | P1-T7: applied the region rules and rules R1/R2 to the five TEI files | 324 passages (abstract 9, body 239, caption 37, back 39); every passage has pages; 2 skipped. R1 joined only 1 of 8 mid-sentence fragments: in 7 cases other text sits between the halves. A looser nearest-unfinished rule would join at least 3 of 8 to the wrong text, so R1 stays strict |
| 2026-11-03 | P1-T7: `docs/design/parser-output.md` written; PRD v0.6 (`FR-ING-007`, §8.2) | Developer chose the regions. **P1-T7 `completed`** |

| 2026-11-03 | P1-T8: Phase 1 acceptance criteria checked against the report; developer chose **go with limits**; recorded in the report §9, PRD v0.7 (`AD-003`, `FR-ING-003`) | All four criteria met; **P1-T8 `completed`, M3 `completed`** |

| 2026-11-03 | P2-T1: PostgreSQL 18.6 feature checks in rolled-back transactions (`uuidv7()`, `UNIQUE` with several `NULL`s, generated `section_path`, `BEFORE UPDATE` trigger, page `CHECK`s) | All behaved as designed: `uuidv7()` time-ordered; many `NULL` DOIs allowed and a duplicate DOI rejected; `section_path` "3.1 Methods" / "Intro"; update blocked with "passages are immutable"; page 0 rejected. Nothing kept |
| 2026-11-03 | P2-T1: `docs/design/schema.md` written; `docs/design/parser-output.md` §7 corrected (`not_pdf`, `empty_file`, `file_too_large` are upload rejections, not stored reasons, per `FR-ING-001`; `storage_error` added) | **P2-T1 `completed`** |

| 2026-11-03 | P2-T2: `uv add sqlalchemy alembic psycopg[binary]` (developer approved) | SQLAlchemy 2.1.6 (MIT), Alembic 1.20.1 (MIT), psycopg and psycopg-binary 3.3.7 (LGPL-3.0, used unmodified; note for the M14 licence review), plus Mako, MarkupSafe, tzdata |
| 2026-11-03 | P2-T2: `alembic init --template pyproject backend/migrations`; `env.py` takes the URL from the settings module (not `alembic.ini`); models `Base` with a constraint naming convention; `app/database` engine (lazy, `pool_pre_ping`) and `session_scope`/`get_session` | ruff and mypy (23 files) clean |
| 2026-11-03 | P2-T2: tests: unit (naming convention; importing the app creates no engine, in a fresh interpreter); integration (psycopg 3 to PostgreSQL 18; a failed `session_scope` rolls back) | Default run 19 passed; `-m integration` 4 passed; combined 23 passed |
| 2026-11-03 | P2-T2: `uv run alembic current`, `heads`, `check`, `upgrade head`, `upgrade head --sql` from the repository folder | All exit 0; `check`: "No new upgrade operations detected"; `upgrade head` created only the `alembic_version` table. From another folder Alembic cannot find its `pyproject.toml` settings (an Alembic limitation), so commands are documented as run from the repository folder. **P2-T2 `completed`** |

| 2026-11-03 | P2-T3: ORM models `Paper`, `Document`, `Passage` (allowed values in `app/models/constraints.py`, used for the CHECK constraints); `alembic revision --autogenerate`, reviewed by hand against `docs/design/schema.md`; added the `passages_immutable` trigger; fixed the DOI check that the draft had written as `'10.%%'`; migration template updated to the project's ruff style | Migration `d2ea199dd3d3`; ruff and mypy clean (28 files) |
| 2026-11-03 | P2-T3: `uv run alembic upgrade head`; `\d` on the three tables; `alembic check` | Applied. Tables, 31 CHECK constraints (6/15/10), unique constraints, indexes (including the partial `ix_documents_processing`), generated `section_path` and trigger as designed; DOI check stored as `LIKE '10.%'`; `check`: no differences between models and database |
| 2026-11-03 | P2-T3: `alembic downgrade base`, then `upgrade head` and `check` again | Downgrade left only `alembic_version` and removed the trigger function; re-upgrade recreated everything; no differences |
| 2026-11-03 | P2-T3: smoke test in a rolled-back transaction: insert paper, parsed document, passage; then an update, a duplicate hash, a failed document without reason | Valid chain inserted (`section_path` "3.1 Methods"); the three bad cases rejected by the trigger, `uq_documents_sha256` and `ck_documents_failure_reason_iff_failed`; nothing kept. All tests 23 passed. **P2-T3 `completed`** |

| 2026-11-03 | P2-T4: DOI values in the five GROBID outputs | Header DOIs for 4 of 5 papers, matching the DOIs checked on the publishers' pages (BERT none); reference-list DOIs plain, 12 with capitals; no prefixes or whitespace observed |
| 2026-11-03 | P2-T4: `tests/unit/test_doi.py` written first and run before the function existed (collection error), then `backend/app/services/doi.py` (`normalize_doi`) | 31 passed |
| 2026-11-03 | P2-T4: mutation check: removed lower-casing, removed trimming, loosened the DOI pattern (one at a time), file restored (hash identical) | 3, 1 and 3 tests failed respectively. All checks: ruff, mypy (31 files) clean; unit 50 passed; all 54 passed. **P2-T4 `completed`** |

| 2026-11-03 | P2-T5: `env.py` accepts a test connection; fixtures create a throwaway database (`<POSTGRES_DB>_test`), migrate it with Alembic and drop it; `tests/integration/test_schema_migration.py` (empty database migrates; downgrade and re-upgrade) and `test_schema_constraints.py` (each rejection checks the named constraint PostgreSQL reports) | 57 integration tests passed; ruff, mypy (33 files) clean |
| 2026-11-03 | P2-T5: targeted mutations of the migration, one at a time: page check `>= 0`; trigger attached to the wrong table; unique hash removed; file restored (hash identical) | Each caught by the intended test only (the trigger change also failed the downgrade test, which drops that trigger). A first, too broad mutation (trigger on INSERT) failed 21 tests and was replaced by these |
| 2026-11-03 | P2-T5: all tests; `alembic check` on the development database; development row counts and leftover test databases before and after | 107 passed; no model/database difference; development database unchanged (head `d2ea199dd3d3`, 0 rows); no test database left. **P2-T5 `completed`** |

| 2026-11-03 | P2-T6: exported constraints from the development database and cross-checked them against the tests | 38 named check/unique/foreign-key constraints; 33 had a test asserting the name. Added the 5 missing cases (`failure_message` length, `joined_paragraphs`, empty `tei_storage_key`, duplicate `storage_key` and `tei_storage_key`): 38/38; integration 62 passed |
| 2026-11-03 | P2-T6: `docs/design/schema.md` §10 written from the database export; inspect command checked in Windows PowerShell (the first form, with nested quotes, failed there and was replaced) | Reference matches the database |
| 2026-11-03 | P2-T6: Phase 2 acceptance check: ruff, mypy (33 files), all tests, the roadmap's P2-T5 list, `alembic check`, table list, `CLAUDE.md` | All clean; 112 passed; P2-T5 list 7 passed; no model/database difference; only `papers`, `documents`, `passages`, `alembic_version`. **P2-T6 `completed`, M4 `completed`** |

| 2026-11-03 | P3-T1: `tests/unit/test_storage.py` written first (collection error before the module existed), then `backend/app/storage.py` (`Storage` interface, `LocalStorage`, `get_storage`) | 28 passed |
| 2026-11-03 | P3-T1: mutation check, one at a time: key-shape check removed; exclusive create replaced by overwrite; partial-file cleanup removed; file restored (hash identical) | 10, 1 and 1 tests failed respectively. With the key-shape check removed, the four `../` cases were still refused by the second (resolved-path) guard |
| 2026-11-03 | P3-T1: ruff, mypy (35 files), all tests; probe through `get_storage()` with the real settings, then deleted | All clean; 140 passed. Probe stored under `data/storage/pdf/<uuid7>.pdf`, git-ignored, read back intact, deleted; no files left. **P3-T1 `completed`** |

| 2026-11-03 | P3-T2: real PDF headers checked (`%PDF-1.3`/`%PDF-1.4` for the 5 papers); `tests/unit/test_upload_validation.py` written first (collection error before the module existed), then `backend/app/services/ingestion/validation.py` (`validate_upload`, `display_filename`) | 34 passed |
| 2026-11-03 | P3-T2: validator run on the 5 papers and the 11 Phase 1 failure inputs with the real 50 MB limit | Papers accepted with correct SHA-256. Rejected: text renamed `.pdf` (`not_pdf`), empty (`empty_file`), 64 MB (`file_too_large`). Accepted as designed, for GROBID to judge: corrupt, truncated, image-only, blank, long synthetic PDFs |
| 2026-11-03 | P3-T2: mutation check, one at a time: trust filename instead of content; `>=` limit; keep path parts; keep control characters | 10, 1, 4 and 1 tests failed respectively; file restored; ruff, mypy (38 files) clean; all tests 174 passed. **P3-T2 `completed`** |

| 2026-11-03 | P3-T3: `httpx` moved from dev to main dependencies (decided in §6.8 for the GROBID client); settings `GROBID_BUSY_RETRIES` (2) and `GROBID_BUSY_RETRY_SECONDS` (5) added with `.env.example` placeholders. The Starlette deprecation warning noted at P0-T6 concerns only the test client's use of httpx; httpx stays the GROBID client | Resolved; open note closed |
| 2026-11-03 | P3-T3: `tests/unit/test_grobid_client.py` written first (collection error before the module existed), then `backend/app/services/ingestion/grobid.py` (`GrobidClient`, `ParserFailure`, fixed form fields) | 30 stub-server tests passed (request shape, consolidation off, 204/empty 200, each 500 code, other statuses, 503 retry and give-up, six transport errors, message without body) |
| 2026-11-03 | P3-T3: `tests/integration/test_grobid_client.py` against the running GROBID (synthetic PDFs) | 4 passed: text page returns TEI; text bytes `unreadable_pdf`; blank page `no_text_layer`; closed port `parser_unreachable` |
| 2026-11-03 | P3-T3: one-off run on the five papers through `GrobidClient.from_settings` | All returned TEI (57–297 KB, 1.8–13.6 s; first includes warm-up), no consolidation markers |
| 2026-11-03 | P3-T3: mutation check, one at a time: consolidation on; no 503 retry; `NO_BLOCKS` unmapped; empty 200 accepted; disconnect mapped as unreachable; file restored (hash identical) | 2, 2, 1, 1, 2 tests failed respectively. ruff, mypy (41 files) clean; all tests 208 passed. **P3-T3 `completed`** |

| 2026-11-03 | P3-T4: expat 2.9.0 bundled; none of the five TEI outputs contain `<!DOCTYPE` or `<!ENTITY`. Python's built-in XML parser used instead of lxml (no new dependency); DOCTYPE/ENTITY rejected as `malformed_tei`; `ParsedDocument.abstract` added for `papers.abstract` | Recorded in `docs/design/parser-output.md` |
| 2026-11-03 | P3-T4: `tests/unit/test_parse_tei.py` written first (collection error before the module existed), then `backend/app/services/ingestion/tei.py` (`parse_tei`) | 33 of 34 passed; the failure was a test that could not fail (its text had letters); test corrected; 34 passed |
| 2026-11-03 | P3-T4: `parse_tei` on the five papers, from the Phase 1 TEI and from fresh client TEI | Both: 324 passages (abstract 9, body 239, caption 37, back 39), 1 join, 2 skipped, none without pages: exactly the P1-T7 counts. Passages and metadata identical between the two TEI sources; DOIs normalise to the verified values |
| 2026-11-03 | P3-T4: mutation check, seven changes one at a time | First round: four caught, three survived (R1 not reset after a figure; references section not excluded; DOCTYPE guard), showing test gaps. Added three tests; each surviving change is now caught. 38 parser tests; ruff, mypy (43 files) clean; all tests 246 passed. **P3-T4 `completed`** |

| 2026-11-04 | P3-T5: Docker Desktop was not running (after a restart); integration fixtures failed loudly as designed; Docker Desktop started, services healthy | 246 tests passed again |
| 2026-11-04 | P3-T5: synthetic builders moved to `tests/synthetic.py` (TEI, tiny PDFs) and reused | All tests still passed |
| 2026-11-04 | P3-T5: `tests/integration/test_ingestion_pipeline.py` written first (collection error before the module existed), then `backend/app/services/ingestion/pipeline.py` (`Ingestion.register`, `Ingestion.process`) | 15 of 17 passed; both failures traced to an invalid synthetic DOI in the test (`10.1/ABC`, correctly treated as no DOI); fixture corrected to `10.1234/ABC`; 17 passed |
| 2026-11-04 | P3-T5: mutation check, one at a time: no file cleanup on failed register; no same-DOI lookup; TEI key dropped on failure; non-pending allowed | 1, 1, 2, 1 tests failed respectively; file restored |
| 2026-11-04 | P3-T5: end-to-end on the five papers: validation, storage, real GROBID, `parse_tei`, PostgreSQL, in a throwaway database (dropped afterwards) | 5 parsed, 5 papers, 324 passages (abstract 9, body 239, caption 37, back 39), none without pages, 2 skipped, 1 joined, parser `grobid 0.9.1`, stored hash = recorded hash = file hash. Development database untouched (0 documents) |
| 2026-11-04 | P3-T5: ruff, mypy (46 files), all tests | Clean; 263 passed. **P3-T5 `completed`** |

| 2026-11-04 | P3-T6: tests written first: identical file returns the existing document; same file twice gives one passage set (`AC-VS-04`); concurrent identical uploads; retry after failure; retry replaces the TEI key; parsed cannot be reprocessed; concurrent processing runs once. `register` now returns `Registration(document_id, created)` | Collection error before implementation; after: 24 passed |
| 2026-11-04 | P3-T6: mutation check, round 1 (five changes) | Caught: no retries, failure kept on retry, no row lock (5/5 runs). **Survived:** removing the race fallback (0/5 runs: the concurrent test never actually raced) and removing the up-front hash lookup (the fallback still gave the right result) |
| 2026-11-04 | P3-T6: tests strengthened: a storage wrapper holds every upload at a barrier between the hash lookup and the insert, forcing the race; PDF saves are counted so a duplicate is proven to store nothing | Round 2: both previously surviving changes caught in 5/5 runs; file restored (hash identical) |
| 2026-11-04 | P3-T6: concurrency and duplicate tests run 10 times; ruff, mypy (46 files), all tests | 10/10 passed; clean; 270 passed. **P3-T6 `completed`** |
| 2026-11-04 | P3-T7: tests written first: `processing` becomes `failed`/`interrupted` with message, start time kept; other statuses untouched; several documents; idempotent; nothing to recover; a recovered document can be retried to `parsed`. Startup tests: recovery runs once; startup fails if recovery raises | 12 passed after one test-helper bug was fixed (duplicate `storage_key` keyword) |
| 2026-11-04 | P3-T7: real server on a throwaway database (`paperpilot_recovery_check`) with one stale `processing` row and one `pending` row; `uvicorn` started, `/health` checked, stopped; database dropped | Health 200; log line `ingestion document_id=... status=failed reason=interrupted`; stale row `failed`/`interrupted` with message and start time; `pending` row unchanged |
| 2026-11-04 | P3-T7: mutation check (recover every non-parsed status; drop the reason; set `pending`; remove the startup call) | All four caught (2, 5, 5, 2 failures); files restored |
| 2026-11-04 | P3-T7: ruff check, ruff format --check, mypy (48 files), all tests | Clean; 278 passed. **P3-T7 `completed`** |
| 2026-11-04 | P3-T8: developer decisions: raw-body upload (no `python-multipart`), explicit retry endpoint (§6.10). PRD `FR-ING-001` wording updated, v0.8 | Recorded |
| 2026-11-04 | P3-T8: `tests/integration/test_documents_api.py` written first (collection error before the API existed), then the routes, error handlers, schemas and read service | 26 passed |
| 2026-11-04 | P3-T8: mutation check, round 1 (12 changes: declared-length check, stream limit, off-by-one limit, background processing, duplicate status code, filename decoding, retry status check, exposed `failure_message`, passage order, catch-all handler, 422 echoing input, missing 409 details) | 11 caught. **Survived:** removing the stream limit (validation still rejected the file, but only after reading all of it) |
| 2026-11-04 | P3-T8: unit tests for `read_limited` with a counting stream (stops at the first chunk over the limit); a chunked upload test without `Content-Length` | Round 2: the surviving change is caught; files restored |
| 2026-11-04 | P3-T8: real server (uvicorn, real GROBID, throwaway database `paperpilot_api_check`, storage in a temporary folder) with failure inputs f01-f08 and paper p3 | f01 `415 not_pdf`; f02 `400 empty_file`; f03, f04, f05 `failed`/`unreadable_pdf`; f06 `failed`/`empty_parse`; f07, f08 `failed`/`no_text_layer`; each failed structure `409 document_not_parsed` with status and reason. p3 `parsed` in 10.5 s (upload to final poll), 32 passages, all with a page, title correct. Re-upload of p3: `200`, `created: false`. Retry of parsed: `409`. Unknown id `404`, malformed id `422`. 7 PDFs stored (f03-f08, p3; the duplicate stored nothing); p3's stored hash equals the original. Database dropped, temporary storage removed |
| 2026-11-04 | P3-T8: ruff check, ruff format --check, mypy (56 files), all tests | Clean; 310 passed. **P3-T8 `completed`** |
| 2026-11-04 | P0-T8: Node 24.15.0, npm 11.12.1 present; pnpm broken. `npm view` for each package (version, licence, last modified) | All updated within four months; licences MIT, Apache-2.0 (typescript), OFL-1.1 (fonts). `npm audit --omit=dev`: 0 vulnerabilities |
| 2026-11-04 | P3-T9: helper and client tests written first (failed before the modules existed), then implementation | 15 passed |
| 2026-11-08 | P3-T9: page tests (upload, polling, failure and retry, duplicate, not found, network error) and components; `npm test`, `npm run typecheck` | 24 passed; strict type check clean |
| 2026-11-08 | P3-T9: browser pane with real backend, GROBID and a throwaway database: upload, parsed (p3, 32 passages) and failed views; no file; rejected file (`not_pdf`); real status sequence on upload (Processing, Failed) and on Retry; backend stopped | All as designed. Backend-down first showed a bare HTTP 500 message, reworded. Console: only the expected 415 from the rejected upload. Database dropped, storage removed |
| 2026-11-08 | P3-T9: widths 375, 768, 1280 px on the parsed view | No horizontal scroll at any width; section list sticky at 1280 |
| 2026-11-08 | P3-T9: contrast measured in the browser from the CSS tokens | 15 pairs, lowest 5.28:1 (Processing), all above AA 4.5:1 |
| 2026-11-08 | P3-T9: keyboard on the upload view (Tab order; focus visible on the file control) | Skip link, wordmark, file control, submit; focus ring visible. Keyboard path checked on the upload view only |
| 2026-11-08 | P3-T9: mutation check (11 changes) | 10 caught at first; "Try again on any error" survived; test added; 11/11 caught; files restored |
| 2026-11-08 | P3-T9: `npm ci`, `npm run dev` without and with `frontend/.env`, `npm run build`; backend ruff, mypy (56 files), all tests | Clean install; refuses to start without the setting and starts with it; build succeeds; clean; 310 backend tests passed. **P3-T9 `completed`** |
| 2026-11-08 | P3-T10: five real papers uploaded through the frontend's `/api` proxy on the development database (real backend, GROBID, PostgreSQL) | All `parsed`, status sequence pending, processing, parsed; 1.8-5.9 s; details in §6.12 |
| 2026-11-08 | P3-T10: structure view in the browser pane for all five | Badge `Parsed`, correct title, full passage counts (128, 104, 32, 39, 21), passages in order, each with a page line. Files were sent by script, not the file picker |
| 2026-11-08 | P3-T10: every passage compared with `pdftotext` for its stated page | 315 checked: 291 exact at both ends; 23 of 24 others mostly on the stated pages; 1 real error (p1 passage 104) |
| 2026-11-08 | P3-T10: database checks | 5 documents, 5 papers, 324 passages; all `parsed`; 0 parsed with zero passages; 0 page 0 or empty section; stored hash equals recorded hash 5/5; 5 TEI files present |
| 2026-11-08 | P3-T10: re-upload of all five (`AC-VS-04`) | `200`, `created: false` each; counts unchanged (5, 5, 324); 5 PDFs on disk |
| 2026-11-08 | P3-T10: real GROBID outage on a throwaway database (container stopped, file uploaded, container restarted, Retry; `AC-VS-03`) | `failed`/`parser_unreachable` with no structure; after Retry the document was processed again and ended `failed`/`unreadable_pdf`, the correct result for that damaged test file. Database dropped, storage removed |
| 2026-11-08 | P3-T10: developer opened the running app and reviewed it: "everything is fine". `AC-VS-01` to `AC-VS-04` evidenced above. Whether the real file picker was used was not stated, so it stays unconfirmed | **P3-T10 `completed`; Phase 3 and M5 `completed`** |
| 2026-11-08 | P4-T1: PostgreSQL 18 documentation read (12.1, 12.2, 12.3, 12.11); GIN versus GiST page not read | Facts recorded in `docs/design/retrieval.md` §2 |
| 2026-11-08 | P4-T1: read-only probes on the development database (324 passages, 6 probe queries): `english` and `simple`; `websearch_to_tsquery`, `plainto_tsquery`, OR form; four rankers; 14 hostile inputs. No rows written | AND matched 1-13 passages per probe, OR 80-167. Normalisation 2 ranked a passage under 100 characters first in 5 of 6 probes, normalisation 1 in 3 of 6. 12 hostile inputs raised no error. 40,000 words and a NUL character raised errors with every parser. Interim choice recorded; these probes are a sanity check, not an evaluation. **P4-T1 `completed`** (`OQ-004` open until P4-T7) |
| 2026-11-08 | P4-T2: tests written first (`tests/integration/test_search_representation.py`, plus a migration test with passages stored before the column exists), then model and migration `e3ab5ad233d7`. The write-rejection test first passed for the wrong reason and was tightened | 8 failed before the migration; after it all pass |
| 2026-11-08 | P4-T2: mutation check (`simple` configuration; session-default configuration; non-GIN index; column not deferred; downgrade keeps the column; model expression differs) | All six caught; files restored |
| 2026-11-08 | P4-T2: `alembic upgrade head` on the development database | 324 passages before and after, fingerprint of id, ordinal, text, section title and page identical. 0 empty or null vectors; index valid; immutability trigger enabled; the column gives the same matches as recomputing from the text (89 of 89 for one probe word); `alembic check` clean; structure view still works |
| 2026-11-08 | P4-T2: ruff check, ruff format --check, mypy (58 files), all tests | Clean; 321 passed. **P4-T2 `completed`** |
| 2026-11-08 | P4-T3: tests written first (collection errors before the module existed), then `search_passages`, `clean_question`, `QueryTooLongError`, setting `MAX_QUERY_CHARS` (default 2000, placeholder added). The tie-break test was first too weak (rows return in insertion order) and now stores ids in reverse | 31 passed |
| 2026-11-08 | P4-T3: mutation check (13 changes: any status, AND, no tie-break, worst first, no limit, each scope ignored, empty scope as everything, NUL kept, surrogates kept, no length limit, no k check) | All 13 caught; file restored |
| 2026-11-08 | P4-T3: real function on the development database with the five excluded probe queries | 3.7-11.4 ms per search; results from the expected paper for four probes, a mix of p2 and p3 for the fifth. This shows it runs on real data, not that results are correct. Scope to one document or paper returned only that paper; no-match empty; SQL-like text ran safely; 40,000 words gave `query_too_long`; 324 passages unchanged |
| 2026-11-08 | P4-T3: ruff check, ruff format --check, mypy (62 files), all tests, `alembic check` | Clean; 352 passed. **P4-T3 `completed`** |
| 2026-11-08 | P4-T4: `tests/integration/test_retrieval_hostile_input.py`: empty and punctuation-only input, SQL-like input with stored data compared before and after, operator-like input, awkward tokens, 300 seeded arbitrary strings, scope isolation, repeated order. No application code changed | One failure on `AT&T`: `ts_debug` shows `AT` and `T` are `english` stop words, so a limit of the configuration, not a bug. Replaced by an explicit known-limit test and recorded in `retrieval.md` |
| 2026-11-08 | P4-T4: mutation check (9 changes). "Replace every ampersand" survived because a URL's host still matched; a test isolating the shared path was added. "No tie-break" survives in this file only; `test_keyword_retrieval.py` catches it | 9/9 caught across the retrieval tests; file restored |
| 2026-11-08 | P4-T4: ruff check, ruff format --check, mypy (63 files), all tests | Clean; 410 passed. **P4-T4 `completed`** |
| 2026-11-08 | P4-T5: draft `benchmarks/retrieval_eval_v1.json`: 20 questions, 16 answerable over 5 papers, 4 unanswerable. Written from the PDF text with `pdftotext`, with questions worded differently from the quotes. **Retrieval was not run on any of these questions.** Claude Code had seen short extracts and probe rankings of the same papers earlier, so the draft is not fully blind; recorded in the file as drafted by Claude Code | Status `draft`; reviewer and date empty |
| 2026-11-08 | P4-T5: each expected quote compared with the stored passages of its paper (plain substring after the provisional `OQ-013` normalisation; not retrieval). Corpus hashes compared with stored documents. Unanswerable topics checked by word search in the PDF text | 17 of 17 quotes found; hashes match. Absent as topics: energy or carbon, gender, astronomy, project budget (p2 mentions "costing millions" only about other trials) |
| 2026-11-08 | P4-T5: `tests/evaluation/dataset.py` (strict format) and `tests/unit/test_evaluation_set.py` | 14 passed |
| 2026-11-08 | P4-T5: developer reviewed the set in the UI and replied "it seems everything is fine". Which questions were checked was not stated, and no name was given: the git `user.name` (`rknishanth152-lgtm`) is recorded as reviewer. Status set to `reviewed`, no question changed | **P4-T5 `completed`** |
| 2026-11-08 | P4-T6: tests written first (collection errors before the harness existed), then `tests/evaluation/retrieval_harness.py` and `run_retrieval.py`: quote-to-passage mapping, Recall@5 across the corpus and within the question's paper, unmatched expectations reported separately, unanswerable questions listed but not scored, review gate, dated result file that never overwrites | 25 passed |
| 2026-11-08 | P4-T6: mutation check (12 changes) | All 12 caught; file restored |
| 2026-11-08 | P4-T6: real quote mapping on the development database, without running retrieval; runner imports | 16 answerable questions, 0 unmatched quotes; corpus found by hash. **The harness has not yet been run on the real questions and no Recall@5 exists**; that is P4-T7. ruff, mypy (69 files) clean; 449 tests passed. **P4-T6 `completed`** |
| 2026-11-08 | P4-T7: saved harness run from clean commit 368fd83 (`benchmarks/results/retrieval-20261108T173245Z-368fd83.json`) | Recall@5 8/16 across all papers, 9/16 within the question's paper; 0 unmatched. 16 scored questions, a coarse baseline only |
| 2026-11-08 | P4-T7: every miss analysed with rank and matching words (`docs/experiments/retrieval-baseline.md` §2) | 8 of 8 vocabulary mismatches; none from passage boundaries or labels. The questions were deliberately paraphrased, which makes the test hard. The evaluation set was not edited |
| 2026-11-08 | P4-T7: `scripts/retrieval_variants.py`, read-only, exploratory, **logged as tried after seeing the baseline** (`CLAUDE.md` §6.9) | Reproduced 8 and 9. ANDed words 0; `ts_rank_cd` 9 and 10 (one question net); others no better. **No configuration change.** Figures are not reported as metrics |
| 2026-11-08 | P4-T7: `AC-VS-05` evidenced by P4-T3 and P4-T4; `FR-EVL-001` met by the reviewed set; baseline recorded; every miss has a cause; `OQ-004` documented as interim. ruff, mypy (70 files) clean; 449 tests passed | **P4-T7 `completed`; Phase 4 and M6 `completed`** |
| 2026-11-08 | P5-T1: provider pages read (pricing, data use, structured output) for Anthropic, OpenAI and Google; developer chose Haiku 5.5 plus a comparison run (§6.13). No code, dependency or API call; nothing sent to any provider | **P5-T1 `completed`** (`OQ-011` interim) |
| 2026-11-08 | P5-T2: tests written first (collection error before the module existed), then `LanguageModel`, `ModelRequest`, six specific `ModelError` types, `FakeModel`, setting `LLM_TIMEOUT_SECONDS` (default 60, placeholder added). Mutation check, 11 changes | 28 passed; 11/11 caught; files restored. ruff, mypy (72 files) clean. No real provider called. **P5-T2 `completed`** |
| 2026-11-08 | Full suite run repeatedly during P5-T2 | 477 passed in most runs; `test_concurrent_identical_uploads_create_one_document` failed intermittently (3 of 12 runs observed), unrelated to P5-T2. **Open defect in `backend/app/storage.py` since P3-T1:** with concurrent saves into a folder that does not exist yet, `Path.resolve()` on Windows can return a `\\?\` path, and the guard in `_path` rejects a valid key. Reproduced outside the tests: 62 to 145 of 4,800 concurrent saves; all 62 captured failures had that prefix. Fixed in the next row |
| 2026-11-08 | Storage race fixed, developer approved: `_path` no longer resolves the path, and the key check uses `fullmatch`, which also rejects a trailing newline that the old pattern let through. Three failing tests written first. Mutation check, 2 changes | 3 failed before, 31 passed after; 2/2 caught. Race script 4,800 of 4,800 saves succeeded. Full suite 12 of 12 clean runs, 480 passed; ruff, mypy (72 files) clean |
| 2026-11-08 | P5-T3: tests written first (collection error before the module existed), then `ModelAnswer`, `parse_answer`, `MalformedAnswerError`, `answer_json_schema`. `FR-CIT-004`: an `insufficient` answer with statements fails the schema; an uncited statement does not. An answer claiming evidence with no statements is also rejected, otherwise it would count as validated. Mutation check, 11 changes | 43 passed; 10 caught. "Not strict" survived because it changes nothing for these types, so the setting was removed. ruff, mypy (74 files) clean; 523 tests passed, three runs. **P5-T3 `completed`** |
| 2026-11-08 | P5-T4: tests written first (collection error before the module existed), then `build_context`. The user message is one JSON document, so passage text cannot change its structure; page numbers and ids are withheld; passages are dropped whole in rank order, with aliases kept for `not_in_context`. A test budget was too small (test mistake) and ASCII escaping survived a first mutation run; a test was added | 22 passed. Mutation check after the fix: 10 of 10 caught; file restored. ruff, mypy (77 files) clean; 545 tests passed, two runs. **P5-T4 `completed`** |
| 2026-11-08 | P5-T5: tests written first (collection errors before the modules existed), then `SYSTEM_PROMPT` (`answer-v1`), `request_answer`, `Answering.ask`, `get_paper_titles`, settings `ANSWER_TOP_K`, `MAX_CONTEXT_CHARS`, `LLM_MAX_OUTPUT_TOKENS`, `LLM_MALFORMED_RETRIES`, all with placeholders. FakeModel only; no provider called | 33 passed; mutation check 15 of 15 caught; file restored. ruff, mypy (81 files) clean; 578 tests passed, two runs. **P5-T5 `completed`** |
| 2026-11-08 | P5-T6: rules measured first (§6.14), tests written first (collection error before the module existed), then `quote_in_passage`. Mutation check, 7 changes | 28 passed; 7 of 7 caught; file restored. ruff, mypy (84 files) clean; 606 tests passed, two runs. **P5-T6 `completed`** (`OQ-013` resolved for VS-1) |
| 2026-11-08 | P5-T7: tests written first (collection error before the module existed), then `validate_answer`, `AnswerScope`, reason codes `passage_not_found`, `not_in_context`, `wrong_paper`, `quote_mismatch`. Deterministic checks only; they do not establish claim support (`AD-008`). Mutation check, 13 changes | 29 passed; 13 of 13 caught; file restored. ruff, mypy (86 files) clean; 635 tests passed, two runs. **P5-T7 `completed`** |
| 2026-11-08 | P5-T8: tests written first (import error before the constants existed), then the skip: with nothing to show the model (nothing retrieved, or nothing fits the budget) it is not called and the answer is `insufficient`, with `model` and `prompt_version` null and 0 attempts. The model's own `insufficient` answer is preserved. Mutation check, 7 changes | 19 passed in that file; 7 of 7 caught; file restored. ruff, mypy (86 files) clean; 646 tests passed, two runs. **P5-T8 `completed`** |
| 2026-11-08 | P5-T9: tests written first (collection error before the modules existed), then `AnswerResponse`, `assemble_response`, `Answering.answer`. Only valid citations become evidence; pages and sections come from the stored passage; `claim_support` can only be `not_evaluated`. Mutation check, 14 changes. One survived at first because retrieval already applied the scope; a test now simulates a retrieval leak | 14 of 14 caught after that test; file restored. ruff, mypy (89 files) clean; 667 tests passed, two runs. **P5-T9 `completed`** |
| 2026-11-08 | P5-T10: fault-injection suite through the whole chain, with the fake model: nonexistent passage, another paper, not in context, malformed output, extra and missing fields, altered quote, model-supplied page, uncited statement, insufficient with statements, instruction in a passage (followed and not followed), six provider failures. No application code changed. Then 16 safeguards disabled one at a time across validator, schema, context, pipeline and quote matching, running this suite alone | 39 passed; 16 of 16 caught; files restored. ruff, mypy (90 files) clean; 706 tests passed, two runs. `AC-VS-08` evidenced. Limit (`RISK-08`): tests show injected text stays data and that an obeying model is caught when its citation fails; they do not show how a real model behaves. **P5-T10 `completed`** |
| 2026-11-09 | P5-T11: API tests written first (collection error before the route existed), then `POST /answers`, structured model errors, `QuestionRequest` (a scope is required). Page tests, then `QuestionPanel`; a failed answer is marked in words, and no wording claims a passage supports a statement. Mutation check, 20 changes (9 backend, 11 frontend) | 23 API tests, 44 frontend tests. 18 caught at first; passing each of the two scopes to retrieval survived because the tests stored one document; a test with a second document was added; 20 of 20 caught. Files restored. (Commit f572f08's message says 22/22; the correct count is 20/20.) |
| 2026-11-09 | P5-T11: browser pane on the five real papers, with a temporary scripted model in the scratch folder (not in the repository, nothing sent anywhere): validated, failed, partial, model insufficient, nothing retrieved, timeout, blank question; widths 375, 768, 1280 px; citation jump | All states as designed. No horizontal scroll at any width. Citation jump keeps the document and runs the highlight. Marker contrast 15.42:1 (Ink), 6.06:1 (Slate text). Found by looking: a failed answer listed its one valid passage under "Evidence"; heading changed and a test added. Console: only the expected 504 from the timeout check. **Not verified:** real keyboard presses on this page (the app window was not drawing; DOM tab order was read instead), `prefers-reduced-motion` in a browser (rule loaded only), screen reader use |
| 2026-11-09 | P5-T11: ruff, mypy (92 files), all backend tests, `npm test`, `npm run typecheck`, `npm run build` | Clean; 729 backend tests passed, two runs; 44 frontend tests passed; build succeeds. **P5-T11 `completed`** |
| 2026-11-09 | P5-T12, adapter: developer approved `anthropic` 2.6.0 (Apache-2.0); `httpx2` added to dev dependencies for the offline tests (already installed by the SDK). Tests written first against the real SDK with a stubbed network, then `AnthropicModel` and `build_language_model`. SDK retries off. Mutation check, 13 changes | 21 passed; 13 of 13 caught; file restored. ruff, mypy (94 files) clean; 750 tests passed, two runs. No API call made |
| 2026-11-09 | P5-T12, Gemini connector: Google's Interactions API documentation read; tests written first with a stubbed network, then `GeminiModel`, `to_gemini_schema`, `llm_factory`, setting `GEMINI_BASE_URL`. No new dependency. How blocked generations are reported is not documented, so a `failed` status with a block code is a refusal and any other unexpected outcome is unavailable. Mutation check, 17 changes: 14 caught at first, one did not apply, two survived (a thought step with no text, a request test whose schema needed no conversion); tests added, 17 of 17 caught | Connector tests pass; files restored. ruff, mypy (97 files) clean; 784 tests passed, two runs. No API call made |
| 2026-11-09 | P5-T12: `tests/evaluation/run_answers.py` tested offline, then committed before any real call. API key confirmed set without displaying it. Diagnostic calls with harmless prompts: `gemini-3.8-flash` overloaded; three other free models responded and accepted the answer format | Real API responses confirm the connector's request format |
| 2026-11-09 | P5-T12: **manual real-model run**, `gemini-3.5-flash-lite`, 20 questions, 30 seconds apart, code at commit d09c9b6 (the file records `working_tree_clean: false`; an earlier result file was still uncommitted in the folder. Corrected 2026-11-09: this row first said "clean commit") | 13 of 16 answerable questions answered with all citations valid; 0 failed validation; 3 said `insufficient`; expected passage retrieved and cited in 9. 4 of 4 unanswerable said `insufficient`. 0 errors. 2.0 s per answer. $0 (about $0.0009 per answer at paid prices). Details and limits in `docs/experiments/answer-baseline.md` |
| 2026-11-09 | P5-T12: nine answers read beside their cited passages | Honest `insufficient` when retrieval missed. q04, q07 correct from a different passage. **q06 passes every check but only partly answers the question.** `claim_support` stays `not_evaluated`. Not established: a real failed validation, injection on a real model, any model comparison (`gemini-3.6-flash` partial runs saved). `AC-VS-06`, `AC-VS-07` evidenced. **P5-T12 `completed`; Phase 5 and M7 `completed`** (`OQ-011` interim) |
| 2026-11-09 | P5-T12: **manual real-model check of the question page** in the browser, `gemini-3.5-flash-lite`, BERT paper, two evaluation questions (q02, q17) | q02: one statement, citation shown as valid, passage text, page 8 and section 5.2 match the database; q17: "Not enough evidence" with limitations and no statements. Model, prompt and retrieval details shown, "Claim support: not evaluated" shown. Both requests 200, no console errors, no paper or question text in the server log, passage count unchanged at 128, no answer table exists. Two questions only; keyboard, screen-reader and reduced-motion checks still deferred |
| 2026-11-09 | P6-T1: tests first; unit and integration tests for the combined command; 17 of 17 mutations caught, then 2 of 2 for the start-up fix | 811 backend tests pass; ruff and mypy clean. First real attempt crashed at import (`No module named 'app'`, only pytest set the path) before any provider call: fixed in 9654929 with a test that starts each command outside pytest. That test first ran `run_retrieval` for real because it had no `--help`; 3 stray retrieval files from a modified tree were moved out of the repository, not deleted, and the test now fails if a command writes a result |
| 2026-11-09 | P6-T1: **manual real-model run** of `run_evaluation --pause 30`, commit 9654929, clean tree, then again with `--answer-limit 1` | Retrieval: the two saved files are identical apart from `run_at`, and match the P4 baseline per question (8/16, 9/16). Answers: `answers-gemini-3.5-flash-lite-20261109T040343Z-9654929.json`: 13 of 16 answerable answered with all citations valid, 0 failed validation, 21 citations, 0 invalid, 3 `insufficient`. Unanswerable: 3 of 4 `insufficient`. **q19 gave a statement** (`partial`): true about microarray data, off-field for an astronomy question, its limitations say so. Against the earlier run retrieval was the same for all 20, statement text differed in 9 (q19 included), and two labels moved: q12 `partial` to `sufficient` with the same off-question statement, q19 `insufficient` to `partial`. The model's own sufficiency label is not stable between runs. 1.97 s per answer. **P6-T1 `completed`** |
| 2026-11-08 | **Not verified for P3-T9:** `prefers-reduced-motion` in a browser (the pane cannot emulate it; only confirmed the CSS rule is loaded); screen reader use; drag and drop with a real file; file picker dialog (file set from script in the browser check) | Open |

Not yet performed: confirmation that the files exist in the developer's folder (see below once committed); any run of application code (none exists). The scripts are structural checks only; they do not prove the documents are correct or complete.
