from typing import List
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture
from typer.testing import CliRunner

from quantuminspire.cli.command_list import app

runner = CliRunner()


@pytest.mark.parametrize(
    "args,output",
    [
        (["algorithms", "create", "Test"], "Creating quantum circuit 'Test'"),
        (["algorithms", "create", "Test", "--hybrid"], "Creating hybrid quantum/classical algorithm 'Test'"),
        (["algorithms", "commit"], "Commit algorithm to API"),
        (["algorithms", "delete"], "Delete local algorithm only"),
        (["algorithms", "delete", "--remote"], "Delete local and remote algorithm"),
        (["algorithms", "describe"], "Describe local algorithm"),
        (["algorithms", "describe", "--remote"], "Describe remote algorithm"),
        (["algorithms", "execute"], "Execute algorithm"),
        (["algorithms", "list"], "List no algorithms for project 'default'"),
        (["algorithms", "list", "--local"], "List local algorithms for project 'default'"),
        (["algorithms", "list", "--local", "--project", "Test"], "List local algorithms for project 'Test'"),
        (["algorithms", "list", "--remote"], "List remote algorithms for project 'default'"),
        (["algorithms", "list", "--remote", "--local"], "List remote and local algorithms for project 'default'"),
        (["algorithms", "select"], "Select algorithm"),
        (["config", "get", "key"], "Get config for 'key'"),
        (["config", "list"], "List custom config only"),
        (["config", "list", "--full"], "List config, custom and default"),
        (["config", "set", "key", "value"], "Set config 'key=value'"),
        (["projects", "create", "Test"], "Create project 'Test'"),
        (["projects", "delete"], "Delete local project"),
        (["projects", "delete", "--remote"], "Delete remote and local project"),
        (["projects", "describe"], "Describe local project"),
        (["projects", "describe", "--remote"], "Describe remote project"),
        (["projects", "list"], "List no projects"),
        (["projects", "list", "--local"], "List local projects"),
        (["projects", "list", "--remote"], "List remote projects"),
        (["projects", "list", "--remote", "--local"], "List remote and local projects"),
        (["projects", "sync", "--dest", "local"], "Sync projects with local"),
        (["projects", "sync", "--dest", "remote"], "Sync projects with remote"),
        (["logout"], "Logout from https://api.qi2.quantum-inspire.com"),
        (["logout", "https://www.quantum-inspire.com"], "Logout from https://www.quantum-inspire.com"),
    ],
)
def test_cli_calls(args: List[str], output: str) -> None:
    result = runner.invoke(app, args)
    assert result.exit_code == 0, repr(result.exception)
    assert output in result.stdout


def test_file_upload(mocker: MockerFixture) -> None:
    mock_remote_backend_inst = MagicMock()
    mocker.patch("quantuminspire.cli.command_list.RemoteBackend", return_value=mock_remote_backend_inst)
    mocker.patch("quantuminspire.cli.command_list.Path")

    result = runner.invoke(app, ["files", "upload", "hqca_circuit.py", "10"])

    assert result.exit_code == 0
    mock_remote_backend_inst.run.assert_called_once()


def test_file_run(mocker: MockerFixture) -> None:
    mock_local_backend_inst = MagicMock()
    mocker.patch("quantuminspire.cli.command_list.LocalBackend", return_value=mock_local_backend_inst)
    mocker.patch("quantuminspire.cli.command_list.Path")

    result = runner.invoke(app, ["files", "run", "hqca_circuit.py"])

    assert result.exit_code == 0
    mock_local_backend_inst.run.assert_called_once()


def test_results_get(mocker: MockerFixture) -> None:
    mock_remote_backend_inst = MagicMock()
    mocker.patch("quantuminspire.cli.command_list.RemoteBackend", return_value=mock_remote_backend_inst)

    result = runner.invoke(app, ["results", "get", "1"])

    assert result.exit_code == 0
    mock_remote_backend_inst.get_results.assert_called_once()


def test_results_get_no_results(mocker: MockerFixture) -> None:
    mock_remote_backend_inst = MagicMock()
    mock_remote_backend_inst.get_results.return_value = None
    mocker.patch("quantuminspire.cli.command_list.RemoteBackend", return_value=mock_remote_backend_inst)

    result = runner.invoke(app, ["results", "get", "1"])

    assert result.exit_code == 1
    mock_remote_backend_inst.get_results.assert_called_once()


def test_login(mocker: MockerFixture, mocked_config_file: MagicMock) -> None:
    device_session = mocker.patch("quantuminspire.cli.command_list.OauthDeviceSession")()
    webbrowser_open = mocker.patch("quantuminspire.cli.command_list.webbrowser.open")
    store_tokens = mocker.patch("quantuminspire.cli.command_list.Settings.store_tokens")
    result = runner.invoke(app, ["login", "https://host"])
    assert result.exit_code == 0, repr(result.exception)
    webbrowser_open.assert_called_once()
    device_session.initialize_authorization.assert_called_once()
    device_session.poll_for_tokens.assert_called_once()
    store_tokens.assert_called_once()
    assert "Login successful!" in result.stdout
