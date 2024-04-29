from typing import Generator
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

from quantuminspire.sdk.models.circuit_v3 import CircuitV3

MOCK_QUANTUM_CIRCUIT = "quantum circuit"


@pytest.fixture
def CircuitBuilder(mocker: MockerFixture) -> Generator[MagicMock, None, None]:
    yield mocker.patch("quantuminspire.sdk.models.circuit_v3.CircuitBuilder")


def test_get_program_name(CircuitBuilder: MagicMock) -> None:
    with CircuitV3(platform_name="platform", program_name="program", number_of_qubits=2) as c:
        pass

    assert c.program_name == "program"


def test_get_platform_name(CircuitBuilder: MagicMock) -> None:
    with CircuitV3(platform_name="platform", program_name="program", number_of_qubits=2) as c:
        pass

    assert c.platform_name == "platform"


def test_get_content_type(CircuitBuilder: MagicMock) -> None:
    with CircuitV3(platform_name="platform", program_name="program", number_of_qubits=2) as c:
        pass

    assert c.content_type.value == "quantum"


def test_get_compile_stage(CircuitBuilder: MagicMock) -> None:
    with CircuitV3(platform_name="platform", program_name="program", number_of_qubits=2) as c:
        pass

    assert c.compile_stage.value == "none"


def test_create_empty_circuit(CircuitBuilder: MagicMock) -> None:
    cb = CircuitBuilder()
    cb.to_circuit.return_value = MOCK_QUANTUM_CIRCUIT
    with CircuitV3(platform_name="platform", program_name="program", number_of_qubits=2) as c:
        pass

    cb.to_circuit.assert_called_once()
    assert c.content == MOCK_QUANTUM_CIRCUIT
