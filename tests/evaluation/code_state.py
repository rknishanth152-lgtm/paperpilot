"""Which code produced an evaluation result (P6-T1)."""

import subprocess
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class CodeState:
    revision: str
    clean: bool


def _git(root: Path, *arguments: str) -> str:
    done = subprocess.run(
        ["git", *arguments], cwd=root, capture_output=True, text=True, check=True
    )
    return done.stdout.strip()


def code_state(root: Path = REPO_ROOT) -> CodeState:
    """The commit, and whether anything differs from it.

    Saved results are left out: they do not change what a run computes, and each
    run adds one, so counting them would mark every later run as modified.
    """
    changes = _git(
        root, "status", "--porcelain", "--", ".", ":(exclude)benchmarks/results"
    )
    return CodeState(_git(root, "rev-parse", "HEAD"), changes == "")
