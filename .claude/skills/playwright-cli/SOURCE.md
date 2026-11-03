# Provenance of this skill

- Installed by: `npx -y @playwright/cli@0.1.23 install --skills=claude` (official command, run 2026-11-03)
- Upstream: https://github.com/microsoft/playwright-cli (licence Apache-2.0)
- Local modifications: none.
- Side effects of the install command: created an empty `.playwright/` folder (removed because it was empty), downloaded the `winldd` helper (~0.1 MB) to `%LOCALAPPDATA%\ms-playwright`, and detected the installed Chrome as the default browser. No Playwright browser was downloaded.
- PaperPilot note: no `playwright-cli` global command or project Playwright dependency is installed. Run commands as `npx -y @playwright/cli@0.1.23 <command>` and ask before any global or project install (OQ-014).
