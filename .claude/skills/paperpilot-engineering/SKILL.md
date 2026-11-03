---
name: paperpilot-engineering
description: PaperPilot-specific rules for implementing or reviewing any feature that touches the frontend, API, services or database. Covers evidence provenance, citation validity vs claim support, insufficient-evidence and not_found states, comparison context, the design and motion process, state testing, and verification before claiming completion. Use for any PaperPilot implementation, review, UI page, or architecture audit task.
---

# PaperPilot engineering

This skill applies `CLAUDE.md` and `PRD.md` to day-to-day work. It does not replace them: when this file and those documents disagree, **they win**, and you flag the conflict (CLAUDE.md §2). Requirement IDs below are defined in `PRD.md`.

The developer is learning. For every non-trivial choice, say in one or two plain sentences **what** you chose, **why**, and **what the alternative would have cost**. Prefer small steps they can read in one sitting.

## 1. Before writing code

1. Read `progress.md` → current task; read that task in `docs/implementation-roadmap.md`; read the PRD IDs it cites.
2. Inspect the real repository. Documents can be stale; code and tests are the truth.
3. **Trace the feature through every layer** it touches and write the trace down in your plan:

   | Layer | Location (PRD §4, CLAUDE.md §4) | Question to answer |
   |---|---|---|
   | UI | `frontend/` page + components | What does the user see in loading, empty, error, success, failed-validation states? |
   | API | `backend/app/api/` route + `schemas/` | Request/response contract? Which structured error codes? |
   | Service | `backend/app/services/<capability>/` | Which pure functions hold the logic? Which status values can result? |
   | Persistence | `backend/app/models/`, migration | Which tables/constraints? Source (passages) or interpretation (derived tables)? |
   | Provenance | derived record → passage(s) + model/parser/prompt version | How does every displayed value get back to a stored passage? |

4. If a step needs a decision the PRD leaves open (`OQ-`), stop and ask.

## 2. Evidence and provenance rules (non-negotiable)

- **Source vs interpretation.** Passages are immutable source text. Generated items and statuses live in their own tables and link to passages (`DR-002`, `AD-013`). VS-1 answers are not persisted (PRD §8.2). Never write generated text into `passages`.
- **Every derived value links to evidence**: passage ID(s) plus the producing model/parser/prompt version (`DR-001`, `DR-005`). The UI shows evidence from the stored passage, never re-derived or paraphrased (`NFR-COR-001`).
- **Locations come from the database.** Page and section shown to users come from the passage record. Model-supplied pages are ignored (`AD-007`, `FR-CIT-003`). Unknown page/section is `null` and displays as "page unknown", never `0` or "".
- **Citations use prompt-local aliases** (`P1`, `P2`) mapped to passage IDs in code.
- **Never fabricate** quotes, citations, pages, test results or metrics. Never put real paper text in fixtures unless properly licensed (`RISK-13`).

## 3. Citation validity is not claim support

Two separate questions, two separate fields:

| Question | How it is answered | Field |
|---|---|---|
| Does the citation point to a real, in-scope passage that was in the context, and does any quote appear in it? | Deterministic code (`FR-CIT-001`, `FR-CIT-002`) with reason codes `passage_not_found`, `wrong_paper`, `not_in_context`, `quote_mismatch` | per-citation `valid` + `validation_status` |
| Does the passage actually support the statement? | Humans, offline, on a labelled sample (`FR-EVL-004`) | `claim_support` = `not_evaluated` (always, in the MVP) |

Rules: an answer with any invalid citation, or any uncited statement in a `sufficient`/`partial` answer, is `validation_status: failed`; an `insufficient` answer has no statements. A failed answer **must not look evidence-backed** in the UI (`FR-CIT-004`, `FR-UI-003`). No label, icon, colour or tooltip may imply semantic verification. Do not add an LLM judge as a quiet shortcut (`AD-008`).

## 4. Insufficient evidence and `not_found`

- `evidence_sufficiency: insufficient` is a correct, first-class answer (`FR-QA-004`). Show it plainly; do not pad it with a guess.
- `not_found` means **"not found in the material examined"**. Always say so in user-facing text and show which material was examined (`FR-REP-004`).
- A failed or partial parse yields `needs_review`, **never** `not_found` (`FR-REP-002`). Never imply a paper is irreproducible. No scores or verdicts.
- Keep the `DR-006` distinctions: unknown ≠ parse failed ≠ extraction failed ≠ not found ≠ verified absent. Each needs its own status and its own UI copy.
- Failures set an explicit status. Never fall back to a plausible-looking result.

## 5. Comparing research results

- Build comparisons **only from existing extracted items** with evidence (`FR-CMP-001`, `FR-CMP-002`). Missing cells show `not_extracted`.
- Keep the experimental context next to every value: dataset (and version), metric, split/protocol, conditions, evidence quote and location (`FR-CMP-004`).
- Label pairs `directly_comparable`, `requires_context`, `not_comparable` or `insufficient_information` by deterministic rules. **No ranking** unless `directly_comparable` (`FR-CMP-003`). Different datasets are never directly comparable.
- UI: never strip context to make a table look cleaner. A bar chart that puts non-comparable numbers on one axis is a defect.

## 6. Architecture checks

Use these when planning and when auditing. They replace generic FastAPI/React rule sets that conflict with the PRD (no auth, no global state library, no monorepo).

- Backend: [references/fastapi-architecture.md](references/fastapi-architecture.md)
- Frontend: [references/react-architecture.md](references/react-architecture.md)

## 7. UI design and motion

Every page must meet `NFR-UX-001`. Before implementing **any page**, follow [references/ui-page-process.md](references/ui-page-process.md) (purpose → existing system → direction → components → responsive/a11y → build → run → test viewports → fix). Design tokens, motion tokens and conventions live in `docs/design-system.md`; reuse them, and update that document when a token is added or changed.

How the installed design skills fit together:

| Skill | Use it for | PaperPilot override |
|---|---|---|
| `frontend-design` | Visual direction, type, layout, avoiding templated defaults | Evidence clarity outranks aesthetic risk. |
| `ui-ux-pro-max` | Searchable UX, accessibility, typography, colour guidance (`python .claude/skills/ui-ux-pro-max/scripts/search.py "<query>" --domain <domain>`) | Ignore the `gsap` domain and `--motion` GSAP snippets: GSAP is not approved. Do not `--persist` output without asking. Results are suggestions, never overrides. |
| `design-motion-principles` | Creating or auditing motion | Weight Emil (restraint) as primary: PaperPilot is a productivity/reading tool. |
| `playwright-cli` | Browser checks of the running app | Run via `npx -y @playwright/cli@0.1.23 <command>`. Ask before any global or project install. The built-in browser pane is an alternative. |

Motion summary (details in `docs/design-system.md`): every animation must explain a state change, hierarchy, causality or feedback; the paper reader and evidence text get near-zero motion; respect `prefers-reduced-motion`; never fake progress (processing indicators reflect real `pending`/`processing` status only); CSS transitions first, Motion for React only when justified and approved as a dependency.

Gradients, shadows, rounded cards, animations and decorative charts are **not** design quality. Quality is: the user can find, read and trust the evidence quickly.

## 8. States every feature must handle and test

For each page or component that shows server data, implement and check:

| State | Must show |
|---|---|
| Loading | Real status (`pending`/`processing`) with text, no invented percentages |
| Empty | What is missing and the next action |
| Error | Plain-language reason from the structured error code; no stack traces |
| Success | The data, with evidence links and locations |
| Domain states | `failed` + `failure_reason`, `validation_status: failed`, `insufficient`, `not_found`, `needs_review`, page unknown |
| Responsive | Narrow (~375 px), tablet (~768 px), desktop (≥1280 px): no clipping or horizontal scroll |
| Accessibility | Keyboard operable, labelled controls, visible focus, status by text not colour alone (`NFR-ACC-001`), reduced motion |

Backend tests cover the same statuses, including fault injection (`NFR-TST-002`). LLM-dependent tests use the fake provider.

## 9. Verify before claiming done

1. Run the commands recorded in `README.md`. If none exist, say so; do not invent them.
2. For UI work, run the app and look at it: each state above, each viewport, keyboard path, reduced motion.
3. Read the actual diff.
4. Report what changed, what ran, the real output, and what is still unverified. Update `progress.md` only with verified facts.

"Code was generated" is not "done". Done means the roadmap exit criteria have recorded evidence.
