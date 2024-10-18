import json
from typing import Any, List
from unittest.mock import AsyncMock, MagicMock

import pytest
from compute_api_client import Member
from pytest_mock import MockerFixture

import quantuminspire.util.configuration as configuration
from tests.conftest import CONFIGURATION

EXAMPLE_TOKENINFO = configuration.TokenInfo(
    access_token="secret",
    expires_in=100,
    refresh_token="also_secret",
    refresh_expires_in=200,
    generated_at=10000,
)


def test_force_file_into_existence_file_does_not_exist(mocked_config_file: MagicMock) -> None:
    mocked_config_file.exists.return_value = False
    open_mock = MagicMock()
    mocked_config_file.open.return_value = open_mock
    configuration.ensure_config_file_exists(mocked_config_file, "utf-8")
    mocked_config_file.parent.mkdir.assert_called_once_with(parents=True, exist_ok=True)
    mocked_config_file.open.assert_called_once_with("w", encoding="utf-8")
    open_mock.write.assert_called_once_with(
        """
{
  "auths": {
    "https://staging.qi2.quantum-inspire.com": {
      "well_known_endpoint":  "https://quantum-inspire-staging.eu.auth0.com/.well-known/openid-configuration"
    },
    "https://api.qi2.quantum-inspire.com": {
      "well_known_endpoint":  "https://auth.qi2.quantum-inspire.com/realms/oidc_production/.well-known/openid-configuration"
    }
  }
}
"""
    )


def test_force_file_into_existence_file_exists() -> None:
    path = MagicMock()
    path.exists.return_value = True
    open_mock = MagicMock()
    path.open.return_value = open_mock
    configuration.ensure_config_file_exists(path, "utf-8")
    path.parent.mkdir.assert_not_called()
    path.open.assert_not_called()
    path.open().write.assert_not_called()
    open_mock.write.assert_not_called()


def test_json_config_settings_file_does_not_exist(mocked_config_file: MagicMock) -> None:
    mocked_config_file.exists.return_value = False

    assert configuration.JsonConfigSettingsSource(configuration.Settings)() == json.loads(CONFIGURATION)


def test_json_config_settings_file_does_exist(mocked_config_file: MagicMock) -> None:
    assert configuration.JsonConfigSettingsSource(configuration.Settings)() == json.loads(CONFIGURATION)


def test_json_config_settings_qi2_813(mocked_config_file: MagicMock) -> None:
    settings = configuration.Settings()

    assert settings.auths["https://host"].well_known_endpoint == "https://some_url"


def test_customise_sources(mocker: MockerFixture) -> None:
    init_settings = MagicMock()
    env_settings = MagicMock()
    dot_env_settings = MagicMock()
    file_secret_settings = MagicMock()
    json_settings_source = mocker.patch("quantuminspire.util.configuration.JsonConfigSettingsSource")
    assert configuration.Settings.settings_customise_sources(
        configuration.Settings, init_settings, env_settings, dot_env_settings, file_secret_settings
    ) == (
        init_settings,
        env_settings,
        json_settings_source(configuration.Settings),
        file_secret_settings,
    )


def test_settings_from_init(mocked_config_file: MagicMock) -> None:
    settings = configuration.Settings(auths={"https://example.com": {"well_known_endpoint": "https://some_url/"}})
    assert (
        settings.auths.items()
        >= {"https://example.com": configuration.AuthSettings(well_known_endpoint="https://some_url/")}.items()
    )


def test_tokeninfo() -> None:
    assert EXAMPLE_TOKENINFO.access_expires_at == 10100


def test_store_tokens(mocked_config_file: MagicMock, mocker: MockerFixture) -> None:
    mocker.patch("quantuminspire.util.configuration.Settings.get_team_member_id", return_value=1)
    settings = configuration.Settings()
    settings.store_tokens("https://host", EXAMPLE_TOKENINFO)


def test_owner_id_none(mocked_config_file: MagicMock) -> None:
    settings = configuration.Settings()
    with pytest.raises(ValueError):
        settings.default_auth_settings.owner_id


def test_owner_id(mocked_config_file: MagicMock) -> None:
    settings = configuration.Settings(
        auths={"https://example.com": {"team_member_id": 42}}, default_host="https://example.com"
    )
    assert settings.default_auth_settings.owner_id == 42


@pytest.mark.parametrize(
    "expected_member_id, members_list, side_effect_user_input",
    [
        (1, [Member(id=1, team_id=4, user_id=6, role="member", is_active=True)], []),
        (
            2,
            [
                Member(id=1, team_id=4, user_id=6, role="member", is_active=True),
                Member(id=2, team_id=5, user_id=7, role="member", is_active=True),
            ],
            [999, "Random", 2],
        ),
    ],
)
def test_get_member_id(
    mocker: MockerFixture, expected_member_id: int, members_list: List[Member], side_effect_user_input: List[Any]
) -> None:
    class PageMember:
        def __init__(self, items_list: list[Member]) -> None:
            self.items = items_list

    members_api = MagicMock()
    members_api.read_members_members_get = AsyncMock(return_value=PageMember(members_list))
    mocker.patch("quantuminspire.util.configuration.MembersApi", return_value=members_api)
    mock_input = mocker.patch("builtins.input", side_effect=side_effect_user_input)
    member_id = configuration.Settings.get_team_member_id(host="https://host", access_token="some token")
    assert member_id == expected_member_id
    assert mock_input.call_count == len(side_effect_user_input)
