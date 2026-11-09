# Evaluation tests

The evaluation harness lives here (Phase 4 onwards: `FR-EVL-*`). Tests in this folder are marked `evaluation` automatically and are excluded from the default `uv run pytest` run. Run them with:

```bash
uv run pytest -m evaluation
```

Retrieval evaluation (P4-T6, `FR-EVL-002`): `run_retrieval.py` reads `benchmarks/retrieval_eval_v1.json`, refuses a set that has not been reviewed, runs retrieval without any LLM, and saves a new dated file in `benchmarks/results/`. From the repository folder, with PostgreSQL running and the corpus ingested:

```bash
uv run python -m tests.evaluation.run_retrieval
```

Whole evaluation (P6-T1, `FR-EVL-002`, `FR-EVL-003`): one command runs retrieval, then answers, on the same code, and saves one new dated file for each. The answer step is a **manual real-model run** that sends the questions and retrieved passages to the provider set in `.env`. Use open-access papers only on a free tier. `--pause` is seconds between questions; `--answer-limit N` runs only the first N answers.

```bash
uv run python -m tests.evaluation.run_evaluation --pause 30
```

Each file records the commit, whether the working tree differed from it (saved results do not count), configuration, model and prompt version. The command exits with 1 if the provider stops the run early.

Citation reference validity (P6-T2, `FR-EVL-003`): new answer runs include it in their summary. To compute it from an already saved answer result, without calling a model:

```bash
uv run python -m tests.evaluation.citation_validity benchmarks/results/answers-X.json
```

It reports valid ÷ total citations with a count per failure reason, and validated ÷ total for answers that contain statements. Answers with no statements pass validation automatically, so they are listed separately instead of raising the rate. Uncited statements and model errors are also listed separately. This is structural correctness only and says nothing about whether a passage supports a statement.

Claim support (P6-T3, `FR-EVL-004`): `claim_support.py` has `draw` (fix the sample once), `sheet` (write the labelling page again) and `report` (check the labels, then save the rate). The guide is `benchmarks/claim_support_guide_v1.md`. The page holds passage text, so it stays in the git-ignored `data/` folder. To open it, serve that folder on this machine only:

```bash
uv run python -m http.server 8765 --bind 127.0.0.1 --directory data/labelling
```

Evaluation results are produced only by saved harness runs, never edited by hand (`CLAUDE.md` §6).
