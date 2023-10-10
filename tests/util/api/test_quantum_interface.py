from unittest.mock import Mock

import pytest

from quantuminspire.sdk.quantum_interface import QuantumInterface
from quantuminspire.util.api.quantum_interface import ExecuteCircuitResult


@pytest.fixture
def local_runtime() -> Mock:
    local_runtime = Mock()

    def run_quantum(_circuit: str, number_of_shots: int) -> ExecuteCircuitResult:
        return ExecuteCircuitResult(results={}, shots_requested=number_of_shots, shots_done=number_of_shots)

    local_runtime.run_quantum = Mock(side_effect=run_quantum)
    return local_runtime


async def test_quantum_interface(local_runtime: Mock) -> None:
    qi = QuantumInterface(local_runtime)
    result = qi.execute_circuit("circuit", 1)
    assert result.shots_done == 1
    local_runtime.run_quantum.assert_called_once()
