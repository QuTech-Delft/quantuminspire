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

import qiskit

from quantuminspire.api import QuantumInspireAPI
from quantuminspire.exceptions import QisKitBackendError
from quantuminspire.qiskit.backend_qx import QiSimulatorPy

def first_item(iterable):
    """ Return the first item from an iterable object """
    return next(iter(iterable))

class TestQiSimulatorPy(unittest.TestCase):

    def setUp(self):
        operations = []
        self._basic_job_dictionary = {'qobj_id': 'f9f944f5-9c9e-439e-a396-851d064cee29',
                                      'config': {'shots': 25, 'memory_slots': 2, 'max_credits': 10, 'n_qubits': 2},
                                      'experiments': [{'instructions': operations,
                                                       'header': {'number_of_qubits': 2, 'number_of_clbits': 2,
                                                                  'name': 'test',
                                                                  'compiled_circuit_qasm': 'dummy'},
                                                       'config': {'coupling_map': 'all-to-all',
                                                                  'basis_gates': 'x,y,z,h,s,cx,ccx,u1,u2,u3,id,snapshot',
                                                                  'n_qubits': 2}}],
                                      'header': {'backend_name': 'qi_simulator'},
                                      'type': 'QASM', 'schema_version': '1.0.0'}

    @staticmethod
    def _instructions_to_two_qubit_experiment(instructions):
        experiment_dict = {'instructions': instructions,
                           'header': {'number_of_qubits': 2,
                                      'number_of_clbits': 2,
                                      'name': 'circuit0',
                                      'compiled_circuit_qasm': ''},
                           'config': {'coupling_map': 'all-to-all',
                                      'basis_gates': 'x,y,z,h,s,cx,ccx,u1,u2,u3,id,snapshot',
                                      'n_qubits': 2}}
        experiment = qiskit.qobj.QobjExperiment.from_dict(experiment_dict)
        return experiment

    def test__collect_measurements(self):
        instructions = [{'name': 'cx', 'params': [], 'texparams': [], 'qubits': [0, 1]},
                        {'name': 'measure', 'qubits': [0], 'clbits': [1], 'memory': [0]},
                        {'name': 'measure', 'qubits': [1], 'clbits': [0], 'memory': [0]}]
        experiment = self._instructions_to_two_qubit_experiment(instructions)

        measurements = QiSimulatorPy._QiSimulatorPy__collect_measurements(experiment)
        self.assertEqual(measurements, [[1, 0], [0, 1]])

    def test__collect_measurements_without_measurements(self):
        instructions = [{'name': 'cx', 'params': [], 'texparams': [], 'qubits': [0, 1]}]
        experiment = self._instructions_to_two_qubit_experiment(instructions)

        measurements = QiSimulatorPy._QiSimulatorPy__collect_measurements(experiment)
        self.assertEqual(measurements, [[0, 0], [1, 1]])

    def test_run_ReturnsCorrectResult(self):
        api = Mock()
        result_mock = qiskit.qobj.ExperimentResult.from_dict({'success': True,
                                                              'shots': 25,
                                                              'data': {'counts': {'11': 13.0, '00': 12.0}, 'snapshots': {}},
                                                              'name': 'dummy_name',
                                                              'seed': None,
                                                              'status': 'DONE',
                                                              'time_taken': 8.021350860595703})
        with patch.object(QiSimulatorPy, "_run_experiment", return_value=result_mock):
            simulator = QiSimulatorPy(api)
            instructions = [{'name': 'cx', 'params': [], 'texparams': [], 'qubits': [0, 1]},
                            {'name': 'measure', 'qubits': [0]}]
            job_dict = self._basic_job_dictionary
            job_dict['experiments'][0]['instructions'] = instructions
            job = qiskit.qobj.Qobj.from_dict(job_dict)

            result = simulator.run(job)
            self.assertEqual(result.get_job_id(), job.qobj_id)
            first_experiment = first_item(result.results)
            self.assertEqual(result.results[first_experiment].data.as_dict(), result_mock.data.as_dict())

    def test_run_experiment_RaisesSimulationError_when_no_histogram(self):
        instructions = [{'name': 'CX'}]
        experiment = self._instructions_to_two_qubit_experiment(instructions)

        number_of_shots = 20
        with unittest.mock.patch('sys.stdout', new_callable=io.StringIO):
            with patch.object(QiSimulatorPy, "_generate_cqasm") as generate_mock:
                api = Mock()
                api.execute_qasm.return_value = {'histogram': []}
                simulator = QiSimulatorPy(api)
                self.assertRaisesRegex(QisKitBackendError, 'Result from backend contains no histogram data!',
                                       simulator._run_experiment, experiment, number_of_shots)
                generate_mock.assert_called_once_with(experiment)

    def test_run_circuit_returns_correctValue(self):
        number_of_shots = 100
        instructions = [{'name': 'h', 'params': [], 'texparams': [], 'qubits': [0]},
                        {'name': 'cx', 'params': [], 'texparams': [], 'qubits': [0, 1]},
                        {'name': 'measure', 'qubits': [1], 'clbits': [1], 'memory': [1]},
                        {'name': 'measure', 'qubits': [0], 'clbits': [0], 'memory': [0]}]
        experiment = self._instructions_to_two_qubit_experiment(instructions)

        with unittest.mock.patch('sys.stdout', new_callable=io.StringIO):
            with patch.object(QiSimulatorPy, "_generate_cqasm"):
                api = Mock()
                api.execute_qasm.return_value = {'histogram': {'1': 0.5, '3': 0.4}}
                simulator = QiSimulatorPy(api)
                experiment_result = simulator._run_experiment(experiment, number_of_shots)
        self.assertEqual(experiment_result.data['counts']['01'], 50)
        self.assertEqual(experiment_result.data['counts']['11'], 40)
        self.assertEqual(experiment_result.name, 'circuit0')
        self.assertEqual(experiment_result.shots, number_of_shots)

    def test_validate_NegativeShotCount(self):
        simulator = QiSimulatorPy(Mock(), logger=Mock())
        job_dict = self._basic_job_dictionary
        job_dict['config']['shots'] = 0
        job = qiskit.qobj.Qobj.from_dict(job_dict)

        self.assertRaises(QisKitBackendError, simulator.run, job)

    def test_validate_NoClassicalQubits(self):
        simulator = QiSimulatorPy(Mock(), logger=Mock())

        job_dict = self._basic_job_dictionary
        job_dict['experiments'][0]['instructions'] = None
        job_dict['experiments'][0]['header']['number_of_clbits'] = 0
        job = qiskit.qobj.Qobj.from_dict(job_dict)

        self.assertRaises(QisKitBackendError, simulator.run, job)

    def test_validate_OperationAfterMeasure(self):
        with patch.object(QiSimulatorPy, "_run_experiment", return_value=Mock()):
            simulator = QiSimulatorPy(Mock(), logger=Mock())
            instructions = [{'name': 'CX', 'qubits': [0]}, {'name': 'measure', 'qubits': [0]},
                            {'name': 'X', 'qubits': [0]}]
            job_dict = self._basic_job_dictionary
            job_dict['experiments'][0]['instructions'] = instructions
            job = qiskit.qobj.Qobj.from_dict(job_dict)
            self.assertRaises(QisKitBackendError, simulator.run, job)

    def test_no_operation_after_measure_cx_gate(self):
        with patch.object(QiSimulatorPy, "_run_experiment", return_value=Mock()):
            simulator = QiSimulatorPy(Mock(), logger=Mock())
            instructions = [{'name': 'X', 'qubits': [1]}, {'name': 'measure', 'qubits': [0]},
                            {'name': 'CX', 'qubits': [0, 1]}]
            job_dict = self._basic_job_dictionary
            job_dict['experiments'][0]['instructions'] = instructions
            job = qiskit.qobj.Qobj.from_dict(job_dict)
            self.assertRaises(QisKitBackendError, simulator.run, job)


class TestQiSimulatorPyHistogram(unittest.TestCase):
    def setUp(self):
        self.mock_api = Mock(spec=QuantumInspireAPI)
        self.simulator = QiSimulatorPy(self.mock_api)

        self._basic_job_dictionary = {'qobj_id': 'f9f944f5-9c9e-439e-a396-851d064cee29',
                                      'config': {'shots': 1000},
                                      'experiments': [{'instructions': [], 'header': {'name': 'test'}}],
                                      'header': {'backend_name': 'qi_simulator'},
                                      'type': 'QASM',
                                      'schema_version': '1.0.0'}

    def run_histogram_test(self, single_experiment, mock_result, expected_histogram):
        self.mock_api.execute_qasm.return_value = mock_result
        self._basic_job_dictionary['experiments'][0] = single_experiment
        job = qiskit.qobj.Qobj.from_dict(self._basic_job_dictionary)

        result = self.simulator.run(job)

        self.assertEqual(1, len(result.results))
        first_experiment = first_item(result.results)
        actual = result.results[first_experiment].data['counts']
        self.assertDictEqual(expected_histogram, actual)

    @staticmethod
    def _instructions_to_experiment(instructions):
        experiment_dictionary = {'instructions': instructions,
                                 'header': {'number_of_qubits': 2, 'number_of_clbits': 2, 'name': 'test_circuit',
                                            'qubit_labels': [['q0', 0], ['q0', 1]],
                                            'clbit_labels': [['c0', 0], ['c1', 1]]}
                                 }
        return experiment_dictionary

    def test_convert_histogram_NormalMeasurement(self):
        self.run_histogram_test(
            single_experiment=self._instructions_to_experiment([{'name': 'h', 'params': [], 'texparams': [], 'qubits': [0]},
                                                                {'name': 'cx', 'params': [],
                                                                    'texparams': [], 'qubits': [0, 1]},
                                                                {'name': 'measure', 'qubits': [0], 'clbits': [0]},
                                                                {'name': 'measure', 'qubits': [1], 'clbits': [1]}]),
            mock_result={'histogram': {'0': 0.1, '1': 0.2, '2': 0.3, '3': 0.4}},
            expected_histogram={'00': 100.0, '01': 200.0, '10': 300.0, '11': 400.0}
        )

    def test_convert_histogram_SwappedClassicalQubits(self):
        self.run_histogram_test(
            single_experiment=self._instructions_to_experiment([{'name': 'h', 'params': [], 'texparams': [], 'qubits': [0]},
                                                                {'name': 'cx', 'params': [],
                                                                    'texparams': [], 'qubits': [0, 1]},
                                                                {'name': 'measure', 'qubits': [0], 'clbits': [1]},
                                                                {'name': 'measure', 'qubits': [1], 'clbits': [0]}]),
            mock_result={'histogram': {'0': 0.1, '1': 0.2, '2': 0.3, '3': 0.4}},
            expected_histogram={'00': 100.0, '01': 300.0, '10': 200.0, '11': 400.0}
        )

    def test_convert_histogram_LessMeasurementsQubitOne(self):
        self.run_histogram_test(
            single_experiment=self._instructions_to_experiment([{'name': 'h', 'params': [], 'texparams': [], 'qubits': [0]},
                                                                {'name': 'cx', 'params': [],
                                                                    'texparams': [], 'qubits': [0, 1]},
                                                                {'name': 'measure', 'qubits': [0], 'clbits': [0]}]),
            mock_result={'histogram': {'0': 0.1, '1': 0.2, '2': 0.3, '3': 0.4}},
            expected_histogram={'0': 400.0, '1': 600.0}
        )

    def test_convert_histogram_LessMeasurementsQubitTwo(self):
        self.run_histogram_test(
            single_experiment=self._instructions_to_experiment([{'name': 'h', 'params': [], 'texparams': [], 'qubits': [0]},
                                                                {'name': 'cx', 'params': [],
                                                                    'texparams': [], 'qubits': [0, 1]},
                                                                {'name': 'measure', 'qubits': [1], 'clbits': [1]}]),
            mock_result={'histogram': {'0': 0.1, '1': 0.2, '2': 0.3, '3': 0.4}},
            expected_histogram={'0': 300.0, '1': 700.0}
        )

    def test_convert_histogram_ClassicalBitsMeasureSameQubits(self):
        with self.assertRaisesRegex(QisKitBackendError, 'Classical bit is used to measure multiple qubits!'):
            self.run_histogram_test(
                single_experiment={'instructions': [{'name': 'h', 'params': [], 'texparams': [], 'qubits': [0]},
                                                    {'name': 'cx', 'params': [], 'texparams': [], 'qubits': [0, 1]},
                                                    {'name': 'measure', 'qubits': [0], 'clbits': [0]},
                                                    {'name': 'measure', 'qubits': [1], 'clbits': [0]}],
                                   'header': {'number_of_qubits': 2, 'number_of_clbits': 2, 'name': 'test',
                                              'qubit_labels': [['q0', 0], ['q0', 1]],
                                              'clbit_labels': [['c0', 0], ['c1', 1]]}
                                   },
                mock_result={'histogram': {'0': 0.1, '1': 0.2, '2': 0.3, '3': 0.4}},
                expected_histogram=None
            )
