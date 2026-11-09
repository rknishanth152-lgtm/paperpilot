# Reproducibility labelling guide, version 1

For `FR-EVL-006` (R5). Applies to `checklist-v1`. Fixed before any label was given and before any model assessed these papers. A change to this file makes a new version, and labels made under the old one are not mixed with labels made under the new one.

For each paper and each checklist item, choose one status. The definition of each item is on the sheet, next to the choices. Judge each item on its own.

**Use only the text shown on the sheet.** It is the text PaperPilot has stored for the paper, in reading order. Tables, figures and supplements are generally not included, because the model will not see them either. Do not use what you remember about the paper.

| Status | Use when |
|---|---|
| `reported` | The text shown meets the item's "reported" definition. |
| `partially_reported` | The text shown meets the item's "partly reported" definition. |
| `not_found` | You looked and the text shown does not contain this. It means not found in the text shown. It is **not** a judgement that the paper omits it or that the work cannot be reproduced. |
| `needs_review` | You cannot decide from the text shown: the relevant text is garbled, or it plainly refers to a table, figure or supplement that holds the information. Not for items that are merely hard. |

Rules:

- There is no score and no overall verdict. Label what the text reports, and do not judge whether the work is good or true.
- Label from the text alone, with no help from an AI tool, so that the labels stay independent of any model.
- Small extraction glitches, such as a word broken in two, are not a reason for a lower status.
- If an item does not apply to the paper, such as code for a study with no software, use `not_found` unless the text says so explicitly.
