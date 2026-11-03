# Architecture Notes: "Claude Code Agentic RAG Masterclass"

**Source:** `transcripts/claude-code-rag.txt` (about 26,000 words, built live with Claude Code)
**Companion notes:** `architecture-notes-fullstack-rag.md` (the other transcript)
**Purpose:** learning input for PaperPilot

---

## 0. How to read these notes

| Tag | Meaning |
|---|---|
| **T** | Explicitly said or demonstrated in the transcript. |
| **T~** | Said in the transcript, but the auto-caption is garbled and I am interpreting it. |
| **R** | My recommendation or inference. Not in the transcript. |
| **U** | Unknown. The transcript does not give enough evidence. I did not guess. |

Caveats:

- This is a speech-only auto-caption. Code and screens are not visible, so file names, schemas and prompts are known only when spoken.
- Caption fixes from context: "Superbase" = Supabase, "Dockane/Dockling" = Docling, "Quinn" = Qwen, "Langmith" = LangSmith, "Tavali" = Tavily, "PG vector" = pgvector, "role level security" = row-level security (RLS), "Cohhere" = Cohere, "GP file systems" = grep over file systems, "text to cipher" = text-to-Cypher.
- The app is a **learning build**. The developer calls it an **alpha** that he would not deploy. Nothing was deployed.
- The developer's own code is not shown. A PRD and prompts are in a public repo, but I only know what was narrated.

---

## 1. What was built

A multi-user **agentic RAG web app** with two interfaces. **(T)**

1. **Chat interface:** threads, streaming, markdown, tool-call display, sub-agent display, history.
2. **Ingestion interface:** drag-and-drop documents with live status, metadata extraction, and settings.

Test corpus: appliance product manuals (an SFTP folder of about 9,000 PDFs; he used about 150–200). **(T)**

It is built in **eight modules** from a short PRD:

| Module | Scope |
|---|---|
| 1 | App shell: Supabase auth, chat UI, LangSmith, managed RAG via the OpenAI Responses API |
| 2 | Bring-your-own retrieval: ingestion UI, chunking, embeddings, pgvector, provider selector |
| 3 | Record manager (dedupe, change detection) |
| 4 | Metadata extraction and filtering |
| 5 | Docling multi-format support |
| 6 | Hybrid search and reranking |
| 7 | More tools: text-to-SQL and web search |
| 8 | Sub-agents |

---

## 2. Architecture at a glance

**Local development (what he built and ran):**

```
Browser ◄── localhost:5173 ── Vite dev server (React/TS/Tailwind/shadcn)
   │  HTTP + SSE (streaming)
   ▼
FastAPI / uvicorn (localhost:8000)  ──────────────►  Supabase (cloud)
   │  routers / services / models / database            Auth, Postgres (pgvector),
   │                                                    Storage, Realtime, RLS
   ├─► LLM provider (configurable): OpenAI | OpenRouter | LM Studio (local Qwen3)
   ├─► Embedding provider (configurable, separate from the chat LLM)
   ├─► Reranker: Cohere (cloud) or local model
   ├─► Docling (parsing, local)
   ├─► Tavily (web search)
   └─► LangSmith (traces)
Browser also holds a realtime connection to Supabase (e.g. document status).
```

**Production architecture (described only, not built):** local repo → GitHub → CI/build trigger → frontend on Vercel/Cloudflare/nginx (e.g. `rag.app`) and backend on a server running uvicorn (e.g. `api.rag.app`) → Supabase for data and auth. It can also run air-gapped on a local network. **(T)**

---

## 3. Component-by-component table

### 3.1 Frontend

| Component | Purpose | Evidence / notes |
|---|---|---|
| React + TypeScript | Interactive UI with type safety. | **T** |
| Tailwind CSS + shadcn/ui | Styling and pre-built components that Claude Code drops in. | **T** |
| Vite dev server (`localhost:5173`) | Bundles and hot-reloads the frontend. | **T.** The build compiles to plain HTML/CSS/JS. |
| Supabase client (auth + realtime) | Login and live updates (e.g. document status). | **T.** A missing realtime update on delete was fixed by enabling realtime. |
| Chat view | Threads, streaming, markdown, stop button, loading icon, dynamic thread titles. | **T.** How titles are generated is **U**. |
| Tool-call and thinking UI | Collapsible steps, `<think>` bubbles, nested sub-agent output, green tick on completion. | **T.** Many bugs: tool calls rendering in the wrong place, duplicated sub-agent text, thought bubbles jumping. |
| Documents tab | Drag-and-drop upload, statuses (pending, processing, completed), expandable metadata panel, delete. | **T** |
| Settings page (global, admin only) | LLM provider/model/API key/base URL, embedding model + dimensions, reranker, web-search toggle and provider, metadata schema. | **T** |
| Dark mode + dark logo | Polish. | **T** |

### 3.2 Backend

| Component | Purpose | Evidence / notes |
|---|---|---|
| Python + FastAPI + uvicorn (`localhost:8000`) | API and agent runtime. Chosen because AI SDKs and eval/parsing tools are Python-first. | **T.** "Vanilla Python, no frameworks": raw SDK calls, no LangChain-style layer. |
| Structure: `app/` with `models`, `routers`, `services`, database layer | Separation of concerns. | **T** |
| Upload endpoint with record-manager logic | Hash the file, skip duplicates, process new or changed files. | **T** |
| Ingestion pipeline (background) | Parse → chunk → metadata → embed → store. | **T.** Exact stage order is **U**. |
| Concurrency limit on ingestion (`max concurrent ingestions`, 3 then 10) | Stop a batch of files from exhausting RAM. | **T** |
| Embedding service with provider abstraction | Any OpenAI-compatible endpoint (OpenRouter, LM Studio). | **T** |
| Metadata extraction service | LLM extracts structured metadata using a Pydantic schema. | **T** |
| Hybrid search service | Keyword + vector + RRF + optional rerank. | **T** |
| LLM service with system prompt and tool loop | Streams the chat, executes tools, caps rounds. | **T.** Max tool rounds 3 → configurable (10), plus a dynamic prompt line urging a final answer before the limit. |
| Tool: `search_documents` | Vector / keyword / hybrid search with optional metadata filters. | **T** |
| Tool: `query_sales_database` (text-to-SQL) | Raw SQL against one table via a read-only DB user. | **T** |
| Tool: web search (Tavily) | Fallback for questions outside the corpus. | **T** |
| Tool: `analyze_document` (sub-agent) | Loads one whole document into an isolated context and analyzes it. | **T** |
| `scripts/` (start / restart / stop services) | Fix the repeated problem of stale servers. Restart was updated to kill all processes first. | **T** |
| Supabase migrations folder (SQL files) + Supabase CLI | Schema changes. | **T.** Claude never seemed to understand that Supabase was remote, so the developer added instructions to `CLAUDE.md`. |

### 3.3 Database / storage (Supabase)

| Component | Purpose | Evidence / notes |
|---|---|---|
| Supabase Auth | Login and user management. | **T** |
| Row-level security | Each user sees only their own data. | **T.** Exact policies are **U**. |
| `threads` / `messages` | Conversation history. | **T.** Legacy OpenAI-assistant columns were removed. Tool calls were later saved in a JSONB column. |
| `documents` | One row per file: name, status, content hash, LLM metadata (title, summary, document type, topics, language), user id. | **T.** Exact column list is **U**. |
| `chunks` | Content, embedding, metadata (file name, chunk index), user id, document id. | **T** |
| pgvector column | Embeddings. The fixed 1536 dimension was removed so users can choose any embedding model. | **T.** Index handling after that change is **U** ("might have had to remove an index… come back to"). |
| Storage bucket `documents` | Original files, with a folder per user id. | **T.** Deleting a document removes the row, its chunks and the stored file. |
| `global_settings` | Provider config, embedding config, reranker config, metadata schema (JSON). | **T** |
| User profile table with admin flag | Only admins can open settings. A profile is created automatically with each user. | **T.** Planned and debugged. |
| `sales_data` (demo table) | Target of text-to-SQL. | **T.** RLS is **not** enabled on it. The developer admits this. |
| Restricted Postgres role | Read-only access to `sales_data`. Connects via the transaction pooler (port 6543). | **T** |
| Realtime | Pushes document-status changes to the browser. | **T** |

### 3.4 AI and external services

| Component | Purpose | Evidence / notes |
|---|---|---|
| OpenAI Responses API + OpenAI vector store (module 1 only) | Managed RAG, used as a first step and then replaced. | **T** |
| Chat Completions API (generic) | One interface for all later providers. | **T** |
| OpenRouter | Cloud models: GLM 4.7, Qwen3 embedding (4096 dims). | **T** |
| LM Studio (local server, RTX 5090, 32 GB) | Local Qwen3-VL 30B mixture-of-experts, Qwen3 32B (emits think tags), small Qwen3 embedding. Context window must be set (70k). | **T** |
| GPT 5.2 | Swapped in to check whether a duplicated-text rendering bug was specific to local models. It was not (a code bug). | **T** |
| Docling | Parsing (standard pipeline used). VLM pipeline is possible. | **T.** Needs PyTorch (about 2 GB) and downloads models on first use. VLM use was **not demonstrated**. |
| Cohere reranker | Cloud rerank. Verified through LangSmith (rerank score, RRF score, similarity). | **T** |
| Local reranker (Qwen3 reranker) | Intended alternative. | **U.** Said "we'll test a local reranker in a minute" but no demonstration follows. |
| Tavily | Web search. | **T.** A self-hosted search engine (likely SearXNG) mentioned as a local alternative (**T~**). |
| LangSmith | Tracing every LLM and tool call. | **T.** Setting it up was the most persistent bug of module 1. |

### 3.5 Developer workflow (part of the lesson)

| Component | Purpose | Evidence / notes |
|---|---|---|
| Claude Code + Cursor IDE | Claude Code builds. Cursor is for reading code, agent chat, and its **debug mode**, which solved the LangSmith tracing bug and an admin-settings bug after Claude Code stalled. | **T** |
| `CLAUDE.md` (lean, global) | Stack, rules of engagement (no frameworks, RLS), plan/build/validate flow, progress tracking. | **T** |
| `PRD.md` | Scope and the eight modules. Deliberately light so details are decided in plan mode. | **T** |
| `progress.md` | Handoff between agents (not started / in progress / completed). | **T** |
| `.claude/commands`: `/onboard`, `/build` | Onboard a fresh agent from the repo. Execute a saved plan. | **T** |
| Plans folder (`agent plans/NN-…md`) | History of plans for onboarding and audit. | **T** |
| `settings.json` permissions | Allow/deny/ask lists, instead of "YOLO mode". | **T** |
| Playwright MCP | Claude drives the browser to test the UI. | **T** |
| Validation (regression) suite | Written during module 2 with acceptance criteria. Later steps can be codified as scripts. | **T** |
| Git: main branch only, tag per module (v0.1, v0.2, …), private GitHub repo | Simplicity and rollback. | **T.** He notes he should commit far more often and use worktrees. |

---

## 4. Implementation order (as actually done)

| # | Step | What happened | Evidence |
|---|---|---|---|
| 0 | Prep | Clone starter repo, open Cursor, run `claude`, set up status line, read `CLAUDE.md`/PRD, run `/onboard`. | **T** |
| 1 | Module 1: shell | Plan mode → save plan → `/clear` → `/build` (14 tasks, about 13 min). Then env keys, migrations, Playwright login test, thread/message tables. | **T** |
| 1b | Module 1 fixes | LangSmith traces missing. Found the build used the older Assistants API, upgraded to the Responses API. Attached an OpenAI vector store via env. Stop button, dynamic titles, loading icon. Multiple Claude sessions in parallel. | **T** |
| 2 | Module 2: BYO retrieval | Ingestion UI, Storage, chunk + embed into pgvector, provider selection, realtime status. Built with parallel sub-agents. | **T** |
| 2b | Module 2 fixes | Tabs layout, config screen, remove legacy columns, realtime delete, **validation suite**, global settings + admin role, secure-credentials plan, variable embedding dimensions, tested OpenRouter and local models. | **T** |
| 3 | Module 3: record manager | Content-hash dedupe. | **T** |
| 4 | Module 4: metadata | Planned in parallel with 3. LLM extraction with a DB-stored schema. | **T** |
| 5 | Module 5: Docling | Planned alongside module 6. Multi-format parsing, followed by slow-ingestion tuning (section 7). | **T** |
| 6 | Module 6: hybrid search | Keyword + vector + RRF, optional Cohere rerank. | **T** |
| 7 | Module 7: tools | Text-to-SQL (rebuilt after a failed design), Tavily web search. | **T** |
| 8 | Module 8: sub-agents | `analyze_document`, nested tool-call UI, `<think>` handling. | **T** |
| 9 | Hardening | Dark mode, tool-call persistence, tool-round limits, prompt changes. Tagged release for modules 7–8 (tag name not stated). | **T** |
| – | Deployment | Not done. Deferred to a later video. | **T** |

---

## 5. Numbered data flows

### A. Module 1 (managed RAG)

1. A user signs in with Supabase Auth.
2. The browser sends the message to FastAPI.
3. The backend calls the OpenAI Responses API with `file_search` on a vector store ID from env.
4. Files in that store were uploaded manually in the OpenAI playground.
5. The answer streams back. The thread and messages are saved in Supabase. **(T)**

### B. Document ingestion (modules 2–6)

1. The user drops a file onto the Documents tab. **T**
2. The backend stores the original in the Supabase Storage bucket under the user's folder and creates a `documents` row with a status. **T**
3. **Record manager:** the content hash is compared with the existing one. Same hash → "document unchanged, skipped." Changed content → delete the old chunks and re-import. New → continue. **T.** Whether the hash is scoped per user is **U**.
4. A background job, throttled by the concurrency limit, takes the file. **T**
5. Docling parses it (PDF, DOCX, PPTX and others; max 50 MB per the plan). **T.** Text/markdown only were accepted before module 5.
6. Text is chunked. **T.** Chunk size and strategy are **U**.
7. An LLM extracts metadata from the first 8,000 characters, shaped by the schema stored in `global_settings`. The metadata is stored on the document and copied to chunks. **T**
8. Each chunk is embedded with the configured embedding provider and written to `chunks` (pgvector) with user id and document id. The vector dimension follows the configured model. **T.** The order of steps 6–8 is **U**.
9. Status changes (pending → processing → completed) are pushed to the browser by Supabase Realtime. **T**

### C. Chat with tools (modules 6–8)

1. The user sends a message from an existing or new thread (full prior history is included, shown by follow-ups like "can this be used outside?"). **T**
2. The backend's LLM service builds the system prompt (tool descriptions, retrieval-strategy instructions) and calls the **configured** chat-completions provider. **T**
3. The model emits tool calls, repeated up to the maximum number of rounds. **T**
4. `search_documents`: keyword search and vector search run, then RRF merges them. If rerank is enabled, Cohere rescores. Optional metadata filters narrow the search. **T**
5. `query_sales_database`: the model writes SQL. It runs under the read-only Postgres role. **T**
6. Web search: the model calls Tavily when documents and SQL do not help. **T**
7. `analyze_document`: the main agent passes a document reference and a question. A sub-agent runs with an isolated message context, loads the entire document, and streams its reasoning and result back. The main agent only receives the result. **T**
8. The backend streams text, think tags and tool-call events (including a tool-complete event) to the browser over SSE. **T**
9. The final messages and the tool-call record (JSONB) are saved to `messages`. **T**
10. Every LLM and tool call is traced in LangSmith. **T**

---

## 6. Architectural decisions and the stated reasoning

| Decision | Reasoning given | Tag |
|---|---|---|
| **Collaborate with the agent** rather than delegate and walk away | The point is to learn while building and keep the solution on a solid foundation. | **T** |
| Python backend, React frontend | Python is the primary AI language: SDKs, eval and parsing libraries are Python-first. | **T** |
| FastAPI | Described as fast for backend ↔ frontend communication. | **T** |
| No agent/RAG frameworks | Raw SDK calls so he understands and controls each step. | **T** |
| Supabase for auth, Postgres/pgvector, storage, realtime | One service covers everything. RLS isolates users. | **T** |
| Start with managed RAG, then replace it | It's a **black box** (no view of chunking, embedding, or retrieval choices), costs money ($0.10/GB and $2.50 per 1,000 tool calls, as stated), ties you to one provider and its models, and streams slowly. | **T** |
| Chat Completions API for modules 2+ | Works with any OpenAI-compatible provider, so local and cloud models can be swapped. | **T** |
| Embedding provider configured separately from the chat model | Asked and answered "Definitely." | **T** |
| Global (not per-user) model and embedding settings, with an admin flag | Different users with different embedding dimensions would conflict. | **T** |
| Block changing the embedding model once chunks exist | Different dimensions would break search. | **T** |
| Delete-and-reimport on a changed file, not partial re-embedding | He found it avoids orphan chunks. He edited the plan to say so. | **T** |
| Hash-based record manager | Duplicate chunks add noise to retrieval. | **T** |
| Metadata schema in a DB JSON field, not hardcoded | Configurable without code changes. Not over-engineered. | **T** |
| Extract metadata from only the first 8,000 characters | Avoid burning budget on huge documents. | **T** |
| No backfill of old documents for metadata | Not needed now. | **T** |
| Use the same LLM provider for metadata extraction as for chat | Simplicity. | **T** |
| Metadata filters: be cautious | Over-filtering returns **zero** results. Demonstrated when the model picked `document type = article` and the data said `reference`. Later he told the agent not to use filters. | **T** |
| Docling only (not Mistral OCR or Unstructured) | Flexible: standard and VLM pipelines, local and free. Cloud parsers are options. | **T** |
| Hybrid search with RRF; Cohere optional, plus a local option | Beyond semantic-only search. | **T** |
| Text-to-SQL: raw SQL + **database-level** read-only role on a single table | Security must be enforced by the database. Parameterized query templates are a valid alternative. Python-side validation alone is not safe. | **T** |
| Rejected the agent's RPC-function design for SQL | Over-engineered and did not give real security. | **T** |
| Use the transaction pooler (port 6543) for the SQL reader | The connection failed on 5432. | **T** |
| Sub-agent for whole-document analysis | RAG gives snippets and loses full context. Loading whole documents into the main agent would flood its context. Sub-agents mirror Claude Code's Explore agent. | **T** |
| Persist tool calls in JSONB on messages | Old conversations lost their tool-call history after refresh. | **T** |
| Tool-round cap configurable (10) + dynamic prompt | The model sometimes ends on a tool call with no answer. | **T** for the decision. Final verified behavior is **U** (he asked for it and re-tested other things). |
| LangSmith from module 1 | Need to see prompts, tool calls and context. "You will end up living in LangSmith." | **T** |
| Plan mode → save plan → `/clear` → `/build` → validate → commit | Keeps context clean and gives a record. | **T** |
| Start a new session when context passes about 50% | Quality drops. | **T** |
| Plan and build independent modules in parallel | Faster. Later worktrees recommended to prevent agents colliding. | **T** |
| Automate repeated chatter (start script, `/onboard`) | Look for duplicated effort and script it. | **T** |
| Regression suite early | Cost explodes as features grow. | **T** |
| Settings.json permissions, not YOLO | Keep track of commands. | **T** |
| Main branch only, tags per module | Simplicity for beginners. Feature branches are better practice. | **T** |

---

## 7. Assumptions, shortcuts and limitations

**Stated by the developer (T):**

- **Alpha quality.** Smoke-tested end to end, partially validated by Claude, not fully tested. He would not deploy it.
- **Not deployed.** Production architecture was only described. CI/CD, staging, rollback and migrations in production are deferred.
- **`sales_data` has RLS off**, so any client can read it. He wants a policy letting logged-in users read it.
- **API keys in the settings table were stored in plain text.** A plan to fix it was produced. Whether and how it was implemented is **U**.
- Test credentials were saved in `CLAUDE.md` for agents (he judged this OK for a test account). **R:** never do this for real credentials.
- Many modules were validated mostly by the agent plus quick manual smoke tests.
- Ingestion is **slow**. 16 files processed roughly one at a time. Memory reached 92% on a laptop running Docling. After four optimizations (e.g. file loaded twice, no concurrency cap) and raising concurrency from 3 to 10, it was slightly faster but "nowhere near" enough. The bottleneck (Docling or LLM calls) was never identified.
- The vector column's fixed dimension was removed. A possibly dropped index is unresolved.
- Metadata filters can silently return nothing. The mitigation was a prompt edit.
- A 30B mixture-of-experts local model sometimes looped or ended on a tool call. A different local model or GPT 5.2 behaved better. The developer said the local model might be "at the edge".
- The local model's context window silently reset to 4,000 tokens after a server restart and degraded results.
- Claude Code repeatedly over-engineered (the SQL RPC function), skipped steps, never learned the remote-Supabase workflow, and stalled on bugs that Cursor's debug mode solved.
- Duplicate server processes made restarts unreliable. Fixed with a kill-all restart script.
- Hit Claude usage limits twice. Commits were too infrequent, and he says rollback would have been easier otherwise.
- Sub-agent UI has remaining bugs (thought bubble placement, duplicate text, lost thinking on reload).
- Long-term memory is mentioned in the PRD framing ("retrieval and memory"). Only message history is shown.

**Unknown (U):**

- Chunking strategy and sizes. Embedding model defaults.
- RLS policy definitions. Auth-token handling between frontend and backend.
- Hybrid-search internals: FTS configuration, RRF constant, candidate counts, how the keyword query is built.
- Whether a different LLM is actually used for the sub-agent (the intro says this is possible; the demo uses the configured model).
- Docling VLM pipeline results. Local reranker results.
- The final state of secret storage. Retrieval quality on the manuals (only small spot checks).
- System prompt text. LangSmith root cause (fixed by Cursor, cause not narrated).
- Whether answers carry **citations**. The video shows tool calls and answers; citation UI or validation is not described.

---

## 8. What applies directly to PaperPilot

| PaperPilot need | What this transcript supports | Applicability |
|---|---|---|
| **Process academic papers** | Upload UI, storage per user, Docling for PDF/DOCX, status tracking with Realtime, concurrency cap. | **Direct**, but the Docling PDF run was a small spot check, not a benchmark. Use your own papers to test table, equation and figure fidelity. **R** |
| **Avoid duplicate papers** | Content-hash record manager, delete-and-reimport on change. | **Direct.** **R:** also key by DOI/arXiv id, since the same paper appears as different files. |
| **Extract structured findings** | LLM + Pydantic schema, schema stored in the DB, propagated to chunks. | **Adapt.** This extracts *document metadata* from the first 8,000 characters. Findings (results, methods, datasets) need full-text or section-aware extraction, and a text limit would cut them off. **R** |
| **Hybrid retrieval** | Keyword + vector + RRF + optional rerank, verified in LangSmith. | **Direct.** |
| **Metadata filtering** | Works but fails to zero results when the model guesses filter values. | **Direct, with the warning.** Offer filter values to the agent, or use soft ranking boosts instead of hard filters. **R** |
| **Compare papers** | Not built. The `analyze_document` sub-agent (isolated context, one document per worker) is the closest pattern. | **Adapt.** **R:** one sub-agent per paper returning a fixed schema, then the main agent compares those results. |
| **Compare structured results** | Text-to-SQL with a read-only DB role on one table. | **Direct pattern.** **R:** run it over a `findings` table you control. Keep DB-enforced permissions. |
| **Evidence-backed QA** | Tool traces and LangSmith show what was retrieved. No citation contract, verification step or page-level source display is described. | **Gap here.** Use the companion transcript's citation + validator design. |
| **Evaluate reproducibility** | Not covered. | **Gap (U).** |
| **Observability** | LangSmith from day one. | **Direct.** |
| **Multi-user isolation** | Supabase Auth + RLS + per-user storage folders. | **Direct.** Remember the `sales_data` mistake (a table with RLS off). |
| **Model flexibility** | Provider abstraction (OpenAI-compatible), separate embedding config, local models. | **Optional.** Useful for cost control or private papers. |
| **Learning workflow** | Plan → save plan → clear → build → validate → commit, a `progress.md` handoff, `/onboard`, and an early regression suite. | **Direct, process-level.** |

**My recommendations (R), not from the transcript:**

1. Verify pgvector index limits before choosing an embedding model. As I understand it (outside this transcript, check the docs), standard `vector` HNSW/IVFFlat indexes cap at 2,000 dimensions, so a 4,096-dimension model such as the Qwen3 embedding used here needs `halfvec` or a smaller dimension.
2. Fix the embedding model and dimension per deployment and re-embed when it changes. The transcript only blocks the change once chunks exist.
3. Build the evaluation set early (questions with known answers and known source pages). Neither transcript shows one.
4. Model "finding" and "reproducibility item" records with evidence pointers (paper id, page, quoted span, confidence), so the QA citation layer and the extraction layer share one evidence model.
5. Enable RLS on every table, including demo tables, and encrypt or avoid storing API keys in app tables.
6. Cap and log agent tool rounds. Persist tool calls with messages from the start.
7. Use git worktrees if running multiple agents in parallel, and commit at every working step.
