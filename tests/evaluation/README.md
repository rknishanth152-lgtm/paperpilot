# Evaluation tests

The evaluation harness lives here (Phase 4 onwards: `FR-EVL-*`). Tests in this folder are marked `evaluation` automatically and are excluded from the default `uv run pytest` run. Run them with:

```bash
uv run pytest -m evaluation
```

Retrieval evaluation (P4-T6, `FR-EVL-002`): `run_retrieval.py` reads `benchmarks/retrieval_eval_v1.json`, refuses a set that has not been reviewed, runs retrieval without any LLM, and saves a new dated file in `benchmarks/results/`. From the repository folder, with PostgreSQL running and the corpus ingested:

```bash
uv run python -m tests.evaluation.run_retrieval
```

Evaluation results are produced only by saved harness runs, never edited by hand (`CLAUDE.md` §6).
