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
import random
import unittest
import warnings
from collections import OrderedDict
from unittest.mock import MagicMock, patch

from projectq.meta import LogicalQubitIDTag, get_control_count
from projectq.ops import (CNOT, CX, CZ, NOT, QFT, All, Allocate, Barrier,
                          BasicPhaseGate, C, Deallocate, FlushGate, H, Measure,
                          Ph, Rx, Ry, Rz, S, Sdag, Swap, T, Tdag, Toffoli, X,
                          Y, Z)

from quantuminspire.exceptions import ProjectQBackendError
from quantuminspire.projectq.backend_qx import QIBackend


class MockApiClient:

    def __init__(self):
        result = {'histogram': {'00': 0.49, '11': 0.51}, 'results': 'dummy'}
        self.execute_qasm = MagicMock(return_value=result)
        self.get_backend_type = MagicMock(return_value=OrderedDict())


class TestProjectQBackend(unittest.TestCase):

    def setUp(self):
        warnings.filterwarnings("ignore", category=PendingDeprecationWarning)

    def test_init_HasCorrectValues(self):
        api = MockApiClient()
        backend = QIBackend(quantum_inspire_api=api)
        self.assertIsInstance(backend.qasm, str)
        self.assertEqual(backend.quantum_inspire_api, api)
        self.assertIsNone(backend.backend_type)

    def test_cqasm_ReturnsCorrectCqasmData(self):
        api = MockApiClient()
        backend = QIBackend(quantum_inspire_api=api)
        expected = 'fake_cqasm_data'
        backend._cqasm = expected
        actual = backend.cqasm()
        self.assertEqual(actual, expected)

    def test_is_available_VerbosePrintsData(self):
        command = MagicMock()
        command.gate = CNOT
        api = MockApiClient()
        backend = QIBackend(quantum_inspire_api=api, verbose=1)
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            is_available = backend.is_available(command)
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

    def test_is_available_CorrectResult(self):
        self.__is_available_assert_equal(NOT, True, count=1)
        self.__is_available_assert_equal(NOT, False, count=3)
        self.__is_available_assert_equal(Z, True, count=1)
        self.__is_available_assert_equal(Z, False, count=3)
        self.__is_available_assert_equal(Ph(0.4), False)
        self.__is_available_assert_equal(Toffoli, False)
        for gate in [Measure, Allocate, Deallocate, Barrier, T, Tdag,
                     S, Sdag, H, X, Y, Z, Rx(0.1), Ry(0.2), Rz(0.3)]:
            self.__is_available_assert_equal(gate, True)

    def test_reset_isCleared(self):
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
        command = MagicMock(gate=gate, qubits=[[MagicMock(id=identity)], [MagicMock(id=identity+1)]],
                            control_qubits=[MagicMock(id=identity-1), MagicMock(id=identity)])
        backend._store(command)
        self.assertEqual(backend.qasm, qasm)

    @patch('quantuminspire.projectq.backend_qx.get_control_count')
    def __store_function_raises_error(self, gate, function_mock, count=0):
        identity = 1
        api = MockApiClient()
        function_mock.return_value = count
        backend = QIBackend(quantum_inspire_api=api)
        command = MagicMock(gate=gate, qubits=[[MagicMock(id=identity)], [MagicMock(id=identity+1)]],
                            control_qubits=[MagicMock(id=identity-1), MagicMock(id=identity)])
        self.assertRaises(NotImplementedError, backend._store, command)

    def test_store_ReturnsCorrectQasm(self):
        angle = 0.1
        self.__store_function_assert_equal(0, NOT, "\nx q[0]")
        self.__store_function_assert_equal(1, NOT, "\nCNOT q[0], q[1]", count=1)
        self.__store_function_assert_equal(0, Swap, "\nswap q[0], q[1]")
        self.__store_function_assert_equal(1, X, "\nToffoli q[0], q[1], q[1]", count=2)
        self.__store_function_assert_equal(1, Z, "\nCZ q[0], q[1]", count=1)
        self.__store_function_assert_equal(0, Barrier, "\n# barrier gate q[0], q[1];")
        self.__store_function_assert_equal(1, Rz(angle), "\nCR q[0],q[1],{0:.12f}".format(angle), count=1)
        self.__store_function_assert_equal(1, Rz(angle), "\nCR q[0],q[1],{0:.12f}".format(angle), count=1)
        self.__store_function_assert_equal(1, Rx(angle), "\nRx q[1],{0}".format(angle))
        self.__store_function_assert_equal(1, Ry(angle), "\nRy q[1],{0}".format(angle))
        self.__store_function_assert_equal(1, Rz(angle), "\nRz q[1],{0}".format(angle))
        self.__store_function_assert_equal(0, Tdag, "\nTdag q[0]")
        self.__store_function_assert_equal(0, X, "\nx q[0]")
        self.__store_function_assert_equal(0, Y, "\ny q[0]")
        self.__store_function_assert_equal(0, Z, "\nz q[0]")
        self.__store_function_assert_equal(0, H, "\nh q[0]")
        self.__store_function_assert_equal(0, S, "\ns q[0]")
        self.__store_function_assert_equal(0, Sdag, "\nSdag q[0]")
        self.__store_function_assert_equal(0, T, "\nt q[0]")
        self.__store_function_assert_equal(0, Tdag, "\nTdag q[0]")

    def test_store_RaisesError(self):
        angle = 0.1
        self.__store_function_raises_error(Toffoli, count=0)
        self.__store_function_raises_error(Rx(angle), count=1)
        self.__store_function_raises_error(Ry(angle), count=1)

    def test_store_AllocateVerboseOutput(self):
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            self.__store_function_assert_equal(0, Allocate, "", verbose=2)
            std_output = mock_stdout.getvalue()
        self.assertTrue('   _allocated_qubits' in std_output)
        self.assertTrue('_store: Allocate gate' in std_output)

    def test_store_DeallocateVerboseOutput(self):
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            self.__store_function_assert_equal(0, Deallocate, "", verbose=2)
            std_output = mock_stdout.getvalue()
        self.assertTrue('   _allocated_qubits' in std_output)
        self.assertTrue('_store: Deallocate gate' in std_output)

    @patch('quantuminspire.projectq.backend_qx.get_control_count')
    def test_store_MeasureGate(self, function_mock):
        mock_tag = 'mock_my_tag'
        api = MockApiClient()
        function_mock.return_value = 4
        backend = QIBackend(quantum_inspire_api=api)
        command = MagicMock(gate=Measure, qubits=[[MagicMock(id=0)]],
                            control_qubits=[MagicMock(id=2), MagicMock(id=3)],
                            tags=[LogicalQubitIDTag(mock_tag)])
        backend._store(command)
        self.assertEqual(backend._measured_ids, [mock_tag])

    def test_logical_to_physical_ReturnsCorrectResult(self):
        qd_id = 0
        expected = 1234
        api = MockApiClient()
        backend = QIBackend(quantum_inspire_api=api)
        backend.main_engine = MagicMock()
        backend.main_engine.mapper.current_mapping = [expected, qd_id]
        actual = backend._logical_to_physical(qd_id)
        self.assertEqual(actual, expected)

    def test_logical_to_physical_ReturnsCorrectResult(self):
        qd_id = 0
        expected = 1234
        api = MockApiClient()
        backend = QIBackend(quantum_inspire_api=api)
        backend.main_engine = MagicMock()
        backend.main_engine.mapper.current_mapping = [expected]
        self.assertRaises(RuntimeError, backend._logical_to_physical, qd_id)

    def test_get_probabilities_RaisesRuntimeError(self):
        api = MockApiClient()
        backend = QIBackend(quantum_inspire_api=api)
        backend.__probabilities = 0
        self.assertRaises(RuntimeError, backend.get_probabilities, None)

    def test_get_probabilities_ReturnsCorrectResult(self):
        api = MockApiClient()
        backend = QIBackend(quantum_inspire_api=api)
        value_a = 0.4892578125
        value_b = 0.5097656250
        backend._probabilities = {'00000000': value_a, '11010000': value_b}
        expected = {'00': value_a, '11': value_b}
        backend.main_engine = MagicMock()
        backend._measured_ids = [0, 1]
        backend.main_engine.mapper.current_mapping = [0, 1]
        actual = backend.get_probabilities([MagicMock(id=0), MagicMock(id=1)])
        self.assertDictEqual(expected, actual)

    def test_calculate_probabilities(self):
        counts = {'00': 10, '01': 20, '10': 30, '11': 40}
        api = MockApiClient()
        backend = QIBackend(quantum_inspire_api=api, verbose=True)
        with patch.object(random, 'random', return_value=1e-5), patch(
         'sys.stdout', new_callable=io.StringIO) as mock_stdout:
            actual = backend._calculate_probabilities(counts)
            std_output = mock_stdout.getvalue()
        self.assertEqual(actual, '00')
        self.assertTrue('*' in std_output)

    @patch('quantuminspire.projectq.backend_qx.get_control_count')
    def test_receive(self, function_mock):
        function_mock.return_value = 1
        command = MagicMock(gate=NOT, qubits=[[MagicMock(id=0)], [MagicMock(id=1)]])
        command_list = [command, MagicMock(gate=FlushGate())]
        api = MockApiClient()
        backend = QIBackend(quantum_inspire_api=api)
        backend.main_engine = MagicMock()
        with patch('sys.stdout', new_callable=io.StringIO):
            backend.receive(command_list)
        self.assertEqual(backend.qasm, "")
        self.assertTrue(backend._clear)

    def test_run_NoQasm(self):
        api = MockApiClient()
        backend = QIBackend(quantum_inspire_api=api)
        backend._run()
        self.assertEqual(backend.qasm, "")

    def test_run_HasCorrectOutput(self):
        api = MockApiClient()
        with patch('sys.stdout', new_callable=io.StringIO) as std_mock:
            backend = QIBackend(quantum_inspire_api=api, verbose=2)
            backend.qasm = "_"
            backend._measured_ids = [0]
            backend.main_engine = MagicMock()
            backend.main_engine.mapper.current_mapping = [0, 1]
            backend._run()
            std_output = std_mock.getvalue()
            actual = backend._quantum_inspire_result
        api.execute_qasm.assert_called_once()
        self.assertTrue('QIBackend: measured' in std_output)
        self.assertEqual(api.execute_qasm(), actual)
        self.assertTrue(backend._clear)

    def test_run_DontPerformExecution(self):
        api = MockApiClient()
        with patch('sys.stdout', new_callable=io.StringIO):
            backend = QIBackend(quantum_inspire_api=api, perform_execution=False,
                                verbose=2)
            backend.qasm = "_"
            backend._measured_ids = [0, 1]
            backend.main_engine = MagicMock()
            backend.main_engine.mapper.current_mapping = [0, 1]
            backend._run()
        api.execute_qasm.assert_not_called()
        self.assertIsNone(backend._quantum_inspire_result)

    def test_run_RaisesErrorRunCirCuit(self):
        api = MockApiClient()
        with patch('sys.stdout', new_callable=io.StringIO):
            backend = QIBackend(quantum_inspire_api=api, verbose=2)
            backend.qasm = "_"
            backend._measured_ids = [0, 1]
            backend.main_engine = MagicMock()
            backend.main_engine.mapper.current_mapping = [0, 1]
            api.execute_qasm.return_value = MagicMock(get=[])
            self.assertRaisesRegex(ProjectQBackendError, 'Aborting', backend._run)
        api.execute_qasm.assert_called_once()

    def test_run_RaisesErrorNoResult(self):
        api = MockApiClient()
        with patch('sys.stdout', new_callable=io.StringIO):
            backend = QIBackend(quantum_inspire_api=api, verbose=2)
            backend.qasm = "_"
            backend._measured_ids = [0, 1]
            backend.main_engine = MagicMock()
            backend.main_engine.mapper.current_mapping = [0, 1]
            result_mock = MagicMock()
            result_mock.get.return_value = {}
            api.execute_qasm.return_value = result_mock
            self.assertRaisesRegex(ProjectQBackendError, 'raw_text', backend._run)
        api.execute_qasm.assert_called_once()


    @patch('quantuminspire.projectq.backend_qx.Measure')
    def test_run_NoMeasurements(self, measure_mock):
        api = MockApiClient()
        with patch('sys.stdout', new_callable=io.StringIO):
            backend = QIBackend(quantum_inspire_api=api, verbose=2)
            backend.qasm = "_"
            backend._measured_ids = []
            backend.main_engine = MagicMock()
            backend.main_engine.active_qubits = [0, 1]
            backend.main_engine.mapper.current_mapping = [0, 1]
            result_mock = MagicMock()
            result_mock.get.return_value = {}
            api.execute_qasm.return_value = result_mock
            self.assertRaisesRegex(ProjectQBackendError, 'raw_text', backend._run)
        api.execute_qasm.assert_called_once()
