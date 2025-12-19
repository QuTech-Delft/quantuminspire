from pathlib import Path
from typing import Any, Dict, cast
from unittest.mock import Mock, call, patch

import pytest

from quantuminspire.auth_manager.auth_manager import AuthManager
from quantuminspire.config_manager.config_manager import ConfigManager
from quantuminspire.job_manager.job_manager import JobManager, JobOptions
from quantuminspire.qi_api.qi_api import QIApi


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
def api_instance(mock_config_manager: Mock, mock_auth_manager: Mock, mock_job_manager: Mock) -> QIApi:
    return QIApi(mock_config_manager, mock_auth_manager, mock_job_manager)


@pytest.mark.parametrize(
    "hostname,expected_hostname",
    [
        ("https://example.com", "https://example.com"),  # explicit hostname
        (None, "https://default_hostname.com"),  # default from config
    ],
)
def test_login(api_instance: QIApi, mock_config_manager: Mock, hostname: str | None, expected_hostname: str) -> None:
    # Arrange
    if hostname is None:
        mock_config_manager.get.return_value = expected_hostname

    # Act
    api_instance.login(hostname)

    # Assert
    login_mock = cast(Mock, api_instance._auth_manager.login)

    login_mock.assert_called_with(expected_hostname)


def test_get_backend_types(api_instance: QIApi) -> None:
    # Arrange & act
    api_instance.get_backend_types()

    # assert
    get_backend_types_mock = cast(Mock, api_instance._job_manager.get_backend_types)

    get_backend_types_mock.assert_called_once()


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
    api_instance: QIApi,
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


def test_inspect(api_instance: QIApi) -> None:
    # Arrange & act
    api_instance.inspect()

    # assert
    inspect_mock = cast(Mock, api_instance._config_manager.inspect)
    inspect_mock.assert_called_once()


def test_initialize(api_instance: QIApi, tmp_path: Path) -> None:
    # Arrange & act
    api_instance.initialize(tmp_path)

    # assert
    initialize_mock = cast(Mock, api_instance._config_manager.initialize)

    initialize_mock.assert_called_once_with(tmp_path)


def test_get(api_instance: QIApi) -> None:
    # Arrange
    key = "project.id"

    # Act
    api_instance.get(key)

    # assert
    get_mock = cast(Mock, api_instance._config_manager.get)

    get_mock.assert_called_once_with(key)


def test_set(api_instance: QIApi) -> None:
    # Arrange
    key, value = "project.id", 3

    # Act
    api_instance.set(key, value)

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
    api_instance: QIApi,
    mock_job_manager: Mock,
    mock_config_manager: Mock,
    persist: bool,
) -> None:
    # Arrange
    file_path = "path/to/file.py"
    file_name = "TestAlgorithm"
    num_shots = 100
    store_raw_data = False
    backend_type_id = 1

    resolved_options = {
        "project_name": "TestProject",
        "project_description": "Test description",
        "backend_type": backend_type_id,
        "number_of_shots": num_shots,
        "raw_data_enabled": store_raw_data,
        "algorithm_name": file_name,
        "project_id": 1,
        "job_id": 1,
    }

    returned_job_options = JobOptions(**(resolved_options | {"file_path": Path(file_path)}))
    mock_job_manager.run_flow.return_value = returned_job_options

    with patch.object(api_instance, "_get_job_options", return_value=resolved_options) as mocked_get_job_options:

        # Act
        _ = api_instance.submit_job(file_path, file_name, num_shots, store_raw_data, backend_type_id, persist)

        # Assert
        mocked_get_job_options.assert_called_with(file_name, num_shots, store_raw_data, backend_type_id)

        expected_calls = [
            call("project.id", returned_job_options.project_id, is_user=False),
        ]

        if persist:
            expected_calls.extend(
                [
                    call("job.id", returned_job_options.job_id, is_user=False),
                    call("algorithm.name", returned_job_options.algorithm_name, is_user=False),
                ]
            )

        mock_config_manager.set.assert_has_calls(expected_calls)


@pytest.mark.parametrize(
    "file_name,num_shots,store_raw_data,backend_type_id,expected_resolved",
    [
        # all explicit values
        (
            "MyAlgorithm",
            100,
            True,
            1,
            {
                "backend_type": 1,
                "number_of_shots": 100,
                "raw_data_enabled": True,
                "algorithm_name": "MyAlgorithm",
            },
        ),
        # all resolved from config
        (
            None,
            None,
            None,
            None,
            {
                "backend_type": 2,
                "number_of_shots": 1024,
                "raw_data_enabled": False,
                "algorithm_name": "DefaultAlgorithm",
            },
        ),
    ],
)
def test_get_resolved_job_options(
    api_instance: QIApi,
    mock_config_manager: Mock,
    file_name: str | None,
    num_shots: int | None,
    store_raw_data: bool | None,
    backend_type_id: int | None,
    expected_resolved: Dict[str, Any],
) -> None:
    # Arrange: config defaults
    config_values = {
        "project.id": 42,
        "project.name": "TestProject",
        "project.description": "Test description",
        "backend_type": 2,
        "algorithm.num_shots": 1024,
        "algorithm.store_raw_data": False,
        "algorithm.name": "DefaultAlgorithm",
    }

    mock_config_manager.get.side_effect = lambda key: config_values[key]

    # Act
    options = api_instance._get_job_options(
        file_name=file_name,
        num_shots=num_shots,
        store_raw_data=store_raw_data,
        backend_type_id=backend_type_id,
    )

    # Assert static config values
    assert options["project_id"] == 42
    assert options["project_name"] == "TestProject"
    assert options["project_description"] == "Test description"

    # Assert resolved values
    for key, value in expected_resolved.items():
        assert options[key] == value
