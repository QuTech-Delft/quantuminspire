from typing import Generator
from unittest.mock import ANY, AsyncMock, MagicMock, call

import pytest
from compute_api_client import RunStatus
from pytest_mock import MockerFixture

from quantuminspire.util.api.remote_runtime import RemoteRuntime


@pytest.fixture
def configuration(mocker: MockerFixture) -> MagicMock:
    return mocker.patch("quantuminspire.util.api.remote_runtime.Configuration")


@pytest.fixture
def compute_api_client(mocker: MockerFixture) -> None:
    mocker.patch("quantuminspire.util.api.remote_runtime.Algorithm", return_value=MagicMock())
    mocker.patch("quantuminspire.util.api.remote_runtime.AlgorithmIn", return_value=MagicMock())
    mocker.patch("quantuminspire.util.api.remote_runtime.AlgorithmsApi", return_value=AsyncMock())
    mocker.patch("quantuminspire.util.api.remote_runtime.BatchRun", return_value=MagicMock())
    mocker.patch("quantuminspire.util.api.remote_runtime.BatchRunIn", return_value=MagicMock())
    mocker.patch("quantuminspire.util.api.remote_runtime.BatchRunsApi", return_value=AsyncMock())
    mocker.patch("quantuminspire.util.api.remote_runtime.Commit", return_value=MagicMock())
    mocker.patch("quantuminspire.util.api.remote_runtime.CommitIn", return_value=MagicMock())
    mocker.patch("quantuminspire.util.api.remote_runtime.CommitsApi", return_value=AsyncMock())
    mocker.patch("quantuminspire.util.api.remote_runtime.File", return_value=MagicMock())
    mocker.patch("quantuminspire.util.api.remote_runtime.FileIn", return_value=MagicMock())
    mocker.patch("quantuminspire.util.api.remote_runtime.FilesApi", return_value=AsyncMock())
    mocker.patch("quantuminspire.util.api.remote_runtime.Project", return_value=MagicMock())
    mocker.patch("quantuminspire.util.api.remote_runtime.ProjectIn", return_value=MagicMock())
    mocker.patch("quantuminspire.util.api.remote_runtime.ProjectsApi", return_value=AsyncMock())
    mocker.patch("quantuminspire.util.api.remote_runtime.Run", return_value=MagicMock())
    mocker.patch("quantuminspire.util.api.remote_runtime.RunIn", return_value=MagicMock())
    mocker.patch("quantuminspire.util.api.remote_runtime.RunsApi", return_value=AsyncMock())
    mocker.patch("quantuminspire.util.api.remote_runtime.RunStatus", return_value=MagicMock())
    mocker.patch("quantuminspire.util.api.remote_runtime.ShareType", return_value=MagicMock())
    mocker.patch("quantuminspire.util.api.remote_runtime.Result", return_value=MagicMock())
    mocker.patch("quantuminspire.util.api.remote_runtime.ResultsApi", return_value=AsyncMock())


@pytest.fixture
def api_client(mocker: MockerFixture) -> MagicMock:
    return mocker.patch("quantuminspire.util.api.remote_runtime.ApiClient")


@pytest.fixture
def mocked_settings(mocker: MockerFixture) -> MagicMock:
    settings = MagicMock()
    settings.auths = {"https://staging.qi2.quantum-inspire.com": {"user_id": 1}}

    mocked_settings = mocker.patch("quantuminspire.util.api.remote_runtime.Settings", return_value=settings)

    return mocked_settings


def test_create(configuration: MagicMock, mocked_settings: MagicMock) -> None:
    _ = RemoteRuntime()
    configuration.assert_called_once_with(host=ANY, api_key={"user": "1"})


def test_run(api_client: MagicMock, compute_api_client: None, mocked_settings: MagicMock) -> None:
    runtime = RemoteRuntime()
    runtime.run(MagicMock())
    api_client.assert_has_calls([call().__aenter__(), call().__aexit__(None, None, None)])


def test_get_results(mocker: MockerFixture, api_client: MagicMock, mocked_settings: MagicMock) -> None:
    runtime = RemoteRuntime()
    runs_api_instance = AsyncMock()
    run = MagicMock()
    run.status = RunStatus.COMPLETED
    runs_api_instance.read_run_runs_id_get.return_value = run
    mocker.patch("quantuminspire.util.api.remote_runtime.RunsApi", return_value=runs_api_instance)
    runtime.get_results(1)
    runs_api_instance.read_run_runs_id_get.assert_called_with(1)


def test_get_results_not_completed(
    mocker: MockerFixture, api_client: MagicMock, compute_api_client: None, mocked_settings: MagicMock
) -> None:
    runtime = RemoteRuntime()
    runs_api_instance = AsyncMock()
    run = MagicMock()
    run.status = RunStatus.RUNNING
    runs_api_instance.read_run_runs_id_get.return_value = run
    mocker.patch("quantuminspire.util.api.remote_runtime.RunsApi", return_value=runs_api_instance)
    runtime.get_results(MagicMock())
    api_client.assert_has_calls([call().__aenter__(), call().__aexit__(None, None, None)])
