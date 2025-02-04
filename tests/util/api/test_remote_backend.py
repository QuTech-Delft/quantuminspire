from unittest.mock import AsyncMock, MagicMock, call

import pytest
from compute_api_client import JobStatus, Language
from pytest_mock import MockerFixture

from quantuminspire.util.api.remote_backend import RemoteBackend
from quantuminspire.util.configuration import AuthSettings


@pytest.fixture
def configuration(mocker: MockerFixture) -> MagicMock:
    return mocker.patch("quantuminspire.util.api.remote_backend.Configuration")


@pytest.fixture
def compute_api_client(mocker: MockerFixture) -> None:
    mocker.patch("quantuminspire.util.api.remote_backend.Algorithm", return_value=MagicMock())
    mocker.patch("quantuminspire.util.api.remote_backend.AlgorithmIn", return_value=MagicMock())
    mocker.patch("quantuminspire.util.api.remote_backend.AlgorithmsApi", return_value=AsyncMock())
    mocker.patch("quantuminspire.util.api.remote_backend.BackendTypesApi", return_value=AsyncMock())
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
    mocker.patch("quantuminspire.util.api.remote_backend.FinalResult", return_value=MagicMock())
    mocker.patch("quantuminspire.util.api.remote_backend.FinalResultsApi", return_value=AsyncMock())
    mocker.patch("quantuminspire.util.api.remote_backend.Language", return_value=AsyncMock())
    mocker.patch("quantuminspire.util.api.remote_backend.LanguagesApi", return_value=AsyncMock())


@pytest.fixture
def api_client(mocker: MockerFixture) -> MagicMock:
    return mocker.patch("quantuminspire.util.api.remote_backend.ApiClient")


@pytest.fixture
def mocked_settings(mocker: MockerFixture) -> MagicMock:
    settings = MagicMock()
    settings.auths = {"https://staging.qi2.quantum-inspire.com": AuthSettings()}
    settings.default_host = "https://staging.qi2.quantum-inspire.com"

    mocked_settings = mocker.patch("quantuminspire.util.api.remote_backend.Settings", return_value=settings)

    return mocked_settings


@pytest.fixture
def mocked_authentication(mocker: MockerFixture) -> MagicMock:
    return mocker.patch("quantuminspire.util.api.remote_backend.OauthDeviceSession")


def test_create(configuration: MagicMock, mocked_settings: MagicMock, mocked_authentication: MagicMock) -> None:
    _ = RemoteBackend()
    configuration.assert_called_once_with(
        host="https://staging.qi2.quantum-inspire.com", oauth_session=mocked_authentication()
    )


def test_run(
    api_client: MagicMock,
    compute_api_client: None,
    mocked_settings: MagicMock,
    mocked_authentication: MagicMock,
    mocker: MockerFixture,
) -> None:
    mocker.patch.object(RemoteBackend, "_get_language_for_algorithm", return_value=AsyncMock())
    backend = RemoteBackend()
    backend.run(MagicMock(), 10)
    api_client.assert_has_calls([call().__aenter__(), call().__aexit__(None, None, None)])


def test_get_backend_types(
    mocker: MockerFixture, api_client: MagicMock, mocked_settings: MagicMock, mocked_authentication: MagicMock
) -> None:
    backend = RemoteBackend()
    backend_types_api_instance = AsyncMock()
    mocker.patch("quantuminspire.util.api.remote_backend.BackendTypesApi", return_value=backend_types_api_instance)
    backend.get_backend_types()
    backend_types_api_instance.read_backend_types_backend_types_get.assert_called_once()


def test_get_job(
    mocker: MockerFixture, api_client: MagicMock, mocked_settings: MagicMock, mocked_authentication: MagicMock
) -> None:
    backend = RemoteBackend()
    jobs_api_instance = AsyncMock()
    job_id = 1
    mocker.patch("quantuminspire.util.api.remote_backend.JobsApi", return_value=jobs_api_instance)
    backend.get_job(job_id)
    jobs_api_instance.read_job_jobs_id_get.assert_called_with(job_id)


def test_get_results(
    mocker: MockerFixture, api_client: MagicMock, mocked_settings: MagicMock, mocked_authentication: MagicMock
) -> None:
    backend = RemoteBackend()
    jobs_api_instance = AsyncMock()
    job = MagicMock()
    job.status = JobStatus.COMPLETED
    job.id = 1
    jobs_api_instance.read_job_jobs_id_get.return_value = job

    results_api_instance = AsyncMock()
    results = MagicMock()
    results_api_instance.read_results_by_job_id_results_job_job_id_get.return_value = results

    mocker.patch("quantuminspire.util.api.remote_backend.JobsApi", return_value=jobs_api_instance)
    mocker.patch("quantuminspire.util.api.remote_backend.ResultsApi", return_value=results_api_instance)
    backend.get_results(job.id)
    jobs_api_instance.read_job_jobs_id_get.assert_called_with(job.id)
    results_api_instance.read_results_by_job_id_results_job_job_id_get.assert_called_with(job.id)


def test_get_results_not_completed(
    mocker: MockerFixture,
    api_client: MagicMock,
    compute_api_client: None,
    mocked_settings: MagicMock,
    mocked_authentication: MagicMock,
) -> None:
    backend = RemoteBackend()
    jobs_api_instance = AsyncMock()
    job = MagicMock()
    job.id = 1
    job.status = JobStatus.RUNNING
    jobs_api_instance.read_job_jobs_id_get.return_value = job

    results_api_instance = AsyncMock()

    mocker.patch("quantuminspire.util.api.remote_backend.JobsApi", return_value=jobs_api_instance)
    mocker.patch("quantuminspire.util.api.remote_backend.ResultsApi", return_value=results_api_instance)
    backend.get_results(job.id)
    api_client.assert_has_calls([call().__aenter__(), call().__aexit__(None, None, None)])
    jobs_api_instance.read_job_jobs_id_get.assert_called_with(job.id)
    results_api_instance.read_results_by_job_id_results_job_job_id_get.assert_not_called()


def test_get_final_results(
    mocker: MockerFixture, api_client: MagicMock, mocked_settings: MagicMock, mocked_authentication: MagicMock
) -> None:
    backend = RemoteBackend()
    jobs_api_instance = AsyncMock()
    job = MagicMock()
    job.status = JobStatus.COMPLETED
    job.id = 1
    jobs_api_instance.read_job_jobs_id_get.return_value = job

    final_results_api_instance = AsyncMock()
    results = MagicMock()
    final_results_api_instance.read_final_result_by_job_id_final_results_job_job_id_get.return_value = results

    mocker.patch("quantuminspire.util.api.remote_backend.JobsApi", return_value=jobs_api_instance)
    mocker.patch("quantuminspire.util.api.remote_backend.FinalResultsApi", return_value=final_results_api_instance)
    backend.get_final_results(job.id)
    jobs_api_instance.read_job_jobs_id_get.assert_called_with(job.id)
    final_results_api_instance.read_final_result_by_job_id_final_results_job_job_id_get.assert_called_with(job.id)


def test_get_final_results_not_completed(
    mocker: MockerFixture,
    api_client: MagicMock,
    compute_api_client: None,
    mocked_settings: MagicMock,
    mocked_authentication: MagicMock,
) -> None:
    backend = RemoteBackend()
    jobs_api_instance = AsyncMock()
    job = MagicMock()
    job.id = 1
    job.status = JobStatus.RUNNING
    jobs_api_instance.read_job_jobs_id_get.return_value = job

    final_results_api_instance = AsyncMock()

    mocker.patch("quantuminspire.util.api.remote_backend.JobsApi", return_value=jobs_api_instance)
    mocker.patch("quantuminspire.util.api.remote_backend.FinalResultsApi", return_value=final_results_api_instance)
    backend.get_final_results(job.id)
    api_client.assert_has_calls([call().__aenter__(), call().__aexit__(None, None, None)])
    jobs_api_instance.read_job_jobs_id_get.assert_called_with(job.id)
    final_results_api_instance.read_final_result_by_job_id_final_results_job_job_id_get.assert_not_called()


async def test__get_language_for_algorithm(
    mocker: MockerFixture,
    api_client: MagicMock,
    compute_api_client: None,
    mocked_settings: MagicMock,
    mocked_authentication: MagicMock,
) -> None:
    # Arrange
    algorithm_mock = MagicMock()
    algorithm_mock.language_name = "MyLanguage"

    backend = RemoteBackend()

    languages_api_instance = AsyncMock()
    expected_language = Language(id=1, name="MyLanguage", version="1.0")
    non_expected_language = Language(id=2, name="NotMyLanguage", version="2.0")
    page_language = MagicMock()
    page_language.items = [expected_language, non_expected_language]
    languages_api_instance.read_languages_languages_get.return_value = page_language
    mocker.patch("quantuminspire.util.api.remote_backend.LanguagesApi", return_value=languages_api_instance)

    # Act
    actual_language = await backend._get_language_for_algorithm(api_client, algorithm_mock)

    # Assert
    assert actual_language == expected_language


async def test__get_language_for_algorithm_fail(
    mocker: MockerFixture,
    api_client: MagicMock,
    compute_api_client: None,
    mocked_settings: MagicMock,
    mocked_authentication: MagicMock,
) -> None:
    # Arrange
    algorithm_mock = MagicMock()
    algorithm_mock.language_name = "MyLanguage"

    backend = RemoteBackend()

    languages_api_instance = AsyncMock()
    expected_language = Language(id=1, name="NotMyLanguage", version="1.0")
    page_language = MagicMock()
    page_language.items = [expected_language]
    languages_api_instance.read_languages_languages_get.return_value = page_language
    mocker.patch("quantuminspire.util.api.remote_backend.LanguagesApi", return_value=languages_api_instance)

    # Act/Assert
    with pytest.raises(ValueError):
        _ = await backend._get_language_for_algorithm(api_client, algorithm_mock)
