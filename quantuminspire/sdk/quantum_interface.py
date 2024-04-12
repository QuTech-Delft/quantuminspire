"""Quantum Inspire SDK.

Copyright 2022 QuTech Delft

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the
License. You may obtain a copy of the License at

https://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an
"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific
language governing permissions and limitations under the License.
"""

from typing import TYPE_CHECKING, Any, List

from quantuminspire.util.api.quantum_interface import ExecuteCircuitResult, QuantumInterface as QuantumInterfaceProtocol

if TYPE_CHECKING:  # pragma: no cover
    from quantuminspire.util.api.local_backend import LocalBackend


class QuantumInterface(QuantumInterfaceProtocol):
    """Quantum Interface implementation for running quantum circuits from hybrid algorithms."""

    # pylint: disable = R0903
    # R0903: Too few public methods (1/2) (too-few-public-methods)

    def __init__(self, backend: "LocalBackend"):
        self.backend = backend
        self.results: List[Any] = []

    def execute_circuit(self, circuit: str, number_of_shots: int) -> ExecuteCircuitResult:
        """Execute a quantum circuit."""
        results = self.backend.run_quantum(circuit, number_of_shots)
        self.results.append(results.results)
        return results
