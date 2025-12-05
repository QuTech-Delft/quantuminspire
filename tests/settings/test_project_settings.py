from os import PathLike

from quantuminspire.settings.project_settings import ProjectSettings


def test_default_factory() -> None:
    assert ProjectSettings.default_factory() == {}


def test_base_dir() -> None:
    assert isinstance(ProjectSettings.base_dir(), PathLike)
