import asyncio
import time
from pathlib import Path
from typing import Any, List
from unittest.mock import AsyncMock, MagicMock

import jwt
import pytest
from compute_api_client import Member, Role
from compute_api_client.exceptions import ForbiddenException
from pytest_mock import MockerFixture

from quantuminspire.managers.auth_manager import AuthManager
from quantuminspire.settings.user_settings import UserSettings
from quantuminspire.utils.authentication import AuthorisationError, OauthDeviceSession
from tests.conftest import TestBaseDirMixin


class DummyUserSettings(TestBaseDirMixin, UserSettings):
    """Test implementation of UserSettings using a temporary directory."""

    pass


@pytest.fixture
def user_settings(tmp_path: Path) -> DummyUserSettings:
    DummyUserSettings._override_base_dir = tmp_path
    instance = DummyUserSettings()
    return instance


@pytest.fixture
def oauth_session(mocker: MockerFixture) -> MagicMock:
    session_instance = MagicMock(spec=OauthDeviceSession)
    mocker.patch("quantuminspire.managers.auth_manager.OauthDeviceSession", return_value=session_instance)
    return session_instance


@pytest.fixture
def auth_manager(user_settings: DummyUserSettings) -> AuthManager:
    instance = AuthManager(user_settings=user_settings)
    return instance


def test_refresh_tokens(auth_manager: AuthManager, oauth_session: MagicMock, mocker: MockerFixture) -> None:
    # Arrange
    host = "http://example.com"
    mock_tokens = MagicMock()
    auth_manager._user_settings.auths[host] = MagicMock()
    oauth_session.refresh.return_value = mock_tokens
    store_tokens_mock = mocker.patch.object(auth_manager, "_store_tokens")

    # Act
    auth_manager.refresh_tokens(host)

    # Assert
    store_tokens_mock.assert_called_once_with(host, mock_tokens)


@pytest.mark.parametrize(
    "is_auth",
    [
        (True),
        (False),
    ],
)
def test_authentication(auth_manager: AuthManager, is_auth: bool) -> None:
    # Arrange
    host = "http://example.com"
    if is_auth:
        auth_manager._user_settings.auths[host] = MagicMock()

    # Act / Assert
    assert auth_manager._is_authenticated(host) == is_auth


@pytest.mark.parametrize(
    "side_effect, expected",
    [
        (None, True),  # refresh succeeds
        (AuthorisationError("invalid refresh token"), False),  # refresh fails
    ],
)
def test_is_refresh_token_valid(
    auth_manager: AuthManager,
    mocker: MockerFixture,
    side_effect: Exception | None,
    expected: bool,
) -> None:
    # Arrange
    host = "https://example.com"
    mocker.patch.object(
        auth_manager,
        "refresh_tokens",
        side_effect=side_effect,
    )

    # Act
    result = auth_manager._is_refresh_token_valid(host)

    # Assert
    assert result is expected


@pytest.mark.parametrize(
    "is_auth,is_refresh,expected",
    [
        (True, True, False),  # authenticated and refresh token valid -> login NOT required
        (False, True, True),  # not authenticated -> login required
        (True, False, True),  # refresh token invalid -> login required
        (False, False, True),  # neither authenticated nor valid -> login required
    ],
)
def test_login_required(
    auth_manager: AuthManager, mocker: MockerFixture, is_auth: bool, is_refresh: bool, expected: bool
) -> None:
    """Test login_required returns correct boolean depending on auth and refresh status."""
    host = "https://example.com"

    mocker.patch.object(auth_manager, "_is_authenticated", return_value=is_auth)
    mocker.patch.object(auth_manager, "_is_refresh_token_valid", return_value=is_refresh)

    assert auth_manager.login_required(host) is expected


@pytest.mark.parametrize(
    "override_auth_config",
    [
        (True),
        (False),
    ],
)
def test_login(
    auth_manager: AuthManager, oauth_session: MagicMock, mocker: MockerFixture, override_auth_config: bool
) -> None:

    host = "http://example.com"
    auth_manager._user_settings.auths[host] = MagicMock(team_member_id=2)
    fetch_auth = mocker.patch.object(auth_manager, "_fetch_auth_settings", return_value=AsyncMock())
    oauth_session.initialize_authorization.return_value = {
        "verification_uri_complete": "https://some_url.com",
        "user_code": "some-code",
    }
    mock_tokens = MagicMock()
    oauth_session.poll_for_tokens.return_value = mock_tokens
    store_tokens_mock = mocker.patch.object(auth_manager, "_store_tokens")
    _ = mocker.patch("quantuminspire.managers.auth_manager.webbrowser.open")

    # Act
    auth_manager.login(host, override_auth_config)
    store_tokens_mock.assert_called_once_with(host, mock_tokens)
    if not override_auth_config:
        fetch_auth.assert_awaited_once()
    else:
        fetch_auth.assert_not_awaited()


async def test_fetch_auth_settings(auth_manager: AuthManager, mocker: MockerFixture) -> None:

    # Arrange
    client_id = "test_client_id"
    audience = "test_audience"
    well_known_endpoint = "https://test.endpoint/.well-known/config"
    host = "http://example.com"

    auth_config = MagicMock()
    auth_config.client_id = client_id
    auth_config.audience = audience
    auth_config.well_known_endpoint = well_known_endpoint

    auth_config_api = AsyncMock()
    auth_config_api.auth_config_auth_config_get = AsyncMock(return_value=auth_config)

    mocker.patch("quantuminspire.managers.auth_manager.ApiClient", return_value=MagicMock())
    mocker.patch("quantuminspire.managers.auth_manager.AuthConfigApi", return_value=auth_config_api)

    # Act
    await auth_manager._fetch_auth_settings(host)
    auth_settings = auth_manager._user_settings.auths[host]

    # Assert
    assert auth_settings.client_id == client_id
    assert auth_settings.audience == audience
    assert auth_settings.well_known_endpoint == well_known_endpoint


async def test_wait_until_token_becomes_valid(auth_manager: AuthManager) -> None:

    secret_key = "some_secret_key"

    current_time = int(time.time())
    valid_from_time = current_time + 1  # Token becomes valid in 1 second

    # Payload with 'iat' and 'exp' claims
    payload = {
        "sub": "user_id_123",
        "iat": valid_from_time,  # Issued at time (valid after 1 second)
        "exp": valid_from_time + 3600,  # Expires 1 hour from valid time
    }

    # Generate the token
    token = jwt.encode(payload, secret_key, algorithm="HS256")

    await asyncio.wait_for(auth_manager._wait_until_token_becomes_valid(token), 3)


@pytest.mark.parametrize(
    "expected_member_id, members_list, side_effect_user_input",
    [
        (1, [Member(id=1, team_id=4, user_id=6, role=Role.MEMBER, is_active=True)], []),
        (
            2,
            [
                Member(id=1, team_id=4, user_id=6, role=Role.MEMBER, is_active=True),
                Member(id=2, team_id=5, user_id=7, role=Role.MEMBER, is_active=True),
            ],
            [999, "Random", 2],
        ),
    ],
)
def test_get_member_id(
    auth_manager: AuthManager,
    mocker: MockerFixture,
    expected_member_id: int,
    members_list: List[Member],
    side_effect_user_input: List[Any],
) -> None:
    class PageMember:
        def __init__(self, items_list: list[Member]) -> None:
            self.items = items_list

    token = (
        "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6Ik5UNkp2YTZvcHZVMTFlbjItdDlBRSJ9."
        "eyJpc3MiOiJodHRwczovL3F1YW50dW0taW5zcGlyZS1zdGFnaW5nLmV1LmF1dGgwLmNvbS8iLCJzdWIi"
        "OiJhdXRoMHw2NzE2MWRhZmEyMDEzZjFkY2VkNjdlODQiLCJhdWQiOlsiY29tcHV0ZS1qb2ItbWFuYWdl"
        "ciIsImh0dHBzOi8vcXVhbnR1bS1pbnNwaXJlLXN0YWdpbmcuZXUuYXV0aDAuY29tL3VzZXJpbmZvIl0s"
        "ImlhdCI6MTczNTA0MTEzMCwiZXhwIjoxNzM1MDQ0NzMwLCJzY29wZSI6Im9wZW5pZCBwcm9maWxlIGVt"
        "YWlsIG9mZmxpbmVfYWNjZXNzIiwiYXpwIjoiWXo3bmk5UFVBeVQ0M2VVQVNaZm1jMXlxSTY2UXhMVUo"
        "ifQ.iJyaZ_F9jhWCpkO85uht5wS9-o3jNnjNQXkO39Q0M5tgheoOCxhVfI3dCF86M2jE0np5lc8Mdxrhgo"
        "HEDad9sq5ZNnQMJUXC9tKE-P8gMvu9_EJuLz-Xa9Tg0E0TDlGGt_wl9_YO-dCl1Wi8okjtXJWn0e4p23w"
        "ZiUlE0SraRvfPmldPy_M0quevF0v55gSCegbybDMFM3KnOh7kXO1t1FqTaSkPRs-PCht3mnXLiFWWkWJD"
        "4OwT7fVUWUOHFXqWkHc8MCGD-cyDqa0jRqzbH_wb_uErwCMYGu-falfEdGoZX_yopgNpvrWke1VH-ieei"
        "KNADUnZ3rMx23kVQJstfQ"
    )

    members_api = MagicMock()
    members_api.read_members_members_get = AsyncMock(return_value=PageMember(members_list))
    mocker.patch("quantuminspire.managers.auth_manager.MembersApi", return_value=members_api)
    mock_input = mocker.patch("builtins.input", side_effect=side_effect_user_input)
    member_id = auth_manager._get_team_member_id(host="https://host", access_token=token)
    assert member_id == expected_member_id
    assert mock_input.call_count == len(side_effect_user_input)


def test_store_tokens(auth_manager: AuthManager, mocker: MockerFixture) -> None:
    # Arrange
    _ = mocker.patch.object(auth_manager, "_get_team_member_id", return_value=1)
    host = "https://host"
    auth_manager._user_settings.auths[host] = MagicMock()
    # Act
    auth_manager._store_tokens(host, MagicMock())
    # Assert
    assert auth_manager._user_settings.auths[host].team_member_id == 1


def test_store_tokens_member_id_fails(auth_manager: AuthManager, mocker: MockerFixture) -> None:
    # Arrange
    host = "https://host"
    _ = mocker.patch.object(auth_manager, "_get_team_member_id", side_effect=ForbiddenException())
    auth_manager._user_settings.auths[host] = MagicMock()

    # Act & Assert
    with pytest.raises(PermissionError):
        auth_manager._store_tokens(host, MagicMock())
