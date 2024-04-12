import json
from datetime import datetime
from typing import Any, Generator

import pytest
import responses
from freezegun import freeze_time
from pytest_mock import MockerFixture

from quantuminspire.util.authentication import AuthorisationError, Configuration, OauthDeviceSession
from quantuminspire.util.configuration import AuthSettings
from tests.util.test_configuration import EXAMPLE_TOKENINFO


@pytest.fixture
def mocked_device_session(mocker: MockerFixture) -> Any:
    session = mocker.patch("quantuminspire.util.authentication.OauthDeviceSession", wraps=OauthDeviceSession)
    return session(AuthSettings())


@pytest.fixture
def mocked_responses() -> Generator[responses.RequestsMock, None, None]:
    with responses.RequestsMock(assert_all_requests_are_fired=False) as responses_mock:
        responses_mock.get(
            "https://auth.qi2.quantum-inspire.com/realms/oidc_production/.well-known/openid-configuration",
            body=json.dumps(
                {
                    "token_endpoint": "https://localhost/tokens",
                    "device_authorization_endpoint": "https://localhost/device",
                }
            ),
        )
        responses_mock.post(
            "https://localhost/device",
            body=json.dumps(
                {
                    "device_code": "secret",
                    "user_code": "ABCD-EFGH",
                    "verification_uri": "https://auth.qi2.quantum-inspire.com/realms/oidc_staging/device",
                    "verification_uri_complete": "https://auth.qi2.quantum-inspire.com/realms/oidc_staging/device?user_code=ABCD-EFGH",
                    "expires_in": 60,
                    "interval": 1,
                }
            ),
        )
        responses_mock.post("https://localhost/tokens", body=EXAMPLE_TOKENINFO.model_dump_json())
        yield responses_mock


@freeze_time(datetime.utcfromtimestamp(1000000))
def test_initialize_authorization(
    mocked_responses: responses.RequestsMock, mocked_device_session: OauthDeviceSession
) -> None:
    mocked_device_session.initialize_authorization()
    assert mocked_device_session.polling_interval == 1
    assert mocked_device_session.expires_in == 60
    assert mocked_device_session.expires_at == 1000000 + 60
    assert mocked_device_session._device_code == "secret"


def test_poll_for_tokens(mocked_responses: responses.RequestsMock, mocked_device_session: OauthDeviceSession) -> None:
    mocked_device_session.initialize_authorization()

    token_info = mocked_device_session.poll_for_tokens()
    assert token_info == EXAMPLE_TOKENINFO


@pytest.mark.parametrize("error", ["authorization_pending", "slow_down"])
@freeze_time(datetime.utcfromtimestamp(1000000), tick=True)
def test_poll_for_tokens_expired(
    error: str, mocked_responses: responses.RequestsMock, mocked_device_session: OauthDeviceSession
) -> None:
    mocked_device_session.initialize_authorization()
    mocked_responses.replace(responses.POST, "https://localhost/tokens", body=json.dumps({"error": error}), status=400)
    mocked_device_session.expires_at = 1000000 + 1
    mocked_device_session.polling_interval = 0.1
    with pytest.raises(AuthorisationError):
        mocked_device_session.poll_for_tokens()


def test_poll_for_tokens_500(
    mocked_responses: responses.RequestsMock, mocked_device_session: OauthDeviceSession
) -> None:
    mocked_device_session.initialize_authorization()
    mocked_responses.replace(
        responses.POST, "https://localhost/tokens", body=json.dumps({"error": "bad request"}), status=400
    )
    with pytest.raises(AuthorisationError):
        mocked_device_session.poll_for_tokens()


def test_refresh(mocked_responses: responses.RequestsMock, mocked_device_session: OauthDeviceSession) -> None:
    mocked_device_session._token_info = EXAMPLE_TOKENINFO.model_copy()
    mocked_device_session._token_info.access_token = "old_token"
    mocked_device_session.refresh()
    assert mocked_device_session._token_info.access_token == "secret"


@freeze_time(datetime.utcfromtimestamp(1000000))
def test_refresh_still_valid(
    mocked_responses: responses.RequestsMock, mocked_device_session: OauthDeviceSession
) -> None:
    mocked_device_session._token_info = EXAMPLE_TOKENINFO.model_copy()
    mocked_device_session._token_info.generated_at = 1000000 - 1
    mocked_device_session._token_info.access_token = "old_token"
    mocked_device_session.refresh()
    assert mocked_device_session._token_info.access_token == "old_token"


def test_refresh_not_logged_in(
    mocked_responses: responses.RequestsMock, mocked_device_session: OauthDeviceSession
) -> None:
    with pytest.raises(AuthorisationError):
        mocked_device_session.refresh()


def test_refresh_500(mocked_responses: responses.RequestsMock, mocked_device_session: OauthDeviceSession) -> None:
    mocked_responses.replace(responses.POST, "https://localhost/tokens", body="internal server error", status=500)
    mocked_device_session._token_info = EXAMPLE_TOKENINFO
    with pytest.raises(AuthorisationError):
        mocked_device_session.refresh()


def test_configuration_auth_settings(
    mocked_responses: responses.RequestsMock, mocked_device_session: OauthDeviceSession
) -> None:
    config = Configuration(host="https://staging.qi2.quantum-inspire.com", oauth_session=mocked_device_session)
    mocked_device_session._token_info = EXAMPLE_TOKENINFO
    assert config.auth_settings()["user_bearer"]["value"] == "Bearer secret"
