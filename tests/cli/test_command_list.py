from unittest.mock import MagicMock

from compute_api_client import BackendStatus, JobStatus
from pydantic import BaseModel
from pytest_mock import MockerFixture
from typer.testing import CliRunner

from quantuminspire.cli.command_list import app
from quantuminspire.sdk.models.cqasm_algorithm import CqasmAlgorithm
from quantuminspire.sdk.models.hybrid_algorithm import HybridAlgorithm

runner = CliRunner()


def test_backend_list(mocker: MockerFixture) -> None:
    class MockBackendType:
        id = 1
        name = "Mock backend"
        status = BackendStatus.IDLE
        is_hardware = True
        supports_raw_data = True
        nqubits = 4
        max_number_of_shots = 2048

    mock_remote_backend_inst = MagicMock()
    paginated_mock = MagicMock()

    paginated_mock.items = [MockBackendType()]
    mock_remote_backend_inst.get_backend_types.return_value = paginated_mock
    mocker.patch("quantuminspire.cli.command_list.RemoteBackend", return_value=mock_remote_backend_inst)

    result = runner.invoke(app, ["backends", "list"])

    assert result.exit_code == 0
    mock_remote_backend_inst.get_backend_types.assert_called_once()


def test_backend_get(mocker: MockerFixture) -> None:
    class MockBackendType(BaseModel):
        id: int = 1
        name: str = "Mock backend"

    mock_remote_backend_inst = MagicMock()
    paginated_mock = MagicMock()

    paginated_mock.items = [MockBackendType()]
    mock_remote_backend_inst.get_backend_types.return_value = paginated_mock
    mocker.patch("quantuminspire.cli.command_list.RemoteBackend", return_value=mock_remote_backend_inst)

    result = runner.invoke(app, ["backends", "get", "1"])

    assert result.exit_code == 0
    mock_remote_backend_inst.get_backend_types.assert_called_once()


def test_backend_get_no_backend(mocker: MockerFixture) -> None:
    mock_remote_backend_inst = MagicMock()
    paginated_mock = MagicMock()

    paginated_mock.items = []
    mock_remote_backend_inst.get_backend_types.return_value = paginated_mock
    mocker.patch("quantuminspire.cli.command_list.RemoteBackend", return_value=mock_remote_backend_inst)

    result = runner.invoke(app, ["backends", "get", "1"])

    assert result.exit_code == 1
    mock_remote_backend_inst.get_backend_types.assert_called_once()


def test_file_upload_hybrid(mocker: MockerFixture) -> None:
    mock_remote_backend_inst = MagicMock()
    mocker.patch("quantuminspire.cli.command_list.RemoteBackend", return_value=mock_remote_backend_inst)
    mocker.patch("quantuminspire.cli.command_list.Path.read_text")

    result = runner.invoke(app, ["files", "upload", "hqca_circuit.py", "10"])

    assert result.exit_code == 0
    mock_remote_backend_inst.run.assert_called_once()
    assert type(mock_remote_backend_inst.run.call_args.args[0]) is HybridAlgorithm


def test_file_upload_no_suffix(mocker: MockerFixture) -> None:
    mock_remote_backend_inst = MagicMock()
    mocker.patch("quantuminspire.cli.command_list.RemoteBackend", return_value=mock_remote_backend_inst)
    mocker.patch("quantuminspire.cli.command_list.Path.read_text")

    result = runner.invoke(app, ["files", "upload", "hqca_circuit", "10"])

    assert type(result.exception) is ValueError


def test_file_upload_cqasm(mocker: MockerFixture) -> None:
    mock_remote_backend_inst = MagicMock()
    mocker.patch("quantuminspire.cli.command_list.RemoteBackend", return_value=mock_remote_backend_inst)
    mocker.patch("quantuminspire.cli.command_list.Path.read_text")

    result = runner.invoke(app, ["files", "upload", "simple_circuit.cq", "10"])

    assert result.exit_code == 0
    mock_remote_backend_inst.run.assert_called_once()
    assert type(mock_remote_backend_inst.run.call_args.args[0]) is CqasmAlgorithm


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


def test_results_get_failed_job(mocker: MockerFixture) -> None:
    mock_remote_backend_inst = MagicMock()
    job = MagicMock()
    job.id = 1
    job.status = JobStatus.FAILED
    job.message = "Job failed."
    job.trace_id = "trace_id"
    mock_remote_backend_inst.get_job.return_value = job
    mocker.patch("quantuminspire.cli.command_list.RemoteBackend", return_value=mock_remote_backend_inst)

    result = runner.invoke(app, ["results", "get", "1"])

    print(result.stdout)

    assert result.stdout == "Job failed.\nTrace id: trace_id\n"
    assert result.exit_code == 1


def test_results_get_no_results(mocker: MockerFixture) -> None:
    mock_remote_backend_inst = MagicMock()
    mock_remote_backend_inst.get_results.return_value = None
    mocker.patch("quantuminspire.cli.command_list.RemoteBackend", return_value=mock_remote_backend_inst)

    result = runner.invoke(app, ["results", "get", "1"])

    assert result.exit_code == 1
    mock_remote_backend_inst.get_results.assert_called_once()


def test_final_results_get(mocker: MockerFixture) -> None:
    mock_remote_backend_inst = MagicMock()
    mocker.patch("quantuminspire.cli.command_list.RemoteBackend", return_value=mock_remote_backend_inst)

    result = runner.invoke(app, ["final_results", "get", "1"])

    assert result.exit_code == 0
    mock_remote_backend_inst.get_final_results.assert_called_once()


def test_final_results_get_failed_job(mocker: MockerFixture) -> None:
    mock_remote_backend_inst = MagicMock()
    job = MagicMock()
    job.id = 1
    job.status = JobStatus.FAILED
    job.message = "Job failed."
    job.trace_id = "trace_id"
    mock_remote_backend_inst.get_job.return_value = job
    mocker.patch("quantuminspire.cli.command_list.RemoteBackend", return_value=mock_remote_backend_inst)

    result = runner.invoke(app, ["final_results", "get", "1"])

    assert result.stdout == "Job failed.\nTrace id: trace_id\n"
    assert result.exit_code == 1


def test_final_results_get_no_results(mocker: MockerFixture) -> None:
    mock_remote_backend_inst = MagicMock()
    mock_remote_backend_inst.get_final_results.return_value = None
    mocker.patch("quantuminspire.cli.command_list.RemoteBackend", return_value=mock_remote_backend_inst)

    result = runner.invoke(app, ["final_results", "get", "1"])

    assert result.exit_code == 1
    mock_remote_backend_inst.get_final_results.assert_called_once()


def test_override_auth_config(mocker: MockerFixture, mocked_config_file: MagicMock) -> None:
    fetch_auth = mocker.patch("quantuminspire.cli.command_list.Settings.fetch_auth_settings")
    runner.invoke(app, ["login", "https://host", "--override-auth-config"])
    fetch_auth.assert_not_called()


def test_login(mocker: MockerFixture, mocked_config_file: MagicMock) -> None:
    device_session = mocker.patch("quantuminspire.cli.command_list.OauthDeviceSession")()
    webbrowser_open = mocker.patch("quantuminspire.cli.command_list.webbrowser.open")
    store_tokens = mocker.patch("quantuminspire.cli.command_list.Settings.store_tokens")
    fetch_auth = mocker.patch("quantuminspire.cli.command_list.Settings.fetch_auth_settings")
    add_protocol = mocker.patch("quantuminspire.cli.command_list.add_protocol", return_value="https://host")

    result = runner.invoke(app, ["login", "https://host"])

    assert result.exit_code == 0, repr(result.exception)
    fetch_auth.assert_called_once()
    webbrowser_open.assert_called_once()
    device_session.initialize_authorization.assert_called_once()
    device_session.poll_for_tokens.assert_called_once()
    store_tokens.assert_called_once()
    add_protocol.assert_called_once_with("https://host")
    assert "Login successful!" in result.stdout


def test_login_store_tokens_failure(mocker: MockerFixture, mocked_config_file: MagicMock) -> None:
    mocker.patch("quantuminspire.cli.command_list.OauthDeviceSession")()
    mocker.patch("quantuminspire.cli.command_list.webbrowser.open")
    mocker.patch("quantuminspire.cli.command_list.Settings.store_tokens", side_effect=PermissionError())
    mocker.patch("quantuminspire.cli.command_list.Settings.fetch_auth_settings")
    mocker.patch("quantuminspire.cli.command_list.add_protocol", return_value="https://host")

    result = runner.invoke(app, ["login", "https://host"])
    assert result.exit_code == 1
    assert "LOGIN FAILED - Your host URL is incorrect." in result.stdout


def test_set_default_host(mocker: MockerFixture, mocked_config_file: MagicMock) -> None:
    host = "https://example.com"
    write_settings_to_file = mocker.patch("quantuminspire.cli.command_list.Settings.write_settings_to_file")
    result = runner.invoke(app, ["set-default-host", host])
    assert result.exit_code == 0, repr(result.exception)
    write_settings_to_file.assert_called_once()
    assert f"Default host set to {host}" in result.stdout
