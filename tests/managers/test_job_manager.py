from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock

import pytest
from compute_api_client import Job

from quantuminspire.managers.auth_manager import AuthManager
from quantuminspire.managers.job_manager import JobManager, JobOptions


@pytest.fixture
def auth_manager() -> AuthManager:
    return AuthManager(MagicMock())


@pytest.fixture
def job_manager(auth_manager: AuthManager) -> JobManager:
    return JobManager(auth_manager)


def test_get_job(job_manager: JobManager) -> None:

    assert isinstance(job_manager.get_job(123), Job) == 1


def test_get_backend_types(job_manager: JobManager) -> None:

    assert len(job_manager.get_backend_types()) == 1


def test_get_final_result(job_manager: JobManager) -> None:

    assert job_manager.get_final_result(123) is None


def test_run_flow(job_manager: JobManager) -> None:

    options: Dict[str, Any] = {
        "file_path": Path.cwd(),
        "project_id": 1,
        "project_name": "some-project",
        "project_description": "some-project",
        "backend_type": 1,
        "number_of_shots": 1,
        "raw_data_enabled": False,
        "algorithm_name": "some-name",
    }

    job_options = job_manager.run_flow(JobOptions(**options))

    assert isinstance(job_options, JobOptions)
