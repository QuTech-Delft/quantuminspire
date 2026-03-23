import copy
from pathlib import Path
from typing import Any, Dict, Optional
from unittest.mock import MagicMock, patch

import pytest

from quantuminspire.managers.config_manager import ConfigManager
from quantuminspire.settings.models import Project
from quantuminspire.settings.project_settings import ProjectSettings
from quantuminspire.settings.user_settings import UserSettings
from tests.conftest import TestBaseDirMixin


class DummyProjectSettings(TestBaseDirMixin, ProjectSettings):
    """Test implementation of ProjectSettings using a temporary directory."""

    shared_setting: str = "shared setting project"


class DummyUserSettings(TestBaseDirMixin, UserSettings):
    """Test implementation of UserSettings using a temporary directory."""

    test_setting: str = "some test setting"
    shared_setting: str = "shared setting user"


@pytest.fixture
def project_settings(tmp_path: Path) -> DummyProjectSettings:
    DummyProjectSettings._override_base_dir = tmp_path
    instance = DummyProjectSettings(
        project=Project(
            id=None,
            name="Example Project",
            description="Example Project",
            algorithms={},
        )
    )
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
        "project": {
            "id": {"value": None, "source": "dummyproject"},
            "name": {"value": "Example Project", "source": "dummyproject"},
            "description": {"value": "Example Project", "source": "dummyproject"},
            "algorithms": {"value": {}, "source": "dummyproject"},
        },
        "default_host": {"value": "https://api.quantum-inspire.com", "source": "dummyuser"},
        "test_setting": {"value": "some test setting", "source": "dummyuser"},
        "shared_setting": {"value": "shared setting user", "source": "dummyuser"},
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
        ("project.id", None),
        ("project.name", "Example Project"),
        ("project.description", "Example Project"),
        ("project.algorithms", {}),
        ("default_host", "https://api.quantum-inspire.com"),
        ("test_setting", "some test setting"),
        ("shared_setting", "shared setting project"),
    ],
)
def test_get_valid_key(config_manager: ConfigManager, key: str, expected_value: Any) -> None:
    assert config_manager.get(key) == expected_value


def test_configurable_field_names(config_manager: ConfigManager) -> None:

    supported_keys = [
        "project.id",
        "project.name",
        "project.description",
        "project.algorithms",
        "default_host",
        "test_setting",
        "shared_setting",
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
        ("test_setting", "some test setting", False),
    ],
)
def test_set_invalid_scopes(config_manager: ConfigManager, key: str, value: Any, is_user: bool) -> None:

    with pytest.raises(ValueError):
        config_manager.set(key, value, is_user)


@pytest.mark.parametrize(
    "key, old_value, new_value",
    [
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
        ("test_setting", "some test setting", "some new setting"),
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
        ("shared_setting", "shared setting user", "shared setting project"),
    ],
)
def test_shared_scope_user_precedence_clears_project_scope(
    config_manager: ConfigManager, key: str, user_value: Any, project_value: Any
) -> None:
    # Arrange & Act
    assert config_manager._project_settings is not None
    config_manager._project_settings.set_value(key, project_value)

    # Act
    config_manager.set(key, user_value, is_user=True)

    # Assert
    assert config_manager._project_settings.get_value(key) is None
    assert config_manager.get(key) == user_value


@pytest.mark.parametrize(
    "key, user_value, project_value",
    [
        ("shared_setting", "shared setting user", "shared setting project"),
    ],
)
def test_shared_scope_project_precedence_without_overwriting_user(
    config_manager: ConfigManager, key: str, user_value: Any, project_value: Any
) -> None:
    # Arrange
    assert config_manager._project_settings is not None
    config_manager._user_settings.set_value(key, user_value)

    # Act
    config_manager.set(key, project_value, is_user=False)

    # Assert
    assert config_manager._user_settings.get_value(key) == user_value
    assert config_manager.get(key) == project_value


@pytest.mark.parametrize(
    "project_value, user_value, expected_value, expected_setting",
    [
        ("shared setting project", "shared setting user", "shared setting project", "dummyproject"),
        (None, "shared setting user", "shared setting user", "dummyuser"),
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

    shared_setting_key = "shared_setting"
    assert config_manager._project_settings is not None
    config_manager._project_settings.set_value(shared_setting_key, project_value)
    config_manager._user_settings.set_value(shared_setting_key, user_value)

    default_settings_map[shared_setting_key]["value"] = expected_value
    default_settings_map[shared_setting_key]["source"] = expected_setting

    assert config_manager.inspect() == default_settings_map


def test_settings_priority_without_project_settings(user_settings: DummyUserSettings) -> None:
    config_manager = ConfigManager(project_settings=None, user_settings=user_settings)
    priority = config_manager._settings_priority
    assert priority == [user_settings]


def test_settings_priority_with_project_settings(
    config_manager: ConfigManager,
    project_settings: DummyProjectSettings,
    user_settings: DummyUserSettings,
) -> None:
    priority = config_manager._settings_priority
    assert priority == [project_settings, user_settings]


def test_initialize_with_existing_project_settings(config_manager: ConfigManager, tmp_path: Path) -> None:
    original_project_settings = config_manager._project_settings
    original_keys = config_manager._configurable_keys

    with patch.object(ProjectSettings, "initialize") as mock_init:
        config_manager.initialize(path=tmp_path)

        mock_init.assert_called_once_with(tmp_path)
        assert config_manager._project_settings is original_project_settings
        assert config_manager._configurable_keys == original_keys


def test_initialize_without_project_settings(user_settings: DummyUserSettings, tmp_path: Path) -> None:
    config_manager = ConfigManager(project_settings=None, user_settings=user_settings)
    mock_project_settings = MagicMock(spec=ProjectSettings)

    assert config_manager._project_settings is None

    with (
        patch.object(ProjectSettings, "initialize"),
        patch(
            "quantuminspire.managers.config_manager.ProjectSettings", return_value=mock_project_settings
        ) as mock_project_settings_class,
        patch.object(
            config_manager, "_compute_flattened_keys", return_value=MagicMock()
        ) as mock_compute_flattened_keys,
    ):
        mock_instance = mock_project_settings_class.return_value

        config_manager.initialize(path=tmp_path)

        mock_project_settings_class.assert_called_once()
        assert config_manager._project_settings is mock_instance
        mock_compute_flattened_keys.assert_called_once()


def test_user_settings(config_manager: ConfigManager) -> None:
    assert isinstance(config_manager.user_settings, UserSettings)
