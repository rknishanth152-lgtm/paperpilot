"""The versioned reproducibility checklist (R5; FR-REP-001, OQ-010).

Six items that apply across fields, reduced from the candidate topics in
`FR-REP-001`. It describes what a paper reports. It is a reporting aid and never
a judgement of whether the work can be reproduced (`FR-REP-004`).

Change `CHECKLIST_VERSION` whenever a definition changes: the version is stored
with every assessment, and labels are tied to it.
"""

from dataclasses import dataclass

CHECKLIST_VERSION = "checklist-v1"


@dataclass(frozen=True)
class ChecklistItem:
    key: str
    title: str
    question: str
    reported: str
    partially_reported: str


CHECKLIST: tuple[ChecklistItem, ...] = (
    ChecklistItem(
        key="dataset_access",
        title="Data access",
        question="Does the paper say how a reader can obtain the data used?",
        reported=(
            "Gives a location or a way to get the data, such as a repository, "
            "accession number, named public dataset or access procedure."
        ),
        partially_reported=(
            "Says data are available without saying how, such as on request only, "
            "or covers only part of the data used."
        ),
    ),
    ChecklistItem(
        key="code_availability",
        title="Code availability",
        question="Does the paper say how a reader can obtain the code or scripts?",
        reported="Gives a location or named release for the code or analysis scripts.",
        partially_reported=(
            "Says code exists or is available without saying where, such as on "
            "request only, or covers only part of the code."
        ),
    ),
    ChecklistItem(
        key="data_preparation",
        title="Data selection and preparation",
        question="Does the paper say how the data were selected and prepared?",
        reported=(
            "States how the data or sample were chosen, and the preparation steps "
            "applied, or that none were."
        ),
        partially_reported=(
            "Gives only selection or only preparation, or describes them without "
            "the detail needed to repeat them."
        ),
    ),
    ChecklistItem(
        key="analysis_procedure",
        title="Experiment or analysis procedure",
        question="Does the paper describe the procedure in enough detail to repeat it?",
        reported=(
            "States the main steps and their settings, such as model structure, "
            "hyperparameters, data splits, random seeds or statistical tests."
        ),
        partially_reported="Names the main steps but leaves out key settings.",
    ),
    ChecklistItem(
        key="measures_and_comparisons",
        title="Measures and comparisons",
        question="Does the paper state what was measured and what it was compared with?",
        reported=(
            "Names the outcome measures or metrics, and the baseline, control or "
            "group they are compared with."
        ),
        partially_reported=(
            "States only one of the two, or names measures without saying what "
            "they mean."
        ),
    ),
    ChecklistItem(
        key="software_environment",
        title="Software and computing environment",
        question="Does the paper state the software or computing environment used?",
        reported=(
            "Names the main software or tools with versions, or the hardware where "
            "it matters."
        ),
        partially_reported="Names software or tools without versions.",
    ),
)
