"""Quantum Inspire SDK.

Copyright 2022 QuTech Delft

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the
License. You may obtain a copy of the License at

https://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an
"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific
language governing permissions and limitations under the License.
"""

import importlib
import sys
import types
from enum import IntEnum
from typing import Any, Union

from quantuminspire.sdk.models.base_algorithm import BaseAlgorithm
from quantuminspire.sdk.models.circuit import Circuit
from quantuminspire.sdk.models.hybrid_algorithm import HybridAlgorithm
from quantuminspire.sdk.quantum_interface import QuantumInterface
from quantuminspire.util.api.base_backend import BaseBackend
from quantuminspire.util.api.quantum_interface import ExecuteCircuitResult, QuantumInterface as QuantumInterfaceProtocol


def import_qxelarator() -> types.ModuleType:  # pragma: no cover
    """Helper function for importing optional dependency qxelarator."""

    try:
        return importlib.import_module("qxelarator")
    except ModuleNotFoundError as exc:
        print(
            "Error: Dependencies for local execution not installed, install with 'pip install quantuminspire[local]'",
            file=sys.stderr,
        )
        raise SystemExit from exc


class LocalBackend(BaseBackend):
    """Connection to remote backend.

    Create a connection with the remote backend for Quantum Inspire. This connection creates the appropriate projects,
    algorithms, files etc. The algorithm/circuit will also be run.
    """

    class JobFakeID(IntEnum):
        """Helper to conform to BaseBackend interface of returning job IDs."""

        QUANTUM = -1
        HYBRID = -2

    def __init__(self, qxelarator: Union[types.ModuleType, None] = None) -> None:
        super().__init__()
        self._quantum_results: Union[ExecuteCircuitResult, None] = None
        self._hybrid_results: Union[Any, None] = None
        self._qxelarator = qxelarator if qxelarator else import_qxelarator()

    def run(self, program: BaseAlgorithm, backend_type_id: int) -> int:
        """Execute provided algorithm/circuit."""
        if isinstance(program, HybridAlgorithm):
            quantum_interface = QuantumInterface(self)
            self._hybrid_results = self.run_hybrid(program, quantum_interface)
            return self.JobFakeID.HYBRID
        if isinstance(program, Circuit):
            self._quantum_results = self.run_quantum(program.content)
            return self.JobFakeID.QUANTUM
        raise AssertionError("Unknown algorithm type")

    def run_hybrid(self, algorithm: HybridAlgorithm, quantum_interface: QuantumInterfaceProtocol) -> Any:
        """Execute provided algorithm."""

        # pylint: disable = E1101, W0122
        # E1101: Instance of 'module' has no 'execute' member (no-member)
        # W0122: Use of exec (exec-used)

        program = types.ModuleType("mod")

        exec(algorithm.content, program.__dict__)

        if not hasattr(program, "execute") or not callable(program.execute):
            raise AssertionError("'execute' hook not found or not callable.")
        program.execute(quantum_interface)

        if not hasattr(program, "finalize") or not callable(program.finalize):
            raise AssertionError("'finalize' hook not found or not callable.")
        result = program.finalize(quantum_interface.results)
        if not isinstance(result, dict):
            raise AssertionError("'finalize' hook returned invalid type, must be dict.")
        return result

    def run_quantum(self, circuit: str, number_of_shots: int = 1) -> ExecuteCircuitResult:
        """Execute provided circuit."""
        result = self._qxelarator.execute_string(circuit, iterations=number_of_shots)
        return ExecuteCircuitResult(
            results=result.results,
            shots_done=result.shots_done,
            shots_requested=result.shots_requested,
        )

    def get_results(self, job_id: int) -> Any:
        """Get results for algorithm/circuit."""
        if job_id == self.JobFakeID.QUANTUM:
            return self._quantum_results
        if job_id == self.JobFakeID.HYBRID:
            return self._hybrid_results

        raise AssertionError("Unknown job id")
