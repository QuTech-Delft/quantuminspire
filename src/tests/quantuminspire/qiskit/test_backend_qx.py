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

import json
import unittest
from collections import OrderedDict
from unittest.mock import Mock, patch

import qiskit
from qiskit.qobj import QobjExperiment

from quantuminspire.api import QuantumInspireAPI
from quantuminspire.exceptions import QisKitBackendError
from quantuminspire.qiskit import QuantumInspireProvider
from quantuminspire.qiskit.backend_qx import QuantumInspireBackend
from quantuminspire.qiskit.qi_job import QIJob


def first_item(iterable):
    """ Return the first item from an iterable object """
    return next(iter(iterable))


class TestQiSimulatorPy(unittest.TestCase):

    def setUp(self):
        operations = []
        self._basic_qobj_dictionary = {'qobj_id': 'f9f944f5-9c9e-439e-a396-851d064cee29',
                                       'config': {'shots': 25, 'memory_slots': 2, 'max_credits': 10, 'n_qubits': 2},
                                       'experiments': [{'instructions': operations,
                                                        'header': {'number_of_qubits': 2, 'number_of_clbits': 2,
                                                                   'name': 'test',
                                                                   'compiled_circuit_qasm': 'dummy'},
                                                        'config': {'coupling_map': 'all-to-all',
                                                                   'basis_gates': 'x,y,z,h,s,cx,ccx,u1,u2,u3,id,snapshot',
                                                                   'n_qubits': 2}}],
                                       'header': {'backend_name': 'QX single-node simulator'},
                                       'type': 'QASM', 'schema_version': '1.0.0'}

        self._basic_job_dictionary = OrderedDict([('url', 'http://saevar-qutech-nginx/api/jobs/24/'),
                                                  ('name', 'circuit0'),
                                                  ('id', 24),
                                                  ('status', 'COMPLETE'),
                                                  ('input', 'http://saevar-qutech-nginx/api/assets/26/'),
                                                  ('backend', 'http://saevar-qutech-nginx/api/backends/1/'),
                                                  ('backend_type',
                                                   'http://saevar-qutech-nginx/api/backendtypes/1/'),
                                                  ('results', 'http://saevar-qutech-nginx/api/jobs/24/result/'),
                                                  ('queued_at', '2018-12-07T09:11:45.976617Z'),
                                                  ('number_of_shots', 100),
                                                  ('full_state_projection', True),
                                                  ('user_data', '')
                                                  ])

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

        measurements = QuantumInspireBackend._collect_measurements(experiment)
        self.assertDictEqual(measurements, {'measurements': [[1, 0], [0, 1]], 'number_of_clbits': 2})

    def test__collect_measurements_without_measurements(self):
        instructions = [{'name': 'cx', 'params': [], 'texparams': [], 'qubits': [0, 1]}]
        experiment = self._instructions_to_two_qubit_experiment(instructions)

        measurements = QuantumInspireBackend._collect_measurements(experiment)
        self.assertDictEqual(measurements, {'measurements': [[0, 0], [1, 1]], 'number_of_clbits': 2})

    def test_backend_name(self):
        simulator = QuantumInspireBackend(Mock(), Mock(), logger=Mock())
        name = simulator.backend_name
        self.assertEqual('qi_simulator', name)

    def test_run_ReturnsCorrectResult(self):
        api = Mock()
        api.create_project.return_value = {'id': 42}
        api.get_jobs_from_project.return_value = []
        api.execute_qasm_async.return_value = 42
        simulator = QuantumInspireBackend(api, Mock())
        instructions = [{'name': 'cx', 'params': [], 'texparams': [], 'qubits': [0, 1], 'clbits': [0, 1]},
                        {'name': 'measure', 'qubits': [0], 'clbits': [1]}]
        qobj_dict = self._basic_qobj_dictionary
        qobj_dict['experiments'][0]['instructions'] = instructions
        qobj = qiskit.qobj.Qobj.from_dict(qobj_dict)

        job = simulator.run(qobj)
        self.assertEqual('42', job.job_id())

    def test_get_experiment_results_RaisesSimulationError_when_no_histogram(self):
        api = Mock()
        api.get.return_value = {'histogram': [], 'raw_text': 'Error'}
        api.get_jobs_from_project.return_value = [{'results': '{}'}]
        job = Mock()
        job.get_id.return_value = 42
        simulator = QuantumInspireBackend(api, Mock())
        with self.assertRaises(QisKitBackendError) as error:
            simulator.get_experiment_results(job)
        self.assertEqual(('Result from backend contains no histogram data!\nError',), error.exception.args)

    def test_get_experiment_results_returns_correct_value(self):
        number_of_shots = 100
        instructions = [{'name': 'h', 'params': [], 'texparams': [], 'qubits': [0]},
                        {'name': 'cx', 'params': [], 'texparams': [], 'qubits': [0, 1]},
                        {'name': 'measure', 'qubits': [1], 'clbits': [1], 'memory': [1]},
                        {'name': 'measure', 'qubits': [0], 'clbits': [0], 'memory': [0]}]
        experiment = self._instructions_to_two_qubit_experiment(instructions)
        api = Mock()
        api.get.return_value = {'histogram': {'1': 0.5, '3': 0.4}, 'execution_time_in_seconds': 2.1,
                                'number_of_qubits': 2}
        jobs = self._basic_job_dictionary
        measurements = QuantumInspireBackend._collect_measurements(experiment)
        jobs['user_data'] = json.dumps(measurements)
        api.get_jobs_from_project.return_value = [jobs]
        job = QIJob('backend', '42', api)
        simulator = QuantumInspireBackend(api, Mock())
        experiment_result = simulator.get_experiment_results(job)[0]
        self.assertEqual(experiment_result.data['counts']['01'], 50)
        self.assertEqual(experiment_result.data['counts']['11'], 40)
        self.assertEqual(experiment_result.name, 'circuit0')
        self.assertEqual(experiment_result.shots, number_of_shots)

    def test_validate_NegativeShotCount(self):
        simulator = QuantumInspireBackend(Mock(), Mock(), logger=Mock())
        job_dict = self._basic_qobj_dictionary
        job_dict['config']['shots'] = 0
        job = qiskit.qobj.Qobj.from_dict(job_dict)

        self.assertRaises(QisKitBackendError, simulator.run, job)

    def test_validate_NoClassicalQubits(self):
        simulator = QuantumInspireBackend(Mock(), Mock(), logger=Mock())

        job_dict = self._basic_qobj_dictionary
        job_dict['experiments'][0]['instructions'] = None
        job_dict['experiments'][0]['header']['number_of_clbits'] = 0
        job = qiskit.qobj.Qobj.from_dict(job_dict)

        self.assertRaises(QisKitBackendError, simulator.run, job)

    def test_validate_OperationAfterMeasure(self):
        with patch.object(QuantumInspireBackend, "_submit_experiment", return_value=Mock()):
            simulator = QuantumInspireBackend(Mock(), Mock(), logger=Mock())
            instructions = [{'name': 'CX', 'qubits': [0]}, {'name': 'measure', 'qubits': [0]},
                            {'name': 'X', 'qubits': [0]}]
            job_dict = self._basic_qobj_dictionary
            job_dict['experiments'][0]['instructions'] = instructions
            job = qiskit.qobj.Qobj.from_dict(job_dict)
            self.assertRaises(QisKitBackendError, simulator.run, job)

    def test_no_operation_after_measure_cx_gate(self):
        with patch.object(QuantumInspireBackend, "_submit_experiment", return_value=Mock()):
            simulator = QuantumInspireBackend(Mock(), Mock(), logger=Mock())
            instructions = [{'name': 'X', 'qubits': [1]}, {'name': 'measure', 'qubits': [0], 'clbits': [0]},
                            {'name': 'CX', 'qubits': [0, 1], 'clbits': [0, 1]}]
            job_dict = self._basic_qobj_dictionary
            job_dict['experiments'][0]['instructions'] = instructions
            job = qiskit.qobj.Qobj.from_dict(job_dict)
            self.assertRaises(QisKitBackendError, simulator.run, job)


class TestQiSimulatorPyHistogram(unittest.TestCase):
    def setUp(self):
        self.mock_api = Mock(spec=QuantumInspireAPI)
        self.mock_provider = Mock(spec=QuantumInspireProvider)
        self.simulator = QuantumInspireBackend(self.mock_api, self.mock_provider)
        self._basic_job_dictionary = OrderedDict([('url', 'http://saevar-qutech-nginx/api/jobs/24/'),
                                                  ('name', 'BLA_BLU'),
                                                  ('id', 24),
                                                  ('status', 'COMPLETE'),
                                                  ('input', 'http://saevar-qutech-nginx/api/assets/26/'),
                                                  ('backend', 'http://saevar-qutech-nginx/api/backends/1/'),
                                                  ('backend_type',
                                                   'http://saevar-qutech-nginx/api/backendtypes/1/'),
                                                  ('results', 'http://saevar-qutech-nginx/api/jobs/24/result/'),
                                                  ('queued_at', '2018-12-07T09:11:45.976617Z'),
                                                  ('number_of_shots', 1000),
                                                  ('full_state_projection', True),
                                                  ('user_data', '')
                                                  ])

    def run_histogram_test(self, single_experiment, mock_result, expected_histogram):
        self.mock_api.get.return_value = mock_result
        jobs = self._basic_job_dictionary
        measurements = QuantumInspireBackend._collect_measurements(QobjExperiment.from_dict(single_experiment))
        jobs['user_data'] = json.dumps(measurements)
        self.mock_api.get_jobs_from_project.return_value = [jobs]
        job = QIJob('backend', '42', self.mock_api)

        result = self.simulator.get_experiment_results(job)
        self.assertEqual(1, len(result))
        first_experiment = first_item(result)
        actual = first_experiment.data['counts']

        self.assertDictEqual(expected_histogram, actual)

    @staticmethod
    def _instructions_to_experiment(instructions, number_of_clbits=2):
        experiment_dictionary = {'instructions': instructions,
                                 'header': {'number_of_qubits': 2, 'number_of_clbits': number_of_clbits,
                                            'name': 'test_circuit', 'qubit_labels': [['q0', 0], ['q0', 1]],
                                            'clbit_labels': [['c0', 0], ['c1', 1]]}
                                 }
        return experiment_dictionary

    def test_convert_histogram_NormalMeasurement(self):
        self.run_histogram_test(
            single_experiment=self._instructions_to_experiment(
                [{'name': 'h', 'params': [], 'texparams': [], 'qubits': [0]},
                 {'name': 'cx', 'params': [],
                  'texparams': [], 'qubits': [0, 1]},
                 {'name': 'measure', 'qubits': [0], 'clbits': [0]},
                 {'name': 'measure', 'qubits': [1], 'clbits': [1]}]),
            mock_result={'histogram': {'0': 0.1, '1': 0.2, '2': 0.3, '3': 0.4}, 'execution_time_in_seconds': 2.1,
                         'number_of_qubits': 2},
            expected_histogram={'00': 100.0, '01': 200.0, '10': 300.0, '11': 400.0}
        )

    def test_classical_bits_are_displayed_correctly(self):
        self.run_histogram_test(
            single_experiment=self._instructions_to_experiment(
                [{'name': 'h', 'params': [], 'texparams': [], 'qubits': [0]},
                 {'name': 'cx', 'params': [],
                  'texparams': [], 'qubits': [0, 1]},
                 {'name': 'measure', 'qubits': [0], 'clbits': [0]},
                 {'name': 'measure', 'qubits': [0], 'clbits': [3]},
                 {'name': 'measure', 'qubits': [1], 'clbits': [4]},
                 {'name': 'measure', 'qubits': [1], 'clbits': [7]}],
                number_of_clbits=8),
            mock_result={'histogram': {'0': 0.1, '1': 0.2, '2': 0.3, '3': 0.4}, 'execution_time_in_seconds': 2.1,
                         'number_of_qubits': 2},
            expected_histogram={'00000000': 100.0, '00001001': 200.0, '10010000': 300.0, '10011001': 400.0}
        )

    def test_convert_histogram_SwappedClassicalQubits(self):
        self.run_histogram_test(
            single_experiment=self._instructions_to_experiment(
                [{'name': 'h', 'params': [], 'texparams': [], 'qubits': [0]},
                 {'name': 'cx', 'params': [],
                  'texparams': [], 'qubits': [0, 1]},
                 {'name': 'measure', 'qubits': [0], 'clbits': [1]},
                 {'name': 'measure', 'qubits': [1], 'clbits': [0]}]),
            mock_result={'histogram': {'0': 0.1, '1': 0.2, '2': 0.3, '3': 0.4}, 'execution_time_in_seconds': 2.1,
                         'number_of_qubits': 2},
            expected_histogram={'00': 100.0, '01': 300.0, '10': 200.0, '11': 400.0}
        )

    def test_convert_histogram_LessMeasurementsQubitOne(self):
        self.run_histogram_test(
            single_experiment=self._instructions_to_experiment(
                [{'name': 'h', 'params': [], 'texparams': [], 'qubits': [0]},
                 {'name': 'cx', 'params': [],
                  'texparams': [], 'qubits': [0, 1]},
                 {'name': 'measure', 'qubits': [0], 'clbits': [0]}]),
            mock_result={'histogram': {'0': 0.1, '1': 0.2, '2': 0.3, '3': 0.4}, 'execution_time_in_seconds': 2.1,
                         'number_of_qubits': 2},
            expected_histogram={'00': 400.0, '01': 600.0}
        )

    def test_convert_histogram_LessMeasurementsQubitTwo(self):
        self.run_histogram_test(
            single_experiment=self._instructions_to_experiment(
                [{'name': 'h', 'params': [], 'texparams': [], 'qubits': [0]},
                 {'name': 'cx', 'params': [],
                  'texparams': [], 'qubits': [0, 1]},
                 {'name': 'measure', 'qubits': [1], 'clbits': [1]}]),
            mock_result={'histogram': {'0': 0.1, '1': 0.2, '2': 0.3, '3': 0.4}, 'execution_time_in_seconds': 2.1,
                         'number_of_qubits': 2},
            expected_histogram={'00': 300.0, '10': 700.0}
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
                mock_result={'histogram': {'0': 0.1, '1': 0.2, '2': 0.3, '3': 0.4}, 'execution_time_in_seconds': 2.1,
                             'number_of_qubits': 2},
                expected_histogram=None
            )

    def test_empty_histogram(self):
        with self.assertRaises(QisKitBackendError) as error:
            self.run_histogram_test(
                single_experiment=self._instructions_to_experiment(
                    [{'name': 'h', 'params': [], 'texparams': [], 'qubits': [0]},
                     {'name': 'cx', 'params': [],
                      'texparams': [], 'qubits': [0, 1]},
                     {'name': 'measure', 'qubits': [1], 'clbits': [1]}]),
                mock_result={'histogram': {}, 'execution_time_in_seconds': 2.1,
                             'number_of_qubits': 2, 'raw_text': 'oopsy daisy'},
                expected_histogram={}
            )
        self.assertEqual(('Result from backend contains no histogram data!\noopsy daisy',), error.exception.args)
