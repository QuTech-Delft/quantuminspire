from os import PathLike
from pathlib import Path
from typing import List

import pytest

from quantuminspire.settings.project_settings import ProjectSettings


def test_default_factory() -> None:
    assert ProjectSettings.default_factory() == {}


def test_base_dir() -> None:
    assert isinstance(ProjectSettings.base_dir(), PathLike)


def test_find_project_root_not_found(tmp_path: Path):

    with pytest.raises(FileNotFoundError):
        ProjectSettings.find_project_root(start=tmp_path)


@pytest.mark.parametrize(
    "nested_path",
    [
        ([]),                # marker in current dir
        ([ "a", "b", "c" ])  # marker in parent dir
    ]
)
def test_find_project_root(tmp_path: Path, nested_path: List[str]):
    # Create nested path if needed
    start_path = tmp_path.joinpath(*nested_path)
    start_path.mkdir(parents=True, exist_ok=True)

    # Create marker in the root tmp_path
    marker_path = tmp_path / ".quantuminspire" / "projectsettings.json"
    marker_path.parent.mkdir(parents=True, exist_ok=True)
    marker_path.write_text("{}")

    # Act
    root = ProjectSettings.find_project_root(start=start_path)

    # Assert
    assert root == tmp_path
