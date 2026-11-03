# FastAPI architecture checklist (PaperPilot)

Source of truth: `PRD.md` §4 and `CLAUDE.md` §4–§5. Use this list when planning a backend change and when auditing one. Report each violation with file, line, the rule, and a suggested fix.

## Layout

`backend/app/{api, models, schemas, services/{discovery, ingestion, extraction, retrieval, comparison, reproducibility}, database}`

| Folder | Holds | Must not hold |
|---|---|---|
| `api/` | Routes: parse request, call a service, map result/errors to HTTP | SQL, business rules, Pydantic model definitions |
| `schemas/` | Pydantic models for API input/output and LLM output | ORM models |
| `models/` | SQLAlchemy 2.x ORM models (`Mapped`, `mapped_column`) (`AD-012`) | Business logic |
| `database/` | Engine, session, migrations wiring | Feature logic |
| `services/<capability>/` | Logic; pure functions for parsing, normalisation, validation | HTTP concerns; another capability's tables |

## Checks

- [ ] Routes do HTTP only; logic lives in services.
- [ ] Cross-capability access goes through service functions, not another module's tables (`NFR-MNT-001`).
- [ ] Pydantic validates every external boundary and all model output; unknown or missing fields are rejected.
- [ ] Errors map to structured codes; no stack traces, paths, prompts or configuration in responses (`NFR-SEC-005`).
- [ ] No broad `except` that hides failures; failures set explicit statuses.
- [ ] Configuration is read in one module; every setting is in `.env.example`; nothing hard-coded.
- [ ] External calls (GROBID, LLM, OpenAlex) have configured timeouts (`NFR-REL-003`).
- [ ] Every schema change has an Alembic migration and tests (constraints, repeat ingestion, rollback) (`NFR-MNT-002`).
- [ ] Generated text never goes into `passages`; derived records link to passages and record model/parser/prompt version.
- [ ] Logs are structured and contain no full paper text, prompts with paper text, or credentials (`NFR-PRI-002`).
- [ ] Uploads validated by PDF signature and size; storage keys generated, client filenames never used as paths (`NFR-SEC-002`).
- [ ] Ingestion runs in-process with status polling; no queue/worker (`AD-010`). No auth layer (`AD-009`).
- [ ] Type hints on public functions.
