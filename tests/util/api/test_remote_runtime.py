from typing import Any, Generator
from unittest.mock import AsyncMock, MagicMock, call

import pytest
from pytest_mock import MockerFixture

from quantuminspire.util.api.remote_runtime import RemoteRuntime


@pytest.fixture
def configuration(mocker: MockerFixture) -> Generator[MagicMock, None, None]:
    yield mocker.patch("quantuminspire.util.api.remote_runtime.Configuration")


@pytest.fixture
def compute_api_client(mocker: MockerFixture) -> None:
    mocker.patch("quantuminspire.util.api.remote_runtime.Algorithm", return_value=AsyncMock())
    mocker.patch("quantuminspire.util.api.remote_runtime.AlgorithmIn", return_value=AsyncMock())
    mocker.patch("quantuminspire.util.api.remote_runtime.AlgorithmsApi", return_value=AsyncMock())
    mocker.patch("quantuminspire.util.api.remote_runtime.AlgorithmType", return_value=AsyncMock())
    mocker.patch("quantuminspire.util.api.remote_runtime.BatchRun", return_value=AsyncMock())
    mocker.patch("quantuminspire.util.api.remote_runtime.BatchRunIn", return_value=AsyncMock())
    mocker.patch("quantuminspire.util.api.remote_runtime.BatchRunsApi", return_value=AsyncMock())
    mocker.patch("quantuminspire.util.api.remote_runtime.Commit", return_value=AsyncMock())
    mocker.patch("quantuminspire.util.api.remote_runtime.CommitIn", return_value=AsyncMock())
    mocker.patch("quantuminspire.util.api.remote_runtime.CommitsApi", return_value=AsyncMock())
    mocker.patch("quantuminspire.util.api.remote_runtime.CompileStage", return_value=AsyncMock())
    mocker.patch("quantuminspire.util.api.remote_runtime.File", return_value=AsyncMock())
    mocker.patch("quantuminspire.util.api.remote_runtime.FileIn", return_value=AsyncMock())
    mocker.patch("quantuminspire.util.api.remote_runtime.FilesApi", return_value=AsyncMock())
    mocker.patch("quantuminspire.util.api.remote_runtime.Project", return_value=AsyncMock())
    mocker.patch("quantuminspire.util.api.remote_runtime.ProjectIn", return_value=AsyncMock())
    mocker.patch("quantuminspire.util.api.remote_runtime.ProjectsApi", return_value=AsyncMock())
    mocker.patch("quantuminspire.util.api.remote_runtime.Run", return_value=AsyncMock())
    mocker.patch("quantuminspire.util.api.remote_runtime.RunIn", return_value=AsyncMock())
    mocker.patch("quantuminspire.util.api.remote_runtime.RunsApi", return_value=AsyncMock())
    mocker.patch("quantuminspire.util.api.remote_runtime.RunStatus", return_value=AsyncMock())
    mocker.patch("quantuminspire.util.api.remote_runtime.ShareType", return_value=AsyncMock())


@pytest.fixture
def api_client(mocker: MockerFixture) -> Generator[MagicMock, None, None]:
    yield mocker.patch("quantuminspire.util.api.remote_runtime.ApiClient")


def test_create(configuration: MagicMock) -> None:
    _ = RemoteRuntime()
    configuration.assert_called_once()


def test_run(api_client: MagicMock, compute_api_client: None) -> None:
    runtime = RemoteRuntime()
    runtime.run(MagicMock())
    api_client.assert_has_calls([call().__aenter__(), call().__aexit__(None, None, None)])


def test_get_results() -> None:
    runtime = RemoteRuntime()
    runtime.get_results()
    assert True
