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

import io
import warnings
import json
import coreapi
from collections import OrderedDict
from functools import reduce
from unittest import TestCase
from unittest.mock import MagicMock, patch

from projectq.meta import LogicalQubitIDTag
from projectq.ops import (CNOT, NOT, Allocate, Barrier,
                          Deallocate, FlushGate, H, Measure,
                          Ph, Rx, Ry, Rz, S, Sdag, Swap, T, Tdag, Toffoli, X,
                          Y, Z, R)

from quantuminspire.api import V1_MEASUREMENT_BLOCK_INDEX
from quantuminspire.exceptions import ProjectQBackendError, AuthenticationError
from quantuminspire.projectq.backend_qx import QIBackend


class MockApiClient:

    def __init__(self):
        result = {'histogram': [{'00': 0.49, '11': 0.51}], 'results': 'dummy', 'measurement_mask': [[1, 1]]}
        self.execute_qasm = MagicMock(return_value=result)
        self.get_backend_type = MagicMock(return_value=dict({'is_hardware_backend': False,
                                                             'is_allowed': True,
                                                             'allowed_operations': {
                                                                 'display': ['display', 'display_binary'],
                                                                 'measure': ['measure_x', 'measure_y',
                                                                             'measure_z', 'measure'],
                                                                 'measure_all': ['measure_all'],
                                                                 'parameterized_single_gates': ['rx', 'ry',
                                                                                                'rz'],
                                                                 'prep': ['prep_x', 'prep_y', 'prep_z', 'prep'],
                                                                 'single_gates': ['mx90', 'my90', 'x90', 'y90',
                                                                                  't', 'tdag', 's', 'sdag',
                                                                                  'x', 'y', 'z', 'h', 'i'],
                                                                 'dual_gates': ['cz', 'cnot', 'swap', 'cr'],
                                                                 'triple_gates': ['toffoli'],
                                                                 'barrier': ['barrier'],
                                                                 'wait': ['wait']
                                                             },
                                                             'flags': ['multiple_measurement'],
                                                             'max_number_of_shots': 4096,
                                                             'number_of_qubits': 26}))


class QIBackendNonProtected(QIBackend):

    @property
    def quantum_inspire_api(self):
        return self._quantum_inspire_api

    @property
    def backend(self):
        return self._backend_type

    @property
    def is_simulation_backend(self):
        return self._is_simulation_backend

    @is_simulation_backend.setter
    def is_simulation_backend(self, x):
        self._is_simulation_backend = x

    @property
    def full_state_projection(self):
        return self._full_state_projection

    @full_state_projection.setter
    def full_state_projection(self, x):
        self._full_state_projection = x

    @property
    def quantum_inspire_result(self):
        return self._quantum_inspire_result

    @quantum_inspire_result.setter
    def quantum_inspire_result(self, x):
        self._quantum_inspire_result = x

    @property
    def clear(self):
        return self._clear

    @clear.setter
    def clear(self, x):
        self._clear = x

    @property
    def the_cqasm(self):
        return self.cqasm()

    @the_cqasm.setter
    def the_cqasm(self, x):
        self._cqasm = x

    @property
    def measured_states(self):
        return self._measured_states

    @measured_states.setter
    def measured_states(self, x):
        self._measured_states = x

    @property
    def allocation_map(self):
        return self._allocation_map

    @allocation_map.setter
    def allocation_map(self, x):
        self._allocation_map = x

    @property
    def measured_ids(self):
        return self._measured_ids

    @measured_ids.setter
    def measured_ids(self, x):
        self._measured_ids = x

    @property
    def qasm(self):
        return self._qasm

    @qasm.setter
    def qasm(self, x):
        self._qasm = x

    @property
    def number_of_qubits(self):
        return self._number_of_qubits

    @property
    def max_number_of_qubits(self):
        return self._max_number_of_qubits

    @max_number_of_qubits.setter
    def max_number_of_qubits(self, x):
        self._max_number_of_qubits = x

    def reset(self):
        self._reset()

    def run(self):
        self._run()

    def logical_to_physical(self, qb_id):
        return self._logical_to_physical(qb_id)

    def simulated_to_logical(self, qb_id):
        return self._physical_to_logical(self._simulated_to_physical(qb_id))

    def filter_result_by_measured_qubits(self):
        self._filter_result_by_measured_qubits()

    def register_random_measurement_outcome(self):
        self._register_random_measurement_outcome()


class TestProjectQBackend(TestCase):

    def setUp(self):
        self.hardware_backend_type = dict({'is_hardware_backend': True,
                                           'is_allowed': True,
                                           'allowed_operations': {
                                              'measure': ['measure_z', 'measure'],
                                              'measure_all': ['measure_all'],
                                              'parameterized_single_gates': ['rx', 'ry', 'rz'],
                                              'single_gates': ['x', 'y', 'z', 'h', 'i'],
                                              'dual_gates': ['cz', 'cnot', 'swap']
                                           },
                                           'max_number_of_shots': 4096,
                                           'max_number_of_simultaneous_jobs': 1,
                                           'topology': {'edges': []},
                                           'number_of_qubits': 3})

        self.simulator_backend_type = dict({'is_hardware_backend': False,
                                            'is_allowed': True,
                                            'allowed_operations': {},
                                            'max_number_of_shots': 4096,
                                            'max_number_of_simultaneous_jobs': 3,
                                            'topology': {'edges': []},
                                            'number_of_qubits': 5})

        warnings.filterwarnings("ignore", category=PendingDeprecationWarning)

        self.api = MockApiClient()
        self.qi_backend = QIBackendNonProtected(quantum_inspire_api=self.api)
        self.qi_verbose_backend = QIBackendNonProtected(quantum_inspire_api=self.api, verbose=2)
        self.api.get_backend_type = MagicMock(return_value=self.hardware_backend_type)
        self.qi_hw_backend = QIBackendNonProtected(quantum_inspire_api=self.api)

    def test_init_has_correct_values(self):
        self.assertIsInstance(self.qi_backend.qasm, str)
        self.assertEqual(self.qi_backend.quantum_inspire_api, self.api)
        self.assertIsNotNone(self.qi_backend.backend)

    def test_init_without_api_has_correct_values(self):
        with patch.dict('os.environ', values={'QI_TOKEN': 'token'}):
            coreapi.Client.get = MagicMock()
            result = self.simulator_backend_type
            coreapi.Client.action = MagicMock(return_value=result)
            self.qi_backend_no_api = QIBackendNonProtected()
            self.assertIsInstance(self.qi_backend_no_api.qasm, str)
            self.assertNotEqual(self.qi_backend_no_api.quantum_inspire_api, None)
            self.assertIsNotNone(self.qi_backend_no_api.backend)
            self.assertTrue(self.qi_backend_no_api.is_simulation_backend)

    def test_init_raises_error_no_runs(self):
        num_runs = 0
        self.assertRaisesRegex(ProjectQBackendError, 'Invalid number of runs \(num_runs=0\)',
                               QIBackend, num_runs, 0, self.api)

    def test_init_raises_no_account_authentication_error(self):
        json.load = MagicMock()
        json.load.return_value = {'faulty_key': 'faulty_token'}
        with patch.dict('os.environ', values={'QI_TOKEN': ''}):
            self.assertRaisesRegex(AuthenticationError, 'Make sure you have saved your token credentials on disk or '
                                                        'provide a QuantumInspireAPI instance as parameter to '
                                                        'QIBackend',
                                   QIBackend)

    def test_cqasm_returns_correct_cqasm_data(self):
        expected = 'fake_cqasm_data'
        self.qi_backend.the_cqasm = expected
        actual = self.qi_backend.the_cqasm
        self.assertEqual(actual, expected)

    def test_is_available_verbose_prints_data(self):
        command = MagicMock()
        command.gate = CNOT
        api = MockApiClient()
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            backend = QIBackend(quantum_inspire_api=api, verbose=3)
            _ = backend.is_available(command)
            std_output = mock_stdout.getvalue()
        self.assertTrue(std_output.startswith("ProjectQ doesn't have an equivalent gate for cQASM gate 'wait'"))
        self.assertTrue('call to is_available with cmd ' in std_output)

    @patch('quantuminspire.projectq.backend_qx.get_control_count')
    def __is_available_assert_equal(self, gate, expected, function_mock, count=0):
        command = MagicMock()
        command.gate = gate
        api = MockApiClient()
        function_mock.return_value = count
        backend = QIBackend(quantum_inspire_api=api)
        actual = backend.is_available(command)
        self.assertEqual(actual, expected, msg="{} failed!".format(gate))

    def test_is_available_correct_result(self):
        self.__is_available_assert_equal(NOT, True, count=1)
        self.__is_available_assert_equal(NOT, True, count=2)
        self.__is_available_assert_equal(NOT, False, count=3)
        self.__is_available_assert_equal(CNOT, False, count=0)
        self.__is_available_assert_equal(Z, True, count=1)
        self.__is_available_assert_equal(Z, False, count=3)
        self.__is_available_assert_equal(R, True, count=1)
        self.__is_available_assert_equal(Ph(0.4), False)
        for gate in [Measure, Allocate, Deallocate, Barrier, T, Tdag,
                     S, Sdag, Swap, H, X, Y, Z, Rx(0.1), Ry(0.2), Rz(0.3)]:
            self.__is_available_assert_equal(gate, True)

    def test_reset_is_cleared(self):
        self.qi_backend.clear = True
        self.qi_backend.reset()
        self.assertTrue(self.qi_backend.clear)

    @patch('quantuminspire.projectq.backend_qx.get_control_count')
    def __store_function_assert_equal(self, identity, gate, qasm, function_mock, count=0, nr_of_qubits=1, verbose=0):
        if count + nr_of_qubits > 3:
            raise ValueError("Invalid testcase: count + nr_of_qubits > 3")
        api = MockApiClient()
        function_mock.return_value = count
        backend = QIBackend(quantum_inspire_api=api, verbose=verbose)
        command_alloc0 = MagicMock(gate=Allocate, qubits=[[MagicMock(id=0)]])
        command_alloc1 = MagicMock(gate=Allocate, qubits=[[MagicMock(id=1)]])
        command_alloc2 = MagicMock(gate=Allocate, qubits=[[MagicMock(id=2)]])
        qubits_list = [[MagicMock(id=identity+x)] for x in range(nr_of_qubits)]
        control_qubits_list = [MagicMock(id=x) for x in range(count)]
        command = MagicMock(gate=gate, qubits=qubits_list,
                            control_qubits=control_qubits_list)
        command_list = [command_alloc0, command_alloc1, command_alloc2, command]
        backend.receive(command_list)
        self.assertEqual(backend.qasm, qasm)

    @patch('quantuminspire.projectq.backend_qx.get_control_count')
    def __store_function_raises_error(self, gate, function_mock, count=0):
        identity = 1
        api = MockApiClient()
        function_mock.return_value = count
        backend = QIBackend(quantum_inspire_api=api)
        command = [MagicMock(gate=gate, qubits=[[MagicMock(id=identity)], [MagicMock(id=identity + 1)]],
                             control_qubits=[MagicMock(id=identity - 1), MagicMock(id=identity)])]
        self.assertRaises(NotImplementedError, backend.receive, command)

    def test_store_returns_correct_qasm(self):
        angle = 0.1
        self.__store_function_assert_equal(0, NOT, "\nx q[0]")
        self.__store_function_assert_equal(1, NOT, "\ncnot q[0], q[1]", count=1)
        self.__store_function_assert_equal(0, Swap, "\nswap q[0], q[1]", nr_of_qubits=2)
        self.__store_function_assert_equal(1, Z, "\ncz q[0], q[1]", count=1)
        self.__store_function_assert_equal(2, X, "\ntoffoli q[0], q[1], q[2]", count=2)
        self.__store_function_assert_equal(0, Barrier, "\nbarrier q[0]")
        self.__store_function_assert_equal(0, Barrier, "\nbarrier q[0,1]", nr_of_qubits=2)
        self.__store_function_assert_equal(0, Barrier, "\nbarrier q[0,1,2]", nr_of_qubits=3)
        self.__store_function_assert_equal(1, Rz(angle), "\ncr q[0],q[1],{0:.12f}".format(angle), count=1)
        self.__store_function_assert_equal(1, R(angle), "\ncr q[0],q[1],{0:.12f}".format(angle), count=1)
        self.__store_function_assert_equal(1, Rx(angle), "\nrx q[1],{0}".format(angle))
        self.__store_function_assert_equal(1, Ry(angle), "\nry q[1],{0}".format(angle))
        self.__store_function_assert_equal(1, Rz(angle), "\nrz q[1],{0}".format(angle))
        self.__store_function_assert_equal(0, X, "\nx q[0]")
        self.__store_function_assert_equal(0, Y, "\ny q[0]")
        self.__store_function_assert_equal(0, Z, "\nz q[0]")
        self.__store_function_assert_equal(0, H, "\nh q[0]")
        self.__store_function_assert_equal(0, S, "\ns q[0]")
        self.__store_function_assert_equal(0, Sdag, "\nsdag q[0]")
        self.__store_function_assert_equal(0, T, "\nt q[0]")
        self.__store_function_assert_equal(0, Tdag, "\ntdag q[0]")

    @patch('quantuminspire.projectq.backend_qx.get_control_count')
    def __store_function(self, backend, identity, gate, function_mock, count=0):
        function_mock.return_value = count
        command = [MagicMock(gate=gate, qubits=[[MagicMock(id=identity)]],
                             control_qubits=[MagicMock(id=identity - 1), MagicMock(id=identity)])]
        backend.receive(command)

    def test_store_returns_correct_qasm_fsp_program_1(self):
        api = MockApiClient()
        backend = QIBackend(quantum_inspire_api=api)
        backend.main_engine = MagicMock(mapper=None)
        self.__store_function(backend, 0, Allocate)
        self.__store_function(backend, 1, Allocate)
        self.__store_function(backend, 0, H)
        self.__store_function(backend, 1, NOT, count=1)
        self.assertEqual(backend.qasm, "\nh q[0]\ncnot q[0], q[1]")

    def test_store_returns_correct_qasm_fsp_program_2(self):
        api = MockApiClient()
        backend = QIBackend(quantum_inspire_api=api)
        backend.main_engine = MagicMock(mapper=None)
        self.__store_function(backend, 0, Allocate)
        self.__store_function(backend, 1, Allocate)
        self.__store_function(backend, 0, H)
        self.__store_function(backend, 1, NOT, count=1)
        self.__store_function(backend, 0, Measure)
        self.__store_function(backend, 1, Measure)
        self.assertEqual(backend.qasm, "\nh q[0]\ncnot q[0], q[1]")

    def test_store_returns_correct_qasm_non_fsp_program_1(self):
        api = MockApiClient()
        backend = QIBackend(quantum_inspire_api=api)
        backend.main_engine = MagicMock(mapper=None)
        self.__store_function(backend, 0, Allocate)
        self.__store_function(backend, 1, Allocate)
        self.__store_function(backend, 0, Measure)
        self.__store_function(backend, 1, Measure)
        self.__store_function(backend, 0, H)
        self.__store_function(backend, 1, NOT, count=1)
        self.assertEqual(backend.qasm, "\nmeasure q[0]\nmeasure q[1]\nh q[0]\ncnot q[0], q[1]")

    def test_store_returns_correct_qasm_non_fsp_program_2(self):
        api = MockApiClient()
        backend = QIBackend(quantum_inspire_api=api)
        backend.main_engine = MagicMock(mapper=None)
        self.__store_function(backend, 0, Allocate)
        self.__store_function(backend, 1, Allocate)
        self.__store_function(backend, 0, H)
        self.__store_function(backend, 0, Measure)
        self.__store_function(backend, 1, NOT, count=1)
        self.__store_function(backend, 1, Measure)
        self.assertEqual(backend.qasm, "\nh q[0]\nmeasure q[0]\ncnot q[0], q[1]\nmeasure q[1]")

    def test_store_raises_error(self):
        angle = 0.1
        self.__store_function_raises_error(Toffoli, count=0)
        self.__store_function_raises_error(Rx(angle), count=1)
        self.__store_function_raises_error(Ry(angle), count=1)

    def test_store_allocate_verbose_output(self):
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            api = MockApiClient()
            backend = QIBackend(quantum_inspire_api=api, verbose=1)
            backend.main_engine = MagicMock(mapper=None)
            self.__store_function(backend, 0, Allocate)
            self.assertEqual(backend.qasm, "")
            std_output = mock_stdout.getvalue()

        self.assertTrue('   _allocation_map [(0, 0)]' in std_output)
        self.assertTrue('_store: Allocate gate (0,)' in std_output)

    def test_store_verbose_output(self):
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            api = MockApiClient()
            backend = QIBackend(quantum_inspire_api=api, verbose=3)
            backend.main_engine = MagicMock(mapper=None)
            self.__store_function(backend, 0, Allocate)
            self.assertEqual(backend.qasm, "")
            std_output = mock_stdout.getvalue()
        self.assertTrue(std_output.startswith("ProjectQ doesn't have an equivalent gate for cQASM gate 'wait'"))
        self.assertTrue('_store ' in std_output)
        self.assertTrue(': cmd ' in std_output)

    def test_store_deallocate_verbose_output(self):
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            self.__store_function_assert_equal(0, Deallocate, "", verbose=1)
            std_output = mock_stdout.getvalue()
        self.assertTrue('   _allocation_map' in std_output)
        self.assertTrue('_store: Deallocate gate' in std_output)

    @patch('quantuminspire.projectq.backend_qx.get_control_count')
    def test_store_measure_gate_with_mapper(self, function_mock):
        mock_tag = 'mock_my_tag'
        function_mock.return_value = 4
        mapper = MagicMock(current_mapping={mock_tag: 0})
        self.qi_backend.main_engine = MagicMock(mapper=mapper)
        self.__store_function(self.qi_backend, 0, Allocate)
        command = [MagicMock(gate=Measure, qubits=[[MagicMock(id=0)]],
                             tags=[LogicalQubitIDTag(mock_tag)])]
        self.qi_backend.receive(command)
        self.__store_function(self.qi_backend, 0, H)
        self.assertEqual(self.qi_backend.measured_ids, [mock_tag])
        self.assertEqual(self.qi_backend.qasm, "\nmeasure q[0]\nh q[0]")

    @patch('quantuminspire.projectq.backend_qx.get_control_count')
    def test_store_measure_gate_without_mapper(self, function_mock):
        mock_tag = 20
        function_mock.return_value = 4
        self.qi_backend.main_engine = MagicMock(mapper=None)
        self.__store_function(self.qi_backend, 0, Allocate)
        self.__store_function(self.qi_backend, mock_tag, Allocate)
        command = [MagicMock(gate=Measure, qubits=[[MagicMock(id=mock_tag)]],
                             tags=[])]
        self.qi_backend.receive(command)
        self.__store_function(self.qi_backend, 0, H)
        self.assertEqual(self.qi_backend.qasm, "\nmeasure q[20]\nh q[0]")
        self.assertEqual(self.qi_backend.full_state_projection, False)

    def test_logical_to_physical_with_mapper_returns_correct_result(self):
        qd_id = 0
        expected = 1234
        self.qi_backend.main_engine = MagicMock()
        self.qi_backend.main_engine.mapper.current_mapping = {qd_id: expected}
        actual = self.qi_backend.logical_to_physical(qd_id)
        self.assertEqual(actual, expected)

    def test_logical_to_physical_without_mapper_returns_correct_result(self):
        qd_id = 1234
        expected = qd_id
        self.qi_backend.main_engine = MagicMock(mapper=None)
        actual = self.qi_backend.logical_to_physical(qd_id)
        self.assertEqual(actual, expected)

    def test_logical_to_physical_raises_runtime_error(self):
        qd_id = 0
        expected = 1234
        self.qi_backend.main_engine = MagicMock()
        self.qi_backend.main_engine.mapper.current_mapping = {expected: expected}
        self.assertRaises(RuntimeError, self.qi_backend.logical_to_physical, qd_id)

    def test_simulated_to_logical_returns_correct_result(self):
        qd_id = 0
        expected = 2
        self.qi_backend.allocation_map = [(0, 3), (1, 1), (2, 2), (3, 0)]
        self.qi_backend.main_engine = MagicMock()
        self.qi_backend.main_engine.mapper.current_mapping = {0: 0, 1: 1, 2: 3, 3: 2}
        actual = self.qi_backend.simulated_to_logical(qd_id)
        self.assertEqual(actual, expected)

    def test_simulated_to_logical_no_mapper_returns_correct_result(self):
        qd_id = 0
        expected = 3
        self.qi_backend.allocation_map = [(0, 3), (1, 1), (2, 2), (3, 0)]
        self.qi_backend.main_engine = MagicMock(mapper=None)
        actual = self.qi_backend.simulated_to_logical(qd_id)
        self.assertEqual(actual, expected)

    def test_simulated_to_logical_for_hardware_backend_returns_correct_result(self):
        qd_id = 3
        expected = 2
        self.qi_backend.is_simulation_backend = False
        self.qi_backend.main_engine = MagicMock()
        self.qi_backend.main_engine.mapper.current_mapping = {0: 0, 1: 2, 2: 3, 3: 1}
        actual = self.qi_backend.simulated_to_logical(qd_id)
        self.assertEqual(actual, expected)

    def test_simulated_to_logical_no_mapper_raises_runtime_error(self):
        qd_id = 4
        self.qi_backend.allocation_map = [(0, 3), (1, 1), (2, 2), (3, 0)]
        self.qi_backend.main_engine = MagicMock(mapper=None)
        self.assertRaises(RuntimeError, self.qi_backend.simulated_to_logical, qd_id)

    def test_simulated_to_logical_for_hardware_backend_raises_runtime_error(self):
        qd_id = 4
        self.qi_backend.is_simulation_backend = False
        self.qi_backend.main_engine = MagicMock()
        self.qi_backend.main_engine.mapper.current_mapping = {0: 0, 1: 2, 2: 3, 3: 1}
        self.assertRaises(RuntimeError, self.qi_backend.simulated_to_logical, qd_id)

    def test_get_probabilities_raises_runtime_error(self):
        api = MockApiClient()
        backend = QIBackend(quantum_inspire_api=api)
        self.assertRaises(RuntimeError, backend.get_probabilities, None)
        self.assertRaises(RuntimeError, backend.get_probabilities_multiple_measurement, None)

    def test_get_probabilities_returns_correct_result(self):
        value_a = 0.4892578125
        value_b = 0.5097656250
        self.qi_backend.measured_states = [{0: value_a, 11: value_b}]  # 00000000 and 00001011
        expected = {'00': value_a, '11': value_b}
        self.qi_backend.main_engine = MagicMock()
        self.qi_backend.measured_ids = [0, 1]
        self.qi_backend.allocation_map = [(0, 0), (1, 1)]
        self.qi_backend.main_engine.mapper.current_mapping = {0: 0, 1: 1}
        actual = self.qi_backend.get_probabilities([MagicMock(id=0), MagicMock(id=1)])
        self.assertDictEqual(expected, actual)

    def test_get_probabilities_reversed_measurement_order_returns_correct_result(self):
        value_a = 0.4892578125
        value_b = 0.5097656250
        self.qi_backend.measured_states = [{0: value_a, 11: value_b}]  # 00000000 and 00001011
        expected = {'00': value_a, '10': value_b}
        self.qi_backend.main_engine = MagicMock()
        self.qi_backend.measured_ids = [1, 0]
        self.qi_backend.allocation_map = [(0, 0), (1, 1), (2, 2)]
        self.qi_backend.main_engine.mapper.current_mapping = {0: 0, 1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 6: 6, 7: 7}
        actual = self.qi_backend.get_probabilities([MagicMock(id=0), MagicMock(id=2)])
        self.assertDictEqual(expected, actual)

    def test_get_probabilities_multiple_measurement_raises_runtime_error(self):
        api = MockApiClient()
        backend = QIBackend(quantum_inspire_api=api)
        self.assertRaises(RuntimeError, backend.get_probabilities_multiple_measurement, None)

    def test_get_probabilities_multiple_measurement_result(self):
        class QB:
            def __init__(self, qubit_id: int) -> None:
                self.id: int = qubit_id

        mm_result = {'id': 502,
                     'url': 'https,//api.quantum-inspire.com/results/502/',
                     'job': 'https,//api.quantum-inspire.com/jobs/10/',
                     'created_at': '1900-01-01T01:00:00:00000Z',
                     'number_of_qubits': 3,
                     'seconds': 0.0,
                     'raw_text': '',
                     'raw_data_url': 'https,//api.quantum-inspire.com/results/502/raw-data/f2b6/',
                     'histogram': [{'1': 0.5068359375, '0': 0.4931640625},
                                   {'5': 0.4068359375, '1': 0.2, '0': 0.3931640625}],
                     'histogram_url': 'https,//api.quantum-inspire.com/results/502/histogram/f2b6/',
                     'measurement_mask': [[1, 0, 0], [1, 0, 1]],
                     'quantum_states_url': 'https,//api.quantum-inspire.com/results/502/quantum-states/f2b6d/',
                     'measurement_register_url': 'https,//api.quantum-inspire.com/results/502/f2b6d/'}

        self.qi_backend.main_engine = MagicMock(mapper=None)
        self.qi_backend.allocation_map = [(0, 0), (1, 1), (2, 2)]
        self.qi_backend.quantum_inspire_result = mm_result
        self.qi_backend.full_state_projection = False
        self.qi_backend.filter_result_by_measured_qubits()
        self.assertEqual(self.qi_backend.measured_states, [{1: 0.5068359375, 0: 0.4931640625},
                                                           {5: 0.4068359375, 1: 0.2, 0: 0.3931640625}])
        self.qi_backend.register_random_measurement_outcome()

        nr_of_measured_bits = reduce(lambda x, y: x + y, mm_result['measurement_mask'][V1_MEASUREMENT_BLOCK_INDEX], 0)
        self.assertEqual(self.qi_backend.main_engine.set_measurement_result.call_count, nr_of_measured_bits)
        qureg = [QB(id) for id in range(3)]
        probabilities = self.qi_backend.get_probabilities(qureg)
        self.assertDictEqual(probabilities, {'101': 0.4068359375, '100': 0.2, '000': 0.3931640625})
        probabilities_list = self.qi_backend.get_probabilities_multiple_measurement(qureg)
        self.assertListEqual(probabilities_list, [{'100': 0.5068359375, '000': 0.4931640625},
                                                  {'101': 0.4068359375, '100': 0.2, '000': 0.3931640625}])

    @patch('quantuminspire.projectq.backend_qx.get_control_count')
    def test_receive(self, function_mock):
        function_mock.return_value = 1
        command_alloc0 = MagicMock(gate=Allocate, qubits=[[MagicMock(id=0)]])
        command_alloc1 = MagicMock(gate=Allocate, qubits=[[MagicMock(id=1)]])
        command = MagicMock(gate=NOT, qubits=[[MagicMock(id=0)]], control_qubits=[MagicMock(id=1)])
        command_list = [command_alloc0, command_alloc1, command, MagicMock(gate=FlushGate())]
        self.qi_backend.main_engine = MagicMock()
        self.qi_backend.main_engine.mapper.current_mapping = {0: 0, 1: 1}  # bits 0 and 1 are logical bits 0 and 1
        with patch('sys.stdout', new_callable=io.StringIO):
            self.qi_backend.receive(command_list)
        self.assertEqual(self.qi_backend.qasm, "")
        self.assertTrue(self.qi_backend.clear)

    @patch('quantuminspire.projectq.backend_qx.get_control_count')
    def test_reuse_after_flush_raises_runtime_error(self, function_mock):
        function_mock.return_value = 1
        command_alloc0 = MagicMock(gate=Allocate, qubits=[[MagicMock(id=0)]])
        command_alloc1 = MagicMock(gate=Allocate, qubits=[[MagicMock(id=1)]])
        command = MagicMock(gate=NOT, qubits=[[MagicMock(id=0)]], control_qubits=[MagicMock(id=1)])
        command_list = [command_alloc0, command_alloc1, command, MagicMock(gate=FlushGate()), command]
        api = MockApiClient()
        backend = QIBackend(quantum_inspire_api=api)
        backend.main_engine = MagicMock()
        backend.main_engine.mapper.current_mapping = {0: 0, 1: 1}  # bits 0 and 1 are logical bits 0 and 1
        with patch('sys.stdout', new_callable=io.StringIO):
            self.assertRaisesRegex(RuntimeError, "Same instance of QIBackend used for circuit after Flush.",
                                   backend.receive, command_list)

    @patch('quantuminspire.projectq.backend_qx.get_control_count')
    def test_receive_multiple_flush(self, function_mock):
        function_mock.return_value = 1
        command_alloc0 = MagicMock(gate=Allocate, qubits=[[MagicMock(id=0)]])
        command_alloc1 = MagicMock(gate=Allocate, qubits=[[MagicMock(id=1)]])
        command = MagicMock(gate=NOT, qubits=[[MagicMock(id=0)]], control_qubits=[MagicMock(id=1)])
        command_list = [command_alloc0, command_alloc1, command, MagicMock(gate=FlushGate()),
                        MagicMock(gate=FlushGate())]
        self.qi_backend.main_engine = MagicMock()
        self.qi_backend.main_engine.mapper.current_mapping = {0: 0, 1: 1}  # bits 0 and 1 are logical bits 0 and 1
        with patch('sys.stdout', new_callable=io.StringIO):
            self.qi_backend.receive(command_list)
        self.assertEqual(self.qi_backend.qasm, "")
        self.assertTrue(self.qi_backend.clear)

    @patch('quantuminspire.projectq.backend_qx.get_control_count')
    def test_flush_with_no_measurements_but_nfsp(self, function_mock):
        function_mock.return_value = 1
        command_alloc0 = MagicMock(gate=Allocate, qubits=[[MagicMock(id=0)]])
        command_alloc1 = MagicMock(gate=Allocate, qubits=[[MagicMock(id=1)]])
        command_alloc2 = MagicMock(gate=Allocate, qubits=[[MagicMock(id=1)]])
        command_dealloc1 = MagicMock(gate=Deallocate, qubits=[[MagicMock(id=1)]])
        command = MagicMock(gate=NOT, qubits=[[MagicMock(id=0)]], control_qubits=[MagicMock(id=1)])
        command_list = [command_alloc0, command_alloc1, command_dealloc1, command_alloc2, command,
                        MagicMock(gate=FlushGate())]
        api = MockApiClient()
        backend = QIBackend(quantum_inspire_api=api, verbose=1)
        backend.main_engine = MagicMock(mapper=None)
        with patch('sys.stdout', new_callable=io.StringIO):
            backend.receive(command_list)
        self.assertEqual(backend.qasm, "")

    def test_maximum_qubit(self):
        command_alloc0 = MagicMock(gate=Allocate, qubits=[[MagicMock(id=0)]])
        command_alloc1 = MagicMock(gate=Allocate, qubits=[[MagicMock(id=1)]])
        command_alloc2 = MagicMock(gate=Allocate, qubits=[[MagicMock(id=2)]])
        command_dealloc0 = MagicMock(gate=Deallocate, qubits=[[MagicMock(id=0)]])
        command_dealloc1 = MagicMock(gate=Deallocate, qubits=[[MagicMock(id=1)]])
        command_dealloc2 = MagicMock(gate=Deallocate, qubits=[[MagicMock(id=2)]])
        command_list = [command_alloc1, command_alloc2, command_dealloc1,
                        command_alloc0, command_dealloc0, command_dealloc2]
        self.qi_backend.main_engine = MagicMock()
        self.qi_backend.receive(command_list)
        self.assertEqual(self.qi_backend.number_of_qubits, 3)
        self.assertEqual(len(self.qi_backend.allocation_map), 3)

    def test_allocate_8_simulator_has_4(self):
        command_alloc0 = MagicMock(gate=Allocate, qubits=[[MagicMock(id=0)]])
        command_alloc1 = MagicMock(gate=Allocate, qubits=[[MagicMock(id=1)]])
        command_alloc2 = MagicMock(gate=Allocate, qubits=[[MagicMock(id=2)]])
        command_alloc3 = MagicMock(gate=Allocate, qubits=[[MagicMock(id=3)]])
        command_alloc4 = MagicMock(gate=Allocate, qubits=[[MagicMock(id=4)]])
        command_alloc5 = MagicMock(gate=Allocate, qubits=[[MagicMock(id=5)]])
        command_alloc6 = MagicMock(gate=Allocate, qubits=[[MagicMock(id=6)]])
        command_alloc7 = MagicMock(gate=Allocate, qubits=[[MagicMock(id=7)]])
        command_dealloc2 = MagicMock(gate=Deallocate, qubits=[[MagicMock(id=2)]])
        command_dealloc3 = MagicMock(gate=Deallocate, qubits=[[MagicMock(id=3)]])
        command_dealloc4 = MagicMock(gate=Deallocate, qubits=[[MagicMock(id=4)]])
        command_dealloc5 = MagicMock(gate=Deallocate, qubits=[[MagicMock(id=5)]])
        command_dealloc6 = MagicMock(gate=Deallocate, qubits=[[MagicMock(id=6)]])
        command_dealloc7 = MagicMock(gate=Deallocate, qubits=[[MagicMock(id=7)]])

        command_list = [command_alloc0, command_alloc1, command_alloc2, command_alloc3,
                        command_dealloc3, command_dealloc2,
                        command_alloc4, command_dealloc4, command_alloc5, command_alloc6,
                        command_dealloc6, command_dealloc5, command_alloc7, command_dealloc7]
        self.qi_backend.main_engine = MagicMock()
        self.qi_backend.max_number_of_qubits = 4
        self.qi_backend.receive(command_list)
        self.assertEqual(self.qi_backend.number_of_qubits, 4)
        self.assertEqual(len(self.qi_backend.allocation_map), 4)

    def test_allocate_8_simulator_has_5(self):
        command_alloc0 = MagicMock(gate=Allocate, qubits=[[MagicMock(id=0)]])
        command_alloc1 = MagicMock(gate=Allocate, qubits=[[MagicMock(id=1)]])
        command_alloc2 = MagicMock(gate=Allocate, qubits=[[MagicMock(id=2)]])
        command_alloc3 = MagicMock(gate=Allocate, qubits=[[MagicMock(id=3)]])
        command_alloc4 = MagicMock(gate=Allocate, qubits=[[MagicMock(id=4)]])
        command_alloc5 = MagicMock(gate=Allocate, qubits=[[MagicMock(id=5)]])
        command_alloc6 = MagicMock(gate=Allocate, qubits=[[MagicMock(id=6)]])
        command_alloc7 = MagicMock(gate=Allocate, qubits=[[MagicMock(id=7)]])
        command_dealloc3 = MagicMock(gate=Deallocate, qubits=[[MagicMock(id=3)]])
        command_dealloc4 = MagicMock(gate=Deallocate, qubits=[[MagicMock(id=4)]])
        command_dealloc5 = MagicMock(gate=Deallocate, qubits=[[MagicMock(id=5)]])
        command_dealloc7 = MagicMock(gate=Deallocate, qubits=[[MagicMock(id=7)]])

        command_list = [command_alloc0, command_alloc1, command_alloc3,
                        command_dealloc3, command_alloc2,
                        command_alloc4, command_dealloc4, command_alloc6,
                        command_alloc5, command_dealloc5, command_alloc7, command_dealloc7]
        self.qi_backend.max_number_of_qubits = 5
        self.qi_backend.main_engine = MagicMock()
        self.qi_backend.receive(command_list)
        self.assertEqual(self.qi_backend.number_of_qubits, 5)
        self.assertEqual(len(self.qi_backend.allocation_map), 5)
        self.assertEqual(self.qi_backend.allocation_map, [(0, 0), (1, 1), (3, 6), (2, 2), (4, -1)])

    def test_allocate_8_simulator_has_8(self):
        command_alloc0 = MagicMock(gate=Allocate, qubits=[[MagicMock(id=0)]])
        command_alloc1 = MagicMock(gate=Allocate, qubits=[[MagicMock(id=1)]])
        command_alloc2 = MagicMock(gate=Allocate, qubits=[[MagicMock(id=2)]])
        command_alloc3 = MagicMock(gate=Allocate, qubits=[[MagicMock(id=3)]])
        command_alloc4 = MagicMock(gate=Allocate, qubits=[[MagicMock(id=4)]])
        command_alloc5 = MagicMock(gate=Allocate, qubits=[[MagicMock(id=5)]])
        command_alloc6 = MagicMock(gate=Allocate, qubits=[[MagicMock(id=6)]])
        command_alloc7 = MagicMock(gate=Allocate, qubits=[[MagicMock(id=7)]])
        command_dealloc2 = MagicMock(gate=Deallocate, qubits=[[MagicMock(id=2)]])
        command_dealloc3 = MagicMock(gate=Deallocate, qubits=[[MagicMock(id=3)]])
        command_dealloc4 = MagicMock(gate=Deallocate, qubits=[[MagicMock(id=4)]])
        command_dealloc5 = MagicMock(gate=Deallocate, qubits=[[MagicMock(id=5)]])
        command_dealloc6 = MagicMock(gate=Deallocate, qubits=[[MagicMock(id=6)]])
        command_dealloc7 = MagicMock(gate=Deallocate, qubits=[[MagicMock(id=7)]])

        command_list = [command_alloc0, command_alloc1, command_alloc2, command_alloc3,
                        command_dealloc3, command_dealloc2,
                        command_alloc4, command_dealloc4, command_alloc5, command_alloc6,
                        command_dealloc6, command_dealloc5, command_alloc7, command_dealloc7]
        self.qi_backend.main_engine = MagicMock()
        self.qi_backend.max_number_of_qubits = 8
        self.qi_backend.receive(command_list)
        self.assertEqual(self.qi_backend.number_of_qubits, 8)
        self.assertEqual(len(self.qi_backend.allocation_map), 8)

    def test_more_qubits_than_available(self):
        command_alloc0 = MagicMock(gate=Allocate, qubits=[[MagicMock(id=0)]])
        command_alloc1 = MagicMock(gate=Allocate, qubits=[[MagicMock(id=1)]])
        command_alloc2 = MagicMock(gate=Allocate, qubits=[[MagicMock(id=2)]])
        command_alloc3 = MagicMock(gate=Allocate, qubits=[[MagicMock(id=3)]])
        command_alloc4 = MagicMock(gate=Allocate, qubits=[[MagicMock(id=4)]])
        command_alloc5 = MagicMock(gate=Allocate, qubits=[[MagicMock(id=5)]])
        command_alloc6 = MagicMock(gate=Allocate, qubits=[[MagicMock(id=6)]])
        command_alloc7 = MagicMock(gate=Allocate, qubits=[[MagicMock(id=7)]])
        command_dealloc2 = MagicMock(gate=Deallocate, qubits=[[MagicMock(id=2)]])
        command_dealloc3 = MagicMock(gate=Deallocate, qubits=[[MagicMock(id=3)]])
        command_dealloc4 = MagicMock(gate=Deallocate, qubits=[[MagicMock(id=4)]])
        command_dealloc5 = MagicMock(gate=Deallocate, qubits=[[MagicMock(id=5)]])
        command_dealloc6 = MagicMock(gate=Deallocate, qubits=[[MagicMock(id=6)]])
        command_dealloc7 = MagicMock(gate=Deallocate, qubits=[[MagicMock(id=7)]])

        command_list = [command_alloc0, command_alloc1, command_alloc2, command_alloc3,
                        command_dealloc3, command_dealloc2,
                        command_alloc4, command_dealloc4, command_alloc5, command_alloc6,
                        command_dealloc6, command_dealloc5, command_alloc7, command_dealloc7]
        self.qi_backend.main_engine = MagicMock()
        self.qi_backend.max_number_of_qubits = 3
        self.qi_backend.receive(command_list)
        self.assertEqual(self.qi_backend.number_of_qubits, 4)
        self.assertEqual(len(self.qi_backend.allocation_map), 4)

    def test_alloc_map_and_mapping(self):
        value_a = 0.4892578125
        value_b = 0.5097656250
        self.qi_backend.measured_states = [{0: value_a, 11: value_b}]  # 00000000 and 00001011
        expected = {'00': value_a, '10': value_b}
        self.qi_backend.main_engine = MagicMock()
        self.qi_backend.measured_ids = [0, 1]  # bits 0 and 1 measured
        self.qi_backend.main_engine.mapper.current_mapping = {0: 0, 1: 1}   # bits 0 and 1 are logical bits 0 and 1
        # logical bit 0 is mapped on bit 3, logical bit 1 is mapped on bit 2 in cqasm
        self.qi_backend.allocation_map = [(0, 100), (1, 110), (2, 1), (3, 0), (4, 2), (5, 3)]
        # so we get a mask of 1100 (bit 3 and bit 2)
        # 0000 & 1100 = 0000, when we concatenate bit[3] and bit[2] we get 00
        # 1011 & 1100 = 1000, when we concatenate bit[3] and bit[2] we get 10
        # resulting is 00 for state 0000 and 10 for state 1011
        actual = self.qi_backend.get_probabilities([MagicMock(id=0), MagicMock(id=1)])
        self.assertDictEqual(expected, actual)

    def test_alloc_map_and_mapping_with_2_bits_flipped_position_in_alloc_map(self):
        value_a = 0.4892578125
        value_b = 0.5097656250
        self.qi_backend.measured_states = [{0: value_a, 11: value_b}]  # 00000000 and 00001011
        expected = {'00': value_a, '01': value_b}
        self.qi_backend.main_engine = MagicMock()
        self.qi_backend.measured_ids = [0, 1]  # bits 0 and 1 measured
        self.qi_backend.main_engine.mapper.current_mapping = {0: 0, 1: 1}   # bits 0 and 1 are logical bits 0 and 1
        # logical bits 0 is mapped on bit 2, logical bit 1 is mapped on bit 3 in cqasm
        self.qi_backend.allocation_map = [(0, 100), (1, 110), (2, 0), (3, 1), (4, 2), (5, 3)]
        # so we get a mask of 1100 (bit 2 and bit 3)
        # 0000 & 1100 = 0000, when we concatenate bit[2] and bit[3] we get 00
        # 1011 & 1100 = 1000, when we concatenate bit[2] and bit[3] we get 01
        # resulting is 00 for state 0000 and 01 for state 1011
        actual = self.qi_backend.get_probabilities([MagicMock(id=0), MagicMock(id=1)])
        self.assertDictEqual(expected, actual)

    def test_alloc_map_with_alternative_mapping(self):
        value_a = 0.4892578125
        value_b = 0.5097656250
        self.qi_backend.measured_states = [{12: value_a, 59: value_b}]  # 001100 and 111011
        expected = {'10': value_a, '11': value_b}
        self.qi_backend.main_engine = MagicMock()
        self.qi_backend.measured_ids = [0, 1]  # bits 0 and 1 measured
        self.qi_backend.main_engine.mapper.current_mapping = {0: 1, 1: 4}   # bits 0 and 1 are logical bits 1 and 4
        # logical bits 1 is mapped on bit 3, logical bit 4 is mapped on bit 5 in cqasm
        self.qi_backend.allocation_map = [(0, 100), (1, 110), (2, 0), (3, 1), (4, 2), (5, 4)]
        # so we get a mask of 101000 (bit 3 and bit 5)
        # 001100 & 101000 = 001000, when we concatenate bit[3] and bit[5] we get 10
        # 111011 & 101000 = 101000, when we concatenate bit[3] and bit[5] we get 11
        # resulting is 10 for state 001100 and 11 for state 111011
        actual = self.qi_backend.get_probabilities([MagicMock(id=0), MagicMock(id=1)])
        self.assertDictEqual(expected, actual)

    def test_reallocation_of_same_bits(self):
        command_alloc0 = MagicMock(gate=Allocate, qubits=[[MagicMock(id=0)]])
        command_alloc1 = MagicMock(gate=Allocate, qubits=[[MagicMock(id=1)]])
        command_alloc2 = MagicMock(gate=Allocate, qubits=[[MagicMock(id=2)]])
        command_dealloc1 = MagicMock(gate=Deallocate, qubits=[[MagicMock(id=1)]])
        command_dealloc2 = MagicMock(gate=Deallocate, qubits=[[MagicMock(id=2)]])

        command_list = [command_alloc0, command_alloc1, command_alloc2, command_dealloc2, command_dealloc1,
                        command_alloc2, command_alloc1]
        self.qi_backend.main_engine = MagicMock()
        self.qi_backend.receive(command_list)
        self.assertEqual(self.qi_backend.number_of_qubits, 3)
        self.assertEqual(len(self.qi_backend.allocation_map), 3)
        self.assertEqual(self.qi_backend.allocation_map, [(0, 0), (1, 1), (2, 2)])

    def test_reallocation_of_used_bits(self):
        command_alloc0 = MagicMock(gate=Allocate, qubits=[[MagicMock(id=0)]])
        command_alloc1 = MagicMock(gate=Allocate, qubits=[[MagicMock(id=1)]])
        command_alloc2 = MagicMock(gate=Allocate, qubits=[[MagicMock(id=2)]])
        command_dealloc0 = MagicMock(gate=Deallocate, qubits=[[MagicMock(id=0)]])

        command_list = [command_alloc0, command_alloc1, command_alloc2, command_dealloc0, command_alloc1]
        api = MockApiClient()
        backend = QIBackend(quantum_inspire_api=api)
        backend.main_engine = MagicMock()
        self.assertRaisesRegex(RuntimeError, "Bit 1 is already allocated.",
                               backend.receive, command_list)

    def test_deallocation_of_unused_bits(self):
        command_alloc0 = MagicMock(gate=Allocate, qubits=[[MagicMock(id=0)]])
        command_alloc1 = MagicMock(gate=Allocate, qubits=[[MagicMock(id=1)]])
        command_dealloc0 = MagicMock(gate=Deallocate, qubits=[[MagicMock(id=0)]])
        command_dealloc2 = MagicMock(gate=Deallocate, qubits=[[MagicMock(id=2)]])

        command_list = [command_alloc0, command_alloc1, command_dealloc0, command_dealloc2]
        api = MockApiClient()
        backend = QIBackend(quantum_inspire_api=api)
        backend.main_engine = MagicMock()
        self.assertRaisesRegex(RuntimeError, "De-allocated bit 2 was not allocated.",
                               backend.receive, command_list)

    def test_usage_of_non_allocate_qubit(self):
        command_alloc0 = MagicMock(gate=Allocate, qubits=[[MagicMock(id=0)]])
        command_alloc1 = MagicMock(gate=Allocate, qubits=[[MagicMock(id=1)]])
        command_dealloc0 = MagicMock(gate=Deallocate, qubits=[[MagicMock(id=0)]])

        command_h0 = MagicMock(gate=H, qubits=[[MagicMock(id=0)]], control_qubits=[])
        command_h1 = MagicMock(gate=H, qubits=[[MagicMock(id=1)]], control_qubits=[])

        command_list = [command_alloc0, command_alloc1, command_h1, command_dealloc0, command_h0]
        api = MockApiClient()
        backend = QIBackend(quantum_inspire_api=api)
        backend.main_engine = MagicMock()
        self.assertRaisesRegex(RuntimeError, "Bit position in simulation backend not found for physical bit 0.",
                               backend.receive, command_list)

    def test_allocation_of_hardware_backend(self):
        command_alloc0 = MagicMock(gate=Allocate, qubits=[[MagicMock(id=0)]])
        command_alloc1 = MagicMock(gate=Allocate, qubits=[[MagicMock(id=1)]])
        command_alloc2 = MagicMock(gate=Allocate, qubits=[[MagicMock(id=2)]])
        command_dealloc1 = MagicMock(gate=Deallocate, qubits=[[MagicMock(id=1)]])
        command_h0 = MagicMock(gate=H, qubits=[[MagicMock(id=0)]], control_qubits=[])

        command_list = [command_alloc0, command_alloc1, command_dealloc1, command_h0, command_alloc2]
        self.qi_hw_backend.main_engine = MagicMock()
        self.qi_hw_backend.receive(command_list)
        self.assertEqual(self.qi_hw_backend.qasm, "\nh q[0]")
        self.assertEqual(self.qi_hw_backend.number_of_qubits, 3)
        self.assertEqual(len(self.qi_hw_backend.allocation_map), 0)

    @patch('quantuminspire.projectq.backend_qx.get_control_count')
    def test_store_allocation_of_bit_larger_than_capacity_backend(self, function_mock):
        function_mock.return_value = 4
        bit_above_max = self.qi_backend.max_number_of_qubits  # 0..max_number_of_qubits - 1 are valid
        self.qi_backend.main_engine = MagicMock(mapper=None)
        self.__store_function(self.qi_backend, 0, Allocate)
        self.__store_function(self.qi_backend, bit_above_max, Allocate)
        command = [MagicMock(gate=Measure, qubits=[[MagicMock(id=bit_above_max)]],
                             tags=[])]
        self.qi_backend.receive(command)
        self.__store_function(self.qi_backend, 0, H)
        self.assertEqual(self.qi_backend.qasm, "\nmeasure q[1]\nh q[0]")
        self.assertEqual(self.qi_backend.full_state_projection, False)

    def test_run_no_qasm(self):
        self.qi_backend.run()
        self.assertEqual(self.qi_backend.qasm, "")

    def test_run_has_correct_output(self):
        with patch('sys.stdout', new_callable=io.StringIO) as std_mock:
            self.qi_verbose_backend.qasm = "_"
            self.qi_verbose_backend.measured_ids = [0]
            self.qi_verbose_backend.allocation_map = [(0, 0), (1, 1)]
            self.qi_verbose_backend.main_engine = MagicMock()
            self.qi_verbose_backend.main_engine.mapper.current_mapping = {0: 0, 1: 1}
            self.qi_verbose_backend.run()
            std_output = std_mock.getvalue()
            actual = self.qi_verbose_backend.quantum_inspire_result
        self.api.execute_qasm.assert_called_once()
        self.assertEqual(self.api.execute_qasm(), actual)
        self.assertTrue(self.qi_verbose_backend.clear)
        self.assertTrue(std_output.startswith('version 1.0\n# cQASM generated by Quantum Inspire'))
        self.assertTrue('qubits 0' in std_output)

    def _run_raises_error_no_result(self, return_val):
        with patch('sys.stdout', new_callable=io.StringIO):
            self.qi_backend.qasm = "_"
            self.qi_backend.measured_ids = []
            self.qi_backend.allocation_map = [(0, 0), (1, 1)]
            self.qi_backend.main_engine = MagicMock()
            self.qi_backend.main_engine.mapper.current_mapping = {0: 0, 1: 1}
            result_mock = MagicMock()
            result_mock.get.return_value = return_val
            self.api.execute_qasm.return_value = result_mock
            self.assertRaisesRegex(ProjectQBackendError, 'Result from backend contains no histogram data!',
                                   self.qi_backend.run)
        self.api.execute_qasm.assert_called_once()

    def test_run_raises_error_no_result_as_ordered_dict(self):
        self._run_raises_error_no_result([OrderedDict()])

    def test_run_raises_error_no_result_as_empty_dict(self):
        self._run_raises_error_no_result([{}])
