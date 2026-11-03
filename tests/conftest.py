"""Test conventions shared by every test folder.

| Folder              | Marker      | Needs                         | Default run |
|---------------------|-------------|-------------------------------|-------------|
| tests/unit/         | (none)      | nothing: pure, offline        | yes         |
| tests/integration/  | integration | services from compose.yaml    | no          |
| tests/evaluation/   | evaluation  | evaluation data and services  | no          |

Markers are added here by folder, so a test cannot forget its marker.
"""

from pathlib import Path

import pytest

TESTS_DIR = Path(__file__).parent
MARKER_BY_FOLDER = {
    "integration": pytest.mark.integration,
    "evaluation": pytest.mark.evaluation,
}


@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    # tryfirst: markers must be added before pytest applies `-m` selection.
    for item in items:
        folder = item.path.relative_to(TESTS_DIR).parts[0]
        marker = MARKER_BY_FOLDER.get(folder)
        if marker is not None:
            item.add_marker(marker)
