from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, Mock, patch

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
    CompilePayload,
    CompileStage,
    File,
    FileIn,
    FilesApi,
    FinalResult,
    FinalResultsApi,
    Job,
    JobIn,
    JobsApi,
    JobStatus,
    Language,
    Project,
    ProjectIn,
    ProjectPatch,
    ProjectsApi,
    Result,
    ResultsApi,
    ShareType,
)
from compute_api_client.exceptions import ForbiddenException, NotFoundException
from pytest_mock import MockerFixture

from quantuminspire.managers.config_manager import ConfigManager
from quantuminspire.managers.resource_manager import CompileOptions, JobOptions, ResourceManager, ResourceOptions


@pytest.fixture
def config_manager() -> ConfigManager:
    mock_manager: MagicMock = MagicMock(spec=ConfigManager)
    mock_manager.get.return_value = "https://api.quantum-inspire.com"
    mock_manager.user_settings.auths = {"https://api.quantum-inspire.com": MagicMock(owner_id=123)}
    return mock_manager


@pytest.fixture
def resource_manager() -> ResourceManager:
    return ResourceManager()


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


@pytest.fixture
def compile_options(mocker: MockerFixture) -> MagicMock:
    mock: MagicMock = mocker.MagicMock(spec=CompileOptions)
    mock.project_name = "Dummy project"
    mock.project_description = "Dummy project description"
    mock.algorithm_name = "Dummy algorithm"
    mock.algorithm_id = 1
    mock.backend_type_id = 2
    mock.compile_stage = CompileStage.NONE
    return mock


@pytest.fixture
def mock_results() -> list[MagicMock]:
    return [
        MagicMock(spec=Result, id=1),
        MagicMock(spec=Result, id=2),
    ]


def test_invoke(resource_manager: ResourceManager, mocker: MockerFixture) -> None:
    mock_result = mocker.MagicMock()
    mock_api_method = mocker.AsyncMock(return_value=mock_result)
    mock_api_instance = mocker.MagicMock()
    setattr(mock_api_instance, "some_method", mock_api_method)

    mock_api_class = mocker.MagicMock(return_value=mock_api_instance)
    mock_client = mocker.MagicMock()
    mock_config = mocker.MagicMock()

    with (
        patch("quantuminspire.managers.resource_manager.ApiClient") as mock_api_client_class,
        patch("quantuminspire.managers.resource_manager.config", return_value=mock_config) as mock_config_func,
    ):
        mock_api_client_class.return_value.__aenter__.return_value = mock_client

        result = ResourceManager._invoke(mock_api_class, "some_method", None, "arg1", "arg2", kwarg1="value1")

        mock_config_func.assert_called_once()
        mock_api_class.assert_called_once_with(mock_client)
        mock_api_method.assert_called_once_with("arg1", "arg2", kwarg1="value1")
        assert result == mock_result


def test_invoke_with_page_reader(resource_manager: ResourceManager, mocker: MockerFixture) -> None:
    mock_result = mocker.MagicMock()
    mock_get_all = mocker.AsyncMock(return_value=mock_result)
    mock_page_reader = mocker.MagicMock()
    mock_page_reader.get_all = mock_get_all

    mock_api_method = mocker.AsyncMock()
    mock_api_instance = mocker.MagicMock()
    setattr(mock_api_instance, "some_method", mock_api_method)

    mock_api_class = mocker.MagicMock(return_value=mock_api_instance)
    mock_client = mocker.MagicMock()
    mock_config = mocker.MagicMock()

    with (
        patch("quantuminspire.managers.resource_manager.ApiClient") as mock_api_client_class,
        patch("quantuminspire.managers.resource_manager.config", return_value=mock_config) as mock_config_func,
    ):
        mock_api_client_class.return_value.__aenter__.return_value = mock_client

        result = ResourceManager._invoke(mock_api_class, "some_method", mock_page_reader, "arg1", kwarg1="value1")

        mock_config_func.assert_called_once()
        mock_api_class.assert_called_once_with(mock_client)
        mock_api_method.assert_not_called()
        mock_get_all.assert_called_once_with(mock_api_method, kwarg1="value1")
        assert result == mock_result


def test_get_results(resource_manager: ResourceManager, mock_results: list[MagicMock], mocker: MockerFixture) -> None:
    mock_page_reader_instance = mocker.MagicMock()

    with (
        patch.object(ResourceManager, "_invoke", return_value=mock_results) as mock_invoke,
        patch("quantuminspire.managers.resource_manager.PageReader") as mock_page_reader_class,
    ):
        mock_page_reader_class.__getitem__.return_value.return_value = mock_page_reader_instance

        result = resource_manager.get_results(job_id=1)

        mock_invoke.assert_called_once_with(
            ResultsApi,
            "read_results_by_job_id_results_job_job_id_get",
            mock_page_reader_instance,
            job_id=1,
        )
        assert result == mock_results


def test_get_backend_types(
    resource_manager: ResourceManager, mock_backend_type: BackendType, mocker: MockerFixture
) -> None:
    mock_page = mocker.MagicMock(items=[mock_backend_type], total=1, page=1, size=50)

    with patch.object(ResourceManager, "_invoke", return_value=mock_page) as mock_invoke:
        result = resource_manager.get_backend_types()

        mock_invoke.assert_called_once_with(
            BackendTypesApi,
            "read_backend_types_backend_types_get",
            None,
        )
        assert result[0] == mock_backend_type


def test_get_job(resource_manager: ResourceManager, mock_job: Job) -> None:
    with patch.object(ResourceManager, "_invoke", return_value=mock_job) as mock_invoke:
        resource_manager.get_job(job_id=1)

        mock_invoke.assert_called_once_with(
            JobsApi,
            "read_job_jobs_id_get",
            None,
            id=1,
        )


def test_wait_for_job_completion_success(resource_manager: ResourceManager) -> None:
    # Arrange
    job_id = 1
    completed_job = Mock(spec=Job)
    completed_job.id = job_id
    completed_job.status = JobStatus.COMPLETED

    with patch.object(resource_manager, "get_job", return_value=completed_job):
        # Act
        result = resource_manager.wait_for_job_completion(job_id, timeout=10)

        # Assert
        assert result == completed_job


def test_wait_for_job_completion_timeout(resource_manager: ResourceManager) -> None:
    # Arrange
    job_id = 1
    running_job = Mock(spec=Job)
    running_job.id = job_id
    running_job.status = JobStatus.RUNNING

    with (
        patch.object(resource_manager, "get_job", return_value=running_job),
        patch("time.sleep"),
    ):
        # Act & Assert
        with pytest.raises(TimeoutError, match=f"Job {job_id} did not complete within 1 seconds"):
            resource_manager.wait_for_job_completion(job_id, timeout=1)


def test_get_final_result(resource_manager: ResourceManager, mock_final_result: FinalResult) -> None:
    with patch.object(ResourceManager, "_invoke", return_value=mock_final_result) as mock_invoke:
        resource_manager.get_final_result(job_id=1)

        mock_invoke.assert_called_once_with(
            FinalResultsApi,
            "read_final_result_by_job_id_final_results_job_job_id_get",
            None,
            1,
        )


def test_get_algorithm_type_hybrid() -> None:
    file_path = Path("test_algorithm.py")
    result = ResourceManager.get_algorithm_type(file_path)

    assert result == AlgorithmType.HYBRID


def test_get_algorithm_type_quantum() -> None:
    file_path = Path("test_algorithm.cq")
    result = ResourceManager.get_algorithm_type(file_path)

    assert result == AlgorithmType.QUANTUM


def test_get_algorithm_type_invalid_extension() -> None:
    file_path = Path("test_algorithm.txt")

    with pytest.raises(ValueError, match="Incorrect file type. Supported types are .py and .cq"):
        ResourceManager.get_algorithm_type(file_path)


def test_create_project(resource_manager: ResourceManager, mock_project: Project) -> None:
    with patch.object(ResourceManager, "_invoke", return_value=mock_project) as mock_invoke:
        resource_manager.create_project(
            owner_id=123,
            project_name=mock_project.name,
            project_description=mock_project.description,
        )

        mock_invoke.assert_called_once_with(
            ProjectsApi,
            "create_project_projects_post",
            None,
            ProjectIn(
                owner_id=123,
                name=mock_project.name,
                description=mock_project.description,
                starred=False,
            ),
        )


def test_create_algorithm(resource_manager: ResourceManager, mock_algorithm: Algorithm) -> None:
    with patch.object(ResourceManager, "_invoke", return_value=mock_algorithm) as mock_invoke:
        resource_manager.create_algorithm(
            project_id=1,
            algorithm_name=mock_algorithm.name,
            algorithm_type=mock_algorithm.type,
        )

        mock_invoke.assert_called_once_with(
            AlgorithmsApi,
            "create_algorithm_algorithms_post",
            None,
            AlgorithmIn(
                project_id=1,
                type=mock_algorithm.type,
                shared=ShareType.PRIVATE,
                name=mock_algorithm.name,
            ),
        )


def test_run_job_submission_flow(
    resource_manager: ResourceManager,
    job_options: JobOptions,
    mock_commit: Commit,
    mock_file: File,
    mock_batch_job: BatchJob,
    mock_job: Job,
) -> None:
    with (
        patch.object(ResourceManager, "run_create_commit_flow", return_value=mock_commit) as mock_commit_flow,
        patch.object(ResourceManager, "run_create_file_flow", return_value=mock_file) as mock_file_flow,
        patch.object(ResourceManager, "_create_batch_job", return_value=mock_batch_job) as mock_create_batch_job,
        patch.object(ResourceManager, "_create_job", return_value=mock_job) as mock_create_job,
        patch.object(ResourceManager, "_enqueue_batch_job") as mock_enqueue_batch_job,
    ):
        result = resource_manager.run_job_submission_flow(job_options, owner_id=123)

        mock_commit_flow.assert_called_once_with(resource_options=job_options, owner_id=123)
        mock_file_flow.assert_called_once_with(resource_options=job_options, commit_id=mock_commit.id)
        mock_create_batch_job.assert_called_once_with(backend_type_id=job_options.backend_type_id)
        mock_create_job.assert_called_once_with(
            file_id=mock_file.id,
            batch_job_id=mock_batch_job.id,
            num_shots=job_options.number_of_shots,
            raw_data_enabled=job_options.raw_data_enabled,
        )
        mock_enqueue_batch_job.assert_called_once_with(batch_job_id=mock_batch_job.id)
        assert result.job_id == mock_job.id


def test_run_create_commit_flow_no_project_no_algorithm(
    resource_manager: ResourceManager,
    mock_project: Project,
    mock_algorithm: Algorithm,
    mock_commit: Commit,
    tmp_path: Path,
) -> None:
    test_file = tmp_path / "test_algorithm.cq"
    test_file.write_text("version 3.0\nqubit[2] q\nH q[0]")

    resource_options = ResourceOptions(
        project_id=None,
        algorithm_id=None,
        project_name="Dummy project",
        project_description="Dummy project description",
        algorithm_name="Dummy algorithm",
        file_path=test_file,
    )

    with (
        patch.object(ResourceManager, "create_project", return_value=mock_project) as mock_create_project,
        patch.object(ResourceManager, "create_algorithm", return_value=mock_algorithm) as mock_create_algorithm,
        patch.object(ResourceManager, "_create_commit", return_value=mock_commit) as mock_create_commit,
    ):
        result = resource_manager.run_create_commit_flow(resource_options, owner_id=123)

        mock_create_project.assert_called_once_with(
            owner_id=123,
            project_name="Dummy project",
            project_description="Dummy project description",
        )
        mock_create_algorithm.assert_called_once_with(
            project_id=mock_project.id,
            algorithm_name="Dummy algorithm",
            algorithm_type=AlgorithmType.QUANTUM,
        )
        mock_create_commit.assert_called_once_with(algorithm_id=mock_algorithm.id)
        assert result == mock_commit


def test_run_create_commit_flow_updates_existing_project_and_algorithm(
    resource_manager: ResourceManager,
    mock_project: Project,
    mock_algorithm: Algorithm,
    mock_commit: Commit,
    tmp_path: Path,
) -> None:
    test_file = tmp_path / "test_algorithm.cq"
    test_file.write_text("version 3.0\nqubit[2] q\nH q[0]")

    resource_options = ResourceOptions(
        project_id=1,
        algorithm_id=1,
        project_name="Dummy project",
        project_description="Dummy project description",
        algorithm_name="Dummy algorithm",
        file_path=test_file,
    )

    with (
        patch.object(ResourceManager, "read_project", return_value=mock_project),
        patch.object(ResourceManager, "update_project", return_value=mock_project) as mock_update_project,
        patch.object(ResourceManager, "read_algorithm", return_value=mock_algorithm),
        patch.object(ResourceManager, "update_algorithm", return_value=mock_algorithm) as mock_update_algorithm,
        patch.object(ResourceManager, "_create_commit", return_value=mock_commit),
    ):
        result = resource_manager.run_create_commit_flow(resource_options, owner_id=123)

        mock_update_project.assert_called_once_with(
            project_id=1,
            project_name="Dummy project",
            project_description="Dummy project description",
        )
        mock_update_algorithm.assert_called_once_with(
            project_id=1,
            algorithm_id=1,
            algorithm_name="Dummy algorithm",
            algorithm_type=AlgorithmType.QUANTUM,
        )
        assert result == mock_commit


def test_run_create_commit_flow_project_not_found_remotely(
    resource_manager: ResourceManager,
    mock_project: Project,
    mock_algorithm: Algorithm,
    mock_commit: Commit,
    tmp_path: Path,
) -> None:
    test_file = tmp_path / "test_algorithm.cq"
    test_file.write_text("version 3.0\nqubit[2] q\nH q[0]")

    resource_options = ResourceOptions(
        project_id=99,
        algorithm_id=None,
        project_name="Dummy project",
        project_description="Dummy project description",
        algorithm_name="Dummy algorithm",
        file_path=test_file,
    )

    with (
        patch.object(ResourceManager, "read_project", return_value=None),
        patch.object(ResourceManager, "create_project", return_value=mock_project) as mock_create_project,
        patch.object(ResourceManager, "create_algorithm", return_value=mock_algorithm) as mock_create_algorithm,
        patch.object(ResourceManager, "_create_commit", return_value=mock_commit),
    ):
        resource_manager.run_create_commit_flow(resource_options, owner_id=123)

        mock_create_project.assert_called_once_with(
            owner_id=123,
            project_name="Dummy project",
            project_description="Dummy project description",
        )
        mock_create_algorithm.assert_called_once_with(
            project_id=mock_project.id,
            algorithm_name="Dummy algorithm",
            algorithm_type=AlgorithmType.QUANTUM,
        )


def test_run_create_commit_flow_algorithm_not_found_remotely(
    resource_manager: ResourceManager,
    mock_project: Project,
    mock_algorithm: Algorithm,
    mock_commit: Commit,
    tmp_path: Path,
) -> None:
    test_file = tmp_path / "test_algorithm.cq"
    test_file.write_text("version 3.0\nqubit[2] q\nH q[0]")

    resource_options = ResourceOptions(
        project_id=1,
        algorithm_id=99,
        project_name="Dummy project",
        project_description="Dummy project description",
        algorithm_name="Dummy algorithm",
        file_path=test_file,
    )

    with (
        patch.object(ResourceManager, "read_project", return_value=mock_project),
        patch.object(ResourceManager, "update_project", return_value=mock_project),
        patch.object(ResourceManager, "read_algorithm", return_value=None),
        patch.object(ResourceManager, "create_algorithm", return_value=mock_algorithm) as mock_create_algorithm,
        patch.object(ResourceManager, "_create_commit", return_value=mock_commit),
    ):
        resource_manager.run_create_commit_flow(resource_options, owner_id=123)

        mock_create_algorithm.assert_called_once_with(
            project_id=resource_options.project_id,
            algorithm_name="Dummy algorithm",
            algorithm_type=AlgorithmType.QUANTUM,
        )


def test_run_create_file_flow(
    resource_manager: ResourceManager,
    mock_language: Language,
    mock_file: File,
    tmp_path: Path,
) -> None:
    file_content = "version 3.0\nqubit[2] q\nH q[0]"
    test_file = tmp_path / "test_algorithm.cq"
    test_file.write_text(file_content)

    resource_options = ResourceOptions(
        project_name="Dummy project",
        project_description="Dummy project description",
        algorithm_name="Dummy algorithm",
        file_path=test_file,
    )

    with (
        patch.object(ResourceManager, "_get_language_for_algorithm", return_value=mock_language),
        patch.object(ResourceManager, "_create_file", return_value=mock_file) as mock_create_file,
    ):
        result = resource_manager.run_create_file_flow(resource_options, commit_id=1)

        mock_create_file.assert_called_once_with(
            file_content=file_content,
            language_id=mock_language.id,
            commit_id=1,
        )
        assert result == mock_file


def test_run_compile_file_flow_success(
    resource_manager: ResourceManager,
    compile_options: CompileOptions,
    mock_commit: Commit,
    mock_file: File,
    tmp_path: Path,
    mocker: MockerFixture,
) -> None:
    test_file = tmp_path / "test_algorithm.cq"
    test_file.write_text("version 3.0\nqubit[2] q\nH q[0]")
    compile_options.file_path = test_file

    compiled_file_mock = mocker.MagicMock(spec=File)
    compiled_file_mock.name = "_compiled"
    compiled_file_mock.content = "compiled content"

    mock_commit_files = mocker.MagicMock()
    mock_commit_files.items = [compiled_file_mock]

    with (
        patch.object(ResourceManager, "run_create_commit_flow", return_value=mock_commit),
        patch.object(ResourceManager, "run_create_file_flow", return_value=mock_file),
        patch.object(ResourceManager, "_invoke") as mock_invoke,
    ):
        mock_invoke.side_effect = [None, mock_commit_files]

        resource_manager.run_compile_file_flow(compile_options, owner_id=123)

        mock_invoke.assert_any_call(
            CommitsApi,
            "compile_commit_commits_id_compile_post",
            None,
            mock_commit.id,
            CompilePayload(
                compile_stage=compile_options.compile_stage,
                backend_type_id=compile_options.backend_type_id,
            ),
        )
        mock_invoke.assert_any_call(
            FilesApi,
            "read_files_files_get",
            None,
            commit_id=mock_commit.id,
            generated=True,
        )

        expected_file_name = f"{test_file.with_suffix('')}{compiled_file_mock.name}{test_file.suffix}"
        assert Path(expected_file_name).read_text() == "compiled content"


def test_run_compile_file_flow_no_compiled_file(
    resource_manager: ResourceManager,
    compile_options: CompileOptions,
    mock_commit: Commit,
    mock_file: File,
    mocker: MockerFixture,
) -> None:
    mock_commit_files = mocker.MagicMock()
    mock_commit_files.items = []

    with (
        patch.object(ResourceManager, "run_create_commit_flow", return_value=mock_commit),
        patch.object(ResourceManager, "run_create_file_flow", return_value=mock_file),
        patch.object(ResourceManager, "_invoke") as mock_invoke,
    ):
        mock_invoke.side_effect = [None, mock_commit_files]

        with pytest.raises(RuntimeError, match="No compiled file was generated for the commit"):
            resource_manager.run_compile_file_flow(compile_options, owner_id=123)


def test_update_project(resource_manager: ResourceManager, mock_project: Project) -> None:
    with patch.object(ResourceManager, "_invoke", return_value=mock_project) as mock_invoke:
        result_project_id = 1
        result_project_name = "updated-project"
        result_project_description = "Updated description"

        resource_manager.update_project(
            project_id=result_project_id,
            project_name=result_project_name,
            project_description=result_project_description,
        )

        mock_invoke.assert_called_once_with(
            ProjectsApi,
            "partial_update_project_projects_id_patch",
            None,
            result_project_id,
            ProjectPatch(name=result_project_name, description=result_project_description),
        )


def test_read_project(resource_manager: ResourceManager, mock_project: Project) -> None:
    with patch.object(ResourceManager, "_invoke", return_value=mock_project) as mock_invoke:
        resource_manager.read_project(project_id=1)

        mock_invoke.assert_called_once_with(
            ProjectsApi,
            "read_project_projects_id_get",
            None,
            1,
        )


@pytest.mark.parametrize(
    "side_effect",
    [
        NotFoundException,
        ForbiddenException,
    ],
)
def test_read_project_exception(resource_manager: ResourceManager, mock_project: Project, side_effect: Any) -> None:
    with patch.object(ResourceManager, "_invoke", side_effect=side_effect) as mock_invoke:
        result = resource_manager.read_project(project_id=1)

        mock_invoke.assert_called_once_with(
            ProjectsApi,
            "read_project_projects_id_get",
            None,
            1,
        )
        assert result is None


def test_read_algorithm(resource_manager: ResourceManager, mock_algorithm: Algorithm) -> None:
    with patch.object(ResourceManager, "_invoke", return_value=mock_algorithm) as mock_invoke:
        resource_manager.read_algorithm(algorithm_id=1)

        mock_invoke.assert_called_once_with(
            AlgorithmsApi,
            "read_algorithm_algorithms_id_get",
            None,
            1,
        )


@pytest.mark.parametrize(
    "side_effect",
    [
        NotFoundException,
        ForbiddenException,
    ],
)
def test_read_algorithm_exception(
    resource_manager: ResourceManager, side_effect: Any, mock_algorithm: Algorithm
) -> None:
    with patch.object(ResourceManager, "_invoke", side_effect=side_effect) as mock_invoke:
        result = resource_manager.read_algorithm(algorithm_id=1)

        mock_invoke.assert_called_once_with(
            AlgorithmsApi,
            "read_algorithm_algorithms_id_get",
            None,
            1,
        )
        assert result is None


def test_update_algorithm(resource_manager: ResourceManager, mock_algorithm: Algorithm) -> None:
    with patch.object(ResourceManager, "_invoke", return_value=mock_algorithm) as mock_invoke:
        resource_manager.update_algorithm(
            project_id=1,
            algorithm_id=mock_algorithm.id,
            algorithm_name=mock_algorithm.name,
            algorithm_type=mock_algorithm.type,
        )

        mock_invoke.assert_called_once_with(
            AlgorithmsApi,
            "update_algorithm_algorithms_id_put",
            None,
            mock_algorithm.id,
            AlgorithmIn(
                project_id=1,
                type=mock_algorithm.type,
                shared=ShareType.PRIVATE,
                name=mock_algorithm.name,
            ),
        )


def test_create_commit(resource_manager: ResourceManager, mock_commit: Commit) -> None:
    with patch.object(ResourceManager, "_invoke", return_value=mock_commit) as mock_invoke:
        resource_manager._create_commit(algorithm_id=1)

        mock_invoke.assert_called_once_with(
            CommitsApi,
            "create_commit_commits_post",
            None,
            CommitIn(
                description="Commit created by SDK",
                algorithm_id=1,
            ),
        )


def test_get_language_for_algorithm_quantum(
    resource_manager: ResourceManager, mock_language: Language, mocker: MockerFixture
) -> None:
    mock_language.name = "cqasm"
    mock_page = mocker.MagicMock(items=[mock_language], total=1, page=1, size=50)

    with patch.object(ResourceManager, "_invoke", return_value=mock_page):
        result = resource_manager._get_language_for_algorithm(AlgorithmType.QUANTUM)

        assert result.name == "cqasm"


def test_get_language_for_algorithm_hybrid(
    resource_manager: ResourceManager, mock_language: Language, mocker: MockerFixture
) -> None:
    mock_language.name = "python"
    mock_page = mocker.MagicMock(items=[mock_language], total=1, page=1, size=50)

    with patch.object(ResourceManager, "_invoke", return_value=mock_page):
        result = resource_manager._get_language_for_algorithm(AlgorithmType.HYBRID)

        assert result.name == "python"


def test_get_language_for_algorithm_not_found(
    resource_manager: ResourceManager, mock_language: Language, mocker: MockerFixture
) -> None:
    mock_language.name = "random language"
    mock_page = mocker.MagicMock(items=[mock_language], total=1, page=1, size=50)

    with patch.object(ResourceManager, "_invoke", return_value=mock_page):
        with pytest.raises(ValueError, match="Language .* not found in API"):
            resource_manager._get_language_for_algorithm(AlgorithmType.QUANTUM)


def test_create_file(resource_manager: ResourceManager, mock_file: File) -> None:
    with patch.object(ResourceManager, "_invoke", return_value=mock_file) as mock_invoke:
        file_content = "version 3.0\nqubit[2] q\nH q[0]\nCNOT q[0], q[1]"
        resource_manager._create_file(
            file_content=file_content,
            language_id=1,
            commit_id=1,
        )

        mock_invoke.assert_called_once_with(
            FilesApi,
            "create_file_files_post",
            None,
            FileIn(
                commit_id=1,
                content=file_content,
                language_id=1,
                compile_stage=CompileStage.NONE,
                compile_properties={},
            ),
        )


def test_create_batch_job(resource_manager: ResourceManager, mock_batch_job: BatchJob) -> None:
    with patch.object(ResourceManager, "_invoke", return_value=mock_batch_job) as mock_invoke:
        resource_manager._create_batch_job(backend_type_id=1)

        mock_invoke.assert_called_once_with(
            BatchJobsApi, "create_batch_job_batch_jobs_post", None, BatchJobIn(backend_type_id=1)
        )


def test_create_job(resource_manager: ResourceManager, mock_job: Job) -> None:
    with patch.object(ResourceManager, "_invoke", return_value=mock_job) as mock_invoke:
        resource_manager._create_job(
            file_id=1,
            batch_job_id=1,
            num_shots=1024,
            raw_data_enabled=False,
        )

        mock_invoke.assert_called_once_with(
            JobsApi,
            "create_job_jobs_post",
            None,
            JobIn(file_id=1, batch_job_id=1, number_of_shots=1024, raw_data_enabled=False),
        )


def test_enqueue_batch_job(resource_manager: ResourceManager, mock_batch_job: BatchJob) -> None:
    with patch.object(ResourceManager, "_invoke", return_value=mock_batch_job) as mock_invoke:
        resource_manager._enqueue_batch_job(batch_job_id=1)

        mock_invoke.assert_called_once_with(BatchJobsApi, "enqueue_batch_job_batch_jobs_id_enqueue_patch", None, 1)
