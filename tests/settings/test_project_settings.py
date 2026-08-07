import json
from pathlib import Path
from typing import List
from unittest.mock import patch

import pytest

from quantuminspire.settings.project_settings import ProjectSettings


def test_default_factory() -> None:
    assert ProjectSettings.default_factory() == {}


def test_base_dir_calls_find_project_root(tmp_path: Path) -> None:
    fake_root = tmp_path / "fake_root"

    with patch.object(ProjectSettings, "find_project_root", return_value=fake_root) as mock_find:
        result = ProjectSettings.base_dir()
        mock_find.assert_called_once()
        assert result == fake_root


@pytest.mark.parametrize(
    "start_subdirs",
    [
        [],  # No marker at all
        ["nested", "folder"],  # Marker exists exactly at end path
    ],
)
def test_find_project_root_not_found_cases(tmp_path: Path, start_subdirs: List[str]) -> None:
    """
    Test cases where project root is not usable:
      1. No marker exists at all
      2. Marker exists exactly at the `end` path (should raise even if marker exists)
    """
    # Arrange
    start_path = tmp_path.joinpath(*start_subdirs)
    start_path.mkdir(parents=True, exist_ok=True)

    if start_subdirs:
        marker_location = tmp_path / ".quantuminspire" / "config.json"
        marker_location.parent.mkdir(parents=True, exist_ok=True)
        marker_location.write_text("{}")

    # Act / Assert
    with pytest.raises(FileNotFoundError, match="Project root not found"):
        ProjectSettings.find_project_root(start=start_path, end=tmp_path)


@pytest.mark.parametrize(
    "nested_path",
    [
        [],  # marker in current dir
        ["a", "b", "c"],  # marker in parent dir
    ],
)
def test_find_project_root(tmp_path: Path, nested_path: List[str]) -> None:
    # Arrange
    start_path = tmp_path.joinpath(*nested_path)
    start_path.mkdir(parents=True, exist_ok=True)

    marker_path = tmp_path / ".quantuminspire" / "config.json"
    marker_path.parent.mkdir(parents=True, exist_ok=True)
    marker_path.write_text("{}")

    # Act
    root = ProjectSettings.find_project_root(start=start_path)

    # Assert
    assert root == tmp_path


def test_initialize_creates_file(tmp_path: Path) -> None:

    json_file_path = ProjectSettings.json_file(path=tmp_path)
    # Precondition: file should not exist yet
    assert not json_file_path.exists()

    # Act
    ProjectSettings.initialize(tmp_path)

    # Assert
    json_file_path = ProjectSettings.json_file(path=tmp_path)
    assert json_file_path.exists()  # File should exist

    content = json.loads(json_file_path.read_text())
    assert content == ProjectSettings.default_factory()
