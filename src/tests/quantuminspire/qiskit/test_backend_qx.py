""" Quantum Inspire SDK

Copyright 2018 QuTech Delft

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

"""

import io
import unittest
from unittest.mock import Mock, patch

from quantuminspire.qiskit.backend_qx import QiSimulatorPy
from quantuminspire.exceptions import QisKitBackendError


class TestQiSimulatorPy(unittest.TestCase):

    def test_run_ReturnsCorrectResult(self):
        api = Mock()
        result_mock = Mock()
        with patch.object(QiSimulatorPy, "_run_circuit", return_value=result_mock) as run_circuit_mock:
            simulator = QiSimulatorPy(api)
            test_name = 'Test'
            operations = [{'name': 'CX'}, {'name': 'measure'}]
            job = {
                'circuits': [{
                    'compiled_circuit': {'operations': operations},
                    'name': test_name}],
                'config': {'shots': 2},
                'id': 1
            }
            result = simulator.run(job)
            self.assertEqual(result._result['id'], job['id'])
            self.assertEqual(result._result['result'], [result_mock])

    def test_run_circuit_RaisesSimulationError(self):
        operations = [{'name': 'CX'}]
        circuit = {
            'compiled_circuit': {'operations': operations},
            'name': 'Test'
        }
        with unittest.mock.patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            with patch.object(QiSimulatorPy, "_generate_cqasm") as generate_mock:
                api = Mock()
                api.execute_qasm.return_value = {'histogram': []}
                simulator = QiSimulatorPy(api)
                self.assertRaises(QisKitBackendError, simulator._run_circuit, circuit)
                generate_mock.assert_called_once_with(circuit['compiled_circuit'])

    def test_run_circuit_returns_correctValue(self):
        operations = [{'name': 'CX'}]
        circuit_name = 'TestName'
        circuit = {
            'compiled_circuit': {'operations': operations},
            'name': circuit_name
        }
        with unittest.mock.patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            with patch.object(QiSimulatorPy, "_generate_cqasm") as generate_mock:
                api = Mock()
                api.execute_qasm.return_value = {'histogram': {'001': 5, '111': 4}}
                simulator = QiSimulatorPy(api)
                simulator.number_of_shots = 2
                executed_circuit = simulator._run_circuit(circuit)
        self.assertEqual(executed_circuit['data']['counts']['001'], 10)
        self.assertEqual(executed_circuit['data']['counts']['111'], 8)
        self.assertEqual(executed_circuit['name'], circuit_name)
        self.assertEqual(executed_circuit['shots'], simulator.number_of_shots)

    def test_validate_RaisesValueError(self):
        api = Mock()
        simulator = QiSimulatorPy(api, logger=Mock())
        job = {'circuits': None, 'config': {'shots': 1}}
        self.assertRaises(QisKitBackendError, simulator.run, job)

    def test_validate_no_measure_LogsWarningCorrectly(self):
        api = Mock()
        log_mock = Mock()
        with patch.object(QiSimulatorPy, "_run_circuit",
                          return_value=Mock()) as run_circuit_mock:
            simulator = QiSimulatorPy(api, logger=log_mock)
            test_name = 'Test'
            operations = [{'name': 'CX'}]
            job = {
                'circuits': [{
                    'compiled_circuit': {'operations': operations},
                    'name': test_name}],
                'config': {'shots': 2},
                'id': 1
            }
            simulator.run(job)
        reply = "No measurements in circuit '%s', classical register will remain all zeros."
        log_mock.warning.assert_called_with(reply, test_name)
