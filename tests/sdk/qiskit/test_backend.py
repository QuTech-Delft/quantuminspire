"""Quantum Inspire SDK.

Copyright 2022 QuTech Delft

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the
License. You may obtain a copy of the License at
https://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import json
import unittest
from collections import OrderedDict
from unittest.mock import ANY, Mock, patch

import numpy as np
import pytest
from qiskit.circuit import ClassicalRegister, QuantumCircuit, QuantumRegister
from qiskit.compiler import assemble
from qiskit.providers.jobstatus import JobStatus
from qiskit.providers.models import QasmBackendConfiguration
from qiskit.providers.models.backendconfiguration import GateConfig
from qiskit.qobj import QasmQobjExperiment

from quantuminspire.sdk.qiskit.backend import QiskitQuantumInspireJob, QuantumInspireBackend
from quantuminspire.sdk.qiskit.exceptions import QiskitBackendError
from quantuminspire.sdk.qiskit.measurements import Measurements


class TestQiskitQuantumInspireJob(unittest.TestCase):

    def setUp(self): ...

    def test_create(self):
        q = QiskitQuantumInspireJob(Mock(), None, 1)
        assert q.status() == JobStatus.DONE

    def test_results(self):
        mock_result = Mock()
        mock_result.results = []
        mock_result.shots_done = 1024
        q = QiskitQuantumInspireJob(Mock(), None, 1)
        q.submit()
        q.add_result(mock_result)
        assert q.result()


class TestBackend:

    @pytest.fixture(scope="function")
    def backend(self) -> QuantumInspireBackend:
        return QuantumInspireBackend(Mock(), None)

    def test_default_configuration(self, backend):
        assert backend.backend_name == "quantum_inspire_2"
        assert backend.configuration().backend_version == "2.0"
        assert backend.configuration().n_qubits == 6
        backend.set_options(shots=1024)
        config = backend._get_run_config(extra="value")
        assert config["shots"] == 1024
        assert config["extra"] == "value"
        status = backend.status()
        assert status.backend_version == "2.0"
        assert status.backend_name == "quantum_inspire_2"
        assert status.pending_jobs == 0
        assert status.operational == True
        assert status.status_msg == "online"

    def test_run_normal(self, backend):
        qc = QuantumCircuit(2, 2)
        qc.h(0)
        qc.cx(0, 1)
        qc.measure([0, 1], [0, 1])

        job = backend.run(qc)
        assert job

    def test_run_normal_not_conditional(self, backend):
        backend.configuration().conditional = False
        qc = QuantumCircuit(2, 4)
        qc.h(0)
        qc.cx(0, 1)
        qc.measure([0, 1], [0, 1])

        job = backend.run(qc)
        assert job

    def test_invalid_shots(self, backend):
        backend.set_options(shots=0)
        with pytest.raises(QiskitBackendError):
            backend.run(QuantumCircuit(2, 2))

    def test_invalid_memory_slots(self, backend):
        backend.configuration().conditional = True
        with pytest.raises(QiskitBackendError):
            qc = QuantumCircuit(2, 4)
            c = ClassicalRegister(4, "c")
            qc.h(1)
            qc.cx(0, 1).c_if(c, 1)
            qc.measure([0, 1], [0, 1])
            backend.run(qc)

    def test_valid_memory_slots(self, backend):
        backend.configuration().conditional = True
        qc = QuantumCircuit(2, 4)
        qc.h(1)
        qc.cx(0, 1)
        qc.measure([0, 1], [0, 1])
        backend.run(qc)
