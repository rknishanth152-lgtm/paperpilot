# PaperPilot v1.0 release plan

| Field | Value |
|---|---|
| Status | **Approved** by the developer and applied, 2026-11-09 (`progress.md` §6.15). |
| Replaces | Phases 6 (remainder) to 11 and gate M14 of `docs/implementation-roadmap.md` |
| Why | The developer wants the project finished soon, at a standard fit for a public GitHub repository |

The roadmap's own rule is the basis for this plan: "Do not shorten a phase by dropping tests or evidence recording; reduce scope instead." So the plan removes features and repeated process, and keeps the quality bar.

## 1. What remains today

| Work | Tasks left |
|---|---|
| Phase 6, evaluation | 2 |
| Phase 7, structured extraction | 9 |
| Phase 8, semantic and hybrid retrieval | 7 |
| Phase 9, discovery | 8 |
| Phase 10, comparison | 7 |
| Phase 11, reproducibility | 7 |
| M14, release readiness | 7 |
| **Total** | **47** |

This plan replaces those 47 tasks with **12 work packages**.

## 2. Scope of v1.0

| Feature | Decision | Reason |
|---|---|---|
| Reproducibility checklist (Phase 11) | **Keep** | It is the feature that sets PaperPilot apart, and it reuses the existing retrieve, structured-output and quote-check chain. It needs Phases 3, 5 and 6, not extraction. |
| Semantic and hybrid retrieval (Phase 8) | **Keep, compressed** | Recall@5 is 8 of 16 and all 8 misses are vocabulary mismatches, the project's largest measured weakness. A before-and-after on the same questions is a strong result either way. The database image already includes pgvector. |
| Structured extraction (Phase 7) | **Defer** | The most expensive phase, with hand labelling of 3 to 5 papers. Its main consumer is comparison. |
| Cross-paper comparison (Phase 10) | **Defer** | Cannot start without extraction, and depends on two further open questions. |
| OpenAlex discovery (Phase 9) | **Defer** | Least tied to the evidence-first idea; upload already covers getting papers in. |

Deferred features move to PRD §12.3 and appear in the README as planned work, never as existing capabilities. `OQ-006`, `OQ-007`, `OQ-008` and `OQ-009` are deferred with them.

## 3. Work packages

Each package ends with tests, a recorded result, a commit and a push.

| # | Package | Covers | Developer input |
|---|---|---|---|
| R1 | Baseline report and VS-1 acceptance | P6-T5, P6-T6 | Accept VS-1 |
| R2 | Embeddings: official docs check, migration, interface with fake and Gemini adapter, batch job, missing embeddings reported | P8-T1 to T3 | Approve sending passages to the embedding service |
| R3 | Semantic and hybrid retrieval | P8-T4, T5 | None |
| R4 | Compare all three on the unchanged question set; choose the default from the results | P8-T6, T7 | None |
| R5 | Checklist v1 (about 6 items) and schema; labelling sheet | P11-T1, T2 | Label 3 papers, about 18 items, **before any model output exists** |
| R6 | Assessment pipeline, status rules, fault-injection tests | P11-T3, T4, T6 | None |
| R7 | Checklist page and API wording review, no score or verdict | P11-T5 | Review the colour explanation and page |
| R8 | Score against the labels; per-status accuracy and `not_found` versus `needs_review` confusion | P11-T7 | None |
| R9 | CI, secret scan of full history, security, privacy, dependency and licence reviews, `LICENSE` file | P0-T9, M14-T2, T3, T7 | Choose a licence |
| R10 | Fresh clone from README only, re-run all evaluations, keyboard, screen-reader and reduced-motion checks | M14-T1, T4, T5 | None |
| R11 | Portfolio README: screenshots, architecture diagram, measured results, known limitations | M14-T6 | Review |
| R12 | Sign-off, then make the repository public | M14 definition of done | Sign off; approve going public |

**Order:** R1 first, because the baseline must exist before retrieval changes. R2 to R4 and R5 to R8 are independent of each other. R9 to R12 come last.

## 4. Changes to how we work

| Today | v1.0 |
|---|---|
| One go-ahead per task | One go-ahead per package |
| Questions come up during a task | Questions are asked together when a package starts |
| Deliberate-breakage checks on most changes | Only on evidence, validation and status rules |
| A log entry per step | One `progress.md` entry per package |

## 5. What does not change

- Tests first, including failure cases; migrations with tests for every schema change.
- Every derived statement links to a stored passage; quotes are checked in code.
- `not_found` is never a verdict; a failed parse gives `needs_review`.
- Metrics come only from saved runs, and post-result changes are logged.
- Secrets, paper text in logs, copyrighted PDFs and unauthenticated deployment stay ruled out.

## 6. Risks

| Risk | Handling |
|---|---|
| Hybrid retrieval does not help | Keyword stays the default and the result is published as a finding. |
| Gemini free-tier embedding limits are unsuitable | Checked against current official documentation at the start of R2. If unsuitable, stop and ask. |
| 18 labels from one labeller is a small sample | Reported with its size as a coarse baseline (`RISK-15`). Labelled before model output, so the labels stay independent. |
| Fewer features than the PRD first planned | Stated openly. A smaller finished system with measured results is stronger than five partial features. |

## 7. Documents to change on approval

- `PRD.md`: §3.1, §12.2, §12.3, §13, and the scope column of the deferred requirements.
- `docs/implementation-roadmap.md`: replace the remaining phases with the packages above.
- `CLAUDE.md`: §9 and §10, from one roadmap task at a time to one work package at a time.
- `progress.md`: decision with date and reason; milestones M9, M11 and M12 marked as deferred.
