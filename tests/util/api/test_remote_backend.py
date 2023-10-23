from typing import Generator
from unittest.mock import ANY, AsyncMock, MagicMock, call

import pytest
from compute_api_client import JobStatus
from pytest_mock import MockerFixture

from quantuminspire.util.api.remote_backend import RemoteBackend


@pytest.fixture
def configuration(mocker: MockerFixture) -> MagicMock:
    return mocker.patch("quantuminspire.util.api.remote_backend.Configuration")


@pytest.fixture
def compute_api_client(mocker: MockerFixture) -> None:
    mocker.patch("quantuminspire.util.api.remote_backend.Algorithm", return_value=MagicMock())
    mocker.patch("quantuminspire.util.api.remote_backend.AlgorithmIn", return_value=MagicMock())
    mocker.patch("quantuminspire.util.api.remote_backend.AlgorithmsApi", return_value=AsyncMock())
    mocker.patch("quantuminspire.util.api.remote_backend.BatchJob", return_value=MagicMock())
    mocker.patch("quantuminspire.util.api.remote_backend.BatchJobIn", return_value=MagicMock())
    mocker.patch("quantuminspire.util.api.remote_backend.BatchJobsApi", return_value=AsyncMock())
    mocker.patch("quantuminspire.util.api.remote_backend.Commit", return_value=MagicMock())
    mocker.patch("quantuminspire.util.api.remote_backend.CommitIn", return_value=MagicMock())
    mocker.patch("quantuminspire.util.api.remote_backend.CommitsApi", return_value=AsyncMock())
    mocker.patch("quantuminspire.util.api.remote_backend.File", return_value=MagicMock())
    mocker.patch("quantuminspire.util.api.remote_backend.FileIn", return_value=MagicMock())
    mocker.patch("quantuminspire.util.api.remote_backend.FilesApi", return_value=AsyncMock())
    mocker.patch("quantuminspire.util.api.remote_backend.Project", return_value=MagicMock())
    mocker.patch("quantuminspire.util.api.remote_backend.ProjectIn", return_value=MagicMock())
    mocker.patch("quantuminspire.util.api.remote_backend.ProjectsApi", return_value=AsyncMock())
    mocker.patch("quantuminspire.util.api.remote_backend.Job", return_value=MagicMock())
    mocker.patch("quantuminspire.util.api.remote_backend.JobIn", return_value=MagicMock())
    mocker.patch("quantuminspire.util.api.remote_backend.JobsApi", return_value=AsyncMock())
    mocker.patch("quantuminspire.util.api.remote_backend.JobStatus", return_value=MagicMock())
    mocker.patch("quantuminspire.util.api.remote_backend.ShareType", return_value=MagicMock())
    mocker.patch("quantuminspire.util.api.remote_backend.Result", return_value=MagicMock())
    mocker.patch("quantuminspire.util.api.remote_backend.ResultsApi", return_value=AsyncMock())


@pytest.fixture
def api_client(mocker: MockerFixture) -> MagicMock:
    return mocker.patch("quantuminspire.util.api.remote_backend.ApiClient")


@pytest.fixture
def mocked_settings(mocker: MockerFixture) -> MagicMock:
    settings = MagicMock()
    settings.auths = {"https://staging.qi2.quantum-inspire.com": {"user_id": 1}}

    mocked_settings = mocker.patch("quantuminspire.util.api.remote_backend.Settings", return_value=settings)

    return mocked_settings


def test_create(configuration: MagicMock, mocked_settings: MagicMock) -> None:
    _ = RemoteBackend()
    configuration.assert_called_once_with(host=ANY, api_key={"user": "1"})


def test_run(api_client: MagicMock, compute_api_client: None, mocked_settings: MagicMock) -> None:
    backend = RemoteBackend()
    backend.run(MagicMock(), 10)
    api_client.assert_has_calls([call().__aenter__(), call().__aexit__(None, None, None)])


def test_get_results(mocker: MockerFixture, api_client: MagicMock, mocked_settings: MagicMock) -> None:
    backend = RemoteBackend()
    jobs_api_instance = AsyncMock()
    jobs = MagicMock()
    jobs.status = JobStatus.COMPLETED
    jobs_api_instance.read_job_jobs_id_get.return_value = jobs
    mocker.patch("quantuminspire.util.api.remote_backend.JobsApi", return_value=jobs_api_instance)
    backend.get_results(1)
    jobs_api_instance.read_job_jobs_id_get.assert_called_with(1)


def test_get_results_not_completed(
    mocker: MockerFixture, api_client: MagicMock, compute_api_client: None, mocked_settings: MagicMock
) -> None:
    backend = RemoteBackend()
    jobs_api_instance = AsyncMock()
    jobs = MagicMock()
    jobs.status = JobStatus.RUNNING
    jobs_api_instance.read_job_jobs_id_get.return_value = jobs
    mocker.patch("quantuminspire.util.api.remote_backend.JobsApi", return_value=jobs_api_instance)
    backend.get_results(MagicMock())
    api_client.assert_has_calls([call().__aenter__(), call().__aexit__(None, None, None)])
