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
import numpy as np
from collections import OrderedDict
from unittest.mock import Mock, patch

import qiskit
from coreapi.exceptions import ErrorMessage
from qiskit.validation import ModelValidationError
from qiskit.providers.models import BackendConfiguration
from qiskit.providers.models.backendconfiguration import GateConfig
from qiskit.qobj import QasmQobjExperiment, QasmQobj

from quantuminspire.api import QuantumInspireAPI
from quantuminspire.exceptions import QisKitBackendError
from quantuminspire.qiskit.qi_job import QIJob
from quantuminspire.version import __version__ as quantum_inspire_version
from quantuminspire.qiskit.backend_qx import QuantumInspireBackend
from quantuminspire.qiskit.quantum_inspire_provider import QuantumInspireProvider


def first_item(iterable):
    """ Return the first item from an iterable object """
    return next(iter(iterable))


class TestQiSimulatorPy(unittest.TestCase):

    def setUp(self):
        operations = []
        self._basic_qobj_dictionary = {'qobj_id': 'f9f944f5-9c9e-439e-a396-851d064cee29',
                                       'config': {'shots': 25, 'memory_slots': 2, 'max_credits': 10,
                                                  'number_qubits': 2},
                                       'experiments': [{'instructions': operations,
                                                        'header': {'n_qubits': 2, 'memory_slots': 2,
                                                                   'name': 'test',
                                                                   'compiled_circuit_qasm': 'dummy',
                                                                   'creg_sizes': [['c1', 2]]},
                                                        'config': {'coupling_map': 'all-to-all',
                                                                   'basis_gates': 'x,y,z,h,rx,ry,rz,s,cx,ccx,'
                                                                                  'u1,u2,u3,id,snapshot',
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
                           'header': {'n_qubits': 2,
                                      'memory_slots': 2,
                                      'name': 'circuit0',
                                      'compiled_circuit_qasm': ''},
                           'config': {'coupling_map': 'all-to-all',
                                      'basis_gates': 'x,y,z,h,rx,ry,rz,s,cx,ccx,u1,u2,u3,id,snapshot',
                                      'n_qubits': 2}}
        experiment = qiskit.qobj.QasmQobjExperiment.from_dict(experiment_dict)
        return experiment

    def test__collect_measurements(self):
        instructions = [{'name': 'cx', 'params': [], 'texparams': [], 'qubits': [0, 1]},
                        {'name': 'measure', 'qubits': [0], 'memory': [1]},
                        {'name': 'measure', 'qubits': [1], 'memory': [0]}]
        experiment = self._instructions_to_two_qubit_experiment(instructions)

        measurements = QuantumInspireBackend._collect_measurements(experiment)
        self.assertDictEqual(measurements, {'measurements': [[1, 0], [0, 1]], 'number_of_clbits': 2})

    def test__collect_measurements_without_measurements(self):
        instructions = [{'name': 'cx', 'params': [], 'texparams': [], 'qubits': [0, 1]}]
        experiment = self._instructions_to_two_qubit_experiment(instructions)

        measurements = QuantumInspireBackend._collect_measurements(experiment)
        self.assertDictEqual(measurements, {'measurements': [[0, 0], [1, 1]], 'number_of_clbits': 2})

    def test_backend_name(self):
        simulator = QuantumInspireBackend(Mock(), Mock())
        name = simulator.backend_name
        self.assertEqual('qi_simulator', name)

    def test_backend_default_configuration(self):
        simulator = QuantumInspireBackend(Mock(), Mock())
        configuration = simulator.configuration()
        expected_configuration = BackendConfiguration(
            backend_name='qi_simulator',
            backend_version=quantum_inspire_version,
            n_qubits=26,
            basis_gates=['x', 'y', 'z', 'h', 'rx', 'ry', 'rz', 's', 'sdg', 't', 'tdg', 'cx', 'ccx', 'u1', 'u2', 'u3',
                         'id', 'swap', 'snapshot'],
            gates=[GateConfig(name='NotUsed', parameters=['NaN'], qasm_def='NaN')],
            conditional=True,
            simulator=True,
            local=False,
            memory=True,
            open_pulse=False,
            max_shots=1024
        )
        self.assertDictEqual(configuration.to_dict(), expected_configuration.to_dict())

    def test_run_returns_correct_result(self):
        api = Mock()
        api.create_project.return_value = {'id': 42}
        api.get_jobs_from_project.return_value = []
        api.execute_qasm_async.return_value = 42
        simulator = QuantumInspireBackend(api, Mock())
        instructions = [{'name': 'cx', 'params': [], 'texparams': [], 'qubits': [0, 1], 'memory': [0, 1]},
                        {'name': 'measure', 'qubits': [0], 'memory': [1]}]
        qobj_dict = self._basic_qobj_dictionary
        qobj_dict['experiments'][0]['instructions'] = instructions
        qobj = QasmQobj.from_dict(qobj_dict)

        job = simulator.run(qobj)
        self.assertEqual('42', job.job_id())

    def test_get_experiment_results_raises_simulation_error_when_no_histogram(self):
        api = Mock()
        api.get_jobs_from_project.return_value = [{'id': 42, 'results': '{}'}]
        api.get_result_from_job.return_value = {'histogram': [], 'raw_text': 'Error'}
        job = Mock()
        job.job_id.return_value = '42'
        simulator = QuantumInspireBackend(api, Mock())
        with self.assertRaises(QisKitBackendError) as error:
            simulator.get_experiment_results(job)
        self.assertEqual(('Result from backend contains no histogram data!\nError',), error.exception.args)

    def test_get_experiment_results_returns_correct_value(self):
        number_of_shots = 100
        instructions = [{'name': 'h', 'params': [], 'texparams': [], 'qubits': [0]},
                        {'name': 'cx', 'params': [], 'texparams': [], 'qubits': [0, 1]},
                        {'name': 'measure', 'qubits': [1], 'memory': [1]},
                        {'name': 'measure', 'qubits': [0], 'memory': [0]}]
        experiment = self._instructions_to_two_qubit_experiment(instructions)
        api = Mock()
        api.get_result_from_job.return_value = {'id': 1, 'histogram': {'1': 0.6, '3': 0.4},
                                                'execution_time_in_seconds': 2.1, 'number_of_qubits': 2,
                                                'raw_data_url': 'http://saevar-qutech-nginx/api/results/24/raw-data/'}
        api.get_raw_data_from_result.return_value = [1] * 60 + [3] * 40
        jobs = self._basic_job_dictionary
        measurements = QuantumInspireBackend._collect_measurements(experiment)
        user_data = {'name': 'name', 'memory_slots': 2,
                     'creg_sizes': [['c1', 2]], 'measurements': measurements}
        jobs['user_data'] = json.dumps(user_data)
        api.get_jobs_from_project.return_value = [jobs]
        job = QIJob('backend', '42', api)
        simulator = QuantumInspireBackend(api, Mock())
        experiment_result = simulator.get_experiment_results(job)[0]
        self.assertEqual(experiment_result.data.counts.to_dict()['0x1'], 60)
        self.assertEqual(experiment_result.data.counts.to_dict()['0x3'], 40)
        self.assertEqual(experiment_result.data.probabilities.to_dict()['0x1'], 0.6)
        self.assertEqual(experiment_result.data.probabilities.to_dict()['0x3'], 0.4)
        self.assertEqual(len(experiment_result.data.memory), 100)
        self.assertEqual(experiment_result.data.memory.count('0x1'), 60)
        self.assertEqual(experiment_result.data.memory.count('0x3'), 40)
        self.assertEqual(experiment_result.name, 'circuit0')
        self.assertEqual(experiment_result.shots, number_of_shots)

    def test_get_experiment_results_returns_single_shot(self):
        number_of_shots = 1
        self._basic_job_dictionary['number_of_shots'] = number_of_shots
        instructions = [{'name': 'h', 'params': [], 'texparams': [], 'qubits': [0]},
                        {'name': 'cx', 'params': [], 'texparams': [], 'qubits': [0, 1]},
                        {'name': 'measure', 'qubits': [1], 'memory': [1]},
                        {'name': 'measure', 'qubits': [0], 'memory': [0]}]
        experiment = self._instructions_to_two_qubit_experiment(instructions)
        api = Mock()
        api.get_result_from_job.return_value = {'id': 1, 'histogram': {'0': 0.5, '3': 0.5},
                                                'execution_time_in_seconds': 2.1, 'number_of_qubits': 2,
                                                'raw_data_url': 'http://saevar-qutech-nginx/api/results/24/raw-data/'}
        api.get_raw_data_from_result.return_value = []
        jobs = self._basic_job_dictionary
        measurements = QuantumInspireBackend._collect_measurements(experiment)
        user_data = {'name': 'name', 'memory_slots': 2,
                     'creg_sizes': [['c1', 2]], 'measurements': measurements}
        jobs['user_data'] = json.dumps(user_data)
        api.get_jobs_from_project.return_value = [jobs]
        job = QIJob('backend', '42', api)
        simulator = QuantumInspireBackend(api, Mock())
        experiment_result = simulator.get_experiment_results(job)[0]
        self.assertEqual(experiment_result.data.probabilities.to_dict()['0x0'], 0.5)
        self.assertEqual(experiment_result.data.probabilities.to_dict()['0x3'], 0.5)
        self.assertEqual('memory' in experiment_result.data.to_dict(), True)
        # Exactly one value in counts histogram
        self.assertEqual(len(experiment_result.data.counts.to_dict()), 1)
        # The single value in counts histogram has count 1
        self.assertEqual(list(experiment_result.data.counts.to_dict().values())[0], 1)
        # Exactly one value in memory
        self.assertEqual(len(experiment_result.data.memory), 1)
        # The only value in memory is the same as the value in the counts histogram.
        self.assertEqual(list(experiment_result.data.counts.to_dict().keys())[0], experiment_result.data.memory[0])
        self.assertEqual(experiment_result.name, 'circuit0')
        self.assertEqual(experiment_result.shots, number_of_shots)

    def test_get_experiment_results_multiple_single_shots(self):
        one_shot_results = {'0x0': 0, '0x1': 0, '0x2': 0, '0x3': 0}
        np.random.seed(2019)
        for i in range(10000):
            number_of_shots = 1
            self._basic_job_dictionary['number_of_shots'] = number_of_shots
            instructions = [{'name': 'h', 'params': [], 'texparams': [], 'qubits': [0]},
                            {'name': 'cx', 'params': [], 'texparams': [], 'qubits': [0, 1]},
                            {'name': 'measure', 'qubits': [1], 'memory': [1]},
                            {'name': 'measure', 'qubits': [0], 'memory': [0]}]
            experiment = self._instructions_to_two_qubit_experiment(instructions)
            api = Mock()
            api.get_result_from_job.return_value = {'id': 1, 'histogram': {'0': 0.2, '1': 0.3, '2': 0.4, '3': 0.1},
                                                    'execution_time_in_seconds': 2.1, 'number_of_qubits': 2,
                                                    'raw_data_url':
                                                        'http://saevar-qutech-nginx/api/results/24/raw-data/'}
            api.get_raw_data_from_result.return_value = []
            jobs = self._basic_job_dictionary
            measurements = QuantumInspireBackend._collect_measurements(experiment)
            user_data = {'name': 'name', 'memory_slots': 2,
                         'creg_sizes': [['c1', 2]], 'measurements': measurements}
            jobs['user_data'] = json.dumps(user_data)
            api.get_jobs_from_project.return_value = [jobs]
            job = QIJob('backend', '42', api)
            simulator = QuantumInspireBackend(api, Mock())
            experiment_result = simulator.get_experiment_results(job)[0]
            # Exactly one value in memory
            self.assertEqual(len(experiment_result.data.memory), 1)
            # The only value in memory is the same as the value in the counts histogram.
            self.assertEqual(list(experiment_result.data.counts.to_dict().keys())[0], experiment_result.data.memory[0])
            one_shot_results[experiment_result.data.memory[0]] += 1

        self.assertEqual(one_shot_results['0x0'], 2066)
        self.assertEqual(one_shot_results['0x1'], 2947)
        self.assertEqual(one_shot_results['0x2'], 4003)
        self.assertEqual(one_shot_results['0x3'], 984)

    def test_validate_shot_count_zero(self):
        simulator = QuantumInspireBackend(Mock(), Mock())
        job_dict = self._basic_qobj_dictionary
        job_dict['config']['shots'] = 1
        job = qiskit.qobj.QasmQobj.from_dict(job_dict)
        job.config.shots = 0
        self.assertRaisesRegex(QisKitBackendError, "Invalid shots \(number_of_shots=0\)", simulator.run, job)

    def test_model_validate_shot_count_zero(self):
        job_dict = self._basic_qobj_dictionary
        job_dict['config']['shots'] = 0

        with self.assertRaises(ModelValidationError) as error:
            job = qiskit.qobj.QasmQobj.from_dict(job_dict)
        message = error.exception.args[0]['config']['shots'][0]
        self.assertEqual("Must be at least 1.", message)

    def test_validate_no_classical_qubits(self):
        simulator = QuantumInspireBackend(Mock(), Mock())

        job_dict = self._basic_qobj_dictionary
        job_dict['experiments'][0]['instructions'] = []
        job_dict['experiments'][0]['header']['memory_slots'] = 0
        job = qiskit.qobj.Qobj.from_dict(job_dict)
        self.assertRaises(QisKitBackendError, simulator.run, job)

    def test_validate_nr_classical_qubits_less_than_nr_qubits_conditional_gate(self):
        simulator = QuantumInspireBackend(Mock(), Mock())
        instructions = [{'conditional': {'mask': '0xF', 'type': 'equals', 'val': '0x1'},
                         'name': 'cx', 'params': [], 'texparams': [], 'qubits': [0, 1], 'memory': [0, 1]},
                        {'name': 'measure', 'qubits': [0], 'memory': [1]}]
        qobj_dict = self._basic_qobj_dictionary
        job_dict = self._basic_qobj_dictionary
        qobj_dict['experiments'][0]['instructions'] = instructions
        job_dict['experiments'][0]['header']['memory_slots'] = 3
        job = qiskit.qobj.Qobj.from_dict(job_dict)
        self.assertRaisesRegex(QisKitBackendError, 'Number of classical bits must be less than or equal to the'
                                                   ' number of qubits when using conditional gate operations',
                               simulator.run, job)

    def test_validate_operation_after_measure(self):
        with patch.object(QuantumInspireBackend, "_submit_experiment", return_value=Mock()):
            simulator = QuantumInspireBackend(Mock(), Mock())
            instructions = [{'name': 'CX', 'qubits': [0, 1]}, {'name': 'measure', 'qubits': [0]},
                            {'name': 'X', 'qubits': [0]}]
            job_dict = self._basic_qobj_dictionary
            job_dict['experiments'][0]['instructions'] = instructions
            job = qiskit.qobj.Qobj.from_dict(job_dict)
            self.assertRaises(QisKitBackendError, simulator.run, job)

    def test_no_operation_after_measure_cx_gate(self):
        with patch.object(QuantumInspireBackend, "_submit_experiment", return_value=Mock()):
            simulator = QuantumInspireBackend(Mock(), Mock())
            instructions = [{'name': 'X', 'qubits': [1]}, {'name': 'measure', 'qubits': [0]},
                            {'name': 'CX', 'qubits': [0, 1]}]
            job_dict = self._basic_qobj_dictionary
            job_dict['experiments'][0]['instructions'] = instructions
            job = qiskit.qobj.Qobj.from_dict(job_dict)
            self.assertRaises(QisKitBackendError, simulator.run, job)

    def test_valid_qubit_operation_after_measurement_other_qubit(self):
        api = Mock()
        api.create_project.return_value = {'id': 42}
        api.get_jobs_from_project.return_value = []
        api.execute_qasm_async.return_value = 42
        simulator = QuantumInspireBackend(api, Mock())
        instructions = [{'name': 'h', 'params': [], 'texparams': [], 'qubits': [0]},
                        {'name': 'measure', 'qubits': [0], 'memory': [0]},
                        {'name': 'h', 'params': [], 'texparams': [], 'qubits': [1]}]
        qobj_dict = self._basic_qobj_dictionary
        qobj_dict['experiments'][0]['instructions'] = instructions
        qobj = QasmQobj.from_dict(qobj_dict)
        job = simulator.run(qobj)
        self.assertEqual('42', job.job_id())

    def test_retrieve_job(self):
        api = Mock()
        api.get_jobs_from_project.return_value = []
        backend = QuantumInspireBackend(api, QuantumInspireProvider())
        qi_job = backend.retrieve_job('42')
        api.get_project.assert_called_with(42)
        self.assertEqual('42', qi_job.job_id())

    def test_retrieve_job_with_error(self):
        api = Mock(side_effect=ErrorMessage(error='404'))
        api.get_project.side_effect = ErrorMessage(error='404')
        backend = QuantumInspireBackend(api, QuantumInspireProvider())
        with self.assertRaises(QisKitBackendError) as error:
            backend.retrieve_job('wrong')
        self.assertEqual(("Could not retrieve job with job_id 'wrong' ",), error.exception.args)


class ApiMock(Mock):
    def __init__(self, spec, *args, **kwargs):
        super().__init__(spec, *args, kwargs)
        self.result = {}
        self.raw_data = []

    @staticmethod
    def _get_child_mock(**kw):
        return Mock(**kw)

    def set(self, res1, res2):
        self.result = res1
        self.raw_data = res2

    def get_raw_data_from_result(self, result_id):
        if result_id == 1:
            return self.raw_data
        return None

    def get_result_from_job(self, job_id):
        if job_id == 24:
            return self.result
        return None


class TestQiSimulatorPyHistogram(unittest.TestCase):
    def setUp(self):
        self.mock_api = ApiMock(spec=QuantumInspireAPI)
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

    def run_histogram_test(self, single_experiment, mock_result1, mock_result2, expected_histogram,
                           expected_histogram_prob, expected_memory):
        self.mock_api.set(mock_result1, mock_result2)
        jobs = self._basic_job_dictionary
        measurements = QuantumInspireBackend._collect_measurements(QasmQobjExperiment.from_dict(single_experiment))
        user_data = {'name': 'name', 'memory_slots': 2,
                     'creg_sizes': [['c1', 2]], 'measurements': measurements}
        jobs['user_data'] = json.dumps(user_data)
        self.mock_api.get_jobs_from_project.return_value = [jobs]
        job = QIJob('backend', '42', self.mock_api)

        result = self.simulator.get_experiment_results(job)
        number_of_shots = jobs['number_of_shots']
        self.assertEqual(1, len(result))
        first_experiment = first_item(result)
        actual = first_experiment.data.counts.to_dict()
        self.assertDictEqual(expected_histogram, actual)
        probabilities = first_experiment.data.probabilities.to_dict()
        self.assertTrue(len(expected_histogram_prob.keys() - probabilities.keys()) == 0)
        for key in set(probabilities.keys()) & set(expected_histogram_prob.keys()):
            self.assertTrue(np.isclose(expected_histogram_prob[key], probabilities[key]))
        self.assertTrue(len(first_experiment.data.memory) == number_of_shots)
        self.assertListEqual(expected_memory, first_experiment.data.memory)

    @staticmethod
    def _instructions_to_experiment(instructions, memory_slots=2):
        experiment_dictionary = {'instructions': instructions,
                                 'header': {'n_qubits': 2, 'memory_slots': memory_slots,
                                            'name': 'test_circuit', 'qubit_labels': [['q0', 0], ['q0', 1]],
                                            'clbit_labels': [['c0', 0], ['c1', 1]]}
                                 }
        return experiment_dictionary

    def test_convert_histogram_normal_measurement(self):
        self.run_histogram_test(
            single_experiment=self._instructions_to_experiment(
                [{'name': 'h', 'params': [], 'texparams': [], 'qubits': [0]},
                 {'name': 'cx', 'params': [],
                  'texparams': [], 'qubits': [0, 1]},
                 {'name': 'measure', 'qubits': [0], 'memory': [0]},
                 {'name': 'measure', 'qubits': [1], 'memory': [1]}]),
            mock_result1={'id': 1, 'histogram': {'0': 0.1, '1': 0.2, '2': 0.3, '3': 0.4},
                          'execution_time_in_seconds': 2.1, 'number_of_qubits': 2,
                          'raw_data_url': 'http://saevar-qutech-nginx/api/results/24/raw-data/'},
            mock_result2=[0] * 100 + [1] * 200 + [2] * 300 + [3] * 400,
            expected_histogram={'0x0': 100, '0x1': 200, '0x2': 300, '0x3': 400},
            expected_histogram_prob={'0x0': 0.1, '0x1': 0.2, '0x2': 0.3, '0x3': 0.4},
            expected_memory=['0x0'] * 100 + ['0x1'] * 200 + ['0x2'] * 300 + ['0x3'] * 400
        )

    def test_classical_bits_are_displayed_correctly(self):
        self.run_histogram_test(
            single_experiment=self._instructions_to_experiment(
                [{'name': 'h', 'params': [], 'texparams': [], 'qubits': [0]},
                 {'name': 'cx', 'params': [],
                  'texparams': [], 'qubits': [0, 1]},
                 {'name': 'measure', 'qubits': [0], 'memory': [0]},
                 {'name': 'measure', 'qubits': [0], 'memory': [3]},
                 {'name': 'measure', 'qubits': [1], 'memory': [4]},
                 {'name': 'measure', 'qubits': [1], 'memory': [7]}],
                memory_slots=8),
            mock_result1={'id': 1, 'histogram': {'0': 0.1, '1': 0.2, '2': 0.3, '3': 0.4},
                          'execution_time_in_seconds': 2.1, 'number_of_qubits': 2,
                          'raw_data_url': 'http://saevar-qutech-nginx/api/results/24/raw-data/'},
            mock_result2=[0] * 100 + [1] * 200 + [2] * 300 + [3] * 400,
            expected_histogram={'0x0': 100, '0x9': 200, '0x90': 300, '0x99': 400},
            expected_histogram_prob={'0x0': 0.1, '0x9': 0.2, '0x90': 0.3, '0x99': 0.4},
            expected_memory=['0x0'] * 100 + ['0x9'] * 200 + ['0x90'] * 300 + ['0x99'] * 400
        )

    def test_convert_histogram_swapped_classical_qubits(self):
        self.run_histogram_test(
            single_experiment=self._instructions_to_experiment(
                [{'name': 'h', 'params': [], 'texparams': [], 'qubits': [0]},
                 {'name': 'cx', 'params': [],
                  'texparams': [], 'qubits': [0, 1]},
                 {'name': 'measure', 'qubits': [0], 'memory': [1]},
                 {'name': 'measure', 'qubits': [1], 'memory': [0]}]),
            mock_result1={'id': 1, 'histogram': {'0': 0.1, '1': 0.2, '2': 0.3, '3': 0.4},
                          'execution_time_in_seconds': 2.1, 'number_of_qubits': 2,
                          'raw_data_url': 'http://saevar-qutech-nginx/api/results/24/raw-data/'},
            mock_result2=[0] * 100 + [1] * 200 + [2] * 300 + [3] * 400,
            expected_histogram={'0x0': 100, '0x1': 300, '0x2': 200, '0x3': 400},
            expected_histogram_prob={'0x0': 0.1, '0x1': 0.3, '0x2': 0.2, '0x3': 0.4},
            expected_memory=['0x0'] * 100 + ['0x2'] * 200 + ['0x1'] * 300 + ['0x3'] * 400
        )

    def test_convert_histogram_less_measurements_qubit_one(self):
        self.run_histogram_test(
            single_experiment=self._instructions_to_experiment(
                [{'name': 'h', 'params': [], 'texparams': [], 'qubits': [0]},
                 {'name': 'cx', 'params': [],
                  'texparams': [], 'qubits': [0, 1]},
                 {'name': 'measure', 'qubits': [0], 'memory': [0]}]),
            mock_result1={'id': 1, 'histogram': {'0': 0.1, '1': 0.2, '2': 0.3, '3': 0.4},
                          'execution_time_in_seconds': 2.1, 'number_of_qubits': 2,
                          'raw_data_url': 'http://saevar-qutech-nginx/api/results/24/raw-data/'},
            mock_result2=[0] * 100 + [1] * 200 + [2] * 300 + [3] * 400,
            expected_histogram={'0x0': 400, '0x1': 600},
            expected_histogram_prob={'0x0': 0.4, '0x1': 0.6},
            expected_memory=['0x0'] * 100 + ['0x1'] * 200 + ['0x0'] * 300 + ['0x1'] * 400
        )

    def test_convert_histogram_less_measurements_qubit_two(self):
        self.run_histogram_test(
            single_experiment=self._instructions_to_experiment(
                [{'name': 'h', 'params': [], 'texparams': [], 'qubits': [0]},
                 {'name': 'cx', 'params': [],
                  'texparams': [], 'qubits': [0, 1]},
                 {'name': 'measure', 'qubits': [1], 'memory': [1]}]),
            mock_result1={'id': 1, 'histogram': {'0': 0.1, '1': 0.2, '2': 0.3, '3': 0.4},
                          'execution_time_in_seconds': 2.1, 'number_of_qubits': 2,
                          'raw_data_url': 'http://saevar-qutech-nginx/api/results/24/raw-data/'},
            mock_result2=[0] * 100 + [1] * 200 + [2] * 300 + [3] * 400,
            expected_histogram={'0x0': 300, '0x2': 700},
            expected_histogram_prob={'0x0': 0.3, '0x2': 0.7},
            expected_memory=['0x0'] * 300 + ['0x2'] * 700
        )

    def test_convert_histogram_classical_bits_measure_same_qubits(self):
        self.run_histogram_test(
            single_experiment={'instructions': [{'name': 'h', 'params': [], 'texparams': [], 'qubits': [0]},
                                                {'name': 'cx', 'params': [], 'texparams': [], 'qubits': [0, 1]},
                                                {'name': 'measure', 'qubits': [0], 'memory': [0]},
                                                {'name': 'measure', 'qubits': [1], 'memory': [0]}],
                               'header': {'n_qubits': 2, 'memory_slots': 2, 'name': 'test',
                                          'qubit_labels': [['q0', 0], ['q0', 1]],
                                          'clbit_labels': [['c0', 0], ['c1', 1]]}
                               },
            mock_result1={'id': 1, 'histogram': {'0': 0.1, '1': 0.2, '2': 0.3, '3': 0.4},
                          'execution_time_in_seconds': 2.1, 'number_of_qubits': 2,
                          'raw_data_url': 'http://saevar-qutech-nginx/api/results/24/raw-data/'},
            mock_result2=[0] * 100 + [1] * 200 + [2] * 300 + [3] * 400,
            expected_histogram={'0x0': 300, '0x1': 700},
            expected_histogram_prob={'0x0': 0.3, '0x1': 0.7},
            expected_memory=['0x0'] * 300 + ['0x1'] * 700
        )

    def test_empty_histogram(self):
        with self.assertRaises(QisKitBackendError) as error:
            self.run_histogram_test(
                single_experiment=self._instructions_to_experiment(
                    [{'name': 'h', 'params': [], 'texparams': [], 'qubits': [0]},
                     {'name': 'cx', 'params': [],
                      'texparams': [], 'qubits': [0, 1]},
                     {'name': 'measure', 'qubits': [1], 'memory': [1]}]),
                mock_result1={'id': 1, 'histogram': {}, 'execution_time_in_seconds': 2.1,
                              'number_of_qubits': 2, 'raw_text': 'oopsy daisy',
                              'raw_data_url': 'http://saevar-qutech-nginx/api/results/24/raw-data/'},
                mock_result2=[],
                expected_histogram={},
                expected_histogram_prob={},
                expected_memory=[]
            )
        self.assertEqual(('Result from backend contains no histogram data!\noopsy daisy',), error.exception.args)
