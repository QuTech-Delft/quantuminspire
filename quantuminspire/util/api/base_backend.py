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
from typing import Any

from quantuminspire.sdk.models.base_algorithm import BaseAlgorithm


class BaseBackend(ABC):
    """Base interface for backends.

    A backend will execute the hybrid algorithm, or quantum circuit provided.
    """

    @abstractmethod
    def run(self, program: BaseAlgorithm, backend_type_id: int) -> int:
        """Execute provided algorithm/circuit."""
        raise NotImplementedError

    @abstractmethod
    def get_results(self, job_id: int) -> Any:
        """Get results for algorithm/circuit."""
        raise NotImplementedError
