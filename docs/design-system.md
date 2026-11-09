# PaperPilot: Design system

| Field | Value |
|---|---|
| Status | **§2 agreed and implemented** (P3-T9, `frontend/src/styles/tokens.css`). §3 motion: only the tokens and patterns used so far are implemented; the rest remains proposed. |
| Owns | Visual and motion tokens, reusable patterns, implementation conventions |
| Implements | `NFR-UX-001` (interface quality) and `NFR-ACC-001` in `PRD.md` |
| Does not own | Requirements (`PRD.md`), working rules (`CLAUDE.md`) |

This document is where tokens live once agreed. Components use tokens from here, never one-off values. When a token is added or changed, update this file in the same change.

## 1. Product character

PaperPilot is a concentration tool for reading and checking evidence. The interface should feel **precise, calm and trustworthy**: the evidence and its status are the most important things on any screen. Visual direction: cool grey-white surfaces, near-black ink, one ink-blue accent, and a reading serif for source text (agreed with the developer at P3-T9).

**Developer requirements (2026-11-03):**

- **Light theme first.** The primary design is a light theme. No dark background with neon or acid-bright accents: the developer considers that look "AI slop". A dark mode, if ever added, is secondary and also avoids neon.
- **Polished, purposeful motion** as defined in §3.
- **Colour theme explained before building.** Before any UI is implemented, the proposed palette is presented to the developer (named colours, hex values, where each is used and why) and agreed.

## 2. Visual tokens

Agreed with the developer at P3-T9. The CSS custom properties in `frontend/src/styles/tokens.css` are the implementation. Contrast ratios were measured in the browser from those tokens.

| Colour | Hex | Use |
|---|---|---|
| Mist | `#F5F7FA` | Page background |
| Sheet | `#FFFFFF` | Panels |
| Frost | `#EDF0F4` | Passage blocks |
| Rule | `#D9DEE5` | Borders, dividers |
| Ink | `#161A1F` | Body and passage text (16.28:1 on Mist, 15.29:1 on Frost) |
| Slate text | `#535B66` | Secondary text, labels (6.40:1 on Mist, 6.01:1 on Frost) |
| Ink blue | `#1F4F82` | Primary button, links, focus ring (7.83:1 on Mist; white text on it 8.40:1) |
| Ink blue hover | `#183F69` | Primary button hover |
| Blue wash | `#E6EEF7` | Hover, selected (Ink blue on it 7.18:1) |
| Marker | `#FFF1B8` | The evidence passage a citation points to (Ink on it 15.42:1, Slate text 6.06:1) |

| Status | Text on background | Contrast | Icon |
|---|---|---|---|
| Pending | `#4A5560` on `#EEF0F2` | 6.66:1 | Clock |
| Processing | `#8A5A00` on `#FBF1DC` | 5.28:1 | Spinner |
| Parsed | `#1E6B3A` on `#E5F2E8` | 5.65:1 | Check |
| Failed | `#A3302A` on `#FBEAE7` | 5.98:1 | Alert |

Reporting checklist statuses (agreed with the developer at R7). Existing colours only, with deliberately no red or green, so nothing reads as a pass or fail grade (`FR-REP-004`).

| Status | Text on background | Contrast | Icon |
|---|---|---|---|
| Reported | `#1F4F82` on `#E6EEF7` | 7.18:1 | Check |
| Partly reported | `#1F4F82` on `#FFFFFF`, inset `#D9DEE5` border | 8.40:1 | Half circle |
| Not found in the material examined | `#4A5560` on `#EEF0F2` | 6.66:1 | Info |
| Needs review | `#8A5A00` on `#FBF1DC` | 5.28:1 | Alert |

A status is always a word plus an icon; colour only reinforces it (`NFR-ACC-001`).

**Type.** IBM Plex Sans (interface; 400, 500, 600) and IBM Plex Serif (paper titles and passage text; 400), self-hosted through `@fontsource`, so no font request leaves the machine. Sizes: `--text-sm` 13px, `--text-base` 15px, `--text-reading` 17px, `--text-lg` 20px, `--text-xl` 24px. Passage text is limited to `--measure-reading` (68 characters wide).

**Space and shape.** `--space-1` to `--space-7` (4, 8, 12, 16, 24, 32, 48 px); `--radius-sm` 4px, `--radius-md` 8px. No shadows or gradients.

**Breakpoints.** At 64rem (1024px) and above, the section list becomes a sticky left column. At 30rem (480px) and below, page and panel padding tighten.

## 3. Motion system

### 3.1 Principles

1. Every animation communicates a **state change, hierarchy, causality or feedback**. If it does none of these, remove it.
2. **Frequency gate.** Rare actions may be expressive; frequent actions are fast and subtle; keyboard-initiated actions and the most frequent interactions are instant.
3. **Reading areas are still.** Paper reader and passage text: no entrance animation, no parallax, no motion while text is being read. Only scroll-to-evidence and a brief highlight are allowed.
4. **Motion follows real state.** Processing indicators reflect real `pending`/`processing` statuses. No invented progress percentages or timed fake steps.
5. **Never block input.** Animations are interruptible; the UI accepts the next click or keypress immediately.
6. **Reduced motion is a first-class mode**, not an afterthought (§3.5).

Avoid: bounce on functional UI, constant pulsing, blur-in entrances, unnecessary parallax, staggering every list, and the same fade-slide-up on every section.

### 3.2 Tokens (proposed)

Durations:

| Token | Value | Use |
|---|---|---|
| `--motion-duration-instant` | `0ms` | Keyboard-initiated changes, very frequent toggles |
| `--motion-duration-fast` | `120ms` | Hover, focus, press feedback, colour/opacity changes |
| `--motion-duration-base` | `180ms` | Dropdowns, tabs, small expand/collapse |
| `--motion-duration-moderate` | `240ms` | Dialogs, side panels (evidence panel, sidebar) |
| `--motion-duration-emphasis` | `320ms` | Rare signature moments only (§3.4) |

Easings:

| Token | Value | Use |
|---|---|---|
| `--motion-ease-out` | `cubic-bezier(0.2, 0, 0, 1)` | Elements entering or responding to the user |
| `--motion-ease-in` | `cubic-bezier(0.4, 0, 1, 1)` | Elements leaving (exit is shorter than enter) |
| `--motion-ease-in-out` | `cubic-bezier(0.4, 0, 0.2, 1)` | Elements moving between two on-screen positions |

Distances: `--motion-distance-sm: 4px`, `--motion-distance-md: 8px`. Movement stays small; panels slide by their own width only when the panel itself is moving into view.

Values are starting points to verify in a browser at P3-T9, not measured results.

### 3.3 Patterns

| Area | Behaviour | Tokens |
|---|---|---|
| Page navigation | Content cross-fades; no full-page slide. Focus moves to the new page heading. | fast, ease-out |
| Sidebar, evidence panel | Slides from its edge with opacity; content inside does not stagger. | moderate, ease-out / ease-in on close |
| Dialog | Fades in with a slight scale (0.98 → 1); backdrop fades. Focus trapped and returned on close. | moderate |
| Dropdown, popover | Opacity + 4px translate from the trigger side. | base |
| Tabs | Indicator moves between tabs; panel content swaps without animation. | base, ease-in-out |
| Expandable section | Height via `grid-template-rows: 0fr → 1fr` (or Motion layout), never by animating `height` with JavaScript per frame. | base |
| Search and filter | Results update in place; removed items fade, remaining items do not jump. No per-item stagger. | fast |
| Loading | Skeleton or text status matching the real state; a spinner only for short waits. No fake progress. | — |
| Success, error, empty | State changes cross-fade; error text appears next to its cause. Failed citation validation never animates like a success. | fast |
| Hover, focus, press | Colour/opacity on hover; visible focus ring appears instantly; press feedback with slight scale (0.98). | fast |

### 3.4 Signature interactions (at most two)

1. **Citation → evidence.** Selecting a citation scrolls the evidence passage into view and briefly highlights it (background tint that fades out, `--motion-duration-highlight`, 1600ms). This shows causality: "this statement came from here". Implemented at P5-T11 for the whole passage, not the quoted span.
2. **Comparison context reveal.** Opening a comparison cell reveals its dataset, split, conditions and evidence in place, so context is never hidden behind a number.

Both are candidates. Each must prove it helps in a browser test before it stays.

### 3.5 Reduced motion

Under `prefers-reduced-motion: reduce`: remove translation, scale and scroll animation; keep instant state changes and short opacity changes (≤ `--motion-duration-fast`); scroll-to-evidence jumps directly and the highlight stays visible without fading.

### 3.6 Implementation conventions

- **CSS transitions first**, using the tokens as CSS custom properties.
- **Motion for React** (`motion` package) only when CSS cannot express it cleanly (exit animations on unmount, shared layout transitions). Adding it is a dependency decision under `OQ-014`; ask first.
- **Not approved:** GSAP, Lottie, Three.js or other animation libraries without a specific feature that justifies them.
- Animate `transform` and `opacity`. Avoid animating layout properties (`width`, `height`, `top`, `left`) when an alternative exists.
- Animations never change the tab order, steal focus, or hide content from screen readers. Decorative motion is not announced.
- Every motion change is checked in a running browser at desktop and mobile widths, with reduced motion on and off, for layout shift, clipping and responsiveness.
