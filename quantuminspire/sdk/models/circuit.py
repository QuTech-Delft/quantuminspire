"""Module containing the Quantum Circuit class."""

from types import TracebackType
from typing import Optional, Type

from compute_api_client import AlgorithmType, CompileStage
from opensquirrel import CircuitBuilder

from quantuminspire.sdk.models.base_algorithm import BaseAlgorithm


class Circuit(BaseAlgorithm):
    """A container object, interacting with OpenSquirrel and storing cQASM internally.

    A circuit wraps OpenSquirrel to handle the boilerplate code for the CircuitBuilder.
    """

    def __init__(
        self, platform_name: str, program_name: str, number_of_qubits: int, bit_registers: Optional[int] = None
    ) -> None:
        super().__init__(platform_name, program_name)
        self._number_of_qubits = number_of_qubits
        if bit_registers is None:
            bit_registers = number_of_qubits
        self._number_of_bit_registers = bit_registers
        self.ir = CircuitBuilder(qubit_register_size=number_of_qubits, bit_register_size=bit_registers)
        self._cqasm: str = ""

    @property
    def content(self) -> str:
        return self._cqasm

    @property
    def content_type(self) -> AlgorithmType:
        return AlgorithmType.QUANTUM

    @property
    def compile_stage(self) -> CompileStage:
        return CompileStage.NONE

    def __enter__(self) -> "Circuit":
        self.initialize()
        return self

    def __exit__(
        self, exc_type: Optional[Type[BaseException]], exc_val: Optional[BaseException], exc_tb: Optional[TracebackType]
    ) -> bool:
        self.finalize()
        return exc_type is None

    @property
    def language_name(self) -> str:
        return "cQASM"

    def initialize(self) -> None:
        """Initialize the quantum circuit."""

    def finalize(self) -> None:
        """Finalize the quantum circuit.

        After finishing writing the quantum circuit various actions are performed to generate the actual cQASM circuit.
        The circuit is converted to cQASM. Due to some differences between OpenSquirrel and QX, the casing of the gates
        need to be tweaked.
        """
        self._cqasm = str(self.ir.to_circuit())
        self._cqasm = (
            self._cqasm.replace("h", "H")
            .replace("cnot", "CNOT")
            .replace("x", "X")
            .replace("y", "Y")
            .replace("z", "Z")
            .replace("x90", "X90")
            .replace("mx90", "mX90")
            .replace("y90", "Y90")
            .replace("my90", "mY90")
            .replace("RZ", "Rz")
            .replace("RX", "Rx")
            .replace("cz", "CZ")
        )
