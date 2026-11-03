# React architecture checklist (PaperPilot)

Source of truth: `PRD.md` §4–§5.10 and `CLAUDE.md` §5. The frontend is React + TypeScript + Vite. The package manager, UI library and any data-fetching library are **open decisions** (`OQ-014`); do not add one without asking.

## Principles

- The frontend **displays** what the API returns. It never re-derives evidence, page numbers, validity or statuses.
- No authentication, route guards or user/session state (`AD-009`).
- No global state library unless a concrete need is shown and approved. Server data comes from the API; local UI state stays in components.
- Every status is shown with text (and optionally an icon), never colour alone (`NFR-ACC-001`).

## Checks

- [ ] TypeScript strict mode; no `any` on props or API types; API types match `backend/app/schemas`.
- [ ] Pages compose components; components are small and single-purpose.
- [ ] Each data view handles loading, empty, error, success, and the domain states listed in SKILL.md §8.
- [ ] `validation_status: failed` answers are visibly not evidence-backed; `claim_support` is never shown as verified.
- [ ] Passage text is rendered exactly as stored (no reformatting that changes words); page unknown shown as text.
- [ ] Error messages come from structured error codes, in plain language.
- [ ] Forms have visible, programmatically associated labels; keyboard order is logical; focus is visible.
- [ ] Design and motion tokens come from `docs/design-system.md`; no raw one-off colours, durations or easings in components.
- [ ] Motion respects `prefers-reduced-motion` and never blocks input or reading.
- [ ] No hard-coded API URL; it comes from configuration.
- [ ] No new dependency without a stated reason, licence and maintenance check.
