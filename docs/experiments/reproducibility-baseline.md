# Reproducibility checklist baseline

| Field | Value |
|---|---|
| Task | R8 (P11-T7; `FR-EVL-006`, `FR-REP-005`) |
| Date | 2026-11-09 |
| Kind | **Manual real-model run** |
| Labels | `benchmarks/reproducibility_labels_v1.json`, 18 labels by one labeller, given before any model assessed these papers |
| Papers | p1, p4 and p5 |

## 1. Method fixed before any result

Written and committed before any model assessed the labelled papers, and coded in `tests/evaluation/score_assessment.py`.

- **Agreement** is items where the assessed status equals the label, over all 18.
- **Commonest-label comparison.** The labels are 16 `reported` and 2 `not_found`, so always answering `reported` would agree on 16 of 18. The real score is reported beside that figure.
- **Per status:** recall (of items labelled this, how many were assessed this) and precision (of items assessed this, how many were labelled this). A status with no labels has no recall.
- **`not_found` versus `needs_review` confusion** is reported only as measurable if both labels occur. With no `needs_review` labels it is not measurable from this set.
- **Overstated and understated.** Among `reported`, `partially_reported` and `not_found`, whether the assessment claimed more or less than the label. `needs_review` claims nothing and is excluded.
- Two runs, because answers vary between runs. Neither the prompt nor the checklist is changed after seeing results unless that change is logged here.
