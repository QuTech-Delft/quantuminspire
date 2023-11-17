""" Quantum Inspire SDK

Copyright 2022 QuTech Delft

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

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
from unittest.mock import Mock, patch, ANY

import numpy as np

from qiskit.circuit import QuantumRegister, ClassicalRegister, QuantumCircuit
from qiskit.compiler import assemble
from qiskit.providers.models import QasmBackendConfiguration
from qiskit.providers.models.backendconfiguration import GateConfig
from qiskit.qobj import QasmQobjExperiment

from quantuminspire.api import QuantumInspireAPI, V1_MEASUREMENT_BLOCK_INDEX
from quantuminspire.exceptions import QiskitBackendError, ApiError
from quantuminspire.qiskit.backend_qx import QuantumInspireBackend
from quantuminspire.qiskit.qi_job import QIJob
from quantuminspire.job import QuantumInspireJob
from quantuminspire.qiskit.measurements import Measurements
from quantuminspire.qiskit.quantum_inspire_provider import QuantumInspireProvider
from quantuminspire.version import __version__ as quantum_inspire_version


def first_item(iterable):
    """ Return the first item from an iterable object """
    return next(iter(iterable))


class TestQiSimulatorPy(unittest.TestCase):

    def setUp(self):
        self._basic_job_dictionary = dict([('url', 'http://saevar-qutech-nginx/api/jobs/24/'),
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
    def _circuit_to_qobj(circuit):
        run_config_dict = {'shots': 25, 'memory': True}
        backend = QuantumInspireBackend(Mock(), Mock())
        qobj = assemble(circuit, backend, **run_config_dict)
        return qobj

    @staticmethod
    def _circuit_to_experiment(circuit):
        qobj = TestQiSimulatorPy._circuit_to_qobj(circuit)
        return qobj.experiments[0]

    def test_backend_name(self):
        simulator = QuantumInspireBackend(Mock(), Mock())
        name = simulator.backend_name
        self.assertEqual('qi_simulator', name)

    def test_backend_default_configuration(self):
        simulator = QuantumInspireBackend(Mock(), Mock())
        configuration = simulator.configuration()
        expected_configuration = QasmBackendConfiguration(
            backend_name='qi_simulator',
            backend_version=quantum_inspire_version,
            n_qubits=26,
            basis_gates=['x', 'y', 'z', 'h', 'rx', 'ry', 'rz', 's', 'sdg', 't', 'tdg', 'cx', 'ccx', 'p', 'u',
                         'id', 'swap', 'cz', 'snapshot', 'delay', 'barrier', 'reset'],
            gates=[GateConfig(name='NotUsed', parameters=['NaN'], qasm_def='NaN')],
            conditional=True,
            simulator=True,
            local=False,
            memory=True,
            open_pulse=False,
            max_shots=1024,
            max_experiments=1,
            coupling_map=[],
            multiple_measurements=False,
            parallel_computing=False
        )
        self.assertDictEqual(configuration.to_dict(), expected_configuration.to_dict())

    def test_backend_status(self):
        api = Mock()
        type(api).__name__ = 'QuantumInspireAPI'
        backend_type = {'max_number_of_shots': 4096,
                        'status': 'OFFLINE',
                        'status_message': 'This backend is offline.'}
        api.get_backend_type_by_name.return_value = backend_type
        simulator = QuantumInspireBackend(api, Mock())
        status = simulator.status()
        self.assertEqual(status.backend_name, 'qi_simulator')
        self.assertEqual(status.status_msg, backend_type['status_message'])
        self.assertEqual(status.backend_version, quantum_inspire_version)
        self.assertFalse(status.operational)
        self.assertEqual(status.pending_jobs, 0)

    def test_strtobool(self):
        simulator = QuantumInspireBackend(Mock(), Mock())
        self.assertFalse(simulator.strtobool('False'))
        self.assertFalse(simulator.strtobool('false'))
        self.assertFalse(simulator.strtobool('0'))
        self.assertFalse(simulator.strtobool('n'))
        self.assertFalse(simulator.strtobool('no'))
        self.assertTrue(simulator.strtobool('True'))
        self.assertTrue(simulator.strtobool('true'))
        self.assertTrue(simulator.strtobool('1'))
        self.assertTrue(simulator.strtobool('y'))
        self.assertTrue(simulator.strtobool('yes'))
        with self.assertRaises(ValueError) as error:
            simulator.strtobool('int')
        self.assertEqual(("invalid truth value int",), error.exception.args)

    def test_run_a_circuit_returns_correct_result(self):
        api = Mock()
        type(api).__name__ = 'QuantumInspireAPI'
        api.create_project.return_value = {'id': 42}
        api.get_asset_from_job.return_value = {'project_id': '42'}
        api.execute_qasm_async.return_value = QuantumInspireJob(api, 42)
        api.get_backend_type_by_name.return_value = {'max_number_of_shots': 4096}
        simulator = QuantumInspireBackend(api, Mock())

        qc = QuantumCircuit(2, 2)
        qc.cx(0, 1)
        qc.measure(0, 1)
        job = simulator.run(qc, shots=1024)

        self.assertEqual('42', job.job_id())

    def test_get_experiment_results_raises_simulation_error_when_no_histogram(self):
        api = Mock()
        api.get_jobs_from_project.return_value = [{'id': 42, 'results': '{}', 'user_data': 'data'}]
        api.get_result_from_job.return_value = {'histogram': [OrderedDict()], 'raw_text': 'Simulation failed'}
        job = Mock()
        job.job_id.return_value = '42'
        simulator = QuantumInspireBackend(api, Mock())
        with self.assertRaises(QiskitBackendError) as error:
            simulator.get_experiment_results_from_all_jobs(job)
        self.assertEqual(('Result from backend contains no histogram data!\nSimulation failed',), error.exception.args)

    def test_get_experiment_results_raises_simulation_error_when_no_user_data(self):
        api = Mock()
        api.get_jobs_from_project.return_value = [{'id': 42, 'results': '{}', 'user_data': ''}]
        api.get_result_from_job.return_value = {'histogram': [{'0': 1.0}], 'raw_text': ''}
        job = Mock()
        job.job_id.return_value = '42'
        simulator = QuantumInspireBackend(api, Mock())
        with self.assertRaises(QiskitBackendError) as error:
            simulator.get_experiment_results_from_all_jobs(job)
        self.assertEqual(("Job '42' from backend contains no user data. This job was not submitted by the SDK",),
                         error.exception.args)

    def test_get_experiment_results_returns_correct_value_from_project(self):
        qc = QuantumCircuit(2, 2)
        qc.h(0)
        qc.cx(0, 1)
        qc.measure(1, 1)
        qc.measure(0, 0)

        number_of_shots = 100
        experiment = self._circuit_to_experiment(qc)
        api = Mock()
        simulator = QuantumInspireBackend(api, Mock())
        api.get_result_from_job.return_value = {'id': 1, 'histogram': [{'1': 0.6, '3': 0.4}],
                                                'execution_time_in_seconds': 2.1, 'number_of_qubits': 2,
                                                'raw_data_url': 'http://saevar-qutech-nginx/api/results/24/raw-data/'}
        api.get_raw_data_from_result.return_value = [[[1, 0]]] * 60 + [[[1, 1]]] * 40
        jobs = self._basic_job_dictionary
        measurements = Measurements.from_experiment(experiment)
        user_data = simulator.generate_user_data(experiment, measurements)
        jobs['user_data'] = json.dumps(user_data)
        api.get_jobs_from_project.return_value = [jobs]
        job = QIJob('backend', '42', api)
        experiment_result = simulator.get_experiment_results_from_all_jobs(job)[0]
        self.assertEqual(experiment_result.data.counts['0x1'], 60)
        self.assertEqual(experiment_result.data.counts['0x3'], 40)
        self.assertEqual(experiment_result.data.counts,
                         experiment_result.data.counts_multiple_measurement[V1_MEASUREMENT_BLOCK_INDEX])
        self.assertEqual(experiment_result.data.probabilities['0x1'], 0.6)
        self.assertEqual(experiment_result.data.probabilities['0x3'], 0.4)
        self.assertEqual(experiment_result.data.probabilities,
                         experiment_result.data.probabilities_multiple_measurement[V1_MEASUREMENT_BLOCK_INDEX])
        self.assertEqual(len(experiment_result.data.memory), 100)
        self.assertEqual(experiment_result.data.memory.count('0x1'), 60)
        self.assertEqual(experiment_result.data.memory.count('0x3'), 40)
        self.assertEqual(experiment_result.data.memory,
                         experiment_result.data.memory_multiple_measurement[V1_MEASUREMENT_BLOCK_INDEX])
        self.assertEqual(experiment_result.name, 'circuit0')
        self.assertEqual(experiment_result.shots, number_of_shots)

    def test_get_experiment_results_returns_correct_value_from_latest_run(self):
        qc = QuantumCircuit(2, 2)
        qc.h(0)
        qc.cx(0, 1)
        qc.measure(1, 1)
        qc.measure(0, 0)

        number_of_shots = 100
        experiment = self._circuit_to_experiment(qc)

        api = Mock()
        simulator = QuantumInspireBackend(api, Mock())
        api.get_result_from_job.return_value = {'id': 1, 'histogram': [{'1': 0.6, '3': 0.4}],
                                                'execution_time_in_seconds': 2.1, 'number_of_qubits': 2,
                                                'raw_data_url': 'http://saevar-qutech-nginx/api/results/24/raw-data/'}
        api.get_raw_data_from_result.return_value = [[[1, 0]]] * 60 + [[[1, 1]]] * 40
        job = self._basic_job_dictionary
        measurements = Measurements.from_experiment(experiment)
        user_data = simulator.generate_user_data(experiment, measurements)
        job['user_data'] = json.dumps(user_data)

        api.get_job.side_effect = [job]
        quantuminspire_job = Mock()
        quantuminspire_job.get_job_identifier.side_effect = [1]
        qijob = QIJob('backend', '42', api)
        qijob.add_job(quantuminspire_job)

        experiment_result = simulator.get_experiment_results_from_latest_run(qijob)[0]
        self.assertEqual(experiment_result.data.counts['0x1'], 60)
        self.assertEqual(experiment_result.data.counts['0x3'], 40)
        self.assertEqual(experiment_result.data.counts,
                         experiment_result.data.counts_multiple_measurement[V1_MEASUREMENT_BLOCK_INDEX])
        self.assertEqual(experiment_result.data.probabilities['0x1'], 0.6)
        self.assertEqual(experiment_result.data.probabilities['0x3'], 0.4)
        self.assertEqual(experiment_result.data.probabilities,
                         experiment_result.data.probabilities_multiple_measurement[V1_MEASUREMENT_BLOCK_INDEX])
        self.assertEqual(len(experiment_result.data.memory), 100)
        self.assertEqual(experiment_result.data.memory.count('0x1'), 60)
        self.assertEqual(experiment_result.data.memory.count('0x3'), 40)
        self.assertEqual(experiment_result.data.memory,
                         experiment_result.data.memory_multiple_measurement[V1_MEASUREMENT_BLOCK_INDEX])
        self.assertEqual(experiment_result.name, 'circuit0')
        self.assertEqual(experiment_result.shots, number_of_shots)

    def test_get_experiment_results_returns_single_shot(self):
        number_of_shots = 1
        self._basic_job_dictionary['number_of_shots'] = number_of_shots

        qc = QuantumCircuit(2, 2)
        qc.h(0)
        qc.cx(0, 1)
        qc.measure(1, 1)
        qc.measure(0, 0)

        experiment = self._circuit_to_experiment(qc)

        api = Mock()
        simulator = QuantumInspireBackend(api, Mock())
        api.get_result_from_job.return_value = {'id': 1, 'histogram': [{'0': 0.5, '3': 0.5}],
                                                'execution_time_in_seconds': 2.1, 'number_of_qubits': 2,
                                                'raw_data_url': 'http://saevar-qutech-nginx/api/results/24/raw-data/'}
        api.get_raw_data_from_result.return_value = [[]]
        api.get_backend_type_by_name.return_value = {'max_number_of_shots': 4096}
        jobs = self._basic_job_dictionary
        measurements = Measurements.from_experiment(experiment)
        user_data = simulator.generate_user_data(experiment, measurements)
        jobs['user_data'] = json.dumps(user_data)
        api.get_jobs_from_project.return_value = [jobs]
        job = QIJob('backend', '42', api)
        experiment_result = simulator.get_experiment_results_from_all_jobs(job)[0]
        self.assertEqual(experiment_result.data.probabilities['0x0'], 0.5)
        self.assertEqual(experiment_result.data.probabilities['0x3'], 0.5)
        self.assertTrue(hasattr(experiment_result.data, 'memory'))
        # Exactly one value in counts histogram
        self.assertEqual(len(experiment_result.data.counts), 1)
        # The single value in counts histogram has count 1
        self.assertEqual(list(experiment_result.data.counts.values())[0], 1)
        # Exactly one value in memory
        self.assertEqual(len(experiment_result.data.memory), 1)
        # The only value in memory is the same as the value in the counts histogram.
        self.assertEqual(list(experiment_result.data.counts.keys())[0], experiment_result.data.memory[0])
        self.assertEqual(experiment_result.name, 'circuit0')
        self.assertEqual(experiment_result.shots, number_of_shots)

    def test_get_experiment_results_multiple_single_shots(self):
        one_shot_results = {'0x0': 0, '0x1': 0, '0x2': 0, '0x3': 0}
        np.random.seed(2019)
        for i in range(10000):
            number_of_shots = 1
            self._basic_job_dictionary['number_of_shots'] = number_of_shots

            qc = QuantumCircuit(2, 2)
            qc.h(0)
            qc.cx(0, 1)
            qc.measure(1, 1)
            qc.measure(0, 0)

            experiment = self._circuit_to_experiment(qc)
            api = Mock()
            simulator = QuantumInspireBackend(api, Mock())
            api.get_result_from_job.return_value = {'id': 1, 'histogram': [{'0': 0.2, '1': 0.3, '2': 0.4, '3': 0.1}],
                                                    'execution_time_in_seconds': 2.1, 'number_of_qubits': 2,
                                                    'raw_data_url':
                                                        'http://saevar-qutech-nginx/api/results/24/raw-data/'}
            api.get_raw_data_from_result.return_value = [[]]
            jobs = self._basic_job_dictionary
            measurements = Measurements.from_experiment(experiment)
            user_data = simulator.generate_user_data(experiment, measurements)
            jobs['user_data'] = json.dumps(user_data)
            api.get_jobs_from_project.return_value = [jobs]
            job = QIJob('backend', '42', api)
            experiment_result = simulator.get_experiment_results_from_all_jobs(job)[0]
            # Exactly one value in memory
            self.assertEqual(len(experiment_result.data.memory), 1)
            # The only value in memory is the same as the value in the counts histogram.
            self.assertEqual(list(experiment_result.data.counts.keys())[0], experiment_result.data.memory[0])
            one_shot_results[experiment_result.data.memory[0]] += 1

        self.assertEqual(one_shot_results['0x0'], 2066)
        self.assertEqual(one_shot_results['0x1'], 2947)
        self.assertEqual(one_shot_results['0x2'], 4003)
        self.assertEqual(one_shot_results['0x3'], 984)

    def test_run_returns_correct_result_for_my_project_number(self):
        default_project_number = 42
        my_project_number = 43
        api = Mock()
        api.create_project.return_value = {'id': default_project_number}
        quantum_inspire_job = Mock()
        quantum_inspire_job.get_project_identifier.return_value = my_project_number
        api.execute_qasm_async.return_value = quantum_inspire_job
        api.get_backend_type_by_name.return_value = {'max_number_of_shots': 4096}
        simulator = QuantumInspireBackend(api, Mock())

        q = QuantumRegister(3, "q")
        c1 = ClassicalRegister(2, "c1")
        c2 = ClassicalRegister(1, "c2")
        qc = QuantumCircuit(q, c1, c2, name="test")
        qc.h(q[0])
        qc.h(q[2])
        qc.measure(q[1], c1[0])
        qc.measure(q[0], c1[1])

        qc.h(q[1]).c_if(c1, 2)
        qc.measure(q[0], c1[1])
        qc.measure(q[1], c1[0])

        job = simulator.run(qc)
        api.delete_project.assert_called_with(default_project_number)
        self.assertEqual(my_project_number, int(job.job_id()))

    def test_run_deletes_empty_project_when_error_occurs(self):
        default_project_number = 42
        my_project_number = 43
        api = Mock()
        api.create_project.return_value = {'id': default_project_number}
        quantum_inspire_job = Mock()
        quantum_inspire_job.get_project_identifier.return_value = my_project_number
        api.execute_qasm_async.return_value = quantum_inspire_job
        api.get_backend_type_by_name.return_value = {'max_number_of_shots': 4096}
        simulator = QuantumInspireBackend(api, Mock())

        qc = QuantumCircuit(2, 2)
        qc.measure(1, 0)

        qobj = self._circuit_to_qobj(qc)
        qobj.experiments[0].header.memory_slots = 0
        self.assertRaisesRegex(QiskitBackendError, 'Invalid number of classical bits \(0\)!',
                               simulator.run, qobj)
        api.delete_project.assert_called_with(default_project_number)

    def test_validate_shot_count(self):
        api = Mock()
        api.create_project.return_value = {'id': 42}
        api.execute_qasm_async.return_value = 42
        api.get_backend_type_by_name.return_value = {'max_number_of_shots': 4096}
        simulator = QuantumInspireBackend(api, Mock())

        qc = QuantumCircuit(2, 2)
        qc.h(0)
        qc.cx(0, 1)
        qc.measure(1, 1)
        qc.measure(0, 0)

        job = self._circuit_to_qobj(qc)

        job.config.shots = 0                            # set the number of shots to 0 to trigger our validation
        self.assertRaisesRegex(QiskitBackendError, "Invalid shots \(number_of_shots=0\)", simulator.run, job)
        job.config.shots = 4097                         # now set the number of shots to a too high value
        self.assertRaisesRegex(QiskitBackendError, "Invalid shots \(number_of_shots=4097\)", simulator.run, job)

    def test_validate_no_classical_qubits(self):
        api = Mock()
        api.create_project.return_value = {'id': 42}
        api.execute_qasm_async.return_value = 42
        api.get_backend_type_by_name.return_value = {'max_number_of_shots': 4096}
        simulator = QuantumInspireBackend(api, Mock())

        qc = QuantumCircuit(2, 2)

        job = self._circuit_to_qobj(qc)
        job.experiments[0].header.memory_slots = 0
        self.assertRaisesRegex(QiskitBackendError, 'Invalid number of classical bits \(0\)!',
                               simulator.run, job)

    def test_validate_nr_classical_qubits_less_than_nr_qubits_conditional_gate(self):
        api = Mock()
        api.create_project.return_value = {'id': 42}
        api.execute_qasm_async.return_value = 42
        api.get_backend_type_by_name.return_value = {'max_number_of_shots': 4096}
        simulator = QuantumInspireBackend(api, Mock())

        q = QuantumRegister(2, "q")
        c = ClassicalRegister(4, "c")
        qc = QuantumCircuit(q, c, name="conditional")
        qc.cx(q[0], q[1]).c_if(c, 1)
        qc.measure(0, 1)
        self.assertRaisesRegex(QiskitBackendError, 'Number of classical bits must be less than or equal to the'
                                                   ' number of qubits when using conditional gate operations',
                               simulator.run, qc)

    def test_for_non_fsp_gate_after_measurement(self):
        with patch.object(QuantumInspireBackend, "_submit_experiment", return_value=Mock()) as result_experiment:
            api = Mock()
            project = {'id': 42}
            api.create_project.return_value = project
            api.execute_qasm_async.return_value = 42
            api.get_backend_type_by_name.return_value = {'max_number_of_shots': 4096}
            simulator = QuantumInspireBackend(api, Mock())

            qc = QuantumCircuit(2, 2)
            qc.cx(0, 1)
            qc.measure(0, 0)
            qc.x(0)

            simulator.run(qc, 25)
            experiment = self._circuit_to_experiment(qc)

        result_experiment.assert_called_once_with(experiment, 25, ANY, project=project,
                                                  full_state_projection=False)

    def test_for_non_fsp_measurements_at_begin_and_end(self):
        with patch.object(QuantumInspireBackend, "_submit_experiment", return_value=Mock()) as result_experiment:
            api = Mock()
            project = {'id': 42}
            api.create_project.return_value = project
            api.execute_qasm_async.return_value = 42
            api.get_backend_type_by_name.return_value = {'max_number_of_shots': 4096}
            simulator = QuantumInspireBackend(api, Mock())

            qc = QuantumCircuit(2, 2)
            qc.measure(0, 0)
            qc.cx(0, 1)
            qc.x(0)
            qc.measure(1, 1)

            simulator.run(qc, 25)
            experiment = self._circuit_to_experiment(qc)
        result_experiment.assert_called_once_with(experiment, 25, ANY, project=project,
                                                  full_state_projection=False)

    def test_for_fsp_measurements_at_end_only(self):
        with patch.object(QuantumInspireBackend, "_submit_experiment", return_value=Mock()) as result_experiment:
            api = Mock()
            project = {'id': 42}
            api.create_project.return_value = project
            api.execute_qasm_async.return_value = 42
            api.get_backend_type_by_name.return_value = {'max_number_of_shots': 4096}
            simulator = QuantumInspireBackend(api, Mock())

            qc = QuantumCircuit(2, 2)
            qc.cx(0, 1)
            qc.x(0)
            qc.measure(0, 1)

            simulator.run(qc, 25)
            experiment = self._circuit_to_experiment(qc)
        result_experiment.assert_called_once_with(experiment, 25, ANY, project=project,
                                                  full_state_projection=True)

    def test_for_fsp_no_measurements(self):
        with patch.object(QuantumInspireBackend, "_submit_experiment", return_value=Mock()) as result_experiment:
            api = Mock()
            project = {'id': 42}
            api.create_project.return_value = project
            api.execute_qasm_async.return_value = 42
            api.get_backend_type_by_name.return_value = {'max_number_of_shots': 4096}
            simulator = QuantumInspireBackend(api, Mock())

            qc = QuantumCircuit(2, 2)
            qc.cx(0, 1)
            qc.x(0)

            simulator.run(qc, 25)
            experiment = self._circuit_to_experiment(qc)
            result_experiment.assert_called_once_with(experiment, 25, ANY, project=project,
                                                      full_state_projection=True)

    def test_fsp_flag_overridden_by_string_parameter(self):
        with patch.object(QuantumInspireBackend, "_submit_experiment", return_value=Mock()) as result_experiment:
            api = Mock()
            project = {'id': 43}
            api.create_project.return_value = project
            api.execute_qasm_async.return_value = 43
            api.get_backend_type_by_name.return_value = {'max_number_of_shots': 1024}
            simulator = QuantumInspireBackend(api, Mock())

            # an algorithm that can be run as fsp
            qc = QuantumCircuit(2, 2)
            qc.cx(0, 1)
            qc.x(0)

            simulator.run(qc, 1000, allow_fsp='False')
            experiment = self._circuit_to_experiment(qc)
            result_experiment.assert_called_once_with(experiment, 1000, ANY, project=project,
                                                      full_state_projection=False)

    def test_for_non_fsp_hardware_backend(self):
        with patch.object(QuantumInspireBackend, "_submit_experiment", return_value=Mock()) as result_experiment:
            api = Mock()
            project = {'id': 42}
            api.create_project.return_value = project
            api.execute_qasm_async.return_value = 42
            api.get_backend_type_by_name.return_value = {'max_number_of_shots': 4096}
            config = QuantumInspireBackend.DEFAULT_CONFIGURATION
            config.backend_name = 'qi_hardware'
            config.simulator = False
            simulator = QuantumInspireBackend(api, config)

            qc = QuantumCircuit(2, 2)
            qc.cx(0, 1)
            qc.x(0)

            simulator.run(qc, 25, allow_fsp=True)
            experiment = self._circuit_to_experiment(qc)
        result_experiment.assert_called_once_with(experiment, 25, ANY, project=project,
                                                  full_state_projection=False)

    def test_valid_non_fsp_measurement_qubit_to_classical(self):
        api = Mock()
        api.create_project.return_value = {'id': 42}
        api.get_asset_from_job.return_value = {'project_id': '42'}
        quantum_inspire_job = Mock()
        quantum_inspire_job.get_project_identifier.return_value = 42
        api.execute_qasm_async.return_value = quantum_inspire_job
        api.get_backend_type_by_name.return_value = {'max_number_of_shots': 4096}
        simulator = QuantumInspireBackend(api, Mock())

        q = QuantumRegister(3, "q")
        c1 = ClassicalRegister(1, "c1")
        c2 = ClassicalRegister(1, "c2")

        qc = QuantumCircuit(q, c1, c2, name="test")

        qc.h(0)
        qc.h(2)
        qc.measure(1, 0)
        qc.measure(0, 1)
        qc.h(1).c_if(c2, 1)
        qc.measure(0, 1)
        qc.measure(1, 0)

        job = simulator.run(qc)
        self.assertEqual('42', job.job_id())

    def test_retrieve_job(self):
        api = Mock()
        backend = QuantumInspireBackend(api, QuantumInspireProvider())
        qi_job = backend.retrieve_job('42')
        api.get_project.assert_called_with(42)
        self.assertEqual('42', qi_job.job_id())

    def test_retrieve_job_with_error(self):
        api = Mock(side_effect=ApiError(f'Project with id 404 does not exist!'))
        api.get_project.side_effect = ApiError(f'Project with id 404 does not exist!')
        backend = QuantumInspireBackend(api, QuantumInspireProvider())
        with self.assertRaises(QiskitBackendError) as error:
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
        self._basic_job_dictionary = dict([('url', 'http://saevar-qutech-nginx/api/jobs/24/'),
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
        experiment = QasmQobjExperiment.from_dict(single_experiment)
        measurements = Measurements.from_experiment(experiment)
        user_data = self.simulator.generate_user_data(experiment, measurements)
        jobs['user_data'] = json.dumps(user_data)
        self.mock_api.get_jobs_from_project.return_value = [jobs]
        job = QIJob('backend', '42', self.mock_api)

        result = self.simulator.get_experiment_results_from_all_jobs(job)
        number_of_shots = jobs['number_of_shots']
        self.assertEqual(1, len(result))
        first_experiment = first_item(result)
        actual = first_experiment.data.counts
        self.assertDictEqual(actual, expected_histogram[V1_MEASUREMENT_BLOCK_INDEX])
        self.assertEqual(expected_histogram, first_experiment.data.counts_multiple_measurement)
        self.assertTrue(len(first_experiment.data.memory) == number_of_shots)
        memory = first_experiment.data.memory
        self.assertListEqual(memory, expected_memory[V1_MEASUREMENT_BLOCK_INDEX])
        self.assertEqual(expected_memory, first_experiment.data.memory_multiple_measurement)
        for experiment_index in range(len(result)):
            probabilities = first_experiment.data.probabilities_multiple_measurement[experiment_index]
            self.assertTrue(len(expected_histogram_prob[experiment_index].keys() - probabilities.keys()) == 0)
            for key in set(probabilities.keys()) & set(expected_histogram_prob[experiment_index].keys()):
                self.assertTrue(np.isclose(expected_histogram_prob[experiment_index][key], probabilities[key]))

    @staticmethod
    def _instructions_to_experiment(instructions, memory_slots=2):
        experiment_dictionary = {'instructions': instructions,
                                 'header': {'n_qubits': 2, 'memory_slots': memory_slots,
                                            'name': 'test_circuit',
                                            'qubit_labels': [['q0', 0], ['q0', 1]], 'qreg_sizes': [['q', 2]],
                                            'clbit_labels': [['c0', 0], ['c1', 1]], 'creg_sizes': [['c', 2]],
                                            'metadata': {}, 'global_phase': 0.08}
                                 }
        return experiment_dictionary

    def test_convert_histogram_normal_measurement(self):
        self.run_histogram_test(
            single_experiment=self._instructions_to_experiment(
                [{'name': 'h', 'qubits': [0]},
                 {'name': 'cx', 'qubits': [0, 1]},
                 {'name': 'measure', 'qubits': [0], 'memory': [0]},
                 {'name': 'measure', 'qubits': [1], 'memory': [1]}]),
            mock_result1={'id': 1, 'histogram': [{'0': 0.1, '1': 0.2, '2': 0.3, '3': 0.4}],
                          'execution_time_in_seconds': 2.1, 'number_of_qubits': 2,
                          'raw_data_url': 'http://saevar-qutech-nginx/api/results/24/raw-data/'},
            mock_result2=[[[0, 0]]] * 100 + [[[1, 0]]] * 200 + [[[0, 1]]] * 300 + [[[1, 1]]] * 400,
            expected_histogram=[{'0x0': 100, '0x1': 200, '0x2': 300, '0x3': 400}],
            expected_histogram_prob=[{'0x0': 0.1, '0x1': 0.2, '0x2': 0.3, '0x3': 0.4}],
            expected_memory=[['0x0'] * 100 + ['0x1'] * 200 + ['0x2'] * 300 + ['0x3'] * 400]
        )

    def test_classical_bits_are_displayed_correctly(self):
        self.run_histogram_test(
            single_experiment=self._instructions_to_experiment(
                [{'name': 'h', 'qubits': [0]},
                 {'name': 'cx', 'qubits': [0, 1]},
                 {'name': 'measure', 'qubits': [0], 'memory': [0]},
                 {'name': 'measure', 'qubits': [0], 'memory': [3]},
                 {'name': 'measure', 'qubits': [1], 'memory': [4]},
                 {'name': 'measure', 'qubits': [1], 'memory': [7]}],
                memory_slots=8),
            mock_result1={'id': 1, 'histogram': [{'0': 0.1, '1': 0.2, '2': 0.3, '3': 0.4}],
                          'execution_time_in_seconds': 2.1, 'number_of_qubits': 2,
                          'raw_data_url': 'http://saevar-qutech-nginx/api/results/24/raw-data/'},
            mock_result2=[[[0, 0]]] * 100 + [[[1, 0]]] * 200 + [[[0, 1]]] * 300 + [[[1, 1]]] * 400,
            expected_histogram=[{'0x0': 100, '0x9': 200, '0x90': 300, '0x99': 400}],
            expected_histogram_prob=[{'0x0': 0.1, '0x9': 0.2, '0x90': 0.3, '0x99': 0.4}],
            expected_memory=[['0x0'] * 100 + ['0x9'] * 200 + ['0x90'] * 300 + ['0x99'] * 400]
        )

    def test_convert_histogram_swapped_classical_qubits(self):
        self.run_histogram_test(
            single_experiment=self._instructions_to_experiment(
                [{'name': 'h', 'qubits': [0]},
                 {'name': 'cx', 'qubits': [0, 1]},
                 {'name': 'measure', 'qubits': [0], 'memory': [1]},
                 {'name': 'measure', 'qubits': [1], 'memory': [0]}]),
            mock_result1={'id': 1, 'histogram': [{'0': 0.1, '1': 0.2, '2': 0.3, '3': 0.4}],
                          'execution_time_in_seconds': 2.1, 'number_of_qubits': 2,
                          'raw_data_url': 'http://saevar-qutech-nginx/api/results/24/raw-data/'},
            mock_result2=[[[0, 0]]] * 100 + [[[1, 0]]] * 200 + [[[0, 1]]] * 300 + [[[1, 1]]] * 400,
            expected_histogram=[{'0x0': 100, '0x1': 300, '0x2': 200, '0x3': 400}],
            expected_histogram_prob=[{'0x0': 0.1, '0x1': 0.3, '0x2': 0.2, '0x3': 0.4}],
            expected_memory=[['0x0'] * 100 + ['0x2'] * 200 + ['0x1'] * 300 + ['0x3'] * 400]
        )

    def test_convert_histogram_less_measurements_qubit_one(self):
        self.run_histogram_test(
            single_experiment=self._instructions_to_experiment(
                [{'name': 'h', 'qubits': [0]},
                 {'name': 'cx', 'qubits': [0, 1]},
                 {'name': 'measure', 'qubits': [0], 'memory': [0]}]),
            mock_result1={'id': 1, 'histogram': [{'0': 0.1, '1': 0.2, '2': 0.3, '3': 0.4}],
                          'execution_time_in_seconds': 2.1, 'number_of_qubits': 2,
                          'raw_data_url': 'http://saevar-qutech-nginx/api/results/24/raw-data/'},
            mock_result2=[[[0, 0]]] * 100 + [[[1, 0]]] * 200 + [[[0, 1]]] * 300 + [[[1, 1]]] * 400,
            expected_histogram=[{'0x0': 400, '0x1': 600}],
            expected_histogram_prob=[{'0x0': 0.4, '0x1': 0.6}],
            expected_memory=[['0x0'] * 100 + ['0x1'] * 200 + ['0x0'] * 300 + ['0x1'] * 400]
        )

    def test_convert_histogram_less_measurements_qubit_two(self):
        self.run_histogram_test(
            single_experiment=self._instructions_to_experiment(
                [{'name': 'h', 'qubits': [0]},
                 {'name': 'cx', 'qubits': [0, 1]},
                 {'name': 'measure', 'qubits': [1], 'memory': [1]}]),
            mock_result1={'id': 1, 'histogram': [{'0': 0.1, '1': 0.2, '2': 0.3, '3': 0.4}],
                          'execution_time_in_seconds': 2.1, 'number_of_qubits': 2,
                          'raw_data_url': 'http://saevar-qutech-nginx/api/results/24/raw-data/'},
            mock_result2=[[[0, 0]]] * 100 + [[[1, 0]]] * 200 + [[[0, 1]]] * 300 + [[[1, 1]]] * 400,
            expected_histogram=[{'0x0': 300, '0x2': 700}],
            expected_histogram_prob=[{'0x0': 0.3, '0x2': 0.7}],
            expected_memory=[['0x0'] * 300 + ['0x2'] * 700]
        )

    def test_convert_histogram_classical_bits_measure_same_qubits(self):
        self.run_histogram_test(
            single_experiment={'instructions': [{'name': 'h', 'qubits': [0]},
                                                {'name': 'cx', 'qubits': [0, 1]},
                                                {'name': 'measure', 'qubits': [0], 'memory': [0]},
                                                {'name': 'measure', 'qubits': [1], 'memory': [0]}],
                               'header': {'n_qubits': 2, 'memory_slots': 2, 'name': 'test',
                                          'qubit_labels': [['q0', 0], ['q0', 1]], 'qreg_sizes': [['q', 2]],
                                          'clbit_labels': [['c0', 0], ['c1', 1]], 'creg_sizes': [['c', 2]],
                                          'metadata': {}, 'global_phase': 0.11}
                               },
            mock_result1={'id': 1, 'histogram': [{'0': 0.1, '1': 0.2, '2': 0.3, '3': 0.4}],
                          'execution_time_in_seconds': 2.1, 'number_of_qubits': 2,
                          'raw_data_url': 'http://saevar-qutech-nginx/api/results/24/raw-data/'},
            mock_result2=[[[0, 0]]] * 100 + [[[1, 0]]] * 200 + [[[0, 1]]] * 300 + [[[1, 1]]] * 400,
            expected_histogram=[{'0x0': 300, '0x1': 700}],
            expected_histogram_prob=[{'0x0': 0.3, '0x1': 0.7}],
            expected_memory=[['0x0'] * 300 + ['0x1'] * 700]
        )

    def test_empty_histogram(self):
        with self.assertRaises(QiskitBackendError) as error:
            self.run_histogram_test(
                single_experiment=self._instructions_to_experiment(
                    [{'name': 'h', 'qubits': [0]},
                     {'name': 'cx', 'qubits': [0, 1]},
                     {'name': 'measure', 'qubits': [1], 'memory': [1]}]),
                mock_result1={'id': 1, 'histogram': [{}], 'execution_time_in_seconds': 2.1,
                              'number_of_qubits': 2, 'raw_text': 'oopsy daisy',
                              'raw_data_url': 'http://saevar-qutech-nginx/api/results/24/raw-data/'},
                mock_result2=[],
                expected_histogram=[],
                expected_histogram_prob=[],
                expected_memory=[]
            )
        self.assertEqual(('Result from backend contains no histogram data!\noopsy daisy',), error.exception.args)

    def test_convert_histogram_mutiple_measurement(self):
        self.run_histogram_test(
            single_experiment=self._instructions_to_experiment(
                [{'name': 'h', 'qubits': [0]},
                 {'name': 'cx', 'qubits': [0, 1]},
                 {'name': 'measure', 'qubits': [0], 'memory': [0]},
                 {'name': 'measure', 'qubits': [1], 'memory': [1]},
                 {'name': 'h', 'qubits': [0]},
                 {'name': 'cx', 'qubits': [0, 1]},
                 {'name': 'measure', 'qubits': [0], 'memory': [0]},
                 {'name': 'measure', 'qubits': [1], 'memory': [1]}]),
            mock_result1={'id': 1, 'histogram': [{'0': 0.1, '1': 0.2, '2': 0.3, '3': 0.4},
                                                 {'0': 0.4, '1': 0.3, '2': 0.2, '3': 0.1}],
                          'execution_time_in_seconds': 2.1, 'number_of_qubits': 2,
                          'raw_data_url': 'http://saevar-qutech-nginx/api/results/24/raw-data/'},
            mock_result2=[[[0, 0], [0, 0]]] * 100 + [[[1, 0], [0, 0]]] * 200 + [[[0, 1], [0, 0]]] * 100 +
                         [[[0, 1], [1, 0]]] * 200 + [[[1, 1], [1, 0]]] * 100 + [[[1, 1], [0, 1]]] * 200 +
                         [[[1, 1], [1, 1]]] * 100,
            expected_histogram=[{'0x0': 100, '0x1': 200, '0x2': 300, '0x3': 400},
                                {'0x0': 400, '0x1': 300, '0x2': 200, '0x3': 100}],
            expected_histogram_prob=[{'0x0': 0.1, '0x1': 0.2, '0x2': 0.3, '0x3': 0.4},
                                     {'0x0': 0.4, '0x1': 0.3, '0x2': 0.2, '0x3': 0.1}],
            expected_memory=[['0x0'] * 100 + ['0x1'] * 200 + ['0x2'] * 300 + ['0x3'] * 400,
                             ['0x0'] * 400 + ['0x1'] * 300 + ['0x2'] * 200 + ['0x3'] * 100]
        )

    def test_convert_histogram_mutiple_measurement_not_all_bits_measured(self):
        self.run_histogram_test(
            single_experiment=self._instructions_to_experiment(
                [{'name': 'h', 'qubits': [0]},
                 {'name': 'cx', 'qubits': [0, 1]},
                 {'name': 'measure', 'qubits': [1], 'memory': [1]},
                 {'name': 'barrier', 'qubits': [0, 1]},
                 {'name': 'h', 'qubits': [0]},
                 {'name': 'cx', 'qubits': [0, 1]},
                 {'name': 'measure', 'qubits': [0], 'memory': [0]},
                 {'name': 'measure', 'qubits': [1], 'memory': [1]}]),
            mock_result1={'id': 1, 'histogram': [{'0': 0.5, '2': 0.5},
                                                 {'0': 0.17, '1': 0.17, '2': 0.33, '3': 0.33}],
                          'execution_time_in_seconds': 2.1, 'number_of_qubits': 2,
                          'raw_data_url': 'http://saevar-qutech-nginx/api/results/24/raw-data/'},
            mock_result2=[[[None, 0], [0, 0]]] * 170 + [[[None, 0], [1, 0]]] * 170 + [[[None, 0], [0, 1]]] * 160 +
                         [[[None, 1], [0, 1]]] * 170 + [[[None, 1], [1, 1]]] * 330,
            expected_histogram=[{'0x0': 500, '0x2': 500},
                                {'0x0': 170, '0x1': 170, '0x2': 330, '0x3': 330}],
            expected_histogram_prob=[{'0x0': 0.5, '0x2': 0.5},
                                     {'0x0': 0.17, '0x1': 0.17, '0x2': 0.33, '0x3': 0.33}],
            expected_memory=[['0x0'] * 500 + ['0x2'] * 500,
                             ['0x0'] * 170 + ['0x1'] * 170 + ['0x2'] * 330 + ['0x3'] * 330]
        )
