from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, call, patch

import pytest
from compute_api_client import Job, JobStatus
from pytest_mock import MockerFixture

from quantuminspire.managers.algorithm_execution_manager import AlgorithmExecutionManager
from quantuminspire.managers.job_manager import JobOptions
from quantuminspire.settings.models import LocalAlgorithm


@pytest.fixture
def mock_api(mocker: MockerFixture) -> MagicMock:
    mock: MagicMock = mocker.MagicMock()
    return mock


@pytest.fixture
def mock_config_manager(mocker: MockerFixture) -> MagicMock:
    mock: MagicMock = mocker.MagicMock()
    mock.initialize.return_value = None
    return mock


@pytest.fixture
def mock_user_settings(mocker: MockerFixture) -> MagicMock:
    mock: MagicMock = mocker.MagicMock()
    return mock


@pytest.fixture
def mock_project_settings(mocker: MockerFixture) -> MagicMock:
    mock: MagicMock = mocker.MagicMock()
    return mock


@pytest.fixture
def mock_get_setting() -> Any:
    def _get_setting(key: str) -> Any:
        return {
            "project.id": 1,
            "project.algorithms": {"Some other algorithm": {}},
        }.get(key)

    return _get_setting


@pytest.fixture
def mock_get_algorithm_setting() -> Any:
    def _get_algorithm_setting(algorithm_name: str, key: str) -> Any:
        algorithms = {
            "Some algorithm": {
                "backend_type": 1,
                "job_id": 243,
            },
            "Algorithm no backend": {},
        }
        return algorithms[algorithm_name].get(key)

    return _get_algorithm_setting


@pytest.fixture
def algorithm_execution_manager(
    mock_api: MagicMock,
    mock_config_manager: MagicMock,
    mock_user_settings: MagicMock,
    mock_project_settings: MagicMock,
) -> AlgorithmExecutionManager:
    with (
        patch("quantuminspire.managers.algorithm_execution_manager.ConfigManager") as mock_config_cls,
        patch("quantuminspire.managers.algorithm_execution_manager.UserSettings") as mock_user_cls,
        patch("quantuminspire.managers.algorithm_execution_manager.ProjectSettings") as mock_project_cls,
        patch("quantuminspire.managers.algorithm_execution_manager.Api") as mock_api_cls,
    ):

        mock_config_cls.return_value = mock_config_manager
        mock_config_cls.initialize = MagicMock()
        mock_user_cls.return_value = mock_user_settings
        mock_project_cls.return_value = mock_project_settings
        mock_api_cls.return_value = mock_api

        manager = AlgorithmExecutionManager()
        manager._api = mock_api
        manager._config_manager = mock_config_manager
        manager._user_settings = mock_user_settings
        manager._project_settings = mock_project_settings

        return manager


def test_initialize_algorithm_execution_manager() -> None:
    with (
        patch("quantuminspire.managers.algorithm_execution_manager.ConfigManager") as mock_config_cls,
        patch("quantuminspire.managers.algorithm_execution_manager.UserSettings") as mock_user_cls,
        patch("quantuminspire.managers.algorithm_execution_manager.ProjectSettings") as mock_project_cls,
        patch("quantuminspire.managers.algorithm_execution_manager.Api") as mock_api_cls,
    ):

        mock_initialize = MagicMock()
        mock_config_cls.initialize = mock_initialize

        mock_config_instance = MagicMock()
        mock_config_cls.return_value = mock_config_instance

        mock_user_instance = MagicMock()
        mock_user_cls.return_value = mock_user_instance

        mock_api_instance = MagicMock()
        mock_api_cls.return_value = mock_api_instance

        AlgorithmExecutionManager()

        mock_initialize.assert_called_once_with(Path.cwd())
        mock_user_cls.assert_called_once_with(default_host="https://staging.qi2.quantum-inspire.com")
        mock_config_cls.assert_called_once_with(user_settings=mock_user_instance)
        mock_project_cls.assert_called_once()

        mock_api_cls.assert_called_once_with(config_manager=mock_config_instance)
        mock_api_instance.login.assert_called_once()


def test_execute_algorithm(
    algorithm_execution_manager: AlgorithmExecutionManager, mock_api: MagicMock, mocker: MockerFixture
) -> None:
    mocker.patch.object(algorithm_execution_manager, "check_project_id")

    algorithm_name = "Some algorithm"
    file_name = "some_file.py"
    mock_api.get_setting.return_value = {algorithm_name: {}}

    algorithm_execution_manager.init_project("Dummy project")

    expected_job_options = JobOptions(
        file_path=Path(file_name),
        project_id=1,
        project_name="TestProject",
        project_description="Test description",
        backend_type_id=1,
        number_of_shots=100,
        raw_data_enabled=True,
        algorithm_name=algorithm_name,
        job_id=1,
    )
    mock_api.submit_job.return_value = expected_job_options

    # Act
    result = algorithm_execution_manager.execute_algorithm(
        file_name, algorithm_name=algorithm_name, backend_type_id=1, persist=True
    )

    # Assert
    mock_api.submit_job.assert_called_once_with(
        file_path=file_name,
        algorithm_name=algorithm_name,
        backend_type_id=1,
        num_shots=None,
        store_raw_data=False,
        persist=True,
    )
    assert result == expected_job_options


def test_execute_algorithm_with_persist_true_and_no_algorithm_name(
    algorithm_execution_manager: AlgorithmExecutionManager,
) -> None:
    with pytest.raises(
        ValueError,
        match="algorithm_name is required when you want to persist the data. "
        "Please add it to the function call of execute_algorithm()",
    ):
        algorithm_execution_manager.execute_algorithm(
            "some_file.py",
            backend_type_id=1,
            persist=True,
        )


def test_execute_algorithm_with_persist_true_creates_algorithm_if_not_exists(
    algorithm_execution_manager: AlgorithmExecutionManager, mock_api: MagicMock
) -> None:
    algorithm_name = "Some algorithm"
    file_name = "some_file.py"

    mock_api.get_setting.return_value = {"Some other algorithm": {}}
    with patch.object(algorithm_execution_manager, "init_algorithm") as mock_init_algorithm:

        algorithm_execution_manager.init_project("Dummy project")
        algorithm_execution_manager.execute_algorithm(
            file_name, algorithm_name=algorithm_name, backend_type_id=1, persist=True
        )

        mock_init_algorithm.assert_called_once_with(algorithm_name=algorithm_name, file_path=file_name)


def test_algorithm_with_persist_falser(
    algorithm_execution_manager: AlgorithmExecutionManager, mock_api: MagicMock, mocker: MockerFixture
) -> None:
    file_name = "some_file.py"

    algorithm_execution_manager.execute_algorithm(
        file_name,
        backend_type_id=1,
        persist=False,
    )

    mock_api.submit_job.assert_called_once_with(
        file_path=file_name, algorithm_name=None, backend_type_id=1, num_shots=None, store_raw_data=False, persist=False
    )


def test_init_project_no_project_id(
    algorithm_execution_manager: AlgorithmExecutionManager, mock_api: MagicMock, mocker: MockerFixture
) -> None:
    project_name = "Dummy project"
    project_description = "Dummy description"

    mock_remote_project = MagicMock(id=1, name=project_name, description=project_description)

    mocker.patch.object(
        algorithm_execution_manager, "check_project_id", side_effect=RuntimeError("No project initialized")
    )

    mock_api.initialize_remote_project.return_value = mock_remote_project

    algorithm_execution_manager.init_project(project_name, project_description)
    expected_calls = [
        call("project.id", mock_remote_project.id),
        call("project.name", mock_remote_project.name),
        call("project.description", mock_remote_project.description),
        call("project.algorithms", {}),
    ]

    mock_api.initialize_remote_project.assert_called_once_with(project_name, project_description)
    mock_api.set_setting.assert_has_calls(expected_calls, any_order=True)


def test_init_project(
    algorithm_execution_manager: AlgorithmExecutionManager, mock_api: MagicMock, mocker: MockerFixture
) -> None:
    project_name = "Dummy project"
    project_description = "Dummy description"

    mocker.patch.object(
        algorithm_execution_manager,
        "check_project_id",
    )

    algorithm_execution_manager.init_project(project_name, project_description)


def test_empty_algorithm_name_raises_error(algorithm_execution_manager: AlgorithmExecutionManager) -> None:
    with pytest.raises(ValueError, match="Algorithm name cannot be empty"):
        algorithm_execution_manager.check_algorithm_name_validity("")

    with pytest.raises(ValueError, match="Algorithm name cannot be empty"):
        algorithm_execution_manager.check_algorithm_name_validity(" ")


@pytest.mark.parametrize(
    "invalid_chars",
    [
        'name with "',
        "name with \\",
    ],
)
def test_algorithm_name_with_double_quotes_raises_error(
    algorithm_execution_manager: AlgorithmExecutionManager, invalid_chars: str
) -> None:
    with pytest.raises(ValueError, match="Algorithm name cannot contain double quotes or backslashes"):
        algorithm_execution_manager.check_algorithm_name_validity(invalid_chars)


def test_algorithm_name_with_control_characters_raises_error(
    algorithm_execution_manager: AlgorithmExecutionManager,
) -> None:
    with pytest.raises(ValueError, match="Algorithm name cannot contain control characters"):
        algorithm_execution_manager.check_algorithm_name_validity("name with control char \x01")


@pytest.mark.parametrize(
    "valid_name",
    [
        "simple_name",
        "name-with-dashes",
        "name.with.dots",
        "Name With Spaces",
        "name123",
        "CamelCaseName",
    ],
)
def test_valid_algorithm_names(algorithm_execution_manager: AlgorithmExecutionManager, valid_name: str) -> None:
    algorithm_execution_manager.check_algorithm_name_validity(valid_name)


def test_init_algorithm(
    algorithm_execution_manager: AlgorithmExecutionManager,
    mock_api: MagicMock,
    mock_get_setting: Any,
    mocker: MockerFixture,
) -> None:
    check_project_id = mocker.patch.object(algorithm_execution_manager, "check_project_id")
    check_algorithm_name_validity = mocker.patch.object(algorithm_execution_manager, "check_algorithm_name_validity")
    mock_api.get_setting.side_effect = mock_get_setting

    algorithm_name = "Some algorithm"
    file_path = "some_file.py"
    project_id = mock_get_setting("project.id")

    mock_remote_algorithm = MagicMock(id=1)
    local_algorithm = LocalAlgorithm(
        id=mock_remote_algorithm.id,
        file_path=file_path,
    )

    mock_api.create_remote_algorithm.return_value = mock_remote_algorithm

    algorithm_execution_manager.init_algorithm(algorithm_name, file_path)

    check_project_id.assert_called_once()
    check_algorithm_name_validity.assert_called_once_with(algorithm_name)
    mock_api.create_remote_algorithm.assert_called_once_with(project_id, algorithm_name, file_path)
    mock_api.add_algorithm_to_settings.assert_called_once_with(algorithm_name, local_algorithm)


def test_get_status(
    algorithm_execution_manager: AlgorithmExecutionManager, mock_api: MagicMock, mock_get_algorithm_setting: Any
) -> None:
    mock_api.get_algorithm_setting.side_effect = mock_get_algorithm_setting

    algorithm_name = "Some algorithm"
    job_id = mock_get_algorithm_setting(algorithm_name, "job_id")
    expected_status = JobStatus.COMPLETED
    mock_api.get_job.return_value = MagicMock(status=expected_status)

    status = algorithm_execution_manager.get_status(algorithm_name)
    mock_api.get_job.assert_called_once_with(job_id)
    assert status == expected_status


def test_get_status_with_wait_and_timeout(
    algorithm_execution_manager: AlgorithmExecutionManager, mock_api: MagicMock, mock_get_algorithm_setting: Any
) -> None:
    mock_api.get_algorithm_setting.side_effect = mock_get_algorithm_setting

    algorithm_name = "Some algorithm"
    job_id = mock_get_algorithm_setting(algorithm_name, "job_id")
    mock_job = MagicMock(spec=Job)
    mock_job.status = JobStatus.COMPLETED
    mock_api.wait_for_job_completion.return_value = mock_job

    status = algorithm_execution_manager.get_status(algorithm_name, wait=True, timeout=5)
    mock_api.wait_for_job_completion.assert_called_once_with(job_id, timeout=5)
    assert status == mock_job.status


def test_get_status_with_wait_and_timeout_exceeds_timeout(
    algorithm_execution_manager: AlgorithmExecutionManager, mock_api: MagicMock, mock_get_algorithm_setting: Any
) -> None:
    mock_api.get_algorithm_setting.side_effect = mock_get_algorithm_setting

    algorithm_name = "Some algorithm"
    job_id = mock_get_algorithm_setting(algorithm_name, "job_id")
    mock_api.wait_for_job_completion.side_effect = TimeoutError

    algorithm_execution_manager.get_status(algorithm_name, True, 5)

    mock_api.get_job.assert_called_once_with(job_id)


def test_get_final_result(
    algorithm_execution_manager: AlgorithmExecutionManager, mock_api: MagicMock, mock_get_algorithm_setting: Any
) -> None:
    mock_api.get_algorithm_setting.side_effect = mock_get_algorithm_setting

    algorithm_name = "Some algorithm"
    job_id = mock_get_algorithm_setting(algorithm_name, "job_id")
    expected_result = MagicMock()
    mock_api.get_final_result.return_value = expected_result

    final_result = algorithm_execution_manager.get_final_result(algorithm_name)
    mock_api.get_final_result.assert_called_once_with(job_id)
    assert final_result == expected_result


def test_check_project_id_with_valid_project(
    algorithm_execution_manager: AlgorithmExecutionManager, mock_api: MagicMock, mock_get_setting: Any
) -> None:
    mock_api.get_setting.side_effect = mock_get_setting
    algorithm_execution_manager.check_project_id()


def test_check_project_id_raises_error_when_no_project(
    algorithm_execution_manager: AlgorithmExecutionManager, mock_api: MagicMock
) -> None:
    mock_api.get_setting.return_value = None

    with pytest.raises(RuntimeError, match="No project found. Please create a project by calling init_project()"):
        algorithm_execution_manager.check_project_id()

    mock_api.get_setting.side_effect = ValueError

    with pytest.raises(RuntimeError, match="No project found. Please create a project by calling init_project()"):
        algorithm_execution_manager.check_project_id()


def test_set_algorithm_setting(algorithm_execution_manager: AlgorithmExecutionManager, mock_api: MagicMock) -> None:
    algorithm_name = "Some algorithm"
    setting_name = "backend_type_id"
    backend_type_id = 1

    algorithm_execution_manager.set_algorithm_setting(algorithm_name, setting_name, backend_type_id)
    mock_api.set_algorithm_setting.assert_called_once_with(algorithm_name, setting_name, backend_type_id)
