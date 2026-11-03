# Evaluation tests

The evaluation harness lives here (Phase 4 onwards: `FR-EVL-*`). Tests in this folder are marked `evaluation` automatically and are excluded from the default `uv run pytest` run. Run them with:

```bash
uv run pytest -m evaluation
```

Evaluation results are produced only by saved harness runs, never edited by hand (`CLAUDE.md` §6).
