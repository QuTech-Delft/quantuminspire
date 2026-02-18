from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from compute_api_client import (
    Algorithm,
    AlgorithmIn,
    AlgorithmsApi,
    AlgorithmType,
    BackendType,
    BackendTypesApi,
    BatchJob,
    BatchJobIn,
    BatchJobsApi,
    Commit,
    CommitIn,
    CommitsApi,
    CompileStage,
    File,
    FileIn,
    FilesApi,
    FinalResult,
    FinalResultsApi,
    Job,
    JobIn,
    JobsApi,
    Language,
    PageLanguage,
    Project,
    ProjectIn,
    ProjectPatch,
    ProjectsApi,
    ShareType,
)
from pytest_mock import MockerFixture

from quantuminspire.managers.config_manager import ConfigManager
from quantuminspire.managers.job_manager import JobManager, JobOptions


@pytest.fixture
def config_manager() -> ConfigManager:
    mock_manager: MagicMock = MagicMock(spec=ConfigManager)
    mock_manager.get.return_value = "https://api.quantum-inspire.com"
    mock_manager.user_settings.auths = {"https://api.quantum-inspire.com": MagicMock(owner_id=123)}
    return mock_manager


@pytest.fixture
def job_manager(config_manager: ConfigManager) -> JobManager:
    return JobManager(config_manager)


@pytest.fixture
def job_options(mocker: MockerFixture) -> MagicMock:
    mock: MagicMock = mocker.MagicMock(spec=JobOptions)
    mock.project_name = "Dummy project"
    mock.project_description = "Dummy project description"
    mock.algorithm_name = "Dummy algorithm"
    mock.algorithm_id = 1
    mock.backend_type_id = 2
    mock.number_of_shots = 1024
    mock.raw_data_enabled = False
    return mock


@pytest.fixture
def mock_project(mocker: MockerFixture) -> MagicMock:
    mock: MagicMock = mocker.MagicMock(spec=Project)
    mock.id = 1
    mock.name = "Dummy project"
    mock.description = "Dummy project description"
    return mock


@pytest.fixture
def mock_algorithm(mocker: MockerFixture) -> MagicMock:
    mock: MagicMock = mocker.MagicMock(spec=Algorithm)
    mock.id = 1
    mock.name = "Dummy algorithm"
    mock.type = AlgorithmType.QUANTUM
    return mock


@pytest.fixture
def mock_commit(mocker: MockerFixture) -> MagicMock:
    mock: MagicMock = mocker.MagicMock(spec=Commit)
    mock.id = 1
    mock.description = "Commit created by SDK"
    mock.algorithm_id = 1
    return mock


@pytest.fixture
def mock_language(mocker: MockerFixture) -> MagicMock:
    mock: MagicMock = mocker.MagicMock(spec=Language)
    mock.id = 1
    mock.name = "cqasm"
    mock.version = "3.0"
    return mock


@pytest.fixture
def mock_file(mocker: MockerFixture) -> MagicMock:
    mock: MagicMock = mocker.MagicMock(spec=File)
    mock.id = 1
    return mock


@pytest.fixture
def mock_batch_job(mocker: MockerFixture) -> MagicMock:
    mock: MagicMock = mocker.MagicMock(spec=BatchJob)
    mock.id = 1
    return mock


@pytest.fixture
def mock_job(mocker: MockerFixture) -> MagicMock:
    mock: MagicMock = mocker.MagicMock(spec=Job)
    mock.id = 1
    return mock


@pytest.fixture
def mock_backend_type(mocker: MockerFixture) -> MagicMock:
    mock: MagicMock = mocker.MagicMock(spec=BackendType)
    return mock


@pytest.fixture
def mock_final_result(mocker: MockerFixture) -> MagicMock:
    mock: MagicMock = mocker.MagicMock(spec=FinalResult)
    return mock


def test_init_with_config_manager(config_manager: ConfigManager) -> None:
    job_manager = JobManager(config_manager)
    assert job_manager._config_manager == config_manager


def test_invoke(job_manager: JobManager, mocker: MockerFixture) -> None:
    mock_result = mocker.MagicMock()
    mock_api_method = mocker.AsyncMock(return_value=mock_result)
    mock_api_instance = mocker.MagicMock()
    setattr(mock_api_instance, "some_method", mock_api_method)

    mock_api_class = mocker.MagicMock(return_value=mock_api_instance)
    mock_client = mocker.MagicMock()

    with patch("quantuminspire.managers.job_manager.ApiClient") as mock_api_client_class:
        mock_api_client_class.return_value.__aenter__.return_value = mock_client

        result = JobManager._invoke(mock_api_class, "some_method", "arg1", "arg2", kwarg1="value1")

        mock_api_class.assert_called_once_with(mock_client)
        mock_api_method.assert_called_once_with("arg1", "arg2", kwarg1="value1")
        assert result == mock_result


def test_get_backend_types(job_manager: JobManager, mock_backend_type: BackendType, mocker: MockerFixture) -> None:
    mock_page = mocker.MagicMock(items=[mock_backend_type], total=1, page=1, size=50)

    with patch.object(JobManager, "_invoke", return_value=mock_page) as mock_invoke:
        result = job_manager.get_backend_types()

        mock_invoke.assert_called_once_with(
            BackendTypesApi,
            "read_backend_types_backend_types_get",
        )
        assert result[0] == mock_backend_type


def test_get_job(job_manager: JobManager, mock_job: Job) -> None:
    with patch.object(JobManager, "_invoke", return_value=mock_job) as mock_invoke:
        job_manager.get_job(job_id=1)

        mock_invoke.assert_called_once_with(
            JobsApi,
            "read_job_jobs_id_get",
            id=1,
        )


def test_get_final_result(job_manager: JobManager, mock_final_result: FinalResult) -> None:
    with patch.object(JobManager, "_invoke", return_value=mock_final_result) as mock_invoke:
        job_manager.get_final_result(job_id=1)

        mock_invoke.assert_called_once_with(
            FinalResultsApi,
            "read_final_result_by_job_id_final_results_job_job_id_get",
            1,
        )


def test_get_algorithm_type_hybrid() -> None:
    file_path = Path("test_algorithm.py")
    result = JobManager.get_algorithm_type(file_path)

    assert result == AlgorithmType.HYBRID


def test_get_algorithm_type_quantum() -> None:
    file_path = Path("test_algorithm.cq")
    result = JobManager.get_algorithm_type(file_path)

    assert result == AlgorithmType.QUANTUM


def test_get_algorithm_type_invalid_extension() -> None:
    file_path = Path("test_algorithm.txt")

    with pytest.raises(ValueError, match="Incorrect file type. Supported types are .py and .cq"):
        JobManager.get_algorithm_type(file_path)


def test_create_project(job_manager: JobManager, mock_project: Project) -> None:
    with patch.object(JobManager, "_invoke", return_value=mock_project) as mock_invoke:
        job_manager.create_project(
            owner_id=123,
            project_name=mock_project.name,
            project_description=mock_project.description,
        )

        mock_invoke.assert_called_once_with(
            ProjectsApi,
            "create_project_projects_post",
            ProjectIn(
                owner_id=123,
                name=mock_project.name,
                description=mock_project.description,
                starred=False,
            ),
        )


def test_create_algorithm(job_manager: JobManager, mock_algorithm: Algorithm) -> None:
    with patch.object(JobManager, "_invoke", return_value=mock_algorithm) as mock_invoke:
        job_manager.create_algorithm(
            project_id=1,
            algorithm_name=mock_algorithm.name,
            algorithm_type=mock_algorithm.type,
        )

        mock_invoke.assert_called_once_with(
            AlgorithmsApi,
            "create_algorithm_algorithms_post",
            AlgorithmIn(
                project_id=1,
                type=mock_algorithm.type,
                shared=ShareType.PRIVATE,
                name=mock_algorithm.name,
            ),
        )


def test_run_flow_creates_new_project_and_algorithm(
    job_manager: JobManager,
    job_options: JobOptions,
    mock_project: Project,
    mock_algorithm: Algorithm,
    mock_commit: Commit,
    mock_language: Language,
    mock_file: File,
    mock_batch_job: BatchJob,
    mock_job: Job,
    tmp_path: Path,
    mocker: MockerFixture,
) -> None:
    test_file = tmp_path / "test_algorithm.cq"
    test_file.write_text("version 3.0\nqubit[2] q\nH q[0]")
    job_options.file_path = test_file
    job_options.project_id = None
    job_options.algorithm_id = None

    mock_page_language = mocker.MagicMock(spec=PageLanguage)
    mock_page_language.items = [mock_language]
    mock_page_language.total = (1,)
    mock_page_language.page = (1,)
    mock_page_language.size = 50

    with (
        patch.object(JobManager, "_invoke") as mock_invoke,
        patch.object(JobManager, "_enqueue_batch_job") as mock_enqueue_batch_job,
        patch.object(JobManager, "create_project", return_value=mock_project) as mock_create_project,
        patch.object(JobManager, "create_algorithm", return_value=mock_algorithm) as mock_create_algorithm,
    ):
        mock_invoke.side_effect = [
            mock_commit,
            mock_page_language,
            mock_file,
            mock_batch_job,
            mock_job,
            mock_batch_job,
        ]

        job_manager.run_flow(job_options)

        mock_enqueue_batch_job.assert_called_once_with(batch_job_id=mock_batch_job.id)

        mock_create_project.assert_called_once_with(
            owner_id=123, project_name=job_options.project_name, project_description=job_options.project_description
        )
        mock_create_algorithm.assert_called_once_with(
            project_id=1,
            algorithm_name=job_options.algorithm_name,
            algorithm_type=AlgorithmType.QUANTUM,
        )


def test_run_flow_with_existing_project_and_algorithm(
    job_manager: JobManager,
    job_options: JobOptions,
    mock_project: Project,
    mock_algorithm: Algorithm,
    mock_commit: Commit,
    mock_language: Language,
    mock_file: File,
    mock_batch_job: BatchJob,
    mock_job: Job,
    tmp_path: Path,
    mocker: MockerFixture,
) -> None:
    job_options.project_id = 2
    job_options.algorithm_id = 2

    test_file = tmp_path / "test_algorithm.cq"
    test_file.write_text("version 3.0\nqubit[2] q\nH q[0]")
    job_options.file_path = test_file

    mock_page_language = mocker.MagicMock(items=[mock_language], total=1, page=1, size=50)

    with (
        patch.object(JobManager, "_invoke") as mock_invoke,
        patch.object(JobManager, "_enqueue_batch_job") as mock_enqueue_batch_job,
        patch.object(JobManager, "_update_project", return_value=mock_project) as mock_update_project,
        patch.object(JobManager, "_read_algorithm", return_value=mock_algorithm) as mock_read_algorithm,
    ):
        mock_invoke.side_effect = [
            mock_commit,
            mock_page_language,
            mock_file,
            mock_batch_job,
            mock_job,
            mock_batch_job,
        ]

        job_manager.run_flow(job_options)

        mock_enqueue_batch_job.assert_called_once_with(batch_job_id=mock_batch_job.id)

        mock_update_project.assert_called_once_with(
            project_id=job_options.project_id,
            project_name=job_options.project_name,
            project_description=job_options.project_description,
        )
        mock_read_algorithm.assert_called_once_with(
            algorithm_id=job_options.algorithm_id,
        )


def test_update_project(job_manager: JobManager, mock_project: Project) -> None:
    with patch.object(JobManager, "_invoke", return_value=mock_project) as mock_invoke:
        result_project_id = 1
        result_project_name = "updated-project"
        result_project_description = "Updated description"

        job_manager._update_project(
            project_id=result_project_id,
            project_name=result_project_name,
            project_description=result_project_description,
        )

        mock_invoke.assert_called_once_with(
            ProjectsApi,
            "partial_update_project_projects_id_patch",
            result_project_id,
            ProjectPatch(name=result_project_name, description=result_project_description),
        )


def test_read_algorithm(job_manager: JobManager, mock_algorithm: Algorithm) -> None:
    with patch.object(JobManager, "_invoke", return_value=mock_algorithm) as mock_invoke:
        job_manager._read_algorithm(algorithm_id=1)

        mock_invoke.assert_called_once_with(
            AlgorithmsApi,
            "read_algorithm_algorithms_id_get",
            1,
        )


def test_create_commit(job_manager: JobManager, mock_commit: Commit) -> None:
    with patch.object(JobManager, "_invoke", return_value=mock_commit) as mock_invoke:
        job_manager._create_commit(algorithm_id=1)

        mock_invoke.assert_called_once_with(
            CommitsApi,
            "create_commit_commits_post",
            CommitIn(
                description="Commit created by SDK",
                algorithm_id=1,
            ),
        )


def test_get_language_for_algorithm_quantum(
    job_manager: JobManager, mock_language: Language, mocker: MockerFixture
) -> None:
    mock_language.name = "cqasm"
    mock_page = mocker.MagicMock(items=[mock_language], total=1, page=1, size=50)

    with patch.object(JobManager, "_invoke", return_value=mock_page):
        result = job_manager._get_language_for_algorithm(AlgorithmType.QUANTUM)

        assert result.name == "cqasm"


def test_get_language_for_algorithm_hybrid(
    job_manager: JobManager, mock_language: Language, mocker: MockerFixture
) -> None:
    mock_language.name = "python"
    mock_page = mocker.MagicMock(items=[mock_language], total=1, page=1, size=50)

    with patch.object(JobManager, "_invoke", return_value=mock_page):
        result = job_manager._get_language_for_algorithm(AlgorithmType.HYBRID)

        assert result.name == "python"


def test_get_language_for_algorithm_not_found(
    job_manager: JobManager, mock_language: Language, mocker: MockerFixture
) -> None:
    mock_language.name = "random language"
    mock_page = mocker.MagicMock(items=[mock_language], total=1, page=1, size=50)

    with patch.object(JobManager, "_invoke", return_value=mock_page):
        with pytest.raises(ValueError, match="Language .* not found in API"):
            job_manager._get_language_for_algorithm(AlgorithmType.QUANTUM)


def test_create_file(job_manager: JobManager, mock_file: File) -> None:
    with patch.object(JobManager, "_invoke", return_value=mock_file) as mock_invoke:
        file_content = "version 3.0\nqubit[2] q\nH q[0]\nCNOT q[0], q[1]"
        job_manager._create_file(
            file_content=file_content,
            language_id=1,
            commit_id=1,
        )

        mock_invoke.assert_called_once_with(
            FilesApi,
            "create_file_files_post",
            FileIn(
                commit_id=1,
                content=file_content,
                language_id=1,
                compile_stage=CompileStage.NONE,
                compile_properties={},
            ),
        )


def test_create_batch_job(job_manager: JobManager, mock_batch_job: BatchJob) -> None:
    with patch.object(JobManager, "_invoke", return_value=mock_batch_job) as mock_invoke:
        job_manager._create_batch_job(backend_type_id=1)

        mock_invoke.assert_called_once_with(
            BatchJobsApi, "create_batch_job_batch_jobs_post", BatchJobIn(backend_type_id=1)
        )


def test_create_job(job_manager: JobManager, mock_job: Job) -> None:
    with patch.object(JobManager, "_invoke", return_value=mock_job) as mock_invoke:
        job_manager._create_job(
            file_id=1,
            batch_job_id=1,
            num_shots=1024,
            raw_data_enabled=False,
        )

        mock_invoke.assert_called_once_with(
            JobsApi,
            "create_job_jobs_post",
            JobIn(file_id=1, batch_job_id=1, number_of_shots=1024, raw_data_enabled=False),
        )


def test_enqueue_batch_job(job_manager: JobManager, mock_batch_job: BatchJob) -> None:
    with patch.object(JobManager, "_invoke", return_value=mock_batch_job) as mock_invoke:
        job_manager._enqueue_batch_job(batch_job_id=1)

        mock_invoke.assert_called_once_with(BatchJobsApi, "enqueue_batch_job_batch_jobs_id_enqueue_patch", 1)
