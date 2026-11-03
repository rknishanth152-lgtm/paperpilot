# Claude Code Workflow Notes (for building PaperPilot)

**Primary source:** `transcripts/claude-code-rag.txt`, a live build with Claude Code and the Cursor IDE.
**Secondary source:** `transcripts/fullstack-rag.txt` (built with Cursor's agent, not Claude Code). I use it only where a technique transfers, and mark it **[Cursor]**.
You wrote "the transcript" in the singular. This topic is about Claude Code, so I treated the Claude Code transcript as the main one.

## Evidence tags

| Tag | Meaning |
|---|---|
| **T** | Said or shown in the transcript. Short quotes are paraphrased from the auto-caption. |
| **R** | My recommendation. Not in the transcript. |
| **U** | The transcript doesn't show it. |

Caveats: the transcript is speech-only, so I never see the actual prompts on screen. Exact file names and slash-command contents are known only where spoken. Claude Code's features change between versions, so check the current docs for the exact keys and settings.

---

## Part 1: Techniques

### 1. Orient a new session with an onboarding command

1. **Principle:** An agent with no memory needs the same briefing every time, so write the briefing once as a reusable command.
2. **Evidence (T):** The repo has an `onboard` slash command. Running it makes Claude scan the project structure, read the git log (even though it was empty) and the progress file, and report state: "nothing is done, module 1 not started". He re-runs it every time he starts a fresh session ("I might just onboard this agent again").
3. **When:** At the start of every new or cleared session, and before any bug fix in a session that didn't write the code.
4. **PaperPilot example (R):** An `/onboard` command that says: read `CLAUDE.md`, `PRD.md`, `progress.md`, the latest plan file and `git log -10`; then state what is done, what is in progress, and what is next, without changing any files.
5. **Mistake to avoid:** Onboarding a fresh agent and then asking for a fix without telling it which plan or module is relevant. The onboard result is general, so point to the specific plan or file.

### 2. Explore the codebase yourself, in the IDE, alongside the agent

1. **Principle:** You can only steer what you can picture. Keep a mental map of where things live.
2. **Evidence (T):** He opens the repo in Cursor "so you can see the code files and actually make changes". He walks the layout out loud: `backend` (app with models, routers, services, database layer, a virtual environment), `frontend` (public, source with components/hooks/pages/types, `node_modules`), `scripts`, `supabase` migrations, and the editor-agent folders. He says to ask the editor's agent to explain folders, "the better mental model… the more likely you're able to keep it on the rails". He also uses the IDE's search to find where the Tavily key setting lives, and finds it is on the settings page, not in `.env`.
3. **When:** After every module build, and whenever an error mentions a layer you can't place.
4. **PaperPilot example (R):** After the ingestion module, open `ingestion/` and ask a second agent: "Explain each file here and draw the call order from upload to the chunks table." Check it against what you expected.
5. **Mistake to avoid:** Only reading the chat summary. He himself notes he "doesn't necessarily need to understand everything in main.py", but you need to know how the parts fit.

### 3. Use read-only exploration agents for hard questions

1. **Principle:** Delegating research to sub-agents keeps the main context small, and plan mode makes the research safe.
2. **Evidence (T):** For the persistent LangSmith tracing bug he goes into plan mode and it "triggered three explore agents to explore the codebase". For planning, a plan sub-agent "protects the context window of the main agent"; each sub-agent consumes its own tokens (30k, 25k, 15k) while the main agent stays near 15%.
3. **When:** Before touching a bug you can't explain after one or two attempts, or when a plan needs to read many files.
4. **PaperPilot example (R):** "Why do citations show the wrong page number? Use plan mode and explore agents; trace chunk creation, storage and the citation render path. Don't change code."
5. **Mistake to avoid:** Letting the building agent keep trying fixes in a long, full session. In the transcript, repeated attempts burned time until a different mode solved it (section 11).

### 4. Convert requirements into a plan with a light PRD plus plan mode

1. **Principle:** Keep the top-level requirements short and decide details at planning time, per feature, when you have the most context.
2. **Evidence (T):** The PRD gives scope and eight modules but is "intentionally light on detail so you can figure out the rest with Claude during the planning stages of each module". They avoid heavyweight spec frameworks. For each module he presses Shift+Tab into plan mode and dictates the request. Claude asks clarifying questions (embedding provider separate? one plan or several? backfill? which file formats? which metadata fields?) and he answers. Plans state complexity ("medium") and sequence tasks (backend, then Supabase client, then database).
3. **When:** Any feature bigger than a few lines.
4. **PaperPilot example (R):** PRD module "Findings extraction". Plan-mode prompt: "Plan module 4 from the PRD. Ask me anything you need to clarify before proposing; in particular ask about the findings schema and where evidence pointers are stored."
5. **Mistake to avoid:** Accepting the plan as printed. He says "this is why I didn't want to just accept what it provided. I want to actually read this plan and make changes". He also admits he should have read the PRD more carefully: it named an older OpenAI API that later broke tracing.

### 5. Save every plan as a file, then edit the file

1. **Principle:** A plan in a file survives context clears, can be audited, and can be reused to onboard another agent.
2. **Evidence (T):** Plan mode is read-only, so after planning he escapes plan mode and asks Claude to "move this plan into our agent plans folder", using a naming convention described in `CLAUDE.md` (numbered plan files, e.g. "plan number nine and ten"). He edits plans by instruction, for example changing the record-manager approach to delete old chunks and re-import because "orphan chunks" can remain. He asks for the plan to be revised for parallel work. He also copies the plan text into the file himself by Ctrl+click when quicker.
3. **When:** Always, before building anything non-trivial.
4. **PaperPilot example (R):** `agent-plans/07-reproducibility-checklist.md`, with acceptance criteria written as checks ("a paper with no code link produces `code_available = false` with an evidence note").
5. **Mistake to avoid:** Editing the plan while the session is in accept-edits mode without saying "do not execute". In the transcript Claude began executing the plan changes, and he had to stop it.

### 6. Split work into units sized for one fresh context

1. **Principle:** A unit of work should fit in one session at well under half the context, and be testable on its own.
2. **Evidence (T):** Eight modules, each planned separately. Module 1 became 14 tasks and took about 13 minutes of building. He considers breaking a medium-complexity plan into several, but tries a single shot first with progress notes as a fallback. He notes the big plan session used about 50,000 tokens, so he clears before building. When a bug list is long, he suggests dictating it into a file, pasting it as a single prompt, or making a plan just for the list.
3. **When:** Whenever the plan has more than about one subsystem, or the agent's context passes roughly 50%.
4. **PaperPilot example (R):** Don't plan "ingestion". Plan "upload + storage", "parse + chunk", "embed + store", each with its own check.
5. **Mistake to avoid:** One giant build. In the Cursor transcript the agent built far more than intended in a "too big" phase, and the developer could not review it all **[Cursor]**.

### 7. Parallelize deliberately, and tell Claude to

1. **Principle:** Independent work can run in parallel, but parallel agents need explicit instruction and isolation.
2. **Evidence (T):** Asks "can any elements of the plan be executed in parallel?" and the plan is rewritten into stages or waves. When the first build run did not use sub-agents he says "can you use general-purpose sub-agents to parallelize this?" and two task agents start. Runs plans for independent modules (3 and 4; 5 and 6) in two sessions at once. Runs a bug fix in one session and front-end changes in another. Four task agents work through a bug batch. Later he says he lost time because agents restarted servers and changed shared files, and recommends **git worktrees**.
3. **When:** Independent modules, separate backend/frontend work, bug batches.
4. **PaperPilot example (R):** Wave 1: Supabase schema migration. Wave 2 (parallel): parser service and the upload UI.
5. **Mistake to avoid:** Running several agents against one working copy and one set of dev servers. Duplicate servers caused "ghost" behavior until the restart script killed all processes.

### 8. Instruct file changes with a command, a plan path and tight scope

1. **Principle:** The cleanest edit instruction is "execute this plan, and nothing else" in a clean context.
2. **Evidence (T):** `/clear`, then the custom `build` command with the plan file dragged in. The build command tells Claude to read the entire plan, execute tasks in order, then test and validate. He notes it was missing one instruction: update `progress.md`. For small changes he uses precise prompts, often with a screenshot. For example, "within this LLM service Python file, update the system prompt around tool usage". He also constrains: "Just finish making changes to the plan. Don't carry out any code changes yet."
3. **When:** Every feature build. Use precise single-file prompts for small edits.
4. **PaperPilot example (R):** `/build agent-plans/05-hybrid-search.md`, then separately "In `retrieval/service.py` only, add a `top_k` parameter; do not touch other files."
5. **Mistake to avoid:** Vague prompts such as "make it better". When Claude over-engineered text-to-SQL, he had to say "that's all I want. Stop overengineering it."

### 9. Review at four levels: the plan, the files, the diff, the behavior

1. **Principle:** Review is cheaper earlier. Read the plan, watch files appear, scan the diff, then test behavior.
2. **Evidence (T):** (a) Reads the plan before building. (b) Watches the file tree fill while Claude works. (c) Uses GitHub Desktop to see "55 changed files" and scans them ("looking through it, it all looks pretty good"). (d) Manually tests in the browser, checks database tables and storage in Supabase, and reads LangSmith traces. He pushes back on design ("Surely what you're proposing means the LLM could delete all data in the table?") and Claude agrees it was wrong. He catches plaintext API keys and the hidden fallback that returned all rows.
3. **When:** Always. Spend the most attention on security, data, and anything the agent says is "done" without verification.
4. **PaperPilot example (R):** After the findings module, run a query that should return one paper's findings and compare the rows to the PDF by hand for three papers.
5. **Mistake to avoid:** Trusting a claim like "migration applied" or "validated". In the transcript, a migration had silently not been applied, and a fallback hid wrong data.

### 10. Make the agent test itself, with a browser and a suite

1. **Principle:** If Claude can run the check, you stop being the feedback loop.
2. **Evidence (T):** Playwright MCP lets Claude log in, click and verify the UI ("I've been tracking Playwright as it tests out the interface"). He adds a **validation / regression suite** during module 2, "covering all features, with acceptance criteria on what it means to pass", and tells `CLAUDE.md` to make future plans update it. He warns that a large suite costs usage and suggests codifying some tests as scripts instead of agent runs. He also does manual smoke tests and a two-user isolation test. He admits "we should have the agent verify itself so you don't need to give the feedback".
3. **When:** Build the suite early (he says it's a monumental task later), and run the relevant part after each feature.
4. **PaperPilot example (R):** A test paper fixture and acceptance checks: "upload fixture PDF → status completed → 3 findings with page numbers → second user cannot see it".
5. **Mistake to avoid:** Running the whole agent-driven suite on every small change. It can exhaust your usage allowance.

### 11. Debug with evidence, fresh context and a different tool when stuck

1. **Principle:** Debugging needs observations, not guesses. If one agent loops, change the context, the mode, or the tool.
2. **Evidence (T):** Pastes the exact error or a screenshot. Uses LangSmith to see the real tool call and SQL. Compares the agent's SQL result to the same query in the Supabase SQL editor. Adds logging ("we need a lot more log files"). Starts a clean session for a bug and onboards it first. For the stubborn tracing bug and the admin-settings bug, **Cursor's debug mode** (hypotheses → add instrumentation → reproduce → narrow the cause → remove instrumentation) solved what Claude Code did not; he notes Claude Code has no equivalent slash command. Switches models to isolate cause (a local model vs GPT 5.2 showed the duplicated text was a code bug).
3. **When:** After two failed fix attempts, or when the symptom is not understood.
4. **PaperPilot example (R):** "Findings are missing for scanned PDFs." Log the parser output length per page, run a failing fixture, then ask a fresh agent to analyze the log.
5. **Mistake to avoid:** Repeated "fix it" in the same bloated session. The transcript shows 8+ minute attempts and poor results near the context limit. **[Cursor]** version of the same lesson: when a chat is broken, switch to a fresh chat and a stronger model.

### 12. Prevent architecture drift with written rules, plans and database-level guarantees

1. **Principle:** Put constraints where they cannot be ignored: in the instructions every session loads, and in the database itself.
2. **Evidence (T):** `CLAUDE.md` lists the tech stack, "rules of engagement" (no frameworks, raw SDK calls, row-level security so users see only their data), the plan/build/validate flow, and the plans-folder convention. The PRD fixes the stack and module list. Security is enforced in Postgres (RLS; a read-only role for text-to-SQL) not in Python checks. When Claude kept mishandling Supabase migrations, he adds a note to `CLAUDE.md` that the CLI is installed and the project is remote. Global (not per-user) embedding settings avoid dimension conflicts across users. Release tags per module give rollback points.
3. **When:** Before the first feature, and every time you correct the same mistake twice.
4. **PaperPilot example (R):** `CLAUDE.md` rule: "Every new table has RLS and a policy test. Findings must carry `paper_id`, `page`, and `quote`."
5. **Mistake to avoid:** Relying on the prompt alone for safety. Python-side validation was rejected for SQL. Also: an RLS-off demo table remained "unrestricted" at the end.

### 13. Maintain context: keep CLAUDE.md lean, track progress in a file, clear often

1. **Principle:** Context is a budget. Persistent facts go in files, the rest goes away on `/clear`.
2. **Evidence (T):** `CLAUDE.md` is "pretty lean" because it loads in every conversation. Status line shows model and context percentage (say 20,000 tokens = 10%). Rule of thumb: above 50% start a new conversation. He runs `/clear` before each build, and between phases. `progress.md` uses not started / in progress / completed so "new agents… will be able to figure out very quickly where the project is at". When blocked halfway through validation he has Claude update the progress file, exits and resumes, then clears and says "check progress.md and continue with plan one". He turns repeated chat into scripts and commands (start-services, restart, onboard, build).
3. **When:** Constantly. Watch the percentage during long builds.
4. **PaperPilot example (R):** After finishing parsing, tell Claude: "Update progress.md: parser done, chunking in progress, known issue: two-column PDFs interleave text."
5. **Mistake to avoid:** Continuing a task past roughly 95k tokens because "it's nearly done". The transcript shows quality dropping and the tracing fix going nowhere near the limit.

### 14. Turn repeated instructions into scripts and commands

1. **Principle:** If you say the same thing twice, make the agent do it from a file.
2. **Evidence (T):** After repeatedly fighting with starting services in PowerShell he asks for a "start services script" and a `CLAUDE.md` note. Later the restart script is changed to kill all processes. He says to watch for "any kind of duplication of effort… create slash commands, create scripts". He also runs the restart script himself since he does it so often.
3. **When:** The second time you repeat an instruction.
4. **PaperPilot example (R):** A `scripts/reset-test-data` script for the fixture papers, plus a `CLAUDE.md` line that tells agents to use it.
5. **Mistake to avoid:** Scripts that start servers without stopping the old ones (stale processes served old code).

### 15. Keep a human in the loop on a defined set of operations

1. **Principle:** Approval should be tied to blast radius, not applied everywhere.
2. **Evidence (T):** See the approvals table in Part 2.
3. **When:** Set permissions at project start, then adjust as you learn what you trust.
4. **PaperPilot example (R):** Allow `pytest` and read-only git commands. Ask for `git push`, migrations and anything touching `.env`.
5. **Mistake to avoid:** Full auto-accept ("YOLO") in a project that holds real credentials or data.

### 16. Give the agent visual references for UI work

1. **Principle:** For UI, show, don't describe.
2. **Evidence (T):** Pastes screenshots of bugs (broken tabs layout, tool-call rendering) and a screenshot of how Claude's own app renders thinking steps and says "can we try to reproduce this type of layout?" **[Cursor]** He numbers items on a screenshot and gives one instruction per number, and runs a dedicated UI design pass with research, gap analysis and a design-system request.
3. **When:** Layout, rendering and interaction bugs.
4. **PaperPilot example (R):** Screenshot of the citation side panel with "1: quote should be highlighted; 2: page badge overlaps title".
5. **Mistake to avoid:** Fixing UI state bugs in the same turn as backend changes. He noted the tool-call UI needed event-level changes (a tool-complete event, persisting tool calls) and not only styling.

---

## Part 2: Which operations need human approval

| Operation | What the transcript shows | Tag |
|---|---|---|
| **Accepting a plan** | Plan mode is read-only. The prompt "would you like to proceed" is answered "not yet", so he can save and edit the plan first. | T |
| **Answering design questions** | Claude asks scoping questions in plan mode and he decides (e.g. same LLM for metadata, no backfill, DB-stored schema, raw SQL with DB permissions). | T |
| **Command permissions** | A `settings.json` with allowed, denied and ask-first command lists. Example: `npm create` commands allowed. He prefers this to accepting everything. Playwright triggers many prompts until added to the settings. | T |
| **Reading secrets** | Claude can't read `.env` ("you can't see it because you don't have permission"), but can use the variables. | T |
| **Putting credentials in files** | He chose to save a **test** account in `CLAUDE.md` and says he doesn't mind for a test login. | T |
| **Running SQL / migrations** | Claude asks him to run SQL in Supabase, or he tells it to use the Supabase CLI. It struggled with the remote setup, so he added guidance. | T |
| **Account/project selection** | Claude asks which Supabase project; he supplies the ID. | T |
| **Hardware/resources** | Claude asks if he accepts a ~2 GB PyTorch download. | T |
| **Commits and releases** | Commits and tags are created through an agent or GitHub Desktop at module boundaries; he checks the file count. Private repo, env files ignored. | T |
| **Restarting servers** | He sometimes runs restart scripts himself. | T |
| **Edit-mode risk** | In accept-edits mode Claude ran code when he only wanted plan edits. | T |
| **What isn't shown** | Whether specific destructive commands (`git reset`, `rm`) were denied in the settings file. | U |

---

## Part 3: What a beginner should adopt first (ranked)

1. **`CLAUDE.md` + PRD + `progress.md`** (techniques 12, 13). They carry everything else.
2. **Plan mode → saved plan → `/clear` → build command** (4, 5, 8). The core loop.
3. **Read the plan and ask questions before building** (4, 9).
4. **Watch the context percentage and clear at about 50%** (13).
5. **Playwright + a small regression suite from the first feature** (10).
6. **Test two-user isolation and database permissions manually** (9, 12).
7. **A start/restart script** (14).
8. **Commit after each working step and tag modules** (the transcript's own regret, section 9).

Things to skip at first: running many parallel agents (7), until you have worktrees.

---

## Part 4: Reusable workflow for one feature at a time

This is my synthesis (R) of the loop the developer used ("plan, build, validate, iterate, commit"). The prompt wording is my template, not a quote.

**Setup (once per project)**
- `CLAUDE.md` (lean): stack, hard rules (RLS on every table, no secrets in code, file layout), how to start/stop services, where plans live, "update `progress.md` when you finish a task", "add tests to the validation suite for every feature".
- `PRD.md`: modules and acceptance criteria in plain language.
- `progress.md`: each module as not started / in progress / completed.
- Commands: `onboard` and `build`.
- Permissions file: allow safe commands, ask for push, migrations and `.env`.

**For each feature**

1. **Fresh session.** `/clear` or start new. Run `onboard`. Check the context indicator.
2. **Plan (read-only).** Enter plan mode. Prompt: "Plan feature X from PRD module N. Ask me questions before proposing. List files to change, the order of tasks, acceptance checks, and which parts can run in parallel."
3. **Answer questions and review the plan.** Look for: stack violations, missing RLS, hidden fallbacks, anything bigger than the request. Say what to change.
4. **Save the plan.** Leave plan mode and ask for the plan to be saved in the plans folder using the naming convention. Say "do not execute yet" when you ask for edits.
5. **Checkpoint.** Commit what exists, so you can revert.
6. **Clear, then build.** `/clear`, then `build <plan file>`. If the plan has independent parts, say "use sub-agents for these tasks".
7. **Verify in layers.**
   - The agent runs the plan's validation steps (browser test, unit tests).
   - You open the changed files and the diff.
   - You test the behavior by hand, plus the data in the database and the trace tool.
   - Two-user isolation check if data is involved.
8. **Fix in batches.** Collect problems in one list (with screenshots and exact errors). Small list: one prompt. Long list: its own plan.
   - If an agent fails twice: stop, `progress.md` note, fresh session, `onboard`, explore agents or a different debugging mode.
9. **Update memory.** Update `progress.md`, add or run regression tests, add any repeated correction to `CLAUDE.md`.
10. **Commit and tag.** Review the file count, confirm no env files, commit, tag.
11. **Clear** and move on.

**Stop conditions:** context above 50% before the build starts; two failed fix attempts; any security surprise (plaintext secrets, RLS off, a fallback that hides errors); the agent doing something you didn't ask for.

---

## What the transcript does not show (U)

- The text of `CLAUDE.md`, the `build` and `onboard` commands, or the plan files.
- How the developer handles merge conflicts, branches or pull requests (he used the main branch only and recommends worktrees later).
- Any automated CI.
- How effective the regression suite actually was beyond the first runs.
- Whether Claude's settings file blocked any dangerous command.
