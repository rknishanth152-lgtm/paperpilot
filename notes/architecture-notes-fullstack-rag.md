# Architecture Notes: "Full-Stack GenAI App" (Driftwood Capital Document Copilot)

**Source:** `transcripts/fullstack-rag.txt` (about 41,000 words, roughly a 4-hour build video)
**Companion notes:** `architecture-notes-claude-code-rag.md` (the other transcript)
**Purpose:** learning input for PaperPilot

---

## 0. How to read these notes

| Tag | Meaning |
|---|---|
| **T** | Explicitly said or demonstrated in the transcript. |
| **T~** | Said in the transcript, but the auto-caption is garbled and I am interpreting it. The garbled form is quoted. |
| **R** | My recommendation or inference. Not in the transcript. |
| **U** | Unknown. The transcript does not give enough evidence. I did not guess. |

Caveats about the evidence:

- This is a speech-only auto-caption. Code, diagrams and screens are not visible. A file name, table, or setting is only known if the speaker said it.
- Caption errors I resolved from context: "Superbase" = Supabase, "PG factor" = pgvector, "Olympic/Alembic" = Alembic, "fight" = Vite, "pmppm" = pnpm, "Pidentic" = Pydantic AI, "PCEL" = presumably Vercel (AI SDK), "Dockling" = Docling, "cipher" = Cypher. Model names (GPT 5.5, Composer 2.5, Opus 4.8) are as spoken.
- The architecture diagram the developer keeps referring to (`architecture.md`) is never shown in the transcript. Only his narration of it is.

---

## 1. What was built

A fictional-client case study. **Driftwood Capital** is an independent equity-research firm. Its analysts spend about half their week on "source document intake": reading SEC filings and copying out sections. The product is an internal **"Document Copilot"** chatbot. **(T)**

- **Corpus:** SEC filings for 5 companies (Apple, Microsoft, Nvidia, Amazon, Google) over the last 5 years. That is 25 documents, downloaded as `.htm` files. **(T)**
- **Core requirement:** every answer must be sourced and cite a specific file and page. A hallucinated figure is a costly error for this client. **(T)**
- **Other requirements:** browser app, login with company email, and a history of each user's past conversations. **(T)**
- **Out of scope:** trading recommendations, external data, multi-tenancy, billing, mobile. **(T)**
- **Definition of done:** a pilot group of analysts uses it in a browser and saves at least 3 hours per week. **(T)** The developer says he will not test the time savings. **(T)**

---

## 2. Architecture at a glance (reconstructed from narration)

```
                          OFFLINE (run locally, one-time)
 SEC download.py ─► data/downloads/*.htm + manifest.json
        │
        ├─► convert script (Docling) ─► data/markdown/*.md ─► load script ─► source_documents
        │
        └─► (later) custom HTML table extractor ─► document_tables
                                        │
        Docling HybridChunker ─► OpenAI embeddings ─► document_chunks (pgvector + text-search column)

                          ONLINE (deployed on Railway)
 Browser ──► React SPA (Vite build, served via Caddy in Docker)
    │  sign-in                                   │ chat requests
    ▼                                            ▼
 Supabase Auth  ◄── token check ──────────  FastAPI backend (Docker, uvicorn)
                                                 │
                                   Pydantic AI agent (GPT 5.5)
                                   tools: search filings (hybrid), read chunks,
                                          read surrounding chunks
                                                 │
                              retrieval: embed query + Postgres full-text
                              ─► Reciprocal Rank Fusion ─► top K + neighbour chunks
                                                 │
                                   grounded structured answer ─► validator
                                                 │
                                   Supabase Postgres (users, threads, messages,
                                   message_citations, chunks, documents)
```

The online boxes follow his description of the diagram. The exact wiring between frontend and Supabase tables is **U** (see section 8).

---

## 3. Component-by-component table

### 3.1 Frontend

| Component | Purpose | Evidence / notes |
|---|---|---|
| React SPA, TypeScript, Vite | The browser app. Created from the Vite `react-ts` template with pnpm, rather than letting the AI generate the scaffold. | **T.** Reason given: lots of config to get right, so use a template. |
| Tailwind CSS + shadcn/ui | Styling and ready-made components. | **T.** |
| `@supabase/supabase-js` + anon (publishable) key | Sign-in/sign-up from the browser. | **T.** The key is safe in the browser only if row-level security (RLS) is on and policies are set. |
| Login / signup screens, protected routes | Gate the app. | **T.** Phase 2. |
| Chat UI with prompt-kit components, "AI SDK from PCEL" | ChatGPT-like chat experience. | **T~** (library names). Whether the answer text itself streams token by token is **U**. |
| Conversation sidebar, new chat, delete conversation, sign-out, user menu | Per-user history. | **T.** |
| Status indicator (analyzing → searching → reading → verifying) | Shows progress during the roughly 60 s agent loop. | **T.** Later restyled as a grey gradient-wipe text. How the backend sends these events (SSE, polling) is **U**. |
| Inline citations + slide-over "sources" sheet | Click a citation to see the retrieved chunk, plus neighbouring chunks, as a rendered markdown table. | **T.** Initial bug: clicking opened a new browser tab. |
| Markdown table renderer | Show financial tables in answers and sources. | **T.** |
| Logo, favicon, monochrome theme | Polish. | **T.** Not architecture. |

### 3.2 Backend

| Component | Purpose | Evidence / notes |
|---|---|---|
| FastAPI + uvicorn | API layer. Has a `/health`-style status endpoint. | **T.** Port 8000 locally. |
| `app/config.py` with pydantic-settings | Loads env vars and fails fast on a missing required one. | **T.** He demonstrated the validation error when `DATABASE_URL` was missing. |
| `app/database/` with SQLAlchemy models, one file per model | Defines tables in Python. | **T.** |
| Alembic migrations (folder sits outside `app/`) | Version-controlled schema changes. The first migration created all tables. | **T.** |
| `supabase.py` client (uses anon key) | Backend connection to Supabase. | **T.** Where the service-role key is used is **U**. |
| `app/auth/dependencies.py` | FastAPI dependencies that check whether the caller is authenticated. | **T.** The exact token mechanism is **U**. |
| Chat endpoints (`chat`, `auth` routers) | Create a thread, store messages. | **T.** Phase 3 began as a stub with no logic. |
| `ingest/` scripts (outside the deployed app) | Load markdown into the DB, chunk, embed, insert. | **T.** Deliberately kept out of the deployment path. |
| `retrieval/` module (small modules: models, query embedding, SQL queries, retriever) | Hybrid search with RRF and neighbour hydration. | **T.** Has a README with a mermaid diagram. |
| Pydantic AI agent (`agent.py`) with tools | Tool loop: search filings, read chunks, read surrounding chunks. Returns a structured grounded answer. | **T.** Scope was much larger than the developer intended (section 7). |
| Grounding validator | Hard pass/fail check on the answer's citations. | **T.** |
| Keyword-extraction step (LLM call) | Pull 3–5 keywords from the user's question for full-text search. | **T.** Run in parallel with query embedding. A filler-word list (NLTK considered) was left as a later optimization. |
| `smoke_assistant.py` script | Run one question end to end from the command line. | **T.** Simplified to a dict of questions plus one function. Needed `nest_asyncio` in the interactive session. |

### 3.3 Database (Supabase Postgres)

| Component | Purpose | Evidence / notes |
|---|---|---|
| Supabase project (hosted, EU region chosen) | Postgres, auth, and RLS in one service. | **T.** "Automatic RLS" enabled at creation. |
| Supabase Auth, email/password | User login. | **T.** Public sign-up **disabled**. Users are created by hand in the dashboard with "auto confirm". Callback URLs configured. |
| `users` | App-level user rows (renamed from `profiles`). Email, optional display name. | **T.** A Supabase Auth user is **not** automatically a row in this table, and he flagged this gap. |
| `source_documents` | One row per filing: ticker, company name, form, filing date, source URL, and the full markdown text. | **T.** 25 rows after loading. |
| `document_chunks` | Chunk text, document id, chunk index, page number, section, token count, embedding vector (pgvector), and a text-search column. | **T.** Search column heard as "search factor", most likely a search vector (**T~**). |
| `chat_threads` / `chat_messages` | Conversation history. | **T.** |
| `message_citations` | Links an assistant message to the chunks it relied on, with denormalized filing metadata for the UI. | **T.** Kept after pushback because it enforces grounding better than embedding citations in the message. Caused a NOT NULL constraint error that was fixed. |
| `document_tables` (added later) | Per-table rows: document id, table index, table as markdown, table as JSON. | **T.** Added by the custom table extractor. |
| pgvector extension | Vector column and semantic search. | **T.** Index type, distance metric and dimensions are **U** (embedding model implies 1536 dims, **R**). |
| Postgres full-text search | Keyword half of hybrid search. Used instead of BM25. | **T.** Ranking function and language config are **U**. |
| Session-pooler connection string | `DATABASE_URL` for SQLAlchemy/Alembic. | **T.** Password special characters broke env parsing until quoted. psycopg v3 required rewriting the URL scheme in a helper. |

### 3.4 AI / retrieval

| Component | Purpose | Evidence / notes |
|---|---|---|
| OpenAI `text-embedding-3-small` | Chunk and query embeddings. | **T.** "text embedding three small is correct." |
| GPT 5.5 | The agent's LLM. | **T.** Quote: "I actually want GPT 5.5 in there." |
| Pydantic AI | Agent framework: model calls, tool calling, structured outputs. | **T.** |
| Docling (document converter) | HTM → markdown with table detection. Run locally, open source. | **T.** Table output was messy (duplicate columns, empty cells). |
| Docling HybridChunker (hierarchical, tokenizer-aware) | Header-aware chunks sized to the embedding model's limit. | **T.** Chosen over naive fixed-size splitting. |
| Custom SEC HTML table extractor | Replaces Docling's table output with parsed tables. | **T.** Required re-running chunking. Built by GPT 5.5 "extra high" from a research prompt. Implementation details **U**. |
| Hybrid retrieval: vector + full-text + Reciprocal Rank Fusion (RRF), k = 60 | Retrieval. Fetch many candidates, fuse, keep top K (5 in the demo). | **T~** ("Retrieval top K RF 60"). |
| Neighbour-chunk expansion (radius 1) | Gives a retrieved chunk its surrounding context. | **T.** |
| Reranker | Cohere cross-encoder was in the reference repo. Explicitly **not** added, to keep it simple and avoid another API key. | **T.** |
| Query classification / routing | Suggested as a future step. Not built. | **T.** |

### 3.5 Infrastructure and developer workflow

| Component | Purpose | Evidence / notes |
|---|---|---|
| Monorepo (backend + frontend + data) | Coding agents can reason across both halves. | **T.** |
| `agents.md` (root, backend, frontend) | Standing instructions injected into every agent session. | **T.** |
| `to-dos.md` | AI-generated phased checklist the developer works through. | **T.** |
| uv (Python) + pnpm (Node) | Dependency management. | **T.** |
| Dependency guardrails | Exact version pins; `exclude-newer` 7 days (uv); pnpm minimum release age 7 days. Reason: supply-chain attacks. | **T.** |
| `.env` / `.env.example` per side, gitignored | Config and secrets. | **T.** |
| Docker (backend, frontend) + Caddy (frontend) | Deployable images. AI-generated; the developer did not walk through them. | **T.** |
| Railway: two services from one GitHub repo | Hosting. Public `*.up.railway.app` domains. | **T.** Chosen as easiest for a tutorial. |
| Railway MCP server in Cursor | Lets the agent create and configure Railway projects. | **T.** First attempt failed. Fixed the next day. |
| Railway CLI (`railway up`) | Manual redeploy per service. No CI/CD. | **T.** |
| Cursor + several models | Composer 2.5 fast (routine work), GPT 5.5 (hard debugging, extraction research), Opus 4.8 + Anthropic frontend-design skill (UI). | **T.** |

---

## 4. Implementation order (as the developer actually did it)

| # | Phase | What happened | Evidence |
|---|---|---|---|
| 0 | Setup | Read client brief. Ran `download.py` (SEC data + `manifest.json`). Created Supabase project. Filled env files. Made OpenAI key. | **T** |
| 1 | Backend foundation | `uv sync` and add deps. `config.py`. `main.py` with health check. SQLAlchemy models. Alembic migration to Supabase. `supabase.py`. | **T** |
| 2 | Auth, full stack | Backend auth dependencies. Vite + Tailwind + shadcn + supabase-js scaffold. Disabled sign-up, set redirect URLs, manually created a user, verified login against backend. | **T** |
| 3 | Chat vertical slice | Backend and frontend stubs planned in parallel, then built. Login, chat list, basic chat skeleton. | **T** |
| 4 | Ingestion | HTM → markdown (Docling). Load 25 docs. Chunk (HybridChunker) → embed → insert. Tested on one chunk first. | **T** |
| 5 | Retrieval | Hybrid search modelled on his earlier cookbook repo, adapted from BM25 to Postgres full-text. | **T** |
| 6 | Agent + grounding | Pydantic AI agent, tools, structured output, validator, keyword extraction. | **T** |
| 7 | Frontend wiring | Connect chat to agent, status updates, source panel, redesign. Debugging with a stronger model. | **T** |
| 8 | Pilot readiness | Delegated to an agent as a review. Not verified by the developer. | **T** |
| 9 | Table-extraction rework | Custom HTML table extractor, re-chunk, re-embed. | **T** |
| 10 | Deployment | Dockerfiles, Caddy, Railway. First attempt failed. Fixed next day. Docling moved to dev dependencies. | **T** |

Process rules he followed: small incremental prompts, new chat per phase, a plan step before big phases, a commit checkpoint before large changes.

---

## 5. Numbered data flows

### A. Offline ingestion (run locally, not part of the deployed app)

1. `download.py` pulls the last 5 years of filings for 5 tickers from the SEC API into `data/downloads/<ticker>/<year>/…htm`, plus `manifest.json` (ticker, filing date, local path). **T**
2. A convert script reads the manifest and runs Docling's `DocumentConverter` on each `.htm`, writing markdown into a mirrored folder structure. **T**
3. A load script inserts one `source_documents` row per file, with metadata and the whole markdown text, skipping existing rows. **T** (25 rows)
4. For chunking, he agreed to rebuild the Docling document from the original HTML, not the markdown, so page numbers are preserved. **T**
5. The HybridChunker produces chunks sized to the embedding model's token limit. **T**
6. OpenAI embeddings are generated and inserted into `document_chunks` with page number, section, token count and a text-search value. A one-chunk dry run came first because embedding is costly. **T**
7. Later fix: the table extractor parses tables from the original HTML into `document_tables` (markdown + JSON), and chunks were rebuilt. **T**
8. Re-running the load appears to have created duplicate chunks (he suspects they were uploaded three times). No dedupe exists. **T~**

### B. Runtime question answering

1. The analyst opens the Railway-hosted SPA and signs in through Supabase Auth with email and password. **T**
2. The browser sends the chat message to the FastAPI backend (API base URL from env). **T**
3. The backend verifies the user via its auth dependency and loads or creates the thread. **T.** The token format and header are **U**.
4. The Pydantic AI agent starts, guided by a "product contract" system prompt (corpus description, tool usage rules, citation rules). **T**
5. The agent calls the search tool. In parallel, the question is embedded and an LLM extracts 3–5 keywords for full-text search. **T**
6. Vector search (pgvector) and full-text search run against `document_chunks`, with optional filters such as ticker and form. **T**
7. The two ranked lists are fused with RRF (k = 60). The top hits are hydrated with document metadata and ±1 neighbour chunk. **T**
8. The agent judges whether the excerpts suffice. If not, it calls read-chunks or read-surrounding-chunks and loops. The maximum number of rounds is **U**. **T** for the loop behavior.
9. The agent must return a structured, grounded answer (Pydantic model) with citations. **T**
10. The validator checks that every citation points to a chunk that was actually retrieved and that quoted excerpts come from that chunk. It returns a hard pass/fail. On fail, the user is told no grounded answer was found. **T.** How the validator re-checks (against the chunks in the database vs. the retrieved set) is hedged by the speaker ("I believe"). **U**
11. The assistant message and its `message_citations` rows are saved. **T**
12. The UI shows progress states while waiting, then the markdown answer with inline citations. Clicking a citation opens the side sheet with the chunk and its neighbours. **T**

### C. Configuration and deployment flow

1. Secrets live in gitignored `.env` files locally and in Railway service variables in production. **T**
2. The frontend's API base URL changes from localhost to the Railway backend URL. **T**
3. Each service is built from its Dockerfile (Railway auto-detects it) and started with its command (`uvicorn app.main:app` on the backend). **T**
4. Redeploys are manual: `railway up` for the backend folder and again for the frontend. **T**

---

## 6. Architectural decisions and the stated reasoning

| Decision | Reasoning given | Tag |
|---|---|---|
| Monorepo with `agents.md` files | Coding agents can reason over backend and frontend together. | **T** |
| Python/FastAPI backend, React/TS/Vite frontend | Presented as his 3-year default. The only detail given is that he is a backend engineer. | **T** |
| Supabase | Easy auth, plus Postgres with pgvector in the same service. | **T** |
| Vector store inside Postgres, not a separate vector DB | Described as "a simple Postgres as part of Supabase". No comparison is made. | **T** |
| Postgres full-text instead of BM25 | Postgres has no native BM25. Full-text is similar enough. | **T** |
| Hybrid search + RRF | Reused his earlier cookbook pattern. | **T** |
| No reranker | Keep it simple, avoid another API key. | **T** |
| Agent tool loop instead of "retrieve once and answer" | A naive pipeline cannot course-correct when evidence is thin. The loop can fetch more context. | **T** |
| Separate validator after the agent | The client brief makes trust the product. A final hard check on citations. | **T** |
| Neighbour chunks | Give retrieved text surrounding context. | **T** |
| LLM keyword extraction before full-text search | A full question rarely matches text verbatim. | **T** |
| SQLAlchemy models + Alembic | Avoid hand-written SQL. Track schema change over time. | **T** |
| One model per file | Easier to navigate. | **T** |
| Keep `message_citations` | Enforces grounding better than putting citations inside messages. | **T** |
| Rename `profiles` to `users` | Matches his mental model. | **T** |
| Ingestion scripts outside the app and outside migrations | One-time local batch. Not needed in deployment. | **T** |
| Docling for parsing | Detects tables and formulas, free, runs locally. Paid cloud tools exist. | **T** |
| Docling converts, then custom extractor for tables | Docling tables were fragile, and filings are structured HTML, so parse the HTML directly. | **T** |
| Disable open sign-up, add users by hand | Internal tool. Otherwise anyone who finds the URL can register. | **T** |
| Same region for DB and backend | Avoid cross-ocean latency. | **T** |
| 7-day minimum package age, exact pins | Supply-chain attack protection. | **T** |
| Docling kept in dev dependencies | It is heavy and can fail on small-RAM hosts. | **T** |
| Railway | Easiest way to show a production-like deploy. Real client work uses AWS, Azure or Hetzner with secret vaults. | **T** |
| Scope GitHub access to one repo | Platform compromise would otherwise expose all repos. | **T** |
| Strong model for hard debugging, fast model for scaffolding | Reset context and escalate model when a chat is "broken". | **T** |
| Prompt style for UI work: research, gap analysis, design-system reuse, Anthropic model, frontend-design skill | Front-end is outside his expertise. | **T** |

---

## 7. Assumptions, shortcuts and limitations

**Stated by the developer (T):**

- Ingestion is a **local, one-time script**. No upload UI, no sync, no scheduler.
- Secrets were shown on screen. He says he will delete the database and keys afterward. The Railway MCP was given credentials and he calls this "yolo" and not how he does client work.
- No automated tests are shown. Phase 8 "pilot readiness" was delegated to an agent and he says he will not test the time savings.
- Chunk quality is weak for tables. Embedded table text has little context, so he expects poor semantic search there. A per-chunk summary was proposed, not built.
- Docling's table output had duplicate columns. A reviewer agent flagged it. He accepted this at first, then fixed it with the custom extractor.
- The agent built **more than he asked for** in the grounding phase (tools, loop, validator). He has not validated the tools, the prompts, or the validator.
- Every question, even "hi", runs the full pipeline. He says users will complain, and proposes a query-classification step or answering simple questions directly.
- **Cost and speed:** about 60 seconds or more per answer. Roughly $1–2 per query with GPT 5.5. He suggests a cheaper model while experimenting.
- Probably **duplicate chunks** in the database. He should have wiped and re-ingested.
- FastAPI's `/docs` page is public on the deployed backend unless restricted.
- Login is plain email/password: no SSO, no 2FA.
- Railway's default memory (1 GB) is low. His client default is 2 vCPU and 4 GB.
- The Railway region appeared to be US ("it was now in the US") while Supabase was in the EU, which contradicts his own latency advice (**T~**).
- No CI/CD pipeline. The first deploy failed and was fixed off-camera ("the next day").
- Retrieval parameters (K, RRF 60, radius 1) are defaults with no tuning. "Perfect numbers don't exist" for any dataset.
- He worked in small incremental prompts, yet admits he has not written or optimized a single word of the agent's prompt.

**Unknown (U), not shown in the transcript:**

- RLS policies on each table and whether the frontend reads tables directly or only via the API.
- How the backend validates a user token, and which Supabase key is used where.
- Whether the runtime DB access uses the supabase client, SQLAlchemy, or raw SQL (the retrieval uses SQL and the supabase.py client is described as "what we run everything through").
- Vector index type, distance metric, dimension count.
- Max tool rounds and timeout behavior.
- Whether the answer text streams.
- Exact system prompt, validator logic, and chunk size.
- Number of chunks. Number of tables extracted.
- Form types in the 25 filings (the count matches one filing per company per year; the form is not named).
- Any evaluation set or accuracy measurement.

---

## 8. What applies directly to PaperPilot

| PaperPilot need | What this transcript supports | Applicability |
|---|---|---|
| **Process academic papers** | Docling conversion, header-aware chunking, page and section stored per chunk. | **Adapt.** Shown only on SEC HTML, not PDFs. Papers have equations, figures and multi-column layout, so expect different failure modes. **R** |
| **Evidence-backed QA** | The strongest part: citation contract, `message_citations`, retrieved-chunk validator, source side-sheet with neighbours, "can't answer" fallback. | **Direct.** |
| **Hybrid retrieval** | pgvector + Postgres full-text + RRF, LLM keyword extraction, neighbour expansion. | **Direct.** |
| **Agent loop** | Pydantic AI with search/read tools and structured output. | **Direct**, with the cost and latency warnings above. |
| **Auth and storage** | Supabase Auth + Postgres + pgvector, SQLAlchemy + Alembic, pydantic-settings. | **Direct** if PaperPilot picks the same stack. **R** |
| **Compare papers** | Ticker/form filters and neighbour reading hint at cross-document queries ("revenue mix 2021 to 2025"). | **Partial.** No comparison feature is built or shown. The mechanism would be an agent running filtered searches per paper. **R** |
| **Extract structured findings** | Not covered. No schema extraction exists in this build. Tables were extracted, but not findings. | **Gap.** See the companion notes for a metadata-extraction pattern. |
| **Evaluate reproducibility** | Not covered at all. | **Gap (U).** |
| **Evaluation of answer quality** | None shown. The developer says to pick a dataset you can fact-check yourself. | **Gap.** Take his advice. |

**My recommendations (R), not from the transcript:**

1. Treat the citation contract (persisted citations, validator, refusal path) as PaperPilot's core, and build it before extra features.
2. Plan for table and figure fidelity from day one. The transcript shows tables caused the biggest quality problem, and papers are table-heavy.
3. Add a `papers` table with DOI/arXiv id and a content hash so re-ingestion does not duplicate chunks (this build had no dedupe).
4. Add a findings table (claim, metric, value, dataset, evidence chunk ids and page, extraction confidence) and a reproducibility checklist table (code link, data link, seeds, hardware, hyperparameters, each with evidence). Neither pattern is in this video.
5. Add a lightweight query router so trivial questions skip the agent loop, and cap tool rounds.
6. Build a small hand-verified question set early so answer accuracy is measured, not eyeballed.
7. Copy the dependency guardrails (exact pins, minimum package age) and keep heavy parsers out of the deployed image's runtime dependencies.
8. Do not copy: public `/docs`, manual user creation as the only onboarding, secrets shown on screen, and a Railway region different from the database's.
