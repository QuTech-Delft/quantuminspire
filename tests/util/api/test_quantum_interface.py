from unittest.mock import Mock

import pytest

from quantuminspire.sdk.quantum_interface import QuantumInterface
from quantuminspire.util.api.quantum_interface import ExecuteCircuitResult


@pytest.fixture
def local_backend() -> Mock:
    local_backend = Mock()

    def run_quantum(_circuit: str, number_of_shots: int) -> ExecuteCircuitResult:
        return ExecuteCircuitResult(results={}, shots_requested=number_of_shots, shots_done=number_of_shots)

    local_backend.run_quantum = Mock(side_effect=run_quantum)
    return local_backend


async def test_quantum_interface(local_backend: Mock) -> None:
    qi = QuantumInterface(local_backend)
    result = qi.execute_circuit("circuit", 1)
    assert result.shots_done == 1
    local_backend.run_quantum.assert_called_once()
