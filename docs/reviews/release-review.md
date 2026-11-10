# Release review: security, privacy, dependencies and licences

| Field | Value |
|---|---|
| Task | R9 (M14-T2, M14-T3, M14-T7, P0-T9) |
| Date | 2026-11-10 |
| Scope | Whole repository and full git history at commit b185f1e |

Each line names the check that was actually run. Nothing here is a claim of security beyond those checks.

## 1. Security (`NFR-SEC-001` to `NFR-SEC-006`)

| Requirement | Verdict | Evidence |
|---|---|---|
| `NFR-SEC-001` no committed secrets | **Met** | Every commit in history scanned: about 124,000 added lines checked against Google, Anthropic, GitHub, AWS, Slack and private-key formats and a broad "assigned secret" pattern. No real secret found. The 7 broad matches are code that reads a setting (6) and a placeholder sentence in a privacy test (1). No `.env` file, PDF or `data/` file has ever been committed. `.env` and `data/` are ignored |
| `NFR-SEC-002` upload checks | **Met** | Content checked for the `%PDF-` signature, empty and size limits enforced while reading (`ingestion/validation.py`). Storage keys are generated UUIDs, and only keys of that shape are accepted (`storage.py`). Tests: `test_upload_validation.py`, `test_documents_api.py` |
| `NFR-SEC-003` untrusted input, no code execution | **Met** | No `eval`, `exec`, `subprocess`, `os.system` or `pickle.load` anywhere in `backend/app`. No SQL built from strings. No `innerHTML` or `dangerouslySetInnerHTML` in the frontend. Model output is validated against a schema, and quotes are checked in code. Passage text reaches the model as JSON data, and prompt-injection tests pass with the fake model; it has not been tested on a real model (`RISK-08`) |
| `NFR-SEC-004` local services not exposed | **Met** | `compose.yaml` publishes PostgreSQL and GROBID on `127.0.0.1` only. In CI they are throwaway containers that exist only for the job |
| `NFR-SEC-005` no internals in errors | **Met** | Structured error responses only (`api/errors.py`). Tests: `test_unexpected_error_hides_internals`, `test_failed_document_shows_reason_and_explanation_not_internal_message`, the API error tests, and the R7 tests that malformed output never echoes the model's text |
| `NFR-SEC-006` no authentication, not for networks | **Met, as a documented limit** | The README says to keep `--host 127.0.0.1` and never expose PaperPilot to a shared network. No CORS is opened. This is a single-user local tool, and deploying it would need authentication first |

## 2. Privacy (`NFR-PRI-001`, `NFR-PRI-002`)

**What leaves the machine, and only with an API key configured:**

| Action | Sent to the provider |
|---|---|
| Asking a question | The question, and the retrieved parts of one paper |
| Running the reporting checklist | For each of six items, the retrieved parts of the paper |
| Running `scripts/embed_passages.py` | The text of every stored passage, once |
| Semantic search | The question |

PDFs are never sent. Uploading and reading a paper happen on the computer. On Google's free tier, submitted content may be used to improve Google's products and read by human reviewers, so only open-access papers should be used there. The README states all of this.

| Requirement | Verdict | Evidence |
|---|---|---|
| `NFR-PRI-001` documented | **Met** | README "Important limits" and "Embeddings" sections |
| `NFR-PRI-002` no paper text or credentials in logs | **Met after a fix** | Logging calls record counts, ids and error codes only, and tests check this for ingestion, retrieval, answering and the checklist. Database errors hide the values they were writing (P6-T4). **Real logs checked:** 296 sentence probes taken from all 324 stored passages, searched in 449 KB of actual backend logs from this project's runs: 0 matches. The key is never printed. **Defect found and fixed:** PostgreSQL's own server log wrote rejected rows with their values, so a rejected passage could put paper text there. Shown locally with the test's stand-in sentence. `compose.yaml` now sets `log_min_messages=fatal` and `log_min_error_statement=panic`; after the change, the same tests left 0 rejected rows and 0 error lines in the database log, and the application still receives every error |

## 3. Dependencies

| Check | Result |
|---|---|
| Python, every locked package (`pip-audit`, approved by the developer) | **No known vulnerabilities** |
| Frontend runtime packages (`npm audit --omit=dev`) | **0 vulnerabilities** |

`pip-audit` ran on the locked versions without hashes, which it accepts with a warning. CI repeats the npm audit on every push.

## 4. Licences

The repository is MIT, chosen by the developer on 2026-11-10.

| Ecosystem | Runtime packages | Licences |
|---|---|---|
| Python | 33 of 34 read. The 34th, `httpx2-jsfetch`, installs only for Python running in WebAssembly (`sys_platform == 'emscripten'`), so it is never installed here or in CI | MIT, BSD-3-Clause, Apache-2.0, PSF-2.0, MPL-2.0 (`certifi`), LGPL-3.0 (`psycopg`, `psycopg-binary`) |
| npm | 21 | MIT, Apache-2.0, ISC, 0BSD, OFL-1.1 (the two fonts) |

All are compatible with an MIT project when used as they are. The LGPL and MPL packages are used unmodified as libraries, and the OFL fonts are bundled unchanged. GROBID (Apache-2.0) runs as a separate service and is not part of this code.

**Bundled Claude Code skills** (checked in R12, 2026-11-10). `.claude/skills/` holds six third-party skills used while building the project, each with its licence file: `design-motion-principles` (MIT, Kyle Zantos), `systematic-debugging`, `test-driven-development` and `verification-before-completion` (MIT, Jesse Vincent), `ui-ux-pro-max` (MIT, Next Level Builder), and `playwright-cli` (Apache-2.0, Microsoft). The Apache-2.0 text for `playwright-cli` was missing and was added from the upstream repository. `paperpilot-engineering` is the project's own.

**Before going public** (R12): the full history up to 221c70c was scanned again, about 131,000 added lines, with no secret found, and no PDF, `.env` or `data/` file was ever committed. Older commits show the developer's email address as author; the developer chose to keep the history unchanged, and later commits use a GitHub no-reply address. `notes/` is published by the developer's choice: the developer's own learning notes, with short quotes from two tutorial videos' captions.

## 5. Continuous integration

`.github/workflows/ci.yml` runs on every push to `main` and every pull request: lint, formatting, types, migrations and `alembic check`, every backend test including integration tests against real PostgreSQL and GROBID containers, then the frontend types, tests, build and runtime audit. Actions are pinned to the commit of their release, the workflow can only read the repository, and no secret is configured, so no AI model is called in CI.

First run, commit b185f1e: both jobs passed. Backend 1,191 tests in 2 minutes, frontend 68 tests and the build in 20 seconds, both audits 0 vulnerabilities.

## 6. Not done

- CI's database is a GitHub service container, which cannot take that setting, so its log can still show rejected rows. It holds only synthetic test data and is discarded after each run.
- No penetration test or threat model beyond the checks above.
- No trademark search for the name or logo.
- Prompt injection is tested only with the fake model.
- Python packages are locked by version, not by hash.
