import os
import shutil
import subprocess
import uuid
from pathlib import Path
from typing import Generator, cast

import pytest
from compute_api_client import BackendType

from quantuminspire.api import Api


@pytest.fixture(scope="session")
def backend_name() -> str:
    return os.getenv("BACKEND_NAME", "")


@pytest.fixture(scope="session")
def quantum_circuit_file_path() -> Path:
    return Path(__file__).parent / "data_files/circuit.cq"


@pytest.fixture(scope="session")
def api() -> Generator[Api, None, None]:
    api = Api()
    yield api


@pytest.fixture(scope="session")
def backend_type(backend_name: str, api: Api) -> BackendType:
    backend_types = api.get_backend_types()
    backend_type = [backend_type for backend_type in backend_types if backend_type.name == backend_name]
    return backend_type[0]


def test_execute_algorithm_no_persist_flow(
    backend_type: BackendType, quantum_circuit_file_path: Path, api: Api
) -> None:

    job_options = api.execute_algorithm(file_path=quantum_circuit_file_path, backend_type_id=backend_type.id)

    _ = api.get_job_status(job_id=job_options.job_id, wait=True)

    results = api.get_results(job_id=job_options.job_id)

    final_result = api.get_final_result(job_id=job_options.job_id)

    assert final_result is not None
    assert results


def test_execute_algorithm_persist_flow(api: Api, quantum_circuit_file_path: Path, backend_type: BackendType) -> None:

    random_str = str(uuid.uuid4().hex[:8])
    project_name = f"E2E CLI {random_str}"
    algorithm_name = f"test_algorithm_{random_str}"
    project_config_dir = Path(__file__).parent.parent / ".quantuminspire"

    if project_config_dir.exists():
        shutil.rmtree(project_config_dir)

    try:
        projects = api.initialize_project(project_name=project_name)
        projects = api.get_projects(name=project_name, exact=True)
        assert projects[0].name == project_name
        assert project_config_dir.exists()

        _ = api.execute_algorithm(
            algorithm_name=algorithm_name,
            file_path=quantum_circuit_file_path,
            backend_type_id=backend_type.id,
            persist=True,
        )

        assert api.get_setting("project.name") == project_name
        assert (
            api.get_algorithm_setting(algorithm_name=algorithm_name, setting_name="file_path")
            == quantum_circuit_file_path
        )

        _ = api.get_job_status(algorithm_name=algorithm_name, wait=True)

        results = api.get_results(algorithm_name=algorithm_name)

        final_result = api.get_final_result(algorithm_name=algorithm_name)

        assert final_result is not None
        assert results

        api.delete_projects(project_ids=[], name=project_name, exact=True)

        projects = api.get_projects(name=project_name, exact=True)
        assert not projects
    finally:
        if project_config_dir.exists():
            shutil.rmtree(project_config_dir)


def test_get_logs(backend_type: BackendType, api: Api) -> None:

    hybrid_file = Path(__file__).parent / "data_files/hqca_circuit.py"

    job_options = api.execute_algorithm(file_path=hybrid_file, backend_type_id=backend_type.id)

    _ = api.get_job_status(job_id=job_options.job_id, wait=True)

    job_id = cast(int, job_options.job_id)

    logs = api.get_job_logs(job_id=job_id)

    assert logs


def test_get_queue(backend_type: BackendType, api: Api) -> None:

    queue = api.get_queue(backend_type_id=backend_type.id)

    assert queue is not None


def test_compile_file(backend_type: BackendType, quantum_circuit_file_path: Path, api: Api) -> None:

    path = Path(__file__).parent / "data_files/circuit_compiled_decomposition.cq"
    path.unlink(missing_ok=True)

    try:
        api.compile_file(file_path=quantum_circuit_file_path, backend_type_id=backend_type.id)
        assert path.exists()
    finally:
        path.unlink(missing_ok=True)


def test_run_jupyter_notebook_clean() -> None:
    notebook_path = Path(__file__).parent / "data_files/notebook.ipynb"

    result = subprocess.run(
        [
            "poetry",
            "run",
            "jupyter",
            "nbconvert",
            "--to",
            "notebook",
            "--execute",
            "--ExecutePreprocessor.timeout=60",
            "--output",
            "/tmp/test_output.ipynb",
            str(notebook_path),
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
