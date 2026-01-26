import copy
from pathlib import Path
from typing import Any, Dict, Optional
from unittest.mock import patch

import pytest
from pytest_mock import MockerFixture

from quantuminspire.managers.config_manager import ConfigManager
from quantuminspire.settings.project_settings import ProjectSettings
from quantuminspire.settings.user_settings import UserSettings
from tests.conftest import TestBaseDirMixin


class DummyProjectSettings(TestBaseDirMixin, ProjectSettings):
    """Test implementation of ProjectSettings using a temporary directory."""

    pass


class DummyUserSettings(TestBaseDirMixin, UserSettings):
    """Test implementation of UserSettings using a temporary directory."""

    pass


@pytest.fixture
def project_settings(tmp_path: Path) -> DummyProjectSettings:
    DummyProjectSettings._override_base_dir = tmp_path
    instance = DummyProjectSettings()
    return instance


@pytest.fixture
def user_settings(tmp_path: Path) -> DummyUserSettings:
    DummyUserSettings._override_base_dir = tmp_path
    instance = DummyUserSettings(auths={})
    return instance


@pytest.fixture
def config_manager(project_settings: DummyProjectSettings, user_settings: DummyUserSettings) -> ConfigManager:
    instance = ConfigManager(project_settings, user_settings)
    return instance


@pytest.fixture
def default_settings_map() -> Dict[str, Any]:
    settings_scopes: Dict[str, Any] = {
        "algorithm": {
            "id": {"value": None, "source": "dummyproject"},
            "name": {"value": "Example Algorithm", "source": "dummyproject"},
            "store_raw_data": {"value": False, "source": "dummyproject"},
            "algorithm_type": {"value": "quantum", "source": "dummyproject"},
            "num_shots": {"value": 1024, "source": "dummyproject"},
        },
        "job": {"id": {"value": None, "source": "dummyproject"}},
        "project": {
            "id": {"value": None, "source": "dummyproject"},
            "name": {"value": "Example Project", "source": "dummyproject"},
            "description": {"value": "Example Project", "source": "dummyproject"},
        },
        "backend_type": {"value": None, "source": "dummyuser"},
        "default_host": {"value": "https://api.quantum-inspire.com", "source": "dummyuser"},
    }

    return copy.deepcopy(settings_scopes)


@pytest.mark.parametrize(
    "key",
    [
        ("some-weird-key"),
        ("project.non_existent_key"),
    ],
)
def test_get_invalid_key(config_manager: ConfigManager, key: str) -> None:
    with pytest.raises(ValueError):
        config_manager.get(key)


@pytest.mark.parametrize(
    "key, expected_value",
    [
        ("project.description", "Example Project"),
        ("job.id", None),
        ("backend_type", None),
        ("algorithm.algorithm_type", "quantum"),
        ("project.id", None),
        ("algorithm.store_raw_data", False),
        ("default_host", "https://api.quantum-inspire.com"),
        ("algorithm.num_shots", 1024),
        ("project.name", "Example Project"),
        ("algorithm.id", None),
        ("algorithm.name", "Example Algorithm"),
    ],
)
def test_get_valid_key(config_manager: ConfigManager, key: str, expected_value: Any) -> None:
    assert config_manager.get(key) == expected_value


def test_configurable_field_names(config_manager: ConfigManager) -> None:

    supported_keys = [
        "algorithm.store_raw_data",
        "project.id",
        "job.id",
        "algorithm.algorithm_type",
        "algorithm.id",
        "algorithm.name",
        "default_host",
        "algorithm.num_shots",
        "project.description",
        "project.name",
        "backend_type",
    ]

    actual = config_manager._configurable_keys

    assert sorted(actual) == sorted(supported_keys)


@pytest.mark.parametrize(
    "key, value",
    [
        ("some-weird-key", 222),
        ("project.non_existent_key", 444),
    ],
)
def test_set_invalid_key(config_manager: ConfigManager, key: str, value: Any) -> None:
    with pytest.raises(ValueError):
        config_manager.set(key, value, False)


@pytest.mark.parametrize(
    "key, value, is_user",
    [
        ("project.description", "Example Project", True),
        ("default_host", "https://api.quantum-inspire.com", False),
    ],
)
def test_set_invalid_scopes(config_manager: ConfigManager, key: str, value: Any, is_user: bool) -> None:

    with pytest.raises(ValueError):
        config_manager.set(key, value, is_user)


@pytest.mark.parametrize(
    "key, old_value, new_value",
    [
        ("algorithm.id", None, 1),
        ("algorithm.store_raw_data", False, True),
        ("algorithm.algorithm_type", "quantum", "classic"),
        ("algorithm.num_shots", 1024, 100),
        ("job.id", None, 1),
        ("project.id", None, 1),
        ("project.name", "Example Project", "Changed Name"),
        ("project.description", "Example Project", "Changed Description"),
    ],
)
def test_set_project_scopes(config_manager: ConfigManager, key: str, old_value: Any, new_value: Any) -> None:
    # Act & Assert
    assert config_manager.get(key) == old_value
    config_manager.set(key, new_value, is_user=False)
    assert config_manager.get(key) == new_value


@pytest.mark.parametrize(
    "key, old_value, new_value",
    [
        ("default_host", "https://api.quantum-inspire.com", "https://api.changed.com"),
    ],
)
def test_set_user_scopes(config_manager: ConfigManager, key: str, old_value: Any, new_value: Any) -> None:
    # Act & Assert
    assert config_manager.get(key) == old_value
    config_manager.set(key, new_value, is_user=True)
    assert config_manager.get(key) == new_value


@pytest.mark.parametrize(
    "key, user_value, project_value",
    [
        ("backend_type", 500, 600),
    ],
)
def test_shared_scope_user_precedence_clears_project_scope(
    config_manager: ConfigManager, key: str, user_value: Any, project_value: Any
) -> None:
    # Arrange & Act
    config_manager._project_settings.set_value(key, project_value)

    # Act
    config_manager.set(key, user_value, is_user=True)

    # Assert
    assert config_manager._project_settings.get_value(key) is None
    assert config_manager.get(key) == user_value


@pytest.mark.parametrize(
    "key, user_value, project_value",
    [
        ("backend_type", 500, 600),
    ],
)
def test_shared_scope_project_precedence_without_overwriting_user(
    config_manager: ConfigManager, key: str, user_value: Any, project_value: Any
) -> None:
    # Arrange
    config_manager._user_settings.set_value(key, user_value)

    # Act
    config_manager.set(key, project_value, is_user=False)

    # Assert
    assert config_manager._user_settings.get_value(key) == user_value
    assert config_manager.get(key) == project_value


@pytest.mark.parametrize(
    "project_value, user_value, expected_value, expected_setting",
    [
        (500, 600, 500, "dummyproject"),
        (None, 600, 600, "dummyuser"),
        (None, None, None, "dummyuser"),
    ],
)
def test_inspect_merger(
    config_manager: ConfigManager,
    default_settings_map: Dict[str, Any],
    user_value: Optional[int],
    project_value: Optional[int],
    expected_value: Optional[int],
    expected_setting: str,
) -> None:

    backend_type_key = "backend_type"
    config_manager._project_settings.set_value(backend_type_key, project_value)
    config_manager._user_settings.set_value(backend_type_key, user_value)

    default_settings_map[backend_type_key]["value"] = expected_value
    default_settings_map[backend_type_key]["source"] = expected_setting

    assert config_manager.inspect() == default_settings_map


def test_config_manager_raises_if_project_not_initialised(
    mocker: MockerFixture, user_settings: DummyUserSettings
) -> None:
    mocker.patch("quantuminspire.managers.config_manager.ProjectSettings", side_effect=FileNotFoundError)

    with pytest.raises(RuntimeError, match="Project not initialised"):
        ConfigManager(user_settings=user_settings)


def test_init_calls_initialize(tmp_path: Path) -> None:
    with patch.object(ProjectSettings, "initialize") as mock_init:
        ConfigManager.initialize(path=tmp_path)

        mock_init.assert_called_once_with(tmp_path)


def test_user_settings(config_manager: ConfigManager) -> None:
    assert isinstance(config_manager.user_settings, UserSettings)
