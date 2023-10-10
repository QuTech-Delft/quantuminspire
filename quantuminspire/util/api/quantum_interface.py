"""Quantum Inspire SDK.

Copyright 2022 QuTech Delft

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the
License. You may obtain a copy of the License at

https://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an
"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific
language governing permissions and limitations under the License.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List

from pydantic import BaseModel


class ExecuteCircuitResult(BaseModel):
    """Result of executing a quantum circuit."""

    results: Dict[str, float]
    shots_requested: int
    shots_done: int


class QuantumInterface(ABC):
    """Interface for running quantum circuits from hybrid algorithms."""

    # pylint: disable = R0903
    # Too few public methods (1/2) (too-few-public-methods)

    results: List[Any]

    @abstractmethod
    def execute_circuit(self, circuit: str, number_of_shots: int) -> ExecuteCircuitResult:
        """Execute a quantum circuit."""
        raise NotImplementedError
