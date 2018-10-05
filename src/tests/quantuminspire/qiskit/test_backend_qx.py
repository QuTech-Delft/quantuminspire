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

from quantuminspire.api import QuantumInspireAPI
from quantuminspire.exceptions import QisKitBackendError
from quantuminspire.qiskit.backend_qx import QiSimulatorPy


class TestQiSimulatorPy(unittest.TestCase):

    def test_run_ReturnsCorrectResult(self):
        api = Mock()
        result_mock = Mock()
        with patch.object(QiSimulatorPy, "_run_circuit", return_value=result_mock):
            simulator = QiSimulatorPy(api)
            test_name = 'Test'
            operations = [{'name': 'CX'}, {'name': 'measure'}]
            job = {
                'circuits': [{
                    'compiled_circuit': {'operations': operations, 'header': {'number_of_qubits': 2,
                                                                              'number_of_clbits': 2}},
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
            'compiled_circuit': {'operations': operations, 'header': {'number_of_qubits': 2}},
            'name': 'Test'
        }
        number_of_shots = 100
        with unittest.mock.patch('sys.stdout', new_callable=io.StringIO):
            with patch.object(QiSimulatorPy, "_generate_cqasm") as generate_mock:
                api = Mock()
                api.execute_qasm.return_value = {'histogram': []}
                simulator = QiSimulatorPy(api)
                self.assertRaises(QisKitBackendError, simulator._run_circuit, circuit, number_of_shots)
                generate_mock.assert_called_once_with(circuit['compiled_circuit'])

    def test_run_circuit_returns_correctValue(self):
        operations = [{'name': 'CX'}]
        circuit_name = 'TestName'
        circuit = {
            'compiled_circuit': {
                'operations': operations, 'header': {
                    'number_of_qubits': 2, 'number_of_clbits': 2
                }
            },
            'name': circuit_name
        }
        number_of_shots = 100
        with unittest.mock.patch('sys.stdout', new_callable=io.StringIO):
            with patch.object(QiSimulatorPy, "_generate_cqasm"):
                api = Mock()
                api.execute_qasm.return_value = {'histogram': {'1': 0.5, '3': 0.4}}
                simulator = QiSimulatorPy(api)
                executed_circuit = simulator._run_circuit(circuit, number_of_shots)
        self.assertEqual(executed_circuit['data']['counts']['01'], 50)
        self.assertEqual(executed_circuit['data']['counts']['11'], 40)
        self.assertEqual(executed_circuit['name'], circuit_name)
        self.assertEqual(executed_circuit['shots'], number_of_shots)

    def test_validate_NegativeShotCount(self):
        simulator = QiSimulatorPy(Mock(), logger=Mock())
        job = {'circuits': None, 'config': {'shots': 0}}
        self.assertRaises(QisKitBackendError, simulator.run, job)

    def test_validate_NoClassicalQubits(self):
        simulator = QiSimulatorPy(Mock(), logger=Mock())
        job = {
            'circuits': [
                {'compiled_circuit': {
                    'operations': None, 'header': {'number_of_clbits': 0}}}],
            'config': {'shots': 2}}
        self.assertRaises(QisKitBackendError, simulator.run, job)

    def test_validate_OperationAfterMeasure(self):
        with patch.object(QiSimulatorPy, "_run_circuit", return_value=Mock()):
            simulator = QiSimulatorPy(Mock(), logger=Mock())
            operations = [{'name': 'CX'}, {'name': 'measure'}, {'name': 'X'}]
            job = {
                'circuits': [
                    {'compiled_circuit': {
                        'operations': operations, 'header': {'number_of_qubits': 2, 'number_of_clbits': 2}},
                        'name': 'Test'}],
                'config': {'shots': 2},
                'id': 1}
            self.assertRaises(QisKitBackendError, simulator.run, job)


class TestQiSimulatorPyHistogram(unittest.TestCase):
    def setUp(self):
        self.mock_api = Mock(spec=QuantumInspireAPI)
        self.simulator = QiSimulatorPy(self.mock_api)

        self.job = {
            'id': 23,
            'config': {
                'shots': 1000,
            },
            'circuits': [
                {
                    'compiled_circuit': {},
                    'name': 'TestName'
                },
            ],

        }

    def run_histogram_test(self, compiled_circuit, mock_result, expected_histogram):
        self.mock_api.execute_qasm.return_value = mock_result
        self.job['circuits'][0]['compiled_circuit'] = compiled_circuit

        result = self.simulator.run(self.job)

        self.assertEqual(1, len(result))
        actual = result[0]['data']['counts']
        self.assertDictEqual(expected_histogram, actual)

    def test_convert_histogram_NormalMeasurement(self):
        self.run_histogram_test(
            compiled_circuit={'operations': [{'name': 'h', 'params': [], 'texparams': [], 'qubits': [0]},
                                             {'name': 'cx', 'params': [], 'texparams': [], 'qubits': [0, 1]},
                                             {'name': 'measure', 'qubits': [0], 'clbits': [0]},
                                             {'name': 'measure', 'qubits': [1], 'clbits': [1]}],
                              'header': {'number_of_qubits': 2, 'number_of_clbits': 2,
                                         'qubit_labels': [['q0', 0], ['q0', 1]],
                                         'clbit_labels': [['c0', 0], ['c1', 1]]}
                              },
            mock_result={'histogram': {'0': 0.1, '1': 0.2, '2': 0.3, '3': 0.4}},
            expected_histogram={'00': 100.0, '01': 200.0, '10': 300.0, '11': 400.0}
        )

    def test_convert_histogram_SwappedClassicalQubits(self):
        self.run_histogram_test(
            compiled_circuit={'operations': [{'name': 'h', 'params': [], 'texparams': [], 'qubits': [0]},
                                             {'name': 'cx', 'params': [], 'texparams': [], 'qubits': [0, 1]},
                                             {'name': 'measure', 'qubits': [0], 'clbits': [1]},
                                             {'name': 'measure', 'qubits': [1], 'clbits': [0]}],
                              'header': {'number_of_qubits': 2, 'number_of_clbits': 2,
                                         'qubit_labels': [['q0', 0], ['q0', 1]],
                                         'clbit_labels': [['c0', 0], ['c1', 1]]}
                              },
            mock_result={'histogram': {'0': 0.1, '1': 0.2, '2': 0.3, '3': 0.4}},
            expected_histogram={'00': 100.0, '01': 300.0, '10': 200.0, '11': 400.0}
        )

    def test_convert_histogram_LessMeasurementsQubitOne(self):
        self.run_histogram_test(
            compiled_circuit={'operations': [{'name': 'h', 'params': [], 'texparams': [], 'qubits': [0]},
                                             {'name': 'cx', 'params': [], 'texparams': [], 'qubits': [0, 1]},
                                             {'name': 'measure', 'qubits': [0], 'clbits': [0]}],
                              'header': {'number_of_qubits': 2, 'number_of_clbits': 2,
                                         'qubit_labels': [['q0', 0], ['q0', 1]],
                                         'clbit_labels': [['c0', 0], ['c1', 1]]}
                              },
            mock_result={'histogram': {'0': 0.1, '1': 0.2, '2': 0.3, '3': 0.4}},
            expected_histogram={'0': 400.0, '1': 600.0}
        )

    def test_convert_histogram_LessMeasurementsQubitTwo(self):
        self.run_histogram_test(
            compiled_circuit={'operations': [{'name': 'h', 'params': [], 'texparams': [], 'qubits': [0]},
                                             {'name': 'cx', 'params': [], 'texparams': [], 'qubits': [0, 1]},
                                             {'name': 'measure', 'qubits': [1], 'clbits': [1]}],
                              'header': {'number_of_qubits': 2, 'number_of_clbits': 2,
                                         'qubit_labels': [['q0', 0], ['q0', 1]],
                                         'clbit_labels': [['c0', 0], ['c1', 1]]}
                              },
            mock_result={'histogram': {'0': 0.1, '1': 0.2, '2': 0.3, '3': 0.4}},
            expected_histogram={'0': 300.0, '1': 700.0}
        )

    def test_convert_histogram_ClassicalBitsMeasureSameQubits(self):
        with self.assertRaisesRegex(QisKitBackendError, 'Classical bit is used to measure multiple qubits!'):
            self.run_histogram_test(
                compiled_circuit={'operations': [{'name': 'h', 'params': [], 'texparams': [], 'qubits': [0]},
                                                 {'name': 'cx', 'params': [], 'texparams': [], 'qubits': [0, 1]},
                                                 {'name': 'measure', 'qubits': [0], 'clbits': [0]},
                                                 {'name': 'measure', 'qubits': [1], 'clbits': [0]}],
                                  'header': {'number_of_qubits': 2, 'number_of_clbits': 2,
                                             'qubit_labels': [['q0', 0], ['q0', 1]],
                                             'clbit_labels': [['c0', 0], ['c1', 1]]}
                                  },
                mock_result={'histogram': {'0': 0.1, '1': 0.2, '2': 0.3, '3': 0.4}},
                expected_histogram=None
            )
