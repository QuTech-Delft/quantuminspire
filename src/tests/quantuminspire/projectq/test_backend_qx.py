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
import warnings
import json
import os
import coreapi
from collections import OrderedDict
from unittest.mock import MagicMock, patch

from projectq.meta import LogicalQubitIDTag, get_control_count
from projectq.ops import (CNOT, CX, CZ, NOT, QFT, All, Allocate, Barrier,
                          BasicPhaseGate, C, Deallocate, FlushGate, H, Measure,
                          Ph, Rx, Ry, Rz, S, Sdag, Swap, T, Tdag, Toffoli, X,
                          Y, Z)

from quantuminspire.exceptions import ProjectQBackendError, AuthenticationError
from quantuminspire.projectq.backend_qx import QIBackend


class MockApiClient:

    def __init__(self):
        result = {'histogram': {'00': 0.49, '11': 0.51}, 'results': 'dummy'}
        self.execute_qasm = MagicMock(return_value=result)
        self.get_backend_type = MagicMock(return_value=OrderedDict({"is_hardware_backend": False,
                                                                    "number_of_qubits": 26}))


class TestProjectQBackend(unittest.TestCase):

    def setUp(self):
        warnings.filterwarnings("ignore", category=PendingDeprecationWarning)

    def test_init_has_correct_values(self):
        api = MockApiClient()
        backend = QIBackend(quantum_inspire_api=api)
        self.assertIsInstance(backend.qasm, str)
        self.assertEqual(backend.quantum_inspire_api, api)
        self.assertIsNone(backend.backend_type)

    def test_init_without_api_has_correct_values(self):
        os.environ.get = MagicMock()
        os.environ.get.return_value = 'token'
        coreapi.Client.get = MagicMock()
        result = {"is_hardware_backend": False, "number_of_qubits": 26}
        coreapi.Client.action = MagicMock(return_value=result)
        backend = QIBackend()
        self.assertIsInstance(backend.qasm, str)
        self.assertNotEqual(backend.quantum_inspire_api, None)
        self.assertIsNone(backend.backend_type)
        self.assertTrue(backend.is_simulation_backend)

    def test_init_raises_error_no_runs(self):
        num_runs = 0
        self.assertRaisesRegex(ProjectQBackendError, 'Invalid number of runs \(num_runs=0\)',
                               QIBackend, num_runs)

    def test_init_raises_no_account_authentication_error(self):
        json.load = MagicMock()
        json.load.return_value = {'faulty_key': 'faulty_token'}
        os.environ.get = MagicMock()
        os.environ.get.return_value = None
        self.assertRaisesRegex(AuthenticationError, 'Make sure you have saved your token credentials on disk '
                                                    'or provide a QuantumInspireAPI instance as parameter to QIBackend',
                               QIBackend)

    def test_cqasm_returns_correct_cqasm_data(self):
        api = MockApiClient()
        backend = QIBackend(quantum_inspire_api=api)
        expected = 'fake_cqasm_data'
        backend._cqasm = expected
        actual = backend.cqasm()
        self.assertEqual(actual, expected)

    def test_is_available_verbose_prints_data(self):
        command = MagicMock()
        command.gate = CNOT
        api = MockApiClient()
        backend = QIBackend(quantum_inspire_api=api, verbose=3)
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            _ = backend.is_available(command)
            std_output = mock_stdout.getvalue()
        self.assertTrue(std_output.startswith('call to is_available with cmd'))

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
        self.__is_available_assert_equal(NOT, False, count=3)
        self.__is_available_assert_equal(CNOT, False, count=0)
        self.__is_available_assert_equal(Z, True, count=1)
        self.__is_available_assert_equal(Z, False, count=3)
        self.__is_available_assert_equal(Ph(0.4), False)
        self.__is_available_assert_equal(Toffoli, False)
        for gate in [Measure, Allocate, Deallocate, Barrier, T, Tdag,
                     S, Sdag, Swap, H, X, Y, Z, Rx(0.1), Ry(0.2), Rz(0.3)]:
            self.__is_available_assert_equal(gate, True)

    def test_reset_is_cleared(self):
        api = MockApiClient()
        backend = QIBackend(quantum_inspire_api=api)
        backend._clear = True
        backend._reset()
        self.assertTrue(backend._clear)

    @patch('quantuminspire.projectq.backend_qx.get_control_count')
    def __store_function_assert_equal(self, identity, gate, qasm, function_mock, count=0, verbose=0):
        api = MockApiClient()
        function_mock.return_value = count
        backend = QIBackend(quantum_inspire_api=api, verbose=verbose)
        command_alloc0 = MagicMock(gate=Allocate, qubits=[[MagicMock(id=identity - 1)]])
        command_alloc1 = MagicMock(gate=Allocate, qubits=[[MagicMock(id=identity)]])
        command_alloc2 = MagicMock(gate=Allocate, qubits=[[MagicMock(id=identity + 1)]])
        command = MagicMock(gate=gate, qubits=[[MagicMock(id=identity)], [MagicMock(id=identity + 1)]],
                            control_qubits=[MagicMock(id=identity - 1), MagicMock(id=identity)])
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
        self.__store_function_assert_equal(0, Swap, "\nswap q[0], q[1]")
        self.__store_function_assert_equal(1, X, "\ntoffoli q[0], q[1], q[1]", count=2)
        self.__store_function_assert_equal(1, Z, "\ncz q[0], q[1]", count=1)
        self.__store_function_assert_equal(0, Barrier, "\n# barrier gate q[0], q[1];")
        self.__store_function_assert_equal(1, Rz(angle), "\ncr q[0],q[1],{0:.12f}".format(angle), count=1)
        self.__store_function_assert_equal(1, Rz(angle), "\ncr q[0],q[1],{0:.12f}".format(angle), count=1)
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
        api = MockApiClient()
        function_mock.return_value = 4
        backend = QIBackend(quantum_inspire_api=api)
        mapper = MagicMock(current_mapping={mock_tag: 0})
        backend.main_engine = MagicMock(mapper=mapper)
        self.__store_function(backend, 0, Allocate)
        command = [MagicMock(gate=Measure, qubits=[[MagicMock(id=0)]],
                             tags=[LogicalQubitIDTag(mock_tag)])]
        backend.receive(command)
        self.__store_function(backend, 0, H)
        self.assertEqual(backend._measured_ids, [mock_tag])
        self.assertEqual(backend.qasm, "\nmeasure q[0]\nh q[0]")

    @patch('quantuminspire.projectq.backend_qx.get_control_count')
    def test_store_measure_gate_without_mapper(self, function_mock):
        mock_tag = 20
        api = MockApiClient()
        function_mock.return_value = 4
        backend = QIBackend(quantum_inspire_api=api)
        backend.main_engine = MagicMock(mapper=None)
        self.__store_function(backend, 0, Allocate)
        self.__store_function(backend, mock_tag, Allocate)
        command = [MagicMock(gate=Measure, qubits=[[MagicMock(id=mock_tag)]],
                             tags=[])]
        backend.receive(command)
        self.__store_function(backend, 0, H)
        self.assertEqual(backend.qasm, "\nmeasure q[20]\nh q[0]")
        self.assertEqual(backend._full_state_projection, False)

    def test_logical_to_physical_with_mapper_returns_correct_result(self):
        qd_id = 0
        expected = 1234
        api = MockApiClient()
        backend = QIBackend(quantum_inspire_api=api)
        backend.main_engine = MagicMock()
        backend.main_engine.mapper.current_mapping = [expected, qd_id]
        actual = backend._logical_to_physical(qd_id)
        self.assertEqual(actual, expected)

    def test_logical_to_physical_without_mapper_returns_correct_result(self):
        qd_id = 1234
        expected = qd_id
        api = MockApiClient()
        backend = QIBackend(quantum_inspire_api=api)
        backend.main_engine = MagicMock(mapper=None)
        actual = backend._logical_to_physical(qd_id)
        self.assertEqual(actual, expected)

    def test_logical_to_physical_raises_runtime_error(self):
        qd_id = 0
        expected = 1234
        api = MockApiClient()
        backend = QIBackend(quantum_inspire_api=api)
        backend.main_engine = MagicMock()
        backend.main_engine.mapper.current_mapping = [expected]
        self.assertRaises(RuntimeError, backend._logical_to_physical, qd_id)

    def test_get_probabilities_raises_runtime_error(self):
        api = MockApiClient()
        backend = QIBackend(quantum_inspire_api=api)
        backend.__probabilities = 0
        self.assertRaises(RuntimeError, backend.get_probabilities, None)

    def test_get_probabilities_returns_correct_result(self):
        api = MockApiClient()
        backend = QIBackend(quantum_inspire_api=api)
        value_a = 0.4892578125
        value_b = 0.5097656250
        backend._measured_states = {0: value_a, 11: value_b}  # 00000000 and 00001011
        expected = {'00': value_a, '11': value_b}
        backend.main_engine = MagicMock()
        backend._measured_ids = [0, 1]
        backend._allocation_map = [(0, 0), (1, 1)]
        backend.main_engine.mapper.current_mapping = [0, 1]
        actual = backend.get_probabilities([MagicMock(id=0), MagicMock(id=1)])
        self.assertDictEqual(expected, actual)

    def test_get_probabilities_reversed_measurement_order_returns_correct_result(self):
        api = MockApiClient()
        backend = QIBackend(quantum_inspire_api=api)
        value_a = 0.4892578125
        value_b = 0.5097656250
        backend._measured_states = {0: value_a, 11: value_b}  # 00000000 and 00001011
        expected = {'00': value_a, '10': value_b}
        backend.main_engine = MagicMock()
        backend._measured_ids = [1, 0]
        backend._allocation_map = [(0, 0), (1, 1), (2, 2)]
        backend.main_engine.mapper.current_mapping = [0, 1, 2, 3, 4, 5, 6, 7]
        actual = backend.get_probabilities([MagicMock(id=0), MagicMock(id=2)])
        self.assertDictEqual(expected, actual)

    @patch('quantuminspire.projectq.backend_qx.get_control_count')
    def test_receive(self, function_mock):
        function_mock.return_value = 1
        command_alloc0 = MagicMock(gate=Allocate, qubits=[[MagicMock(id=0)]])
        command_alloc1 = MagicMock(gate=Allocate, qubits=[[MagicMock(id=1)]])
        command = MagicMock(gate=NOT, qubits=[[MagicMock(id=0)]], control_qubits=[MagicMock(id=1)])
        command_list = [command_alloc0, command_alloc1, command, MagicMock(gate=FlushGate())]
        api = MockApiClient()
        backend = QIBackend(quantum_inspire_api=api)
        backend.main_engine = MagicMock()
        with patch('sys.stdout', new_callable=io.StringIO):
            backend.receive(command_list)
        self.assertEqual(backend.qasm, "")
        self.assertTrue(backend._clear)

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
        api = MockApiClient()
        backend = QIBackend(quantum_inspire_api=api)
        backend.main_engine = MagicMock()
        with patch('sys.stdout', new_callable=io.StringIO):
            backend.receive(command_list)
        self.assertEqual(backend.qasm, "")
        self.assertTrue(backend._clear)

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
        backend.main_engine = MagicMock()
        with patch('sys.stdout', new_callable=io.StringIO):
            backend.receive(command_list)
        self.assertEqual(backend.qasm, "")
        self.assertTrue(backend._clear)

    def test_maximum_qubit(self):
        command_alloc0 = MagicMock(gate=Allocate, qubits=[[MagicMock(id=0)]])
        command_alloc1 = MagicMock(gate=Allocate, qubits=[[MagicMock(id=1)]])
        command_alloc2 = MagicMock(gate=Allocate, qubits=[[MagicMock(id=2)]])
        command_dealloc0 = MagicMock(gate=Deallocate, qubits=[[MagicMock(id=0)]])
        command_dealloc1 = MagicMock(gate=Deallocate, qubits=[[MagicMock(id=1)]])
        command_dealloc2 = MagicMock(gate=Deallocate, qubits=[[MagicMock(id=2)]])
        command_list = [command_alloc1, command_alloc2, command_dealloc1,
                        command_alloc0, command_dealloc0, command_dealloc2]
        api = MockApiClient()
        backend = QIBackend(quantum_inspire_api=api)
        backend.main_engine = MagicMock()
        backend.receive(command_list)
        self.assertEqual(backend._number_of_qubits, 3)
        self.assertEqual(len(backend._allocation_map), 3)

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
        api = MockApiClient()
        backend = QIBackend(quantum_inspire_api=api)
        backend.main_engine = MagicMock()
        backend.max_number_of_qubits = 4
        backend.receive(command_list)
        self.assertEqual(backend._number_of_qubits, 4)
        self.assertEqual(len(backend._allocation_map), 4)

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
        api = MockApiClient()
        backend = QIBackend(quantum_inspire_api=api)
        backend.max_number_of_qubits = 5
        backend.main_engine = MagicMock()
        backend.receive(command_list)
        self.assertEqual(backend._number_of_qubits, 5)
        self.assertEqual(len(backend._allocation_map), 5)
        self.assertEqual(backend._allocation_map, [(0, 0), (1, 1), (3, 6), (2, 2), (4, -1)])

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
        api = MockApiClient()
        backend = QIBackend(quantum_inspire_api=api)
        backend.main_engine = MagicMock()
        backend.max_number_of_qubits = 8
        backend.receive(command_list)
        self.assertEqual(backend._number_of_qubits, 8)
        self.assertEqual(len(backend._allocation_map), 8)

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
        api = MockApiClient()
        backend = QIBackend(quantum_inspire_api=api)
        backend.main_engine = MagicMock()
        backend.max_number_of_qubits = 3
        backend.receive(command_list)
        self.assertEqual(backend._number_of_qubits, 4)
        self.assertEqual(len(backend._allocation_map), 4)

    def test_alloc_map_and_mapping(self):
        api = MockApiClient()
        backend = QIBackend(quantum_inspire_api=api)
        value_a = 0.4892578125
        value_b = 0.5097656250
        backend._measured_states = {0: value_a, 11: value_b}  # 00000000 and 00001011
        expected = {'00': value_a, '10': value_b}
        backend.main_engine = MagicMock()
        backend._measured_ids = [0, 1]  # bits 0 and 1 measured
        backend.main_engine.mapper.current_mapping = [0, 1]   # bits 0 and 1 are logical bits 0 and 1
        # logical bit 0 is mapped on bit 3, logical bit 1 is mapped on bit 2 in cqasm
        backend._allocation_map = [(0, 100), (1, 110), (2, 1), (3, 0), (4, 2), (5, 3)]
        # so we get a mask of 1100 (bit 3 and bit 2)
        # 0000 & 1100 = 0000, when we concatenate bit[3] and bit[2] we get 00
        # 1011 & 1100 = 1000, when we concatenate bit[3] and bit[2] we get 10
        # resulting is 00 for state 0000 and 10 for state 1011
        actual = backend.get_probabilities([MagicMock(id=0), MagicMock(id=1)])
        self.assertDictEqual(expected, actual)

    def test_alloc_map_and_mapping_with_2_bits_flipped_position_in_alloc_map(self):
        api = MockApiClient()
        backend = QIBackend(quantum_inspire_api=api)
        value_a = 0.4892578125
        value_b = 0.5097656250
        backend._measured_states = {0: value_a, 11: value_b}  # 00000000 and 00001011
        expected = {'00': value_a, '01': value_b}
        backend.main_engine = MagicMock()
        backend._measured_ids = [0, 1]  # bits 0 and 1 measured
        backend.main_engine.mapper.current_mapping = [0, 1]   # bits 0 and 1 are logical bits 0 and 1
        # logical bits 0 is mapped on bit 2, logical bit 1 is mapped on bit 3 in cqasm
        backend._allocation_map = [(0, 100), (1, 110), (2, 0), (3, 1), (4, 2), (5, 3)]
        # so we get a mask of 1100 (bit 2 and bit 3)
        # 0000 & 1100 = 0000, when we concatenate bit[2] and bit[3] we get 00
        # 1011 & 1100 = 1000, when we concatenate bit[2] and bit[3] we get 01
        # resulting is 00 for state 0000 and 01 for state 1011
        actual = backend.get_probabilities([MagicMock(id=0), MagicMock(id=1)])
        self.assertDictEqual(expected, actual)

    def test_alloc_map_with_alternative_mapping(self):
        api = MockApiClient()
        backend = QIBackend(quantum_inspire_api=api)
        value_a = 0.4892578125
        value_b = 0.5097656250
        backend._measured_states = {12: value_a, 59: value_b}  # 001100 and 111011
        expected = {'10': value_a, '11': value_b}
        backend.main_engine = MagicMock()
        backend._measured_ids = [0, 1]  # bits 0 and 1 measured
        backend.main_engine.mapper.current_mapping = [1, 4, 0]   # bits 0 and 1 are logical bits 1 and 4
        # logical bits 1 is mapped on bit 3, logical bit 4 is mapped on bit 5 in cqasm
        backend._allocation_map = [(0, 100), (1, 110), (2, 0), (3, 1), (4, 2), (5, 4)]
        # so we get a mask of 101000 (bit 3 and bit 5)
        # 001100 & 101000 = 001000, when we concatenate bit[3] and bit[5] we get 10
        # 111011 & 101000 = 101000, when we concatenate bit[3] and bit[5] we get 11
        # resulting is 10 for state 001100 and 11 for state 111011
        actual = backend.get_probabilities([MagicMock(id=0), MagicMock(id=1)])
        self.assertDictEqual(expected, actual)

    def test_reallocation_of_same_bits(self):
        command_alloc0 = MagicMock(gate=Allocate, qubits=[[MagicMock(id=0)]])
        command_alloc1 = MagicMock(gate=Allocate, qubits=[[MagicMock(id=1)]])
        command_alloc2 = MagicMock(gate=Allocate, qubits=[[MagicMock(id=2)]])
        command_dealloc1 = MagicMock(gate=Deallocate, qubits=[[MagicMock(id=1)]])
        command_dealloc2 = MagicMock(gate=Deallocate, qubits=[[MagicMock(id=2)]])

        command_list = [command_alloc0, command_alloc1, command_alloc2, command_dealloc2, command_dealloc1,
                        command_alloc2, command_alloc1]
        api = MockApiClient()
        backend = QIBackend(quantum_inspire_api=api)
        backend.main_engine = MagicMock()
        backend.receive(command_list)
        self.assertEqual(backend._number_of_qubits, 3)
        self.assertEqual(len(backend._allocation_map), 3)
        self.assertEqual(backend._allocation_map, [(0, 0), (1, 1), (2, 2)])

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
        api = MockApiClient()
        api.get_backend_type = MagicMock(return_value=OrderedDict({"is_hardware_backend": True,
                                                                   "number_of_qubits": 26}))
        backend = QIBackend(quantum_inspire_api=api)
        backend.main_engine = MagicMock()
        backend.receive(command_list)
        self.assertEqual(backend.qasm, "\nh q[0]")
        self.assertEqual(backend._number_of_qubits, 3)
        self.assertEqual(len(backend._allocation_map), 0)

    @patch('quantuminspire.projectq.backend_qx.get_control_count')
    def test_store_allocation_of_bit_larger_than_capacity_backend(self, function_mock):
        api = MockApiClient()
        function_mock.return_value = 4
        backend = QIBackend(quantum_inspire_api=api)
        bit_above_max = backend.max_number_of_qubits  # 0..max_number_of_qubits - 1 are valid
        backend.main_engine = MagicMock(mapper=None)
        self.__store_function(backend, 0, Allocate)
        self.__store_function(backend, bit_above_max, Allocate)
        command = [MagicMock(gate=Measure, qubits=[[MagicMock(id=bit_above_max)]],
                             tags=[])]
        backend.receive(command)
        self.__store_function(backend, 0, H)
        self.assertEqual(backend.qasm, "\nmeasure q[1]\nh q[0]")
        self.assertEqual(backend._full_state_projection, False)

    def test_run_no_qasm(self):
        api = MockApiClient()
        backend = QIBackend(quantum_inspire_api=api)
        backend._run()
        self.assertEqual(backend.qasm, "")

    def test_run_has_correct_output(self):
        api = MockApiClient()
        with patch('sys.stdout', new_callable=io.StringIO) as std_mock:
            backend = QIBackend(quantum_inspire_api=api, verbose=2)
            backend.qasm = "_"
            backend._measured_ids = [0]
            backend._allocation_map = [(0, 0), (1, 1)]
            backend.main_engine = MagicMock()
            backend.main_engine.mapper.current_mapping = [0, 1]
            backend._run()
            std_output = std_mock.getvalue()
            actual = backend._quantum_inspire_result
        api.execute_qasm.assert_called_once()
        self.assertEqual(api.execute_qasm(), actual)
        self.assertTrue(backend._clear)
        self.assertTrue(std_output.startswith('version 1.0\n# cQASM generated by Quantum Inspire'))
        self.assertTrue('qubits 0' in std_output)

    def test_run_raises_error_no_result(self):
        api = MockApiClient()
        with patch('sys.stdout', new_callable=io.StringIO):
            backend = QIBackend(quantum_inspire_api=api, verbose=2)
            backend.qasm = "_"
            backend._measured_ids = [0, 1]
            backend._allocation_map = [(0, 0), (1, 1)]
            backend.main_engine = MagicMock()
            backend.main_engine.mapper.current_mapping = [0, 1]
            result_mock = MagicMock()
            result_mock.get.return_value = {}
            api.execute_qasm.return_value = result_mock
            self.assertRaisesRegex(ProjectQBackendError, 'raw_text', backend._run)
        api.execute_qasm.assert_called_once()

    @patch('quantuminspire.projectq.backend_qx.Measure')
    def test_run_no_measurements(self, measure_mock):
        api = MockApiClient()
        with patch('sys.stdout', new_callable=io.StringIO):
            backend = QIBackend(quantum_inspire_api=api, verbose=2)
            backend.qasm = "_"
            backend._measured_ids = []
            backend._allocation_map = [(0, 0), (1, 1)]
            backend.main_engine = MagicMock()
            backend.main_engine.active_qubits = [0, 1]
            backend.main_engine.mapper.current_mapping = [0, 1]
            result_mock = MagicMock()
            result_mock.get.return_value = {}
            api.execute_qasm.return_value = result_mock
            self.assertRaisesRegex(ProjectQBackendError, 'raw_text', backend._run)
        api.execute_qasm.assert_called_once()
