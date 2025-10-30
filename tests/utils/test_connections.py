import requests
from pytest_mock import MockerFixture

from quantuminspire.utils import connections


def test_add_protocol_with_protocol() -> None:
    url = connections.add_protocol("http://host")
    assert url == "http://host"


def test_add_protocol_with_https(mocker: MockerFixture) -> None:
    mock_head = mocker.patch("quantuminspire.utils.connections.requests.head")
    mock_head.return_value.status_code = 200

    url = connections.add_protocol("host")
    assert url == "https://host"


def test_add_protocol_with_http(mocker: MockerFixture) -> None:
    mock_head = mocker.patch("quantuminspire.utils.connections.requests.head")
    mock_head.return_value.status_code = 400

    url = connections.add_protocol("host")
    assert url == "http://host"


def test_add_protocol_raises_exception(mocker: MockerFixture) -> None:
    mock_head = mocker.patch("quantuminspire.utils.connections.requests.head")
    mock_head.side_effect = requests.RequestException()

    url = connections.add_protocol("host")
    assert url == "http://host"
