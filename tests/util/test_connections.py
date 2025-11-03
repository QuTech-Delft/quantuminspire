from unittest.mock import MagicMock

import requests
from pytest import LogCaptureFixture
from pytest_mock import MockerFixture

from quantuminspire.util.connections import add_protocol


def test_url_with_scheme(caplog: LogCaptureFixture) -> None:
    test_url = "https://test_url.com"
    result_url = add_protocol(test_url)

    assert result_url == test_url
    assert "It is not necessary to specify the protocol in the URL" in caplog.text


def test_https_works(mocker: MockerFixture) -> None:
    test_url = "test_url.com"

    mock_head_response = MagicMock()
    mock_head_response.status_code = 200

    mocker.patch("requests.head", return_value=mock_head_response)
    result_url = add_protocol(test_url)

    assert result_url == f"https://{test_url}"


def test_https_fails(mocker: MockerFixture) -> None:
    test_url = "test_url.com"

    mock_head_response = MagicMock()
    mock_head_response.status_code = 404

    mocker.patch("requests.head", return_value=mock_head_response)
    result_url = add_protocol(test_url)

    assert result_url == f"http://{test_url}"


def test_requests_raises_exception(mocker: MockerFixture) -> None:
    test_url = "test_url.com"

    mocker.patch("requests.head", side_effect=requests.RequestException)
    result_url = add_protocol(test_url)

    assert result_url == f"http://{test_url}"
