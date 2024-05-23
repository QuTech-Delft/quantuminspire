from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from quantuminspire.sdk.models.circuit import Circuit
from quantuminspire.sdk.models.hybrid_algorithm import HybridAlgorithm
from quantuminspire.util.api.local_backend import LocalBackend
from quantuminspire.util.api.quantum_interface import ExecuteCircuitResult


@pytest.fixture
def qxelarator() -> Mock:
    qxelarator = Mock()

    def execute_string(_circuit: str, iterations: int) -> SimpleNamespace:
        return SimpleNamespace(results={}, shots_requested=iterations, shots_done=iterations, state={})

    qxelarator.execute_string = Mock(side_effect=execute_string)
    return qxelarator


@pytest.fixture
def quantum_interface() -> Mock:
    quantum_interface = Mock()

    def execute_circuit(_circuit: str, number_of_shots: int) -> ExecuteCircuitResult:
        return ExecuteCircuitResult(results={}, shots_requested=number_of_shots, shots_done=number_of_shots)

    quantum_interface.execute_circuit = Mock(side_effect=execute_circuit)
    return quantum_interface


class MockLocalBackend(LocalBackend):
    run_quantum = Mock(
        spec=LocalBackend.run_quantum, return_value=ExecuteCircuitResult(results={}, shots_requested=1, shots_done=1)
    )
    run_hybrid = Mock(spec=LocalBackend.run_hybrid, return_value={"test": "result"})


@pytest.fixture
def local_backend(qxelarator: Mock) -> MockLocalBackend:
    return MockLocalBackend(qxelarator)


def test_local_backend_run_quantum(qxelarator: Mock) -> None:
    backend = LocalBackend(qxelarator)
    result = backend.run_quantum("circuit", 1)
    assert result.shots_done == 1
    qxelarator.execute_string.assert_called_once()


def test_local_backend_run_hybrid(qxelarator: Mock, quantum_interface: Mock) -> None:
    backend = LocalBackend(qxelarator)
    file = Path("examples/hqca_circuit.py")
    algorithm = HybridAlgorithm("test", "Test")
    algorithm.read_file(file)
    backend.run_hybrid(algorithm, quantum_interface)


def test_local_backend_run_with_hybrid_algorithm(local_backend: MockLocalBackend) -> None:
    algorithm = HybridAlgorithm("test", "Test")
    job_id = local_backend.run(algorithm, 0)
    local_backend.run_hybrid.assert_called_once()
    results = local_backend.get_results(job_id)
    assert results == {"test": "result"}


def test_local_backend_run_with_quantum_algorithm(local_backend: MockLocalBackend) -> None:
    algorithm = Circuit("test", "Test", 2)
    job_id = local_backend.run(algorithm, 0)
    local_backend.run_hybrid.assert_called_once()
    results = local_backend.get_results(job_id)
    assert results == ExecuteCircuitResult(results={}, shots_requested=1, shots_done=1)
