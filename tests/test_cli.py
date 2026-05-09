from datetime import datetime
from pathlib import Path
from typing import Any, Generator
from unittest.mock import MagicMock, patch

import pytest
from pytest import MonkeyPatch
from typer.testing import CliRunner

from quantuminspire.cli import app

runner = CliRunner()


@pytest.fixture
def mock_api() -> Generator[MagicMock, Any, None]:
    """Patch the Api class so every command gets a shared MagicMock instance."""
    with patch("quantuminspire.cli.Api") as mock_api_class:
        api = MagicMock()
        mock_api_class.return_value = api
        yield api


# ---------------------------------------------------------------------------
# Login / Logout
# ---------------------------------------------------------------------------


def test_login(mock_api: MagicMock) -> None:
    result = runner.invoke(app, ["login"])

    assert result.exit_code == 0, repr(result.exception)
    mock_api.login.assert_called_once_with(None, False, False)


def test_login_with_host(mock_api: MagicMock) -> None:
    result = runner.invoke(app, ["login", "https://host"])

    assert result.exit_code == 0, repr(result.exception)
    mock_api.login.assert_called_once_with("https://host", False, False)


def test_login_with_override_auth_config(mock_api: MagicMock) -> None:
    result = runner.invoke(app, ["login", "--override-auth-config"])

    assert result.exit_code == 0, repr(result.exception)
    mock_api.login.assert_called_once_with(None, True, False)


def test_login_with_force(mock_api: MagicMock) -> None:
    result = runner.invoke(app, ["login", "--force"])

    assert result.exit_code == 0, repr(result.exception)
    mock_api.login.assert_called_once_with(None, False, True)


def test_logout(mock_api: MagicMock) -> None:
    host = "https://host"
    result = runner.invoke(app, ["logout", host])
    assert result.exit_code == 0, repr(result.exception)
    mock_api.logout.assert_called_once_with(host)


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------


def test_initialize_project(mock_api: MagicMock) -> None:
    result = runner.invoke(app, ["projects", "init", "my-project"])

    assert result.exit_code == 0, repr(result.exception)
    assert "Project 'my-project' initialized successfully" in result.stdout
    mock_api.initialize_project.assert_called_once_with("my-project", "", None)


def test_initialize_project_with_description(mock_api: MagicMock) -> None:
    result = runner.invoke(app, ["projects", "init", "my-project", "my description"])

    assert result.exit_code == 0, repr(result.exception)
    assert "Project 'my-project' initialized successfully" in result.stdout
    mock_api.initialize_project.assert_called_once_with("my-project", "my description", None)


def test_initialize_project_with_path(mock_api: MagicMock) -> None:
    result = runner.invoke(app, ["projects", "init", "my-project", "--path", "/tmp/test"])

    assert result.exit_code == 0, repr(result.exception)
    assert "Project 'my-project' initialized successfully at '/tmp/test'" in result.stdout
    mock_api.initialize_project.assert_called_once_with("my-project", "", "/tmp/test")


def test_list_projects_empty(mock_api: MagicMock) -> None:
    mock_api.get_projects.return_value = []

    result = runner.invoke(app, ["projects", "list"])

    assert result.exit_code == 0, repr(result.exception)
    mock_api.get_projects.assert_called_once_with(None, False)


def test_list_projects_with_data(mock_api: MagicMock) -> None:
    mock_project = MagicMock()
    mock_project.id = 1
    mock_project.name = "my-project"
    mock_project.description = "desc"
    mock_project.created_on = datetime(2024, 1, 1, 10, 0, 0)
    mock_project.starred = False
    mock_api.get_projects.return_value = [mock_project]

    result = runner.invoke(app, ["projects", "list"])

    assert result.exit_code == 0, repr(result.exception)
    mock_api.get_projects.assert_called_once_with(None, False)


def test_list_projects_with_name_filter(mock_api: MagicMock) -> None:
    mock_api.get_projects.return_value = []

    result = runner.invoke(app, ["projects", "list", "--name", "my-project"])

    assert result.exit_code == 0, repr(result.exception)
    mock_api.get_projects.assert_called_once_with("my-project", False)


def test_list_projects_with_exact(mock_api: MagicMock) -> None:
    mock_api.get_projects.return_value = []

    result = runner.invoke(app, ["projects", "list", "--exact"])

    assert result.exit_code == 0, repr(result.exception)
    mock_api.get_projects.assert_called_once_with(None, True)


def test_list_projects_with_ids(mock_api: MagicMock) -> None:
    mock_project = MagicMock()
    mock_project.id = 42
    mock_api.get_projects.return_value = [mock_project]

    result = runner.invoke(app, ["projects", "list", "--quiet"])

    assert result.exit_code == 0, repr(result.exception)
    assert "42" in result.stdout
    mock_api.get_projects.assert_called_once_with(None, False)


def test_delete_projects_by_ids(mock_api: MagicMock) -> None:
    result = runner.invoke(app, ["projects", "delete", "1", "2"], input="y\n")

    assert result.exit_code == 0, repr(result.exception)
    mock_api.delete_projects.assert_called_once_with([1, 2], None, False)


def test_delete_projects_by_name(mock_api: MagicMock) -> None:
    result = runner.invoke(app, ["projects", "delete", "--name", "my-project"], input="y\n")

    assert result.exit_code == 0, repr(result.exception)
    mock_api.delete_projects.assert_called_once_with(None, "my-project", False)


def test_delete_projects_by_name_with_exact(mock_api: MagicMock) -> None:
    result = runner.invoke(app, ["projects", "delete", "--name", "my-project", "--exact"], input="y\n")

    assert result.exit_code == 0, repr(result.exception)
    mock_api.delete_projects.assert_called_once_with(None, "my-project", True)


def test_delete_all_projects(mock_api: MagicMock) -> None:
    result = runner.invoke(app, ["projects", "delete"], input="y\n")

    assert result.exit_code == 0, repr(result.exception)
    assert "This will delete ALL your projects" in result.stdout
    mock_api.delete_projects.assert_called_once_with(None, None, False)


def test_delete_projects_abort(mock_api: MagicMock) -> None:
    result = runner.invoke(app, ["projects", "delete", "1"], input="n\n")

    assert result.exit_code != 0
    assert "Aborted" in result.stdout
    mock_api.delete_projects.assert_not_called()


# ---------------------------------------------------------------------------
# Algorithms
# ---------------------------------------------------------------------------


def test_initialize_algorithm(mock_api: MagicMock) -> None:
    result = runner.invoke(app, ["algorithms", "init", "my-algorithm", "path/to/file", "1"])

    assert result.exit_code == 0, repr(result.exception)
    assert "Algorithm 'my-algorithm' initialized successfully in local config." in result.stdout
    mock_api.initialize_algorithm.assert_called_once_with("my-algorithm", Path("path/to/file"), 1, None, False)


def test_initialize_algorithm_with_options(mock_api: MagicMock) -> None:
    result = runner.invoke(
        app,
        [
            "algorithms",
            "init",
            "my-algorithm",
            "path/to/file",
            "1",
            "--num-shots",
            "100",
            "--store-raw-data",
        ],
    )

    assert result.exit_code == 0, repr(result.exception)
    mock_api.initialize_algorithm.assert_called_once_with("my-algorithm", Path("path/to/file"), 1, 100, True)


def test_get_algorithm_status(mock_api: MagicMock) -> None:
    mock_status = MagicMock()
    mock_status.value = "RUNNING"
    mock_api.get_job_status.return_value = mock_status

    result = runner.invoke(app, ["algorithms", "status", "my-algo"])

    assert result.exit_code == 0, repr(result.exception)
    assert "Status of latest job for 'my-algo' algorithm: 'RUNNING'" in result.stdout
    mock_api.get_job_status.assert_called_once_with("my-algo", None, False, 60.0)


def test_get_algorithm_status_with_wait(mock_api: MagicMock) -> None:
    mock_status = MagicMock()
    mock_status.value = "COMPLETED"
    mock_api.get_job_status.return_value = mock_status

    result = runner.invoke(app, ["algorithms", "status", "my-algo", "--wait"])

    assert result.exit_code == 0, repr(result.exception)
    mock_api.get_job_status.assert_called_once_with("my-algo", None, True, 60.0)


def test_get_algorithm_status_with_timeout(mock_api: MagicMock) -> None:
    mock_status = MagicMock()
    mock_status.value = "COMPLETED"
    mock_api.get_job_status.return_value = mock_status

    result = runner.invoke(app, ["algorithms", "status", "my-algo", "--timeout", "120"])

    assert result.exit_code == 0, repr(result.exception)
    mock_api.get_job_status.assert_called_once_with("my-algo", None, False, 120.0)


def test_get_algorithm_results(mock_api: MagicMock) -> None:
    mock_result = MagicMock()
    mock_result.model_dump.return_value = {"id": 1}
    mock_api.get_results.return_value = [mock_result]

    result = runner.invoke(app, ["algorithms", "results", "my-algo"])

    assert result.exit_code == 0, repr(result.exception)
    assert "Retrieving results for latest job of 'my-algo' algorithm..." in result.stdout
    mock_api.get_results.assert_called_once_with("my-algo", None)


def test_get_algorithm_results_empty(mock_api: MagicMock) -> None:
    mock_api.get_results.return_value = []

    result = runner.invoke(app, ["algorithms", "results", "my-algo"])

    assert result.exit_code == 0, repr(result.exception)
    assert "[]" in result.stdout
    mock_api.get_results.assert_called_once_with("my-algo", None)


def test_get_algorithm_results_save(mock_api: MagicMock, tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    mock_result = MagicMock()
    mock_result.model_dump_json.return_value = '{"id": 1}'
    mock_api.get_results.return_value = [mock_result]
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["algorithms", "results", "my-algo", "--save"])

    assert result.exit_code == 0, repr(result.exception)
    assert "Saving results to" in result.stdout


def test_get_algorithm_final_result(mock_api: MagicMock) -> None:
    mock_final_result = MagicMock()
    mock_final_result.model_dump.return_value = {"id": 1}
    mock_api.get_final_result.return_value = mock_final_result

    result = runner.invoke(app, ["algorithms", "final-result", "my-algo"])

    assert result.exit_code == 0, repr(result.exception)
    assert "Retrieving final result for latest job of 'my-algo' algorithm..." in result.stdout
    mock_api.get_final_result.assert_called_once_with("my-algo", None)


def test_get_algorithm_final_result_save(mock_api: MagicMock, tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    mock_final_result = MagicMock()
    mock_final_result.model_dump_json.return_value = '{"id": 1}'
    mock_api.get_final_result.return_value = mock_final_result
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["algorithms", "final-result", "my-algo", "--save"])

    assert result.exit_code == 0, repr(result.exception)
    assert "Saving final result to" in result.stdout


def test_get_algorithm_final_result_none(mock_api: MagicMock) -> None:
    mock_api.get_final_result.return_value = None

    result = runner.invoke(app, ["algorithms", "final-result", "my-algo"])

    assert result.exit_code == 0, repr(result.exception)
    assert "None" in result.stdout


# ---------------------------------------------------------------------------
# Files
# ---------------------------------------------------------------------------


def test_compile_file_with_file_and_backend(mock_api: MagicMock) -> None:
    result = runner.invoke(
        app,
        [
            "files",
            "compile",
            "--file",
            "path/to/file",
            "--backend-type-id",
            "1",
        ],
    )

    assert result.exit_code == 0, repr(result.exception)
    assert "File compiled successfully!" in result.stdout
    mock_api.compile_file.assert_called_once_with(Path("path/to/file"), None, 1, None)


def test_compile_file_with_name(mock_api: MagicMock) -> None:
    result = runner.invoke(app, ["files", "compile", "--name", "my-algorithm"])

    assert result.exit_code == 0, repr(result.exception)
    assert "File compiled successfully!" in result.stdout
    mock_api.compile_file.assert_called_once_with(None, "my-algorithm", None, None)


def test_compile_file_all_options(mock_api: MagicMock) -> None:
    result = runner.invoke(
        app,
        [
            "files",
            "compile",
            "--file",
            "path/to/file",
            "--name",
            "my-algorithm",
            "--backend-type-id",
            "2",
        ],
    )

    assert result.exit_code == 0, repr(result.exception)
    mock_api.compile_file.assert_called_once_with(Path("path/to/file"), "my-algorithm", 2, None)


def test_compile_file_with_compile_stage(mock_api: MagicMock) -> None:
    from compute_api_client import CompileStage

    result = runner.invoke(
        app,
        [
            "files",
            "compile",
            "--file",
            "path/to/file",
            "--backend-type-id",
            "1",
            "--compile-stage",
            "decomposition",
        ],
    )

    assert result.exit_code == 0, repr(result.exception)
    assert "File compiled successfully!" in result.stdout
    mock_api.compile_file.assert_called_once_with(Path("path/to/file"), None, 1, CompileStage.DECOMPOSITION)


# ---------------------------------------------------------------------------
# Backends
# ---------------------------------------------------------------------------


def test_get_backend_types_empty(mock_api: MagicMock) -> None:
    mock_api.get_backend_types.return_value = []

    result = runner.invoke(app, ["backends", "list"])

    assert result.exit_code == 0, repr(result.exception)
    mock_api.get_backend_types.assert_called_once()


def test_get_backend_types_with_data(mock_api: MagicMock) -> None:
    mock_backend = MagicMock()
    mock_backend.id = 1
    mock_backend.name = "test_backend"
    mock_backend.status.name = "AVAILABLE"
    mock_backend.is_hardware = False
    mock_backend.supports_raw_data = True
    mock_backend.nqubits = 5
    mock_backend.max_number_of_shots = 1000
    mock_backend.messages = {}
    mock_api.get_backend_types.return_value = [mock_backend]

    result = runner.invoke(app, ["backends", "list"])
    assert result.exit_code == 0, repr(result.exception)
    mock_api.get_backend_types.assert_called_once()


def test_get_backend_types_with_multiple_messages(mock_api: MagicMock) -> None:
    mock_message_1 = MagicMock()
    mock_message_1.content = "message 1"
    mock_message_2 = MagicMock()
    mock_message_2.content = "message 2"

    mock_backend = MagicMock()
    mock_backend.id = 2
    mock_backend.name = "test_backend_2"
    mock_backend.status.name = "MAINTENANCE"
    mock_backend.is_hardware = True
    mock_backend.supports_raw_data = False
    mock_backend.nqubits = 10
    mock_backend.max_number_of_shots = 512
    mock_backend.messages = {"warning": mock_message_1, "info": mock_message_2}
    mock_api.get_backend_types.return_value = [mock_backend]

    result = runner.invoke(app, ["backends", "list"])

    assert result.exit_code == 0, repr(result.exception)
    mock_api.get_backend_types.assert_called_once()


def test_get_backend_type(mock_api: MagicMock) -> None:
    mock_backend = MagicMock()
    mock_backend.model_dump.return_value = {"id": 1, "name": "test_backend"}
    mock_api.get_backend_type.return_value = mock_backend

    result = runner.invoke(app, ["backends", "get", "1"])

    assert result.exit_code == 0, repr(result.exception)
    assert "Retrieving backend type with ID '1'..." in result.stdout
    mock_api.get_backend_type.assert_called_once_with(1)


def test_get_queue(mock_api: MagicMock) -> None:
    backend_type_id = 1
    mock_queue = MagicMock()
    mock_queue.model_dump.return_value = {
        "number_of_jobs_in_queue": 2,
        "min_wait_time_in_queue_secs": 12.0,
        "avg_wait_time_in_queue_secs": 13.0,
        "max_wait_time_in_queue_secs": 14.0,
    }
    mock_api.get_queue.return_value = mock_queue

    result = runner.invoke(app, ["backends", "queue", str(backend_type_id)])

    assert result.exit_code == 0, repr(result.exception)
    assert f"Retrieving queue for backend type with ID '{backend_type_id}'..." in result.stdout
    mock_api.get_queue.assert_called_once_with(backend_type_id=backend_type_id, user_only=False)


def test_get_user_queue(mock_api: MagicMock) -> None:
    backend_type_id = 1
    mock_queue = MagicMock()
    mock_queue.model_dump.return_value = {
        "number_of_jobs_in_queue": 2,
        "min_wait_time_in_queue_secs": 12.0,
        "avg_wait_time_in_queue_secs": 13.0,
        "max_wait_time_in_queue_secs": 14.0,
    }
    mock_api.get_queue.return_value = mock_queue

    result = runner.invoke(app, ["backends", "queue", str(backend_type_id), "--user-only"])

    assert result.exit_code == 0, repr(result.exception)
    assert f"Retrieving queue for backend type with ID '{backend_type_id}'..." in result.stdout
    mock_api.get_queue.assert_called_once_with(backend_type_id=backend_type_id, user_only=True)


# ---------------------------------------------------------------------------
# Jobs: run
# ---------------------------------------------------------------------------


def test_run_job_with_file(mock_api: MagicMock) -> None:
    result = runner.invoke(app, ["run", "--file", "path/to/file"])

    assert result.exit_code == 0, repr(result.exception)
    mock_api.execute_algorithm.assert_called_once_with(Path("path/to/file"), None, None, False, None, False)


def test_run_job_no_file(mock_api: MagicMock) -> None:
    result = runner.invoke(app, ["run"])

    assert result.exit_code == 0, repr(result.exception)
    mock_api.execute_algorithm.assert_called_once_with(None, None, None, False, None, False)


def test_run_job_with_all_options(mock_api: MagicMock) -> None:
    result = runner.invoke(
        app,
        [
            "run",
            "--file",
            "path/to/file",
            "--backend-type-id",
            "1",
            "--num-shots",
            "100",
            "--name",
            "my-algo",
            "--store-raw-data",
            "--persist",
        ],
    )

    assert result.exit_code == 0, repr(result.exception)
    mock_api.execute_algorithm.assert_called_once_with(Path("path/to/file"), 1, 100, True, "my-algo", True)


def test_run_job_with_persist(mock_api: MagicMock) -> None:
    result = runner.invoke(app, ["run", "--file", "path/to/file", "--persist"])

    assert result.exit_code == 0, repr(result.exception)
    assert "The project and algorithm have been stored." in result.stdout
    mock_api.execute_algorithm.assert_called_once_with(Path("path/to/file"), None, None, False, None, True)


def test_run_job_with_name(mock_api: MagicMock) -> None:
    result = runner.invoke(app, ["run", "--name", "my-algorithm"])

    assert result.exit_code == 0, repr(result.exception)
    mock_api.execute_algorithm.assert_called_once_with(None, None, None, False, "my-algorithm", False)


def test_run_job_with_store_raw_data(mock_api: MagicMock) -> None:
    result = runner.invoke(
        app,
        ["run", "--file", "path/to/file", "--backend-type-id", "1", "--store-raw-data"],
    )

    assert result.exit_code == 0, repr(result.exception)
    mock_api.execute_algorithm.assert_called_once_with(Path("path/to/file"), 1, None, True, None, False)


# ---------------------------------------------------------------------------
# Jobs: inspect
# ---------------------------------------------------------------------------


def test_inspect_job(mock_api: MagicMock) -> None:
    mock_job = MagicMock()
    mock_job.id = 123
    mock_job.status.value = "RUNNING"
    mock_job.algorithm_type.value = "HYBRID"
    mock_job.queued_at = None
    mock_job.finished_at = None
    mock_job.number_of_shots = 100
    mock_job.message = None
    mock_job.source = None
    mock_job.session_id = "session-123"
    mock_job.trace_id = "trace-123"
    mock_api.get_job.return_value = mock_job

    result = runner.invoke(app, ["jobs", "inspect", "123"])

    assert result.exit_code == 0, repr(result.exception)
    assert "Retrieving job with ID '123'..." in result.stdout
    mock_api.get_job.assert_called_once_with(123)


def test_inspect_job_all_fields(mock_api: MagicMock) -> None:
    mock_job = MagicMock()
    mock_job.id = 42
    mock_job.status.value = "COMPLETED"
    mock_job.algorithm_type.value = "QUANTUM"
    mock_job.queued_at = datetime(2024, 1, 1, 10, 0, 0)
    mock_job.finished_at = datetime(2024, 1, 1, 10, 5, 0)
    mock_job.number_of_shots = 1024
    mock_job.message = "Success"
    mock_job.source = "cli"
    mock_job.session_id = "sess-abc"
    mock_job.trace_id = "trace-abc"
    mock_api.get_job.return_value = mock_job

    result = runner.invoke(app, ["jobs", "inspect", "42"])

    assert result.exit_code == 0, repr(result.exception)
    assert "COMPLETED" in result.stdout


def test_inspect_job_requires_id() -> None:
    result = runner.invoke(app, ["jobs", "inspect"])

    assert result.exit_code != 0


# ---------------------------------------------------------------------------
# Jobs: status
# ---------------------------------------------------------------------------


def test_get_job_status_with_job_id(mock_api: MagicMock) -> None:
    mock_status = MagicMock()
    mock_status.value = "COMPLETED"
    mock_api.get_job_status.return_value = mock_status

    result = runner.invoke(app, ["jobs", "status", "123"])

    assert result.exit_code == 0, repr(result.exception)
    assert "Job 123 status: 'COMPLETED'" in result.stdout
    mock_api.get_job_status.assert_called_once_with(None, 123, False, 60.0)


def test_get_job_status_with_wait(mock_api: MagicMock) -> None:
    mock_status = MagicMock()
    mock_status.value = "COMPLETED"
    mock_api.get_job_status.return_value = mock_status

    result = runner.invoke(app, ["jobs", "status", "123", "--wait"])

    assert result.exit_code == 0, repr(result.exception)
    mock_api.get_job_status.assert_called_once_with(None, 123, True, 60.0)


def test_get_job_status_with_custom_timeout(mock_api: MagicMock) -> None:
    mock_status = MagicMock()
    mock_status.value = "RUNNING"
    mock_api.get_job_status.return_value = mock_status

    result = runner.invoke(app, ["jobs", "status", "123", "--timeout", "120"])

    assert result.exit_code == 0, repr(result.exception)
    mock_api.get_job_status.assert_called_once_with(None, 123, False, 120.0)


def test_get_job_status_requires_id() -> None:
    result = runner.invoke(app, ["jobs", "status"])

    assert result.exit_code != 0


# ---------------------------------------------------------------------------
# Jobs: results
# ---------------------------------------------------------------------------


def test_get_results_with_job_id(mock_api: MagicMock) -> None:
    mock_result = MagicMock()
    mock_result.model_dump.return_value = {"id": 1}
    mock_api.get_results.return_value = [mock_result]

    result = runner.invoke(app, ["jobs", "results", "456"])

    assert result.exit_code == 0, repr(result.exception)
    assert "Retrieving results for job with ID '456'..." in result.stdout
    mock_api.get_results.assert_called_once_with(None, 456)


def test_get_results_return_empty(mock_api: MagicMock) -> None:
    mock_api.get_results.return_value = []
    result = runner.invoke(app, ["jobs", "results", "456"])

    assert result.exit_code == 0, repr(result.exception)
    assert "[]" in result.stdout


def test_get_results_save(mock_api: MagicMock, tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    mock_result = MagicMock()
    mock_result.model_dump_json.return_value = '{"id": 1}'
    mock_api.get_results.return_value = [mock_result]
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["jobs", "results", "456", "--save"])

    assert result.exit_code == 0, repr(result.exception)
    assert "Saving results to" in result.stdout


def test_get_results_save_empty(mock_api: MagicMock, tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    mock_api.get_results.return_value = []
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["jobs", "results", "456", "--save"])

    assert result.exit_code == 0, repr(result.exception)


def test_get_results_empty_no_save(mock_api: MagicMock) -> None:
    """Test that empty results are printed as empty list when not saving."""
    mock_api.get_results.return_value = []

    result = runner.invoke(app, ["jobs", "results", "456"])

    assert result.exit_code == 0, repr(result.exception)
    assert "[]" in result.stdout


def test_get_results_requires_id() -> None:
    result = runner.invoke(app, ["jobs", "results"])

    assert result.exit_code != 0


# ---------------------------------------------------------------------------
# Jobs: final-result
# ---------------------------------------------------------------------------


def test_get_final_result_with_job_id(mock_api: MagicMock) -> None:
    mock_final_result = MagicMock()
    mock_final_result.model_dump.return_value = {"id": 1}
    mock_api.get_final_result.return_value = mock_final_result

    result = runner.invoke(app, ["jobs", "final-result", "789"])

    assert result.exit_code == 0, repr(result.exception)
    assert "Retrieving final result for job with ID '789'..." in result.stdout
    mock_api.get_final_result.assert_called_once_with(None, 789)


def test_get_final_result_save(mock_api: MagicMock, tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    mock_final_result = MagicMock()
    mock_final_result.model_dump_json.return_value = '{"id": 1}'
    mock_api.get_final_result.return_value = mock_final_result
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["jobs", "final-result", "789", "--save"])

    assert result.exit_code == 0, repr(result.exception)
    assert "Saving final result to" in result.stdout


def test_get_final_result_none_no_save(mock_api: MagicMock) -> None:
    """Test that None final result is printed as 'None' when not saving."""
    mock_api.get_final_result.return_value = None

    result = runner.invoke(app, ["jobs", "final-result", "789"])

    assert result.exit_code == 0, repr(result.exception)
    assert "None" in result.stdout


def test_get_final_result_requires_id() -> None:
    result = runner.invoke(app, ["jobs", "final-result"])

    assert result.exit_code != 0


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


def test_set_local_config_string_value(mock_api: MagicMock) -> None:
    result = runner.invoke(app, ["config", "set", "key", "value"])

    assert result.exit_code == 0, repr(result.exception)
    assert "Configuration 'key' set to 'value'." in result.stdout
    mock_api.set_setting.assert_called_once_with("key", "value", is_user=False)


def test_set_local_config_int_value(mock_api: MagicMock) -> None:
    result = runner.invoke(app, ["config", "set", "key", "42"])

    assert result.exit_code == 0, repr(result.exception)
    assert "Configuration 'key' set to '42'." in result.stdout
    mock_api.set_setting.assert_called_once_with("key", 42, is_user=False)


def test_set_user_config(mock_api: MagicMock) -> None:
    result = runner.invoke(app, ["config", "set", "--user", "user_key", "user_value"])

    assert result.exit_code == 0, repr(result.exception)
    assert "User configuration 'user_key' set to 'user_value'." in result.stdout
    mock_api.set_setting.assert_called_once_with("user_key", "user_value", is_user=True)


def test_set_algorithm_config(mock_api: MagicMock) -> None:
    result = runner.invoke(app, ["config", "set", "key", "value", "--algorithm", "my-algo"])

    assert result.exit_code == 0, repr(result.exception)
    assert "Configuration 'key' for 'my-algo' set to 'value'." in result.stdout
    mock_api.set_algorithm_setting.assert_called_once_with("my-algo", "key", "value")


def test_get_local_config(mock_api: MagicMock) -> None:
    mock_api.get_setting.return_value = "value"

    result = runner.invoke(app, ["config", "get", "key"])

    assert result.exit_code == 0, repr(result.exception)
    assert "'key': value" in result.stdout
    mock_api.get_setting.assert_called_once_with("key")


def test_get_algorithm_config(mock_api: MagicMock) -> None:
    mock_api.get_algorithm_setting.return_value = "algo_value"

    result = runner.invoke(app, ["config", "get", "key", "--algorithm", "my-algo"])

    assert result.exit_code == 0, repr(result.exception)
    assert "'key' for 'my-algo': algo_value" in result.stdout
    mock_api.get_algorithm_setting.assert_called_once_with("my-algo", "key")
