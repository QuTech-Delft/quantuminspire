from datetime import datetime
from pathlib import Path
from typing import Any, Optional, cast
from unittest import mock
from unittest.mock import MagicMock, Mock, call, patch

import pytest
import requests
from compute_api_client import Algorithm, AlgorithmType, Job, JobStatus, Project
from pytest_mock import MockerFixture

from quantuminspire.api import Api
from quantuminspire.managers.auth_manager import AuthManager
from quantuminspire.managers.config_manager import ConfigManager
from quantuminspire.managers.job_manager import JobManager, JobOptions
from quantuminspire.settings.models import LocalAlgorithm


@pytest.fixture
def mock_config_manager() -> Mock:
    return Mock(spec=ConfigManager)


@pytest.fixture
def mock_auth_manager() -> Mock:
    return Mock(spec=AuthManager)


@pytest.fixture
def mock_job_manager() -> Mock:
    return Mock(spec=JobManager)


@pytest.fixture
def api_instance(mock_config_manager: Mock, mock_auth_manager: Mock, mock_job_manager: Mock) -> Api:
    return Api(mock_config_manager, mock_auth_manager, mock_job_manager)

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





@pytest.mark.parametrize(
    "hostname,expected_hostname",
    [
        ("https://example.com", "https://example.com"),  # explicit hostname
        (None, "https://default_hostname.com"),  # default from config
    ],
)
def test_login_force(
    api_instance: Api, mock_config_manager: Mock, hostname: Optional[str], expected_hostname: str
) -> None:
    # Arrange
    if hostname is None:
        mock_config_manager.get.return_value = expected_hostname

    # Act
    api_instance.login(hostname, force=True)

    # Assert
    login_mock = cast(Mock, api_instance._auth_manager.login)
    refresh_mock = cast(Mock, api_instance._auth_manager.refresh_tokens)
    set_mock = cast(Mock, api_instance._config_manager.set)

    login_mock.assert_called_with(expected_hostname, False)
    refresh_mock.assert_not_called()
    set_mock.assert_called_once_with("default_host", expected_hostname, True)


def test_login_user_not_authenticated(api_instance: Api) -> None:
    # Arrange
    hostname = "https://example.com"
    login_required_mock = cast(Mock, api_instance._auth_manager.login_required)
    login_required_mock.return_value = True

    # Act
    api_instance.login(hostname)

    # Assert
    login_mock = cast(Mock, api_instance._auth_manager.login)
    refresh_mock = cast(Mock, api_instance._auth_manager.refresh_tokens)
    set_mock = cast(Mock, api_instance._config_manager.set)

    login_mock.assert_called_with(hostname, False)
    refresh_mock.assert_not_called()
    set_mock.assert_called_once_with("default_host", hostname, True)


def test_login_user_already_authenticated(api_instance: Api) -> None:
    # Arrange
    hostname = "https://example.com"

    login_required_mock = cast(Mock, api_instance._auth_manager.login_required)
    login_required_mock.return_value = False

    # Act
    api_instance.login(hostname)

    # Assert
    login_mock = cast(Mock, api_instance._auth_manager.login)
    refresh_mock = cast(Mock, api_instance._auth_manager.refresh_tokens)
    set_mock = cast(Mock, api_instance._config_manager.set)

    refresh_mock.assert_called_with(hostname)
    login_mock.assert_not_called()
    set_mock.assert_not_called()


def test_get_backend_types(api_instance: Api) -> None:
    # Arrange & act
    api_instance.get_backend_types()

    # assert
    get_backend_types_mock = cast(Mock, api_instance._job_manager.get_backend_types)

    get_backend_types_mock.assert_called_once()

def test_execute_algorithm(
    api_instance: Api, mocker: MockerFixture
) -> None:
    algorithm_name = "Some algorithm"
    file_name = "some_file.py"

    mocker.patch.object(api_instance, "check_project_id")
    mocker.patch.object(api_instance, "get_setting", return_value={algorithm_name: {}})

    api_instance.initialize_project("Dummy project")

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
    mock_submit_job = mocker.patch.object(api_instance, "submit_job", return_value=expected_job_options)

    # Act
    result = api_instance.execute_algorithm(
        file_name, algorithm_name=algorithm_name, backend_type_id=1, persist=True
    )

    # Assert
    mock_submit_job.assert_called_once_with(
        file_path=file_name,
        algorithm_name=algorithm_name,
        backend_type_id=1,
        num_shots=None,
        store_raw_data=False,
        persist=True,
    )
    assert result == expected_job_options

def test_execute_algorithm_with_persist_true_and_no_algorithm_name(
    api_instance: Api,
) -> None:
    with pytest.raises(
        ValueError,
        match="algorithm_name is required when you want to persist the data. "
        "Please add it to the function call of execute_algorithm()",
    ):
        api_instance.execute_algorithm(
            "some_file.py",
            backend_type_id=1,
            persist=True,
        )

def test_execute_algorithm_with_persist_true_creates_algorithm_if_not_exists(
    api_instance: Api,
    mocker: MockerFixture
) -> None:
    algorithm_name = "Some algorithm"
    file_name = "some_file.py"

    mocker.patch.object(api_instance, "get_setting", return_value={"Some other algorithm": {}})
    mocker.patch.object(api_instance, "submit_job")
    with patch.object(api_instance, "initialize_algorithm") as mock_init_algorithm:

        api_instance.initialize_project("Dummy project")
        api_instance.execute_algorithm(
            file_name, algorithm_name=algorithm_name, backend_type_id=1, persist=True
        )

        mock_init_algorithm.assert_called_once_with(algorithm_name=algorithm_name, file_path=file_name)


def test_algorithm_with_persist_false(
    api_instance: Api,
    mocker: MockerFixture
) -> None:
    file_name = "some_file.py"
    mock_submit_job = mocker.patch.object(api_instance, "submit_job")

    api_instance.execute_algorithm(
        file_name,
        backend_type_id=1,
        persist=False,
    )

    mock_submit_job.assert_called_once_with(
        file_path=file_name,
        algorithm_name=None,
        backend_type_id=1,
        num_shots=None,
        store_raw_data=False,
        persist=False
    )

def test_initialize_project_no_project_id(
    api_instance: Api, mocker: MockerFixture
) -> None:
    project_name = "Dummy project"
    project_description = "Dummy description"

    mock_remote_project = MagicMock(id=1, name=project_name, description=project_description)

    mocker.patch.object(
        api_instance, "check_project_id", side_effect=RuntimeError("No project initialized")
    )

    mock_initialize_remote_project = (
        mocker.patch.object(api_instance, "initialize_remote_project", return_value=mock_remote_project))
    mock_set_setting = mocker.patch.object(api_instance, "set_setting")

    api_instance.initialize_project(project_name, project_description)
    expected_calls = [
        call("project.id", mock_remote_project.id),
        call("project.name", mock_remote_project.name),
        call("project.description", mock_remote_project.description),
        call("project.algorithms", {}),
    ]

    mock_initialize_remote_project.assert_called_once_with(project_name, project_description)
    mock_set_setting.assert_has_calls(expected_calls, any_order=True)


def test_initialize_project(
    api_instance: Api, mocker: MockerFixture, tmp_path: Path
) -> None:
    project_name = "Dummy project"
    project_description = "Dummy description"

    with mock.patch("quantuminspire.api.ConfigManager.initialize") as initialize_mock:
        mocker.patch.object(
            api_instance,
            "check_project_id",
        )

        api_instance.initialize_project(project_name, project_description, path=str(tmp_path))
        initialize_mock.assert_called_once_with(tmp_path)


def test_initialize_algorithm(
    api_instance: Api,
    mock_get_setting: Any,
    mocker: MockerFixture,
) -> None:
    check_project_id = mocker.patch.object(api_instance, "check_project_id")
    mocker.patch.object(api_instance, "get_setting", side_effect=mock_get_setting)

    algorithm_name = "Some algorithm"
    file_path = "some_file.py"
    project_id = mock_get_setting("project.id")

    mock_remote_algorithm = MagicMock(id=1)
    local_algorithm = LocalAlgorithm(
        id=mock_remote_algorithm.id,
        file_path=file_path,
    )

    mock_create_remote_algorithm = mocker.patch.object(
        api_instance, "create_remote_algorithm", return_value=mock_remote_algorithm)
    mock_add_algorithm_to_settings = mocker.patch.object(api_instance, "_add_algorithm_to_settings")

    api_instance.initialize_algorithm(algorithm_name, file_path)

    check_project_id.assert_called_once()
    mock_create_remote_algorithm.assert_called_once_with(project_id, algorithm_name, file_path)
    mock_add_algorithm_to_settings.assert_called_once_with(algorithm_name, local_algorithm)

def test_get_status(
    api_instance: Api, mock_get_algorithm_setting: Any, mocker: MockerFixture
) -> None:
    mocker.patch.object(api_instance, "get_algorithm_setting", side_effect=mock_get_algorithm_setting)

    algorithm_name = "Some algorithm"
    job_id = mock_get_algorithm_setting(algorithm_name, "job_id")
    expected_status = JobStatus.COMPLETED
    mock_get_job = mocker.patch.object(api_instance, "get_job", return_value=MagicMock(status=expected_status))

    status = api_instance.get_status(algorithm_name)
    mock_get_job.assert_called_once_with(job_id)
    assert status == expected_status


def test_get_status_with_wait_and_timeout(
    api_instance: Api, mock_get_algorithm_setting: Any, mock_job_manager: Mock, mocker: MockerFixture
) -> None:
    mocker.patch.object(api_instance, "get_algorithm_setting", side_effect=mock_get_algorithm_setting)

    algorithm_name = "Some algorithm"
    job_id = mock_get_algorithm_setting(algorithm_name, "job_id")
    mock_job = MagicMock(spec=Job)
    mock_job.status = JobStatus.COMPLETED
    mock_wait = mocker.patch.object(mock_job_manager, "wait_for_job_completion", return_value=mock_job)

    status = api_instance.get_status(algorithm_name, wait=True, timeout=5)
    mock_wait.assert_called_once_with(job_id, timeout=5)
    assert status == mock_job.status

def test_get_status_with_wait_and_timeout_exceeds_timeout(
    api_instance: Api, mock_get_algorithm_setting: Any, mock_job_manager: Mock, mocker: MockerFixture
) -> None:
    mocker.patch.object(api_instance, "get_algorithm_setting", side_effect=mock_get_algorithm_setting)

    algorithm_name = "Some algorithm"
    job_id = mock_get_algorithm_setting(algorithm_name, "job_id")
    mock_wait = mocker.patch.object(mock_job_manager, "wait_for_job_completion", side_effect=TimeoutError)

    api_instance.get_status(algorithm_name, True, 5)

    mock_wait.assert_called_once_with(job_id, timeout=5)

def test_get_final_result_by_algorithm_name(
    api_instance: Api, mock_get_algorithm_setting: Any, mocker: MockerFixture
) -> None:
    mocker.patch.object(api_instance, "get_algorithm_setting", side_effect=mock_get_algorithm_setting)

    algorithm_name = "Some algorithm"
    job_id = mock_get_algorithm_setting(algorithm_name, "job_id")
    expected_result = MagicMock()
    mock_get_final_result = mocker.patch.object(api_instance, "get_final_result", return_value=expected_result)

    final_result = api_instance.get_final_result_by_algorithm_name(algorithm_name)
    mock_get_final_result.assert_called_once_with(job_id)
    assert final_result == expected_result


def test_check_project_id_with_valid_project(
    api_instance: Api, mock_get_setting: Any, mocker: MockerFixture
) -> None:
    mocker.patch.object(api_instance, "get_setting", side_effect=mock_get_setting)
    api_instance.check_project_id()


def test_check_project_id_raises_error_when_no_project(
    api_instance: Api, mocker: MockerFixture
) -> None:
    mocker.patch.object(api_instance, "get_setting", return_value=None)

    with pytest.raises(RuntimeError, match="No project found. Please create a project by calling initialize_project()"):
        api_instance.check_project_id()

    mocker.patch.object(api_instance, "get_setting", side_effect=ValueError)


    with pytest.raises(RuntimeError, match="No project found. Please create a project by calling initialize_project()"):
        api_instance.check_project_id()


@pytest.mark.parametrize(
    "api_method,job_manager_method,job_id,expected_job_id",
    [
        ("get_job", "get_job", 1, 1),  # explicit job_id
        ("get_job", "get_job", None, 100),  # default job_id
        ("get_final_result", "get_final_result", 1, 1),  # explicit job_id
        ("get_final_result", "get_final_result", None, 100),  # default job_id
    ],
)
def test_job_methods(
    api_instance: Api,
    mock_config_manager: Mock,
    job_id: int | None,
    expected_job_id: int,
    api_method: str,
    job_manager_method: str,
) -> None:
    # Arrange
    if job_id is None:
        mock_config_manager.get.return_value = expected_job_id

    # Act
    getattr(api_instance, api_method)(job_id)

    # Assert
    getattr(api_instance._job_manager, job_manager_method).assert_called_once_with(expected_job_id)


def test_view_settings(api_instance: Api) -> None:
    # Arrange & act
    api_instance.view_settings()

    # assert
    inspect_mock = cast(Mock, api_instance._config_manager.inspect)
    inspect_mock.assert_called_once()


def test_get_setting(api_instance: Api) -> None:
    # Arrange
    key = "project.id"

    # Act
    api_instance.get_setting(key)

    # assert
    get_mock = cast(Mock, api_instance._config_manager.get)

    get_mock.assert_called_once_with(key)


def test_set_setting(api_instance: Api) -> None:
    # Arrange
    key, value = "project.id", 3

    # Act
    api_instance.set_setting(key, value)

    # assert
    set_mock = cast(Mock, api_instance._config_manager.set)
    set_mock.assert_called_once_with(key, value, False)


@pytest.mark.parametrize(
    "persist",
    [
        True,
        False,
    ],
)
def test_submit_job(
    api_instance: Api,
    mock_job_manager: Mock,
    mock_config_manager: Mock,
    persist: bool,
) -> None:
    # Arrange
    file_path = "path/to/file.py"
    algorithm_name = "TestAlgorithm"
    num_shots = 100
    store_raw_data = False
    backend_type_id = 1

    resolved_options = {
        "project_name": "TestProject",
        "project_description": "Test description",
        "backend_type_id": backend_type_id,
        "number_of_shots": num_shots,
        "raw_data_enabled": store_raw_data,
        "algorithm_name": algorithm_name,
        "project_id": 1,
        "job_id": 1,
        "algorithm_id": 1,
    }

    returned_job_options = JobOptions(**(resolved_options | {"file_path": Path(file_path)}))
    mock_job_manager.run_flow.return_value = returned_job_options

    with (
        patch.object(api_instance, "_get_job_options", return_value=resolved_options) as mocked_get_job_options,
        patch.object(api_instance, "_add_algorithm_to_settings") as mocked_resolve_algorithm_setting,
    ):

        # Act
        _ = api_instance.submit_job(file_path, algorithm_name, num_shots, store_raw_data, backend_type_id, persist)

        # Assert
        mocked_get_job_options.assert_called_with(algorithm_name, num_shots, store_raw_data, backend_type_id)

        if persist:
            local_algorithm = LocalAlgorithm(
                id=returned_job_options.algorithm_id,
                file_path=str(returned_job_options.file_path),
                num_shots=returned_job_options.number_of_shots,
                store_raw_data=returned_job_options.raw_data_enabled,
                job_id=returned_job_options.job_id,
                backend_type_id=returned_job_options.backend_type_id,
            )
            mocked_resolve_algorithm_setting.assert_called_once_with(
                returned_job_options.algorithm_name, local_algorithm
            )


def test_submit_job_persist_false_algorithm_name_none(
    api_instance: Api,
    mock_job_manager: Mock,
    mock_config_manager: Mock,
) -> None:
    file_path = "path/to/file.py"
    algorithm_name = None
    num_shots = 100
    store_raw_data = False
    backend_type_id = 1

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    options = {
        "project_name": f"Project created on {timestamp}",
        "project_description": "Project created for non-persistent algorithm",
        "backend_type_id": backend_type_id,
        "number_of_shots": num_shots,
        "raw_data_enabled": store_raw_data,
        "algorithm_name": f"Algorithm created on {timestamp}",
    }

    returned_job_options = JobOptions(**(options | {"file_path": Path(file_path)}))
    mock_job_manager.run_flow.return_value = returned_job_options

    result = api_instance.submit_job(file_path, algorithm_name, num_shots, store_raw_data, backend_type_id, False)
    assert result == returned_job_options


def test_submit_job_persist_true_algorithm_name_none(
    api_instance: Api,
    mock_job_manager: Mock,
    mock_config_manager: Mock,
) -> None:

    with pytest.raises(ValueError, match="algorithm_name must be provided when persist is True"):
        _ = api_instance.submit_job("", None, None, False, None, True)


def test_submit_job_persist_false_algorithm_name_none_backend_type_id_none(
    api_instance: Api,
    mock_job_manager: Mock,
    mock_config_manager: Mock,
) -> None:

    with pytest.raises(ValueError, match="backend_type_id not provided"):
        _ = api_instance.submit_job("", None, None, False, None, False)


def test_resolve_protocol_url_with_scheme() -> None:
    test_url = "https://test_url.com"
    result_url = Api._resolve_protocol(test_url)

    assert result_url == test_url


def test_resolve_protocol_https_works(mocker: MockerFixture) -> None:
    test_url = "test_url.com"

    mock_head_response = MagicMock()
    mock_head_response.status_code = 200

    mocker.patch("requests.head", return_value=mock_head_response)
    result_url = Api._resolve_protocol(test_url)

    assert result_url == f"https://{test_url}"


def test_resolve_protocol_https_fails(mocker: MockerFixture) -> None:
    test_url = "test_url.com"

    mock_head_response = MagicMock()
    mock_head_response.status_code = 404

    mocker.patch("requests.head", return_value=mock_head_response)
    result_url = Api._resolve_protocol(test_url)

    assert result_url == f"http://{test_url}"


def test_resolve_protocol_requests_raises_exception(mocker: MockerFixture) -> None:
    test_url = "test_url.com"

    mocker.patch("requests.head", side_effect=requests.RequestException)
    result_url = Api._resolve_protocol(test_url)

    assert result_url == f"http://{test_url}"


@pytest.mark.parametrize(
    "num_shots,store_raw_data,backend_type_id,expected_backend_type_id,expected_num_shots,expected_store_raw_data",
    [
        (100, True, 2, 2, 100, True),  # with overrides
        (None, None, None, 1, 500, False),  # with defaults from local_algorithm
    ],
)
def test_get_job_options(
    api_instance: Api,
    mock_config_manager: Mock,
    num_shots: Optional[int],
    store_raw_data: Optional[bool],
    backend_type_id: Optional[int],
    expected_backend_type_id: int,
    expected_num_shots: int,
    expected_store_raw_data: bool,
) -> None:
    # Arrange
    algorithm_name = "TestAlgorithm"

    project_id = 42
    project_name = "TestProject"
    project_description = "Test Description"

    algorithm_id = 10
    default_num_shots = 500
    default_store_raw_data = False
    default_backend_type_id = 1

    local_algorithm = LocalAlgorithm(
        id=algorithm_id,
        file_path="path/to/algorithm.py",
        num_shots=default_num_shots,
        store_raw_data=default_store_raw_data,
        job_id=None,
        backend_type_id=default_backend_type_id,
    )

    def get_side_effect(key: str) -> Any:
        config_values = {
            "project.id": project_id,
            "project.name": project_name,
            "project.description": project_description,
            "project.algorithms": {algorithm_name: local_algorithm},
        }
        return config_values.get(key)

    mock_config_manager.get.side_effect = get_side_effect

    result = api_instance._get_job_options(algorithm_name, num_shots, store_raw_data, backend_type_id)

    assert result == {
        "project_id": project_id,
        "project_name": project_name,
        "project_description": project_description,
        "algorithm_id": algorithm_id,
        "algorithm_name": algorithm_name,
        "backend_type_id": expected_backend_type_id,
        "number_of_shots": expected_num_shots,
        "raw_data_enabled": expected_store_raw_data,
    }


def test_get_local_algorithm(api_instance: Api, mock_config_manager: Mock) -> None:
    # Arrange
    algorithm_name = "TestAlgorithm"
    local_algorithm = LocalAlgorithm(
        id=1,
        file_path="path/to/algorithm.py",
        num_shots=100,
        store_raw_data=True,
        job_id=5,
        backend_type_id=2,
    )

    mock_config_manager.get.return_value = {algorithm_name: local_algorithm}

    # Act
    result = api_instance._get_local_algorithm(algorithm_name)

    # Assert
    assert result == local_algorithm
    mock_config_manager.get.assert_called_once_with("project.algorithms")


def test_get_local_algorithm_not_found(api_instance: Api, mock_config_manager: Mock) -> None:
    # Arrange
    algorithm_name = "NonExistentAlgorithm"
    mock_config_manager.get.return_value = {}

    # Act & Assert
    with pytest.raises(ValueError, match=f"Algorithm '{algorithm_name}' not found in settings."):
        api_instance._get_local_algorithm(algorithm_name)


def test_add_algorithm_to_settings(api_instance: Api, mock_config_manager: Mock) -> None:
    # Arrange
    algorithm_name = "NewAlgorithm"
    existing_algorithm = LocalAlgorithm(
        id=1,
        file_path="path/to/old_algorithm.py",
        num_shots=50,
        store_raw_data=False,
        job_id=1,
        backend_type_id=1,
    )
    new_algorithm = LocalAlgorithm(
        id=2,
        file_path="path/to/new_algorithm.py",
        num_shots=100,
        store_raw_data=True,
        job_id=2,
        backend_type_id=2,
    )

    existing_algorithms = {"OldAlgorithm": existing_algorithm}
    mock_config_manager.get.return_value = existing_algorithms

    # Act
    api_instance._add_algorithm_to_settings(algorithm_name, new_algorithm)

    # Assert
    mock_config_manager.get.assert_called_once_with("project.algorithms")
    expected_algorithms = {
        "OldAlgorithm": existing_algorithm,
        algorithm_name: new_algorithm,
    }
    mock_config_manager.set.assert_called_once_with("project.algorithms", expected_algorithms, False)


def test_add_algorithm_to_settings_overwrite_existing(api_instance: Api, mock_config_manager: Mock) -> None:
    # Arrange
    algorithm_name = "TestAlgorithm"
    old_algorithm = LocalAlgorithm(
        id=1,
        file_path="path/to/old.py",
        num_shots=50,
        store_raw_data=False,
        job_id=1,
        backend_type_id=1,
    )
    updated_algorithm = LocalAlgorithm(
        id=1,
        file_path="path/to/updated.py",
        num_shots=200,
        store_raw_data=True,
        job_id=3,
        backend_type_id=2,
    )

    existing_algorithms = {algorithm_name: old_algorithm}
    mock_config_manager.get.return_value = existing_algorithms

    # Act
    api_instance._add_algorithm_to_settings(algorithm_name, updated_algorithm)

    # Assert
    expected_algorithms = {algorithm_name: updated_algorithm}
    mock_config_manager.set.assert_called_once_with("project.algorithms", expected_algorithms, False)


def test_initialize_remote_project(api_instance: Api, mock_config_manager: Mock, mock_job_manager: Mock) -> None:
    # Arrange
    project_name = "TestProject"
    project_description = "Test project description"
    host = "https://example.com"
    owner_id = 42

    mock_user_settings = Mock()
    mock_auth_info = Mock()
    mock_auth_info.owner_id = owner_id
    mock_user_settings.auths = {host: mock_auth_info}

    mock_config_manager.get.return_value = host
    mock_config_manager.user_settings = mock_user_settings

    expected_project = Mock(spec=Project)
    mock_job_manager.create_project.return_value = expected_project

    # Act
    result = api_instance.initialize_remote_project(project_name, project_description)

    # Assert
    mock_config_manager.get.assert_called_once_with("default_host")
    mock_job_manager.create_project.assert_called_once_with(owner_id, project_name, project_description)
    assert result == expected_project


def test_create_remote_algorithm_with_file(api_instance: Api, mock_job_manager: Mock) -> None:
    # Arrange
    project_id = 1
    algorithm_name = "TestAlgorithm"
    file_path = "path/to/algorithm.py"

    expected_algorithm_type = AlgorithmType.QUANTUM
    expected_algorithm = Mock(spec=Algorithm)

    mock_job_manager.get_algorithm_type.return_value = expected_algorithm_type
    mock_job_manager.create_algorithm.return_value = expected_algorithm

    # Act
    result = api_instance.create_remote_algorithm(project_id, algorithm_name, file_path)

    # Assert
    mock_job_manager.get_algorithm_type.assert_called_once_with(Path(file_path))
    mock_job_manager.create_algorithm.assert_called_once_with(project_id, algorithm_name, expected_algorithm_type)
    assert result == expected_algorithm


def test_create_remote_algorithm_without_file(api_instance: Api, mock_job_manager: Mock) -> None:
    # Arrange
    project_id = 1
    algorithm_name = "TestAlgorithm"
    file_path = ""

    expected_algorithm = Mock(spec=Algorithm)
    mock_job_manager.create_algorithm.return_value = expected_algorithm

    # Act
    result = api_instance.create_remote_algorithm(project_id, algorithm_name, file_path)

    # Assert
    mock_job_manager.get_algorithm_type.assert_not_called()
    mock_job_manager.create_algorithm.assert_called_once_with(project_id, algorithm_name, AlgorithmType.HYBRID)
    assert result == expected_algorithm


def test_get_algorithm_setting(api_instance: Api, mock_config_manager: Mock) -> None:
    # Arrange
    algorithm_name = "TestAlgorithm"
    setting_name = "num_shots"
    expected_value = 1024

    local_algorithm = LocalAlgorithm(
        id=1,
        file_path="path/to/algorithm.py",
        num_shots=expected_value,
        store_raw_data=True,
        job_id=5,
        backend_type_id=2,
    )

    mock_config_manager.get.return_value = {algorithm_name: local_algorithm}

    # Act
    result = api_instance.get_algorithm_setting(algorithm_name, setting_name)

    # Assert
    assert result == expected_value
    mock_config_manager.get.assert_called_once_with("project.algorithms")


def test_set_setting_user_setting(api_instance: Api, mock_config_manager: Mock) -> None:
    # Arrange
    key = "default_host"
    value = "https://example.com"

    # Act
    api_instance.set_setting(key, value, is_user=True)

    # Assert
    mock_config_manager.set.assert_called_once_with(key, value, True)


def test_set_setting_project_setting(api_instance: Api, mock_config_manager: Mock) -> None:
    # Arrange
    key = "project.name"
    value = "MyProject"

    # Act
    api_instance.set_setting(key, value, is_user=False)

    # Assert
    mock_config_manager.set.assert_called_once_with(key, value, False)


def test_set_algorithm_setting(api_instance: Api, mock_config_manager: Mock) -> None:
    # Arrange
    algorithm_name = "TestAlgorithm"
    setting_name = "num_shots"
    new_value = 1024

    old_local_algorithm = LocalAlgorithm(
        id=1,
        file_path="path/to/algorithm.py",
        num_shots=100,
        store_raw_data=True,
        job_id=5,
        backend_type_id=2,
    )
    new_local_algorithm = LocalAlgorithm(
        id=1,
        file_path="path/to/algorithm.py",
        num_shots=new_value,
        store_raw_data=True,
        job_id=5,
        backend_type_id=2,
    )

    mock_config_manager.get.return_value = {algorithm_name: old_local_algorithm}

    with patch.object(api_instance, "_add_algorithm_to_settings") as mocked_resolve_algorithm_setting:

        # Act
        api_instance.set_algorithm_setting(algorithm_name, setting_name, new_value)

        # Assert
        mock_config_manager.get.assert_called_with("project.algorithms")
        mocked_resolve_algorithm_setting.assert_called_once_with(algorithm_name, new_local_algorithm)


def test_resolve_algorithm_setting_with_override(api_instance: Api, mock_config_manager: Mock) -> None:
    # Arrange
    algorithm_name = "TestAlgorithm"
    setting_name = "num_shots"
    override_value = 1024

    local_algorithm = LocalAlgorithm(
        id=1,
        file_path="path/to/algorithm.py",
        num_shots=100,
        store_raw_data=True,
        job_id=5,
        backend_type_id=2,
    )

    mock_config_manager.get.return_value = {algorithm_name: local_algorithm}

    # Act
    result = api_instance._resolve_algorithm_setting(override_value, setting_name, algorithm_name)

    # Assert
    assert result == override_value


def test_resolve_algorithm_setting_without_override(api_instance: Api, mock_config_manager: Mock) -> None:
    # Arrange
    algorithm_name = "TestAlgorithm"
    setting_name = "num_shots"
    default_value = 100

    local_algorithm = LocalAlgorithm(
        id=1,
        file_path="path/to/algorithm.py",
        num_shots=default_value,
        store_raw_data=True,
        job_id=5,
        backend_type_id=2,
    )

    mock_config_manager.get.return_value = {algorithm_name: local_algorithm}

    # Act
    result = api_instance._resolve_algorithm_setting(None, setting_name, algorithm_name)

    # Assert
    assert result == default_value
    mock_config_manager.get.assert_called_once_with("project.algorithms")
