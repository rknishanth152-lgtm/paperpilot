# Commit ID map

On 2026-11-10, after the v1.0.0 release, the developer had the git history rewritten to remove a co-author line from every commit message and to replace the author email with a GitHub no-reply address. File contents, dates, authors' names and commit subjects did not change; this was checked for every commit.

Every commit therefore has a new ID. Documents and result files written before the rewrite (for example `progress.md`, `docs/experiments/`, and the commit part of each `benchmarks/results/` file name) quote the old IDs. They are left as written, because they are the record of what was run. Use this table to find the commit an old ID refers to.

| # | Old ID | New ID | Date | Subject |
|---|---|---|---|---|
| 1 | `e860441` | `1bdc767` | 2026-11-03 | chore: initialise PaperPilot repository (P0-T2) |
| 2 | `aba8dda` | `6bf7a97` | 2026-11-03 | docs: record P0-T2 completion in progress.md |
| 3 | `cd5135c` | `62fcee7` | 2026-11-03 | feat: local PostgreSQL and GROBID with Docker Compose (P0-T3) |
| 4 | `14c5c47` | `d0f981a` | 2026-11-03 | build: Python 3.14 environment with uv, pytest, ruff, mypy (P0-T4) |
| 5 | `62b1233` | `5cf184f` | 2026-11-03 | feat: settings module and complete .env.example (P0-T5) |
| 6 | `71e1b58` | `2f9dc4f` | 2026-11-03 | docs: record private GitHub repository in progress.md |
| 7 | `c88131e` | `41dab01` | 2026-11-03 | feat: backend skeleton with health endpoint (P0-T6) |
| 8 | `f5e9c32` | `19601ab` | 2026-11-03 | test: test conventions with folder-based markers (P0-T7) |
| 9 | `23f60e1` | `90011eb` | 2026-11-03 | docs: M2 fresh-clone check passed; Phase 0 complete |
| 10 | `4a4e988` | `00699c9` | 2026-11-03 | docs: GROBID documentation findings (P1-T1); light-theme UI rule |
| 11 | `178b579` | `0c3425c` | 2026-11-03 | docs: record the five CC BY papers for the GROBID experiment (P1-T2) |
| 12 | `3d5bbdb` | `3829c2f` | 2026-11-03 | feat: GROBID experiment script and first results (P1-T3) |
| 13 | `c5e4f60` | `a0460c6` | 2026-11-03 | docs: inspection of GROBID output for five papers (P1-T4) |
| 14 | `ad190e5` | `ae21829` | 2026-11-03 | docs: GROBID failure behaviour (P1-T5) |
| 15 | `3dc510a` | `aab3755` | 2026-11-03 | docs: answers to the Phase 1 open questions (P1-T6) |
| 16 | `029046d` | `21b02c1` | 2026-11-03 | docs: record Phase 1 answers in the PRD (v0.5) |
| 17 | `d52bfd8` | `55ee4e3` | 2026-11-03 | docs: parser output representation (P1-T7); PRD v0.6 |
| 18 | `ebfacd7` | `168b0c0` | 2026-11-03 | docs: GROBID decision go-with-limits; Phase 1 complete (P1-T8) |
| 19 | `cb1d2c9` | `7036d14` | 2026-11-03 | docs: core schema design note (P2-T1) |
| 20 | `c8590ae` | `fe4f7a6` | 2026-11-03 | feat: database access layer and Alembic environment (P2-T2) |
| 21 | `16e9fa4` | `c09efa6` | 2026-11-03 | feat: first migration for papers, documents, passages (P2-T3) |
| 22 | `fb82a05` | `40590a7` | 2026-11-03 | feat: DOI normalisation (P2-T4) |
| 23 | `106d762` | `6d52336` | 2026-11-03 | test: schema constraint tests on a throwaway database (P2-T5) |
| 24 | `db4304f` | `72ea4d2` | 2026-11-03 | docs: schema reference and Phase 2 completion (P2-T6) |
| 25 | `d0bba6a` | `62bc2fc` | 2026-11-03 | feat: file storage interface with local-folder implementation (P3-T1) |
| 26 | `d800faf` | `022d1da` | 2026-11-03 | feat: upload validation (P3-T2) |
| 27 | `6427fc4` | `f96c22a` | 2026-11-03 | feat: GROBID client with failure-reason mapping (P3-T3) |
| 28 | `c3e71f3` | `5c525c4` | 2026-11-03 | feat: parse GROBID TEI into passages (P3-T4) |
| 29 | `6f097f0` | `6adddab` | 2026-11-04 | feat: ingestion pipeline from upload to stored passages (P3-T5) |
| 30 | `aec6ae8` | `7261e3d` | 2026-11-04 | feat: duplicate uploads and retries (P3-T6) |
| 31 | `c6df62e` | `cce3d58` | 2026-11-04 | P3-T7: recover interrupted documents at startup |
| 32 | `83f982d` | `14c25ed` | 2026-11-04 | P3-T8: document HTTP API (upload, status, structure, retry) |
| 33 | `9f81a13` | `edf3657` | 2026-11-08 | P3-T9: first frontend pages (upload, status, structure) |
| 34 | `0a193a5` | `9dba6be` | 2026-11-08 | P3-T10: manual run on five real papers, observations recorded |
| 35 | `2811c69` | `d6936c5` | 2026-11-08 | P3-T10 complete: developer review recorded, Phase 3 and M5 complete |
| 36 | `686d451` | `0e38387` | 2026-11-08 | P4-T1: interim full-text search configuration (OQ-004) |
| 37 | `3a4b402` | `bc8b2d5` | 2026-11-08 | P4-T2: full-text search column and GIN index on passages |
| 38 | `02dcf19` | `0c54a93` | 2026-11-08 | P4-T3: keyword retrieval function |
| 39 | `783763d` | `62b130b` | 2026-11-08 | P4-T4: hostile-input and scope isolation tests for retrieval |
| 40 | `c12127e` | `b13b264` | 2026-11-08 | P4-T5: draft retrieval evaluation set, pending developer review |
| 41 | `368fd83` | `d78f503` | 2026-11-08 | P4-T6: retrieval evaluation harness; evaluation set reviewed |
| 42 | `f3fd4ad` | `065ff0a` | 2026-11-08 | P4-T7: keyword retrieval baseline and miss analysis |
| 43 | `2841b1e` | `113e09f` | 2026-11-08 | P5-T1: choose the interim answer model (OQ-011) |
| 44 | `eefe282` | `c9b0890` | 2026-11-08 | P5-T2: model interface, explicit errors and fake model |
| 45 | `083764d` | `213cf3f` | 2026-11-08 | Fix storage race on concurrent saves into a new folder |
| 46 | `395ee80` | `962b5b4` | 2026-11-08 | P5-T3: answer schema for model output |
| 47 | `f003dd5` | `4b2f185` | 2026-11-08 | P5-T4: context builder for the model |
| 48 | `e5c8ea4` | `37677df` | 2026-11-08 | P5-T5: prompt and single model call with bounded retry |
| 49 | `acdc67e` | `d838ef6` | 2026-11-08 | P5-T6: quote matching against stored passages (OQ-013) |
| 50 | `cc5d99e` | `1e19145` | 2026-11-08 | P5-T7: deterministic citation validator |
| 51 | `364852e` | `798e6ae` | 2026-11-08 | P5-T8: insufficient-evidence paths |
| 52 | `e8af9e9` | `1eb430c` | 2026-11-08 | P5-T9: final answer response and full chain |
| 53 | `7d71740` | `1e0acf6` | 2026-11-08 | P5-T10: fault-injection suite for the answering chain |
| 54 | `f572f08` | `e075985` | 2026-11-09 | P5-T11: answers API route and question page |
| 55 | `83ace8a` | `5f55967` | 2026-11-09 | Correct the P5-T11 mutation count in progress.md |
| 56 | `8a77dcc` | `8a773a5` | 2026-11-09 | P5-T12 (part): Anthropic adapter, tested offline |
| 57 | `cf97295` | `7e0e33e` | 2026-11-09 | P5-T12 (part): Gemini free-tier connector |
| 58 | `aefe32f` | `1b8e6a6` | 2026-11-09 | P5-T12 (part): script for the labelled real-model run |
| 59 | `d09c9b6` | `6aa05fb` | 2026-11-09 | P5-T12 (part): first partial real-model run, Gemini 3.6 Flash |
| 60 | `8bcb701` | `057deeb` | 2026-11-09 | P5-T12: real-model answer baseline; Phase 5 and M7 complete |
| 61 | `69a382d` | `1fc3da6` | 2026-11-09 | P5-T12: check the question page with the real model |
| 62 | `1d7340c` | `a3a2564` | 2026-11-09 | P6-T1: one command runs the whole evaluation |
| 63 | `9654929` | `49e1dea` | 2026-11-09 | P6-T1: make the evaluation command start outside pytest |
| 64 | `aeac70b` | `1bc80bd` | 2026-11-09 | P6-T1: record the first complete evaluation run |
| 65 | `5f8f674` | `a85a992` | 2026-11-09 | P6-T1: correct the count of answers that changed |
| 66 | `fd0cb2a` | `0242228` | 2026-11-09 | P6-T2: citation reference-validity rate over saved answers |
| 67 | `ac42417` | `425ea6f` | 2026-11-09 | P6-T2: record citation validity for both complete runs |
| 68 | `a21b569` | `e615051` | 2026-11-09 | P6-T3 (part): labelling guide and claim-support tools |
| 69 | `b34eacf` | `740b203` | 2026-11-09 | P6-T3 (part): fix the claim-support sample |
| 70 | `5861f96` | `f70e82a` | 2026-11-09 | P6-T3 (part): sheet command and a usable labelling page |
| 71 | `2400f5c` | `a8a59ed` | 2026-11-09 | P6-T3: record that labelling is waiting for the developer |
| 72 | `0d443cc` | `94e8385` | 2026-11-09 | P6-T4: reliability tests, and keep paper text out of error logs |
| 73 | `b99b759` | `0826a34` | 2026-11-09 | Say when selected documents are not parsed (DR-006) |
| 74 | `9e8e8c5` | `5b3bd52` | 2026-11-09 | Add the developer's claim-support labels (P6-T3) |
| 75 | `6292619` | `2ed7375` | 2026-11-09 | Record the claim-support result (P6-T3) |
| 76 | `9e98060` | `11b0e79` | 2026-11-09 | Add the developer's revised claim-support labels (P6-T3) |
| 77 | `3b57f22` | `de6481c` | 2026-11-09 | Record the revised claim-support result (P6-T3) |
| 78 | `49ab45e` | `bca1e97` | 2026-11-09 | Propose a shorter plan for the v1.0 release |
| 79 | `90f4944` | `c33606b` | 2026-11-09 | Apply the v1.0 release plan |
| 80 | `601663c` | `021e094` | 2026-11-09 | Add the VS-1 baseline report and acceptance review (R1) |
| 81 | `a778358` | `e3c580d` | 2026-11-09 | Accept VS-1 with one recorded exception (R1) |
| 82 | `b728134` | `418b2fb` | 2026-11-09 | Add passage embeddings: table, interface and batch job (R2) |
| 83 | `c665c54` | `6b26ec4` | 2026-11-09 | Record the embedding design and real run (R2) |
| 84 | `3e3dcb6` | `10e3c29` | 2026-11-09 | Add semantic and hybrid retrieval (R3) |
| 85 | `e97811d` | `b7aa803` | 2026-11-09 | Fix the retrieval comparison and its rule before running it (R4) |
| 86 | `3d8a7fb` | `f0917c1` | 2026-11-09 | Make semantic retrieval the default on recorded results (R4) |
| 87 | `93da3eb` | `24119ce` | 2026-11-09 | Record the retrieval comparison and semantic answers (R4) |
| 88 | `23064ab` | `3e79182` | 2026-11-09 | Add the reproducibility checklist, schema and labelling sheet (R5) |
| 89 | `231349a` | `b5ba610` | 2026-11-09 | Add the developer's reproducibility labels (R5) |
| 90 | `9d3907a` | `f3ba8a3` | 2026-11-09 | Add the reproducibility assessment pipeline (R6) |
| 91 | `078de34` | `8e74158` | 2026-11-09 | Add the reporting checklist API and page (R7) |
| 92 | `9746851` | `e84a0f2` | 2026-11-09 | Redesign the interface as a research workspace with a new logo |
| 93 | `9df342b` | `49ed9b9` | 2026-11-09 | Record the developer's logo choice |
| 94 | `0fa73b0` | `9248466` | 2026-11-09 | Fix the checklist scoring method before running it (R8) |
| 95 | `218c17f` | `7779b92` | 2026-11-09 | Retry brief provider outages when scoring the checklist (R8) |
| 96 | `622d967` | `34b7976` | 2026-11-09 | Record the reproducibility checklist baseline (R8) |
| 97 | `d0ed921` | `fb505ef` | 2026-11-09 | Correct the test count in the R8 record |
| 98 | `b185f1e` | `38ff4ab` | 2026-11-10 | Add CI and the MIT licence (R9) |
| 99 | `c8892ac` | `14ab350` | 2026-11-10 | Record the release review and keep rejected rows out of the database log (R9) |
| 100 | `c352dcb` | `87b2674` | 2026-11-10 | Fix accessibility findings from the axe and keyboard checks (R10) |
| 101 | `a79d4aa` | `4bcdec6` | 2026-11-10 | Record the R10 fresh-clone, evaluation and accessibility checks |
| 102 | `221c70c` | `ffd8029` | 2026-11-10 | Rewrite the README as a portfolio page and move setup to a guide (R11) |
| 103 | `ab517cf` | `8b013ea` | 2026-11-10 | Add the Playwright skill licence and record the pre-release checks (R12) |
| 104 | `f6b9dbb` | `240de09` | 2026-11-10 | Record the v1.0 sign-off and the repository going public (R12) |
| 105 | `185498c` | `baf8086` | 2026-11-10 | Record the v1.0.0 GitHub release |
