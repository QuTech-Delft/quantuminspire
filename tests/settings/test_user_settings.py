from os import PathLike
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import requests
from pytest_mock import MockerFixture

from quantuminspire.settings.user_settings import AuthSettings, DevOverrides, UserSettings
from tests.conftest import TestBaseDirMixin


class DummyUserSettings(TestBaseDirMixin, UserSettings):
    """Test implementation of UserSettings using a temporary directory."""


@pytest.fixture(autouse=True)
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make sure a developer's shell doesn't leak into the tests."""
    monkeypatch.delenv("QI2_DEV_HOST", raising=False)
    monkeypatch.delenv("QI2_DEFAULT_HOST", raising=False)


def test_default_factory() -> None:
    assert UserSettings.default_factory() == {"auths": {}}


def test_base_dir() -> None:
    assert isinstance(UserSettings.base_dir(), PathLike)


def test_system_managed_fields() -> None:
    assert UserSettings.system_managed_fields() == {"auths"}


def test_default_auth_settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(DummyUserSettings, "_override_base_dir", tmp_path)

    user_settings = DummyUserSettings(auths={})
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


@pytest.mark.parametrize(
    "url",
    [
        "https://api.quantum-inspire.com",
        "http://example.com",
        "http://localhost:8000",
        "https://example.com:8443/path",
    ],
)
def test_resolve_protocol_url_with_scheme(url: str) -> None:
    assert UserSettings._resolve_protocol(url) == url


def test_resolve_protocol_https_works(mocker: MockerFixture) -> None:
    test_url = "example.com"

    mock_head_response = MagicMock()
    mock_head_response.status_code = 200

    mocker.patch("requests.head", return_value=mock_head_response)
    result_url = UserSettings._resolve_protocol(test_url)

    assert result_url == f"https://{test_url}"


def test_resolve_protocol_requests_raises_exception(mocker: MockerFixture) -> None:
    test_url = "test_url.com"

    mocker.patch("requests.head", side_effect=requests.RequestException)
    result_url = UserSettings._resolve_protocol(test_url)

    assert result_url == f"http://{test_url}"


@pytest.mark.parametrize("url", ["localhost", "localhost:8000", "localhost:8000/path", "127.0.0.1"])
def test_resolve_protocol_with_localhost(url: str) -> None:
    assert UserSettings._resolve_protocol(url) == f"http://{url}"


def test_default_host_validator_resolves_scheme(
    mocker: MockerFixture, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(DummyUserSettings, "_override_base_dir", tmp_path)

    mocker.patch(
        "quantuminspire.settings.user_settings.requests.head",
        return_value=MagicMock(),
    )

    settings = DummyUserSettings(default_host="example.com")

    assert str(settings.default_host) == "https://example.com"


def test_dev_overrides_default_is_none() -> None:
    assert DevOverrides().dev_host is None


def test_dev_overrides_reads_env_with_scheme(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("QI2_DEV_HOST", "http://localhost:8000")

    assert str(DevOverrides().dev_host).startswith("http://localhost:8000")


def test_dev_overrides_bare_localhost_gets_http(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("QI2_DEV_HOST", "localhost:8000")

    assert str(DevOverrides().dev_host).startswith("http://localhost:8000")
