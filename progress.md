# PaperPilot: Progress

This file records **what actually exists and has been verified**. It is not a plan (see `docs/implementation-roadmap.md`) and not a specification (see `PRD.md`). Update it only with facts. Rules for working are in `CLAUDE.md`.

## 1. Project status

| Field | Value |
|---|---|
| Project | PaperPilot |
| Current stage | Environment setup. Documentation reviewed and approved; no application code written. |
| Overall status | `in_progress` (documentation only) |
| Last updated | 2026-11-03 |
| Current milestone | M2: Repository and development environment setup (`in_progress`: P0-T2 and P0-T3 completed; next P0-T4). M1 `completed` 2026-11-03. |
| Current phase | Phase 0 (`docs/implementation-roadmap.md`) |
| Next release target | VS-1 (see `PRD.md` §12.1) |

Generated documents and transcript analysis are **planning artefacts**. They are not implementation.

## 2. Milestone status

Milestones are proposals from the roadmap, not claims of completion. Statuses: `not_started`, `in_progress`, `blocked`, `completed`. A milestone becomes `completed` only with evidence in the "Evidence" column.

| ID | Milestone (Phase) | Status | Objective | Completion criteria (summary) | Evidence | Blockers / dependencies |
|---|---|---|---|---|---|---|
| M1 | Requirements and architecture documentation (0) | `completed` | Agreed PRD, rules, roadmap, status file | Developer has reviewed the four documents; `OQ-` triage recorded (roadmap P0-T1) | 2026-11-03: developer approved the architecture and incremental strategy; requested corrections applied and verified (§6.7 rows 8–9, §7); developer delegated the remaining Phase 0 decisions (§6.8); `OQ-` triage in §6.7 | None |
| M2 | Repository and development environment setup (0) | `in_progress` | Repo, Compose with PostgreSQL + GROBID, tooling, test conventions | A fresh clone plus README reproduces running services and a passing smoke test | None | `OQ-014`, `OQ-015` |
| M3 | GROBID parsing experiment (1) | `not_started` | Learn real GROBID behaviour on 3–5 permitted papers | `docs/experiments/grobid-feasibility.md` with observations, failures, go/no-go | None | M2 (minimal subset: P0-T2, P0-T3, Python environment) |
| M4 | Database schema and migrations (2) | `not_started` | `papers`, `documents`, `passages` with constraints | Migration applies to an empty DB; constraint tests pass | None | M3 |
| M5 | Paper ingestion and passage persistence (3) | `not_started` | Upload → GROBID → passages, honest statuses | `AC-VS-01`..`AC-VS-04` evidenced | None | M4 |
| M6 | Keyword retrieval (4) | `not_started` | PostgreSQL full-text retrieval; evaluation set; Recall@5 baseline | `AC-VS-05`; baseline file recorded | None | M5 |
| M7 | Evidence-backed question answering (5) | `not_started` | Retrieval → structured answer → citation validation | `AC-VS-06`..`AC-VS-08` | None | M6; `OQ-011` |
| M8 | Evaluation harness (6) | `not_started` | Repeatable evaluation; VS-1 acceptance | `AC-VS-09`, `AC-VS-10` | None | M7 |
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
| Task | Developer review of the four planning documents (roadmap P0-T1) |
| Expected output | Review notes; `OQ-` triage (which questions block Phase 0/1); corrections to the PRD where the developer disagrees; decision on where the repository lives |
| Status | P0-T1 `completed` 2026-11-03. The developer reviewed the documents, approved the overall architecture and strategy, asked for two corrections (applied and checked, §6.7 rows 8–9), then asked Claude to settle the remaining open Phase 0 questions (§6.8). Docker Desktop and WSL2 were installed by the developer and verified the same day (§7). P0-T2 `completed` (commit `e860441`). P0-T3 `completed` (services verified). Next task: **P0-T4** (install uv and Python 3.14; record commands). |

## 5. Next actions

In dependency order. The first technical task after documentation is the GROBID experiment; it is **not yet done**.

1. ~~P0-T2~~ `completed` 2026-11-03 (commit `e860441`). Remote hosting (for example GitHub) is not set up and not required yet.
2. ~~P0-T3~~ `completed` 2026-11-03: PostgreSQL and GROBID run with Compose; commands in `README.md`.
3. **Install the chosen Python tooling** (P0-T4, decided in §6.8): uv, then a uv-managed Python 3.14 pinned in `.python-version`; confirm FastAPI and pydantic install on 3.14 (not yet verified) and record commands in `README.md`.
4. **Phase 1 GROBID experiment** on 3–5 permitted papers, then inspection of the returned structure and failure behaviour, written up in `docs/experiments/grobid-feasibility.md` (P1-T1..T8).

## 6. Decisions and blockers

### 6.1 Decisions recorded in the PRD (proposed; developer read-through in progress, see §6.7)

`AD-001`..`AD-016` in `PRD.md` §4.3. The most consequential: modular monolith (`AD-001`), GROBID as initial parser pending the Phase 1 experiment (`AD-003`), paragraph-level passages as a hypothesis (`AD-004`), keyword retrieval before vectors (`AD-005`), plain RAG with no agent loop (`AD-006`), deterministic citation validation separate from claim support (`AD-008`), no authentication in the MVP (`AD-009`).

### 6.2 Open questions that block the next steps

| ID | Blocks | Note |
|---|---|---|
| OQ-017 | Resolved 2026-11-03 | Docker Desktop and WSL2 installed and verified (§7) | No Docker or WSL2; about 18 GB free on C: (checked 2026-11-03). Developer cannot free space on C: now; the repository moved to E:. Docker's data location still to be checked |
| OQ-014 | Decided (§6.8) | Installation and FastAPI/pydantic 3.14 check pending (P0-T4) |
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
| 6 | How a failed document is retried (re-upload vs explicit retry) is unspecified | Decide in the P3-T6 design note; no PRD change now | — |
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
| `OQ-014` frontend | Vite + React + TypeScript (strict), **pnpm** as package manager (installed at P0-T8/P3 with `npm install -g pnpm`, the method pnpm recommends on Windows). Node 24 is already installed (Vite needs 20.19+ or 22.12+). **No component library, data-fetching library or animation library chosen now**: decided at P3-T9 against `NFR-UX-001`; Motion for React (`motion`, imported from `motion/react`) is the candidate if CSS transitions are not enough. | Avoids committing to libraries before the first page exists (`CLAUDE.md` §10). | — |
| Repository contents (P0-T2) | Commit `notes/` (the developer's own learning notes). Do **not** commit `transcripts/` (add to `.gitignore`). | Transcripts are third-party video content (`RISK-13`); notes are the developer's own writing. | — |
| OneDrive original folder | Left in place. The developer deletes it when satisfied. | Deleting the developer's data is the developer's call. | — |

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

Not yet performed: confirmation that the files exist in the developer's folder (see below once committed); any run of application code (none exists). The scripts are structural checks only; they do not prove the documents are correct or complete.
