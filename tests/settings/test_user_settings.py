from os import PathLike

from quantuminspire.settings.user_settings import UserSettings


def test_default_factory() -> None:
    assert UserSettings.default_factory() == {}


def test_base_dir() -> None:
    assert isinstance(UserSettings.base_dir(), PathLike)
