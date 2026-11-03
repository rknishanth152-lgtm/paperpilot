# UI page process (PaperPilot)

Follow these steps in order for every new or reshaped page. Do not start from a generic SaaS dashboard template. Write steps 1–5 down briefly in the plan and get agreement before step 6.

1. **Purpose.** What is this page for, and what is the one primary task (for example: "check whether this answer's citations are valid and read the evidence")? Which PRD requirements does it serve?
2. **Existing system.** Read `docs/design-system.md` and the neighbouring pages. List the tokens and components you will reuse.
3. **Direction and hierarchy.** Propose the visual direction and information hierarchy: what the eye lands on first, second, third. Evidence and status come before decoration. Use `frontend-design` for the plan-review pass; use `ui-ux-pro-max` searches for specific UX or accessibility questions.
4. **Components and interactions.** Name the reusable components and the page-specific interactions. For each interaction, decide whether it needs motion at all (frequency gate in `design-motion-principles`) and which motion token it uses.
5. **Responsive and accessibility.** Define behaviour at ~375 px, ~768 px and ≥1280 px. List keyboard paths, focus order, labels, text-based statuses, and reduced-motion behaviour.
6. **Implement** only the agreed scope.
7. **Run the app** and look at the rendered result (built-in browser pane or `playwright-cli`).
8. **Test** each viewport, every state (SKILL.md §8), keyboard-only use, and `prefers-reduced-motion: reduce`.
9. **Fix verified defects** before reporting. Report what you saw, with screenshots or snapshots where useful, and what was not checked.

Removing a decoration or an animation that adds nothing is a valid fix.
