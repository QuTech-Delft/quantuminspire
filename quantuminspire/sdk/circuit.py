"""Module containing the Quantum Circuit class."""
from pathlib import Path
from types import TracebackType
from typing import Optional, Type

import openql
from openql import Kernel, Platform, Program


class Circuit:
    """A container object, interacting with OpenQL and storing cQASM internally.

    A circuit wraps OpenQL to handle the boilerplate code for platform, program and kernels. These objects can still be
    used.
    """

    def __init__(self, platform_name: str, program_name: str) -> None:
        self._output_dir = Path(__file__).parent.absolute() / "output"
        openql.set_option("output_dir", str(self._output_dir))
        self._platform_name = platform_name
        self._program_name = program_name
        self._openql_platform = Platform(self._platform_name, "none")
        self._openql_program: Optional[Program] = None
        self._openql_kernels: list[Kernel] = []
        self._cqasm: str = ""

    @property
    def program_name(self) -> str:
        """Return the name of the quantum circuit.

        Returns:
            The string representation of the quantum circuit name.
        """
        return self._program_name

    @property
    def qasm(self) -> str:
        """Return the quantum circuit.

        Returns:
            The string representation of the quantum circuit.
        """
        return self._cqasm

    def __enter__(self) -> "Circuit":
        self.initialize()
        return self

    def __exit__(
        self, exc_type: Optional[Type[BaseException]], exc_val: Optional[BaseException], exc_tb: Optional[TracebackType]
    ) -> bool:
        self.finalize()
        return True

    def initialize(self) -> None:
        """Initialize the quantum circuit."""

    def finalize(self) -> None:
        """Finalize the quantum circuit.

        After finishing writing the quantum circuit various actions are performed to generate the actual cQASM circuit.
        First, the used number of qubits is determined, based on the various kernels. It is assumed that the qubits will
        be reused over the various kernels. This creates an OpenQL program, to which the various kernels are added.
        Finally, the program is compiled and the generated cQASM file is processed to an internal variable.
        """
        self._openql_program = openql.Program(self._program_name, self._openql_platform, self.max_number_of_qubits)
        for kernel in self._openql_kernels:
            self._openql_program.add_kernel(kernel)
        self._openql_program.compile()
        self._cqasm = self._process_cqasm_file()

    @property
    def max_number_of_qubits(self) -> int:
        """Determine the number of qubits over the various kernels.

        Returns:
            The maximum number of qubits used in the kernels, assuming that the qubits can be reused.
        """
        return int(max((kernel.qubit_count for kernel in self._openql_kernels), default=0))

    def _process_cqasm_file(self) -> str:
        """Read and remove the generated cQASM file.

        Returns:
            The content of the OpenQL generated cQASM file.
        """
        cqasm_file = self._output_dir / f"{self._program_name}.qasm"
        with open(cqasm_file, encoding="utf-8") as file_pointer:
            cqasm = file_pointer.read()
        Path.unlink(cqasm_file)
        return cqasm

    def init_kernel(self, name: str, number_of_qubits: int) -> Kernel:
        """Initialize an OpenQL kernel.

        A new OpenQL kernel is created and added to an internal list (ordered) of kernels. This list will be used to
        compile the final program (in order).

        Args:
            name: Name of the kernel.
            number_of_qubits: Number of qubits used in the kernel.

        Returns:
            The OpenQL kernel.
        """
        kernel = Kernel(name, self._openql_platform, number_of_qubits)
        self._openql_kernels.append(kernel)
        return kernel

    def add_kernel(self, kernel: Kernel) -> None:
        """Add an existing kernel to the list of kernels."""
        self._openql_kernels.append(kernel)
