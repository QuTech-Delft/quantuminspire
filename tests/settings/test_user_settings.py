from os import PathLike
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from quantuminspire.settings.user_settings import AuthSettings, UserSettings


def test_default_factory() -> None:
    assert UserSettings.default_factory() == {"auths": {}}


def test_base_dir() -> None:
    assert isinstance(UserSettings.base_dir(), PathLike)


def test_system_managed_fields() -> None:
    assert UserSettings.system_managed_fields() == {"auths"}


def test_default_auth_settings(tmp_path: Path) -> None:
    class DummyUserSetting(UserSettings):
        @classmethod
        def base_dir(cls) -> Path:
            return tmp_path

    user_settings = DummyUserSetting(auths={})
    auth_settings = MagicMock()
    user_settings.auths[user_settings.default_host] = auth_settings
    assert user_settings.default_auth_settings == auth_settings


def test_auth_settings_raises() -> None:
    auth_settings = AuthSettings()
    with pytest.raises(ValueError):
        auth_settings.owner_id


def test_auth_settings_owner_id() -> None:
    auth_settings = AuthSettings(team_member_id=1)
    assert auth_settings.owner_id == 1
