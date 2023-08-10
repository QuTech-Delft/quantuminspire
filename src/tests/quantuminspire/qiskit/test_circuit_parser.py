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
import copy
import unittest
from unittest.mock import Mock

import numpy as np
import qiskit
from qiskit import QuantumRegister, ClassicalRegister, QuantumCircuit
from qiskit.compiler import assemble, transpile
from qiskit.circuit import Instruction
from quantuminspire.qiskit.circuit_parser import CircuitToString
from quantuminspire.qiskit.backend_qx import QuantumInspireBackend
from quantuminspire.qiskit.measurements import Measurements
from quantuminspire.exceptions import ApiError


class TestQiCircuitToString(unittest.TestCase):

    @staticmethod
    def _generate_cqasm_from_circuit(circuit, full_state_projection=True, transpile_first=False):
        run_config_dict = {'shots': 25, 'memory': True}
        configuration = copy.copy(QuantumInspireBackend.DEFAULT_CONFIGURATION)
        if transpile_first:
            configuration.simulator = False
            configuration.coupling_map = [[0, 1], [0, 2], [1, 3], [2, 3]]
        backend = QuantumInspireBackend(Mock(), Mock(), configuration)
        if transpile_first:
            circuit = transpile(circuit, backend=backend)
        qobj = assemble(circuit, backend, **run_config_dict)
        experiment = qobj.experiments[0]
        measurements = Measurements.from_experiment(experiment)
        # simulator = QuantumInspireBackend(Mock(), Mock())
        result = backend._generate_cqasm(experiment, measurements, full_state_projection)
        return result

    @staticmethod
    def _generate_cqasm_from_instructions(instructions, number_of_qubits=2, full_state_projection=True):
        """ Needed to create invalid qiskit circuits for triggering Exceptions """
        experiment_dict = {'instructions': instructions,
                           'header': {'n_qubits': number_of_qubits,
                                      'memory_slots': number_of_qubits,
                                      'compiled_circuit_qasm': ''},
                           'config': {'coupling_map': 'all-to-all',
                                      'basis_gates': 'x,y,z,h,rx,ry,rz,s,cx,ccx,p,id,snapshot',
                                      'n_qubits': number_of_qubits}}
        experiment = qiskit.qobj.QasmQobjExperiment.from_dict(experiment_dict)
        for instruction in experiment.instructions:
            if hasattr(instruction, 'params'):
                # convert params to params used in qiskit instructions
                qiskit_instruction = Instruction('dummy', 0, 0, instruction.params)
                instruction.params = qiskit_instruction.params

        measurements = Measurements.from_experiment(experiment)
        simulator = QuantumInspireBackend(Mock(), Mock())
        result = simulator._generate_cqasm(experiment, measurements, full_state_projection)
        return result

    def test_generate_cqasm_with_entangle_algorithm(self):
        q = QuantumRegister(2)
        b = ClassicalRegister(2)
        circuit = QuantumCircuit(q, b)

        circuit.h(q[0])
        circuit.cx(q[0], q[1])
        circuit.measure(q[0], b[0])
        circuit.measure(q[1], b[1])

        result = self._generate_cqasm_from_circuit(circuit)

        expected = "version 1.0\n" \
                   "# cQASM generated by QI backend for Qiskit\n" \
                   "qubits 2\n" \
                   "H q[0]\n" \
                   "CNOT q[0], q[1]\n"
        self.assertEqual(result, expected)

    def test_generate_cqasm_correct_output_controlled_z(self):
        qc = QuantumCircuit(2, 2)
        qc.cz(0, 1)
        result = self._generate_cqasm_from_circuit(qc)
        self.assertTrue('CZ q[0], q[1]\n' in result)

    def test_generate_cqasm_correct_output_conditional_controlled_z(self):
        q = QuantumRegister(4, "q")
        c = ClassicalRegister(4, "c")
        qc = QuantumCircuit(q, c, name="test")
        qc.cz(0, 1).c_if(c, 14)
        result = self._generate_cqasm_from_circuit(qc)
        self.assertTrue('not b[0]\nC-CZ b[0,1,2,3], q[0], q[1]\nnot b[0]\n' in result)

    def test_generate_cqasm_correct_output_controlled_not(self):
        qc = QuantumCircuit(2, 2)
        qc.cx(0, 1)
        result = self._generate_cqasm_from_circuit(qc)
        self.assertTrue('CNOT q[0], q[1]\n' in result)

    def test_generate_cqasm_correct_output_conditional_controlled_not(self):
        q = QuantumRegister(4, "q")
        c = ClassicalRegister(4, "c")
        qc = QuantumCircuit(q, c, name="test")
        qc.cx(0, 1).c_if(c, 14)
        result = self._generate_cqasm_from_circuit(qc)
        self.assertTrue('not b[0]\nC-CNOT b[0,1,2,3], q[0], q[1]\nnot b[0]\n' in result)

    def test_generate_cqasm_correct_output_toffoli(self):
        qc = QuantumCircuit(3, 3)
        qc.ccx(0, 1, 2)
        result = self._generate_cqasm_from_circuit(qc)
        self.assertTrue('Toffoli q[0], q[1], q[2]\n' in result)

    def test_generate_cqasm_correct_output_conditional_toffoli(self):
        q = QuantumRegister(8, "q")
        c = ClassicalRegister(8, "c")
        qc = QuantumCircuit(q, c, name="test")
        qc.ccx(0, 1, 2).c_if(c, 14)
        result = self._generate_cqasm_from_circuit(qc)
        self.assertTrue('not b[0,4,5,6,7]\nC-Toffoli b[0,1,2,3,4,5,6,7], q[0], q[1], q[2]\nnot b[0,4,5,6,7]\n' in result)

    def test_generate_cqasm_correct_output_measure(self):
        qc = QuantumCircuit(2, 2)
        qc.measure(0, 0)
        result = self._generate_cqasm_from_circuit(qc)
        measure_line = 'measure q[0]\n'
        self.assertTrue(measure_line not in result)

    def test_generate_cqasm_correct_output_measure_q0_non_fsp(self):
        qc = QuantumCircuit(2, 2)
        qc.measure(0, 0)
        result = self._generate_cqasm_from_circuit(qc, False)
        measure_line = 'measure q[0]\n'
        self.assertTrue(measure_line in result)

    def test_generate_cqasm_correct_output_measure_q1_non_fsp(self):
        qc = QuantumCircuit(2, 2)
        qc.measure(1, 0)
        result = self._generate_cqasm_from_circuit(qc, False)
        measure_line = 'measure q[1]\n'
        self.assertTrue(measure_line in result)

    def test_generate_cqasm_correct_output_hadamard(self):
        qc = QuantumCircuit(2, 2)
        qc.h(0)
        result = self._generate_cqasm_from_circuit(qc)
        self.assertTrue('H q[0]\n' in result)

    def test_generate_cqasm_correct_output_conditional_hadamard(self):
        q = QuantumRegister(8, "q")
        c = ClassicalRegister(8, "c")
        qc = QuantumCircuit(q, c, name="test")
        qc.h(0).c_if(c, 14)
        result = self._generate_cqasm_from_circuit(qc)
        self.assertTrue('not b[0,4,5,6,7]\nC-H b[0,1,2,3,4,5,6,7], q[0]\nnot b[0,4,5,6,7]\n' in result)

    def test_generate_cqasm_correct_output_barrier(self):
        qc = QuantumCircuit(2, 2)
        qc.barrier(0)
        result = self._generate_cqasm_from_circuit(qc)
        self.assertTrue('barrier q[0]\n' in result)

    def test_generate_cqasm_correct_output_barrier_multiple_qubits(self):
        q1 = QuantumRegister(2, "q1")
        q2 = QuantumRegister(4, "q2")
        c1 = ClassicalRegister(2, "c1")
        c2 = ClassicalRegister(4, "c2")
        qc = QuantumCircuit(q1, q2, c1, c2, name="test")

        qc.barrier(q1)
        result = self._generate_cqasm_from_circuit(qc)
        self.assertTrue('barrier q[0,1]\n' in result)

        qc.barrier(q2)
        result = self._generate_cqasm_from_circuit(qc)
        self.assertTrue('barrier q[2,3,4,5]\n' in result)

    def test_generate_cqasm_correct_output_barrier_all_qubits(self):
        q1 = QuantumRegister(2, "q1")
        q2 = QuantumRegister(4, "q2")
        c1 = ClassicalRegister(2, "c1")
        c2 = ClassicalRegister(4, "c2")
        qc = QuantumCircuit(q1, q2, c1, c2, name="test")

        qc.barrier()
        result = self._generate_cqasm_from_circuit(qc)
        self.assertTrue('barrier q[0,1,2,3,4,5]\n' in result)

    def test_generate_cqasm_correct_output_delay_all_qubits(self):
        q1 = QuantumRegister(1, "q1")
        q2 = QuantumRegister(2, "q2")
        c1 = ClassicalRegister(1, "c1")
        c2 = ClassicalRegister(2, "c2")
        qc = QuantumCircuit(q1, q2, c1, c2, name="test")

        qc.delay(1.0)
        result = self._generate_cqasm_from_circuit(qc)
        self.assertTrue('wait q[0], 1\n' in result)
        self.assertTrue('wait q[1], 1\n' in result)
        self.assertTrue('wait q[2], 1\n' in result)

    def test_generate_cqasm_correct_output_delay_qarg(self):
        q1 = QuantumRegister(1, "q1")
        q2 = QuantumRegister(2, "q2")
        c1 = ClassicalRegister(1, "c1")
        c2 = ClassicalRegister(2, "c2")
        qc = QuantumCircuit(q1, q2, c1, c2, name="test")

        qc.delay(1, q2)
        result = self._generate_cqasm_from_circuit(qc)
        self.assertTrue('wait q[1], 1\n' in result)
        self.assertTrue('wait q[2], 1\n' in result)

        # float is translated to int
        qc.delay(2.0, q1)
        result = self._generate_cqasm_from_circuit(qc)
        self.assertTrue('wait q[0], 2\n' in result)

    def test_generate_cqasm_correct_output_delay_units_in_dt(self):
        q1 = QuantumRegister(2, "q1")
        q2 = QuantumRegister(2, "q2")
        c1 = ClassicalRegister(2, "c1")
        c2 = ClassicalRegister(2, "c2")
        qc = QuantumCircuit(q1, q2, c1, c2, name="test")

        qc.delay(1.0, q1, unit="dt")
        result = self._generate_cqasm_from_circuit(qc)
        self.assertTrue('wait q[0], 1\n' in result)
        self.assertTrue('wait q[1], 1\n' in result)

        qc.delay(2, q1, unit="dt")
        result = self._generate_cqasm_from_circuit(qc)
        self.assertTrue('wait q[0], 2\n' in result)
        self.assertTrue('wait q[1], 2\n' in result)

    def test_generate_cqasm_correct_output_delay_units_in_s(self):
        # we need to transpile first to let the circuit convert the delay to seconds
        q1 = QuantumRegister(2, "q1")
        q2 = QuantumRegister(2, "q2")
        c1 = ClassicalRegister(2, "c1")
        c2 = ClassicalRegister(2, "c2")
        qc = QuantumCircuit(q1, q2, c1, c2, name="test")

        # waits are only valid on hardware backends, qiskit transpiler expects hw backend
        qc.delay(1.1, q1, "ms")
        result = self._generate_cqasm_from_circuit(qc, full_state_projection=False, transpile_first=True)
        self.assertTrue('wait q[0], 0\n' in result)
        self.assertTrue('wait q[1], 0\n' in result)

        qc.delay(0.9, q2, "ns")
        result = self._generate_cqasm_from_circuit(qc, full_state_projection=False, transpile_first=True)
        self.assertTrue('wait q[2], 0\n' in result)
        self.assertTrue('wait q[3], 0\n' in result)

        qc.delay(1.0, unit="s")
        result = self._generate_cqasm_from_circuit(qc, full_state_projection=False, transpile_first=True)
        self.assertTrue('wait q[0], 1\n' in result)
        self.assertTrue('wait q[1], 1\n' in result)
        self.assertTrue('wait q[2], 1\n' in result)
        self.assertTrue('wait q[3], 1\n' in result)

    def test_generate_cqasm_correct_output_identity(self):
        qc = QuantumCircuit(2, 2)
        qc.i(0)
        result = self._generate_cqasm_from_circuit(qc)
        self.assertTrue('I q[0]\n' in result)

        qc = QuantumCircuit(2, 2)
        qc.id(0)
        result = self._generate_cqasm_from_circuit(qc)
        self.assertTrue('I q[0]\n' in result)

    def test_generate_cqasm_correct_output_conditional_identity(self):
        q = QuantumRegister(8, "q")
        c = ClassicalRegister(8, "c")
        qc = QuantumCircuit(q, c, name="test")
        qc.i(0).c_if(c, 14)
        result = self._generate_cqasm_from_circuit(qc)
        self.assertTrue('not b[0,4,5,6,7]\nC-I b[0,1,2,3,4,5,6,7], q[0]\nnot b[0,4,5,6,7]\n' in result)

        q = QuantumRegister(8, "q")
        c = ClassicalRegister(8, "c")
        qc = QuantumCircuit(q, c, name="test")
        qc.id(0).c_if(c, 14)
        result = self._generate_cqasm_from_circuit(qc)
        self.assertTrue('not b[0,4,5,6,7]\nC-I b[0,1,2,3,4,5,6,7], q[0]\nnot b[0,4,5,6,7]\n' in result)

    def test_generate_cqasm_correct_output_gate_s(self):
        qc = QuantumCircuit(2, 2)
        qc.s(1)
        result = self._generate_cqasm_from_circuit(qc)
        self.assertTrue('S q[1]\n' in result)

    def test_generate_cqasm_correct_output_conditional_gate_s(self):
        q = QuantumRegister(9, "q")
        c = ClassicalRegister(9, "c")
        qc = QuantumCircuit(q, c, name="test")
        qc.s(2).c_if(c, 11)
        result = self._generate_cqasm_from_circuit(qc)
        self.assertTrue('not b[2,4,5,6,7,8]\nC-S b[0,1,2,3,4,5,6,7,8], q[2]\nnot b[2,4,5,6,7,8]\n' in result)

    def test_generate_cqasm_correct_output_gate_sdag(self):
        qc = QuantumCircuit(3, 3)
        qc.sdg(2)
        result = self._generate_cqasm_from_circuit(qc)
        self.assertTrue('Sdag q[2]\n' in result)

    def test_generate_cqasm_correct_output_conditional_gate_sdag(self):
        q = QuantumRegister(4, "q")
        c = ClassicalRegister(4, "c")
        qc = QuantumCircuit(q, c, name="test")
        qc.sdg(0).c_if(c, 14)
        result = self._generate_cqasm_from_circuit(qc)
        self.assertTrue('not b[0]\nC-Sdag b[0,1,2,3], q[0]\nnot b[0]\n' in result)

    def test_generate_cqasm_correct_output_gate_swap(self):
        qc = QuantumCircuit(4, 4)
        qc.swap(2, 3)
        result = self._generate_cqasm_from_circuit(qc)
        self.assertTrue('SWAP q[2], q[3]\n' in result)

    def test_generate_cqasm_correct_output_conditional_gate_swap(self):
        q = QuantumRegister(4, "q")
        c = ClassicalRegister(4, "c")
        qc = QuantumCircuit(q, c, name="test")
        qc.swap(0, 1).c_if(c, 14)
        result = self._generate_cqasm_from_circuit(qc)
        self.assertTrue('not b[0]\nC-SWAP b[0,1,2,3], q[0], q[1]\nnot b[0]\n' in result)

    def test_generate_cqasm_correct_output_gate_t(self):
        qc = QuantumCircuit(3, 3)
        qc.t(2)
        result = self._generate_cqasm_from_circuit(qc)
        self.assertTrue('T q[2]\n' in result)

    def test_generate_cqasm_correct_output_conditional_gate_t(self):
        q = QuantumRegister(9, "q")
        c = ClassicalRegister(9, "c")
        qc = QuantumCircuit(q, c, name="test")
        qc.t(1).c_if(c, 11)
        result = self._generate_cqasm_from_circuit(qc)
        self.assertTrue('not b[2,4,5,6,7,8]\nC-T b[0,1,2,3,4,5,6,7,8], q[1]\nnot b[2,4,5,6,7,8]\n' in result)

    def test_generate_cqasm_correct_output_gate_tdag(self):
        qc = QuantumCircuit(3, 3)
        qc.tdg(2)
        result = self._generate_cqasm_from_circuit(qc)
        self.assertTrue('Tdag q[2]\n' in result)

    def test_generate_cqasm_correct_output_conditional_gate_tdag(self):
        q = QuantumRegister(4, "q")
        c = ClassicalRegister(4, "c")
        qc = QuantumCircuit(q, c, name="test")
        qc.tdg(0).c_if(c, 14)
        result = self._generate_cqasm_from_circuit(qc)
        self.assertTrue('not b[0]\nC-Tdag b[0,1,2,3], q[0]\nnot b[0]\n' in result)

    def test_generate_cqasm_correct_output_gate_x(self):
        qc = QuantumCircuit(2, 2)
        qc.x(0)
        result = self._generate_cqasm_from_circuit(qc)
        self.assertTrue('X q[0]\n' in result)

    def test_generate_cqasm_correct_output_conditional_gate_x(self):
        q = QuantumRegister(4, "q")
        c = ClassicalRegister(4, "c")
        qc = QuantumCircuit(q, c, name="test")
        qc.x(0).c_if(c, 14)
        result = self._generate_cqasm_from_circuit(qc)
        self.assertTrue('not b[0]\nC-X b[0,1,2,3], q[0]\nnot b[0]\n' in result)

    def test_generate_cqasm_correct_output_gate_y(self):
        qc = QuantumCircuit(2, 2)
        qc.y(0)
        result = self._generate_cqasm_from_circuit(qc)
        self.assertTrue('Y q[0]\n' in result)

    def test_generate_cqasm_correct_output_conditional_gate_y(self):
        q = QuantumRegister(4, "q")
        c = ClassicalRegister(4, "c")
        qc = QuantumCircuit(q, c, name="test")
        qc.y(0).c_if(c, 1)
        result = self._generate_cqasm_from_circuit(qc)
        self.assertTrue('not b[1,2,3]\nC-Y b[0,1,2,3], q[0]\nnot b[1,2,3]\n' in result)

    def test_generate_cqasm_correct_output_gate_z(self):
        qc = QuantumCircuit(2, 2)
        qc.z(0)
        result = self._generate_cqasm_from_circuit(qc)
        self.assertTrue('Z q[0]\n' in result)

    def test_generate_cqasm_correct_output_conditional_gate_z(self):
        q = QuantumRegister(4, "q")
        c = ClassicalRegister(4, "c")
        qc = QuantumCircuit(q, c, name="test")
        qc.z(0).c_if(c, 3)
        result = self._generate_cqasm_from_circuit(qc)
        self.assertTrue('not b[2,3]\nC-Z b[0,1,2,3], q[0]\nnot b[2,3]\n' in result)

    def test_generate_cqasm_correct_output_gate_u(self):
        qc = QuantumCircuit(2, 2)
        qc.u(0, 0, np.pi / 2, 0)
        result = self._generate_cqasm_from_circuit(qc)
        self.assertTrue('Rz q[0], 1.570796\n' in result)

        qc = QuantumCircuit(2, 2)
        qc.u(-np.pi / 2, 0, 0, 0)
        result = self._generate_cqasm_from_circuit(qc)
        self.assertTrue('Ry q[0], -1.570796\n' in result)

        qc = QuantumCircuit(2, 2)
        qc.u(np.pi / 4, np.pi / 2, -np.pi / 2, 0)
        result = self._generate_cqasm_from_circuit(qc)
        self.assertTrue('Rz q[0], -1.570796\nRy q[0], 0.785398\nRz q[0], 1.570796\n' in result)

        qc = QuantumCircuit(2, 2)
        qc.u(0.123456, 0.654321, -0.333333, 1)
        result = self._generate_cqasm_from_circuit(qc)
        self.assertTrue('Rz q[1], -0.333333\nRy q[1], 0.123456\nRz q[1], 0.654321\n' in result)

    def test_generate_cqasm_correct_output_conditional_gate_u(self):
        q = QuantumRegister(4, "q")
        c = ClassicalRegister(4, "c")
        qc = QuantumCircuit(q, c, name="test")
        qc.u(0, 0, np.pi / 2, 0).c_if(c, 3)
        result = self._generate_cqasm_from_circuit(qc)
        self.assertTrue('not b[2,3]\nC-Rz b[0,1,2,3], q[0], 1.570796\nnot b[2,3]\n' in result)

        q = QuantumRegister(4, "q")
        c = ClassicalRegister(4, "c")
        qc = QuantumCircuit(q, c, name="test")
        qc.u(-np.pi / 2, 0, 0, 0).c_if(c, 3)
        result = self._generate_cqasm_from_circuit(qc)
        self.assertTrue('not b[2,3]\nC-Ry b[0,1,2,3], q[0], -1.570796\nnot b[2,3]' in result)

        q = QuantumRegister(4, "q")
        c = ClassicalRegister(4, "c")
        qc = QuantumCircuit(q, c, name="test")
        qc.u(np.pi / 4, np.pi / 2, -np.pi / 2, 0).c_if(c, 3)
        result = self._generate_cqasm_from_circuit(qc)
        self.assertTrue('not b[2,3]\nC-Rz b[0,1,2,3], q[0], -1.570796\nC-Ry b[0,1,2,3], q[0], 0.785398\nC-Rz b[0,1,2,3],'
                        ' q[0], 1.570796\nnot b[2,3]\n' in result)

        q = QuantumRegister(4, "q")
        c = ClassicalRegister(4, "c")
        qc = QuantumCircuit(q, c, name="test")
        qc.u(0.123456, 0.654321, -0.333333, 1).c_if(c, 3)
        result = self._generate_cqasm_from_circuit(qc)
        self.assertTrue('not b[2,3]\nC-Rz b[0,1,2,3], q[1], -0.333333\nC-Ry b[0,1,2,3], q[1], 0.123456\nC-Rz b[0,1,2,3],'
                        ' q[1], 0.654321\nnot b[2,3]\n' in result)

    def test_generate_cqasm_correct_output_gate_p(self):
        qc = QuantumCircuit(2, 2)
        qc.p(np.pi / 2, 0)
        result = self._generate_cqasm_from_circuit(qc)
        self.assertTrue('Rz q[0], 1.570796\n' in result)

        qc = QuantumCircuit(2, 2)
        qc.p(np.pi / 4, 1)
        result = self._generate_cqasm_from_circuit(qc)
        self.assertTrue('Rz q[1], 0.785398\n' in result)

        qc = QuantumCircuit(3, 3)
        qc.p(-np.pi / 4, 2)
        result = self._generate_cqasm_from_circuit(qc)
        self.assertTrue('Rz q[2], -0.785398\n' in result)

        qc = QuantumCircuit(3, 3)
        qc.p(0.123456, 2)
        result = self._generate_cqasm_from_circuit(qc)
        self.assertTrue('Rz q[2], 0.123456\n' in result)

        qc = QuantumCircuit(2, 2)
        qc.p(0, 0)
        result = self._generate_cqasm_from_circuit(qc)
        self.assertFalse('q[0]' in result)

    def test_generate_cqasm_correct_output_conditional_gate_p(self):
        q = QuantumRegister(4, "q")
        c = ClassicalRegister(4, "c")
        qc = QuantumCircuit(q, c, name="test")
        qc.p(np.pi / 2, 0).c_if(c, 3)
        result = self._generate_cqasm_from_circuit(qc)
        self.assertTrue('not b[2,3]\nC-Rz b[0,1,2,3], q[0], 1.570796\nnot b[2,3]\n' in result)

        q = QuantumRegister(4, "q")
        c = ClassicalRegister(4, "c")
        qc = QuantumCircuit(q, c, name="test")
        qc.p(np.pi / 4, 1).c_if(c, 3)
        result = self._generate_cqasm_from_circuit(qc)
        self.assertTrue('not b[2,3]\nC-Rz b[0,1,2,3], q[1], 0.785398\nnot b[2,3]\n' in result)

        q = QuantumRegister(4, "q")
        c = ClassicalRegister(4, "c")
        qc = QuantumCircuit(q, c, name="test")
        qc.p(-np.pi / 4, 2).c_if(c, 3)
        result = self._generate_cqasm_from_circuit(qc)
        self.assertTrue('not b[2,3]\nC-Rz b[0,1,2,3], q[2], -0.785398\nnot b[2,3]\n' in result)

        q = QuantumRegister(4, "q")
        c = ClassicalRegister(4, "c")
        qc = QuantumCircuit(q, c, name="test")
        qc.p(0.123456, 2).c_if(c, 3)
        result = self._generate_cqasm_from_circuit(qc)
        self.assertTrue('not b[2,3]\nC-Rz b[0,1,2,3], q[2], 0.123456\nnot b[2,3]\n' in result)

        q = QuantumRegister(4, "q")
        c = ClassicalRegister(4, "c")
        qc = QuantumCircuit(q, c, name="test")
        qc.p(0, 0).c_if(c, 3)
        result = self._generate_cqasm_from_circuit(qc)
        self.assertFalse('q[0]' in result)

    def test_generate_cqasm_correct_output_gate_u2(self):
        # Qiskit u2 is deprecated from 0.16.0. u2(a, b) -> u(pi/2, a, b)
        qc = QuantumCircuit(2, 2)
        qc.u(np.pi / 2, np.pi, np.pi / 2, 0)
        result = self._generate_cqasm_from_circuit(qc)
        self.assertTrue('Rz q[0], 1.570796\nRy q[0], 1.570796\nRz q[0], 3.141593\n' in result)

        qc = QuantumCircuit(2, 2)
        qc.u(np.pi / 2, 0, np.pi, 1)
        result = self._generate_cqasm_from_circuit(qc)
        self.assertTrue('Rz q[1], 3.141593\nRy q[1], 1.570796\n' in result)

        qc = QuantumCircuit(3, 3)
        qc.u(np.pi / 2, 0.123456, -0.654321, 2)
        result = self._generate_cqasm_from_circuit(qc)
        self.assertTrue('Rz q[2], -0.654321\nRy q[2], 1.570796\nRz q[2], 0.123456\n' in result)

        qc = QuantumCircuit(3, 3)
        qc.u(np.pi / 2, 0, 0, 0)
        result = self._generate_cqasm_from_circuit(qc)
        self.assertTrue('Ry q[0], 1.570796\n' in result)

    def test_generate_cqasm_correct_output_conditional_gate_u2(self):
        # Qiskit u2 is deprecated from 0.16.0. u2(a, b) -> u(pi/2, a, b)
        q = QuantumRegister(4, "q")
        c = ClassicalRegister(4, "c")
        qc = QuantumCircuit(q, c, name="test")
        qc.u(np.pi / 2, np.pi, np.pi / 2, 0).c_if(c, 3)
        result = self._generate_cqasm_from_circuit(qc)
        self.assertTrue('not b[2,3]\nC-Rz b[0,1,2,3], q[0], 1.570796\nC-Ry b[0,1,2,3], q[0], 1.570796\nC-Rz b[0,1,2,3], q[0],'
                        ' 3.141593\nnot b[2,3]\n' in result)

        q = QuantumRegister(4, "q")
        c = ClassicalRegister(4, "c")
        qc = QuantumCircuit(q, c, name="test")
        qc.u(np.pi / 2, 0, np.pi, 1).c_if(c, 3)
        result = self._generate_cqasm_from_circuit(qc)
        self.assertTrue('not b[2,3]\nC-Rz b[0,1,2,3], q[1], 3.141593\nC-Ry b[0,1,2,3], q[1], 1.570796\nnot b[2,3]\n' in result)

        q = QuantumRegister(4, "q")
        c = ClassicalRegister(4, "c")
        qc = QuantumCircuit(q, c, name="test")
        qc.u(np.pi / 2, 0.123456, -0.654321, 2).c_if(c, 3)
        result = self._generate_cqasm_from_circuit(qc)
        self.assertTrue('not b[2,3]\nC-Rz b[0,1,2,3], q[2], -0.654321\nC-Ry b[0,1,2,3], q[2], 1.570796\nC-Rz b[0,1,2,3], q[2],'
                        ' 0.123456\nnot b[2,3]\n' in result)

        q = QuantumRegister(4, "q")
        c = ClassicalRegister(4, "c")
        qc = QuantumCircuit(q, c, name="test")
        qc.u(np.pi / 2, 0, 0, 0).c_if(c, 3)
        result = self._generate_cqasm_from_circuit(qc)
        self.assertTrue('not b[2,3]\nC-Ry b[0,1,2,3], q[0], 1.570796\nnot b[2,3]\n' in result)

    def test_generate_cqasm_correct_output_gate_u3(self):
        # Qiskit u3 is deprecated from 0.16.0. u3 -> u
        qc = QuantumCircuit(2, 2)
        qc.u(1, 2, 3, 0)
        result = self._generate_cqasm_from_circuit(qc)
        self.assertTrue('Rz q[0], 3.000000\nRy q[0], 1.000000\nRz q[0], 2.000000\n' in result)

        qc = QuantumCircuit(2, 2)
        qc.u(0.123456, 0.654321, -0.333333, 1)
        result = self._generate_cqasm_from_circuit(qc)
        self.assertTrue('Rz q[1], -0.333333\nRy q[1], 0.123456\nRz q[1], 0.654321\n' in result)

        qc = QuantumCircuit(2, 2)
        qc.u(0, 0.654321, 0, 1)
        result = self._generate_cqasm_from_circuit(qc)
        self.assertTrue('Rz q[1], 0.654321\n' in result)

        qc = QuantumCircuit(3, 3)
        qc.u(0.654321, 0, 0, 2)
        result = self._generate_cqasm_from_circuit(qc)
        self.assertTrue('Ry q[2], 0.654321\n' in result)

        qc = QuantumCircuit(2, 2)
        qc.u(0, 0, 0, 0)
        result = self._generate_cqasm_from_circuit(qc)
        self.assertFalse('q[0]' in result)

    def test_generate_cqasm_correct_output_conditional_gate_u3(self):
        # Qiskit u3 is deprecated from 0.16.0. u3 -> u
        q = QuantumRegister(4, "q")
        c = ClassicalRegister(4, "c")
        qc = QuantumCircuit(q, c, name="test")
        qc.u(1, 2, 3, 0).c_if(c, 3)
        result = self._generate_cqasm_from_circuit(qc)
        self.assertTrue('not b[2,3]\nC-Rz b[0,1,2,3], q[0], 3.000000\nC-Ry b[0,1,2,3], q[0], 1.000000\nC-Rz b[0,1,2,3], q[0],'
                        ' 2.000000\nnot b[2,3]\n' in result)

        q = QuantumRegister(4, "q")
        c = ClassicalRegister(4, "c")
        qc = QuantumCircuit(q, c, name="test")
        qc.u(0.123456, 0.654321, -0.333333, 1).c_if(c, 3)
        result = self._generate_cqasm_from_circuit(qc)
        self.assertTrue('not b[2,3]\nC-Rz b[0,1,2,3], q[1], -0.333333\nC-Ry b[0,1,2,3], q[1], 0.123456\nC-Rz b[0,1,2,3], q[1],'
                        ' 0.654321\nnot b[2,3]\n' in result)

        q = QuantumRegister(4, "q")
        c = ClassicalRegister(4, "c")
        qc = QuantumCircuit(q, c, name="test")
        qc.u(0, 0.654321, 0, 1).c_if(c, 3)
        result = self._generate_cqasm_from_circuit(qc)
        self.assertTrue('not b[2,3]\nC-Rz b[0,1,2,3], q[1], 0.654321\nnot b[2,3]\n' in result)

        q = QuantumRegister(4, "q")
        c = ClassicalRegister(4, "c")
        qc = QuantumCircuit(q, c, name="test")
        qc.u(0.654321, 0, 0, 2).c_if(c, 3)
        result = self._generate_cqasm_from_circuit(qc)
        self.assertTrue('not b[2,3]\nC-Ry b[0,1,2,3], q[2], 0.654321\nnot b[2,3]\n' in result)

        q = QuantumRegister(4, "q")
        c = ClassicalRegister(4, "c")
        qc = QuantumCircuit(q, c, name="test")
        qc.u(0, 0, 0, 0).c_if(c, 3)
        result = self._generate_cqasm_from_circuit(qc)
        self.assertFalse('q[0]' in result)

    def test_generate_cqasm_correct_output_sympy_special_cases(self):
        # Zero
        qc = QuantumCircuit(2, 2)
        qc.rx(0, 1)
        result = self._generate_cqasm_from_circuit(qc)
        self.assertTrue('Rx q[1], 0.000000\n' in result)

        # One
        qc = QuantumCircuit(2, 2)
        qc.rx(1, 1)
        result = self._generate_cqasm_from_circuit(qc)
        self.assertTrue('Rx q[1], 1.000000\n' in result)

        # Integer
        qc = QuantumCircuit(2, 2)
        qc.rx(2, 1)
        result = self._generate_cqasm_from_circuit(qc)
        self.assertTrue('Rx q[1], 2.000000\n' in result)

        # NegativeOne
        qc = QuantumCircuit(2, 2)
        qc.rx(-1, 1)
        result = self._generate_cqasm_from_circuit(qc)
        self.assertTrue('Rx q[1], -1.000000\n' in result)

        # Float
        qc = QuantumCircuit(2, 2)
        qc.rx(np.pi / 2, 0)
        result = self._generate_cqasm_from_circuit(qc)
        self.assertTrue('Rx q[0], 1.570796\n' in result)

    def test_generate_cqasm_correct_output_rotation_x(self):
        qc = QuantumCircuit(2, 2)
        qc.rx(np.pi / 2, 0)
        result = self._generate_cqasm_from_circuit(qc)
        self.assertTrue('Rx q[0], 1.570796\n' in result)

        qc = QuantumCircuit(2, 2)
        qc.rx(0.123456, 1)
        result = self._generate_cqasm_from_circuit(qc)
        self.assertTrue('Rx q[1], 0.123456\n' in result)

    def test_generate_cqasm_correct_output_conditional_rotation_x(self):
        q = QuantumRegister(8, "q")
        c = ClassicalRegister(8, "c")
        qc = QuantumCircuit(q, c, name="test")
        qc.rx(np.pi / 2, 0).c_if(c, 14)
        result = self._generate_cqasm_from_circuit(qc)
        self.assertTrue('not b[0,4,5,6,7]\nC-Rx b[0,1,2,3,4,5,6,7], q[0], 1.570796\nnot b[0,4,5,6,7]\n' in result)

        q = QuantumRegister(8, "q")
        c = ClassicalRegister(8, "c")
        qc = QuantumCircuit(q, c, name="test")
        qc.rx(0.123456, 1).c_if(c, 14)
        result = self._generate_cqasm_from_circuit(qc)
        self.assertTrue('not b[0,4,5,6,7]\nC-Rx b[0,1,2,3,4,5,6,7], q[1], 0.123456\nnot b[0,4,5,6,7]\n' in result)

    def test_generate_cqasm_correct_output_rotation_y(self):
        qc = QuantumCircuit(2, 2)
        qc.ry(np.pi / 2, 0)
        result = self._generate_cqasm_from_circuit(qc)
        self.assertTrue('Ry q[0], 1.570796\n' in result)

        qc = QuantumCircuit(2, 2)
        qc.ry(0.654321, 1)
        result = self._generate_cqasm_from_circuit(qc)
        self.assertTrue('Ry q[1], 0.654321\n' in result)

    def test_generate_cqasm_correct_output_conditional_rotation_y(self):
        q = QuantumRegister(4, "q")
        c = ClassicalRegister(4, "c")
        qc = QuantumCircuit(q, c, name="test")
        qc.ry(np.pi / 2, 0).c_if(c, 3)
        result = self._generate_cqasm_from_circuit(qc)
        self.assertTrue('not b[2,3]\nC-Ry b[0,1,2,3], q[0], 1.570796\nnot b[2,3]\n' in result)

        q = QuantumRegister(4, "q")
        c = ClassicalRegister(4, "c")
        qc = QuantumCircuit(q, c, name="test")
        qc.ry(0.654321, 1).c_if(c, 3)
        result = self._generate_cqasm_from_circuit(qc)
        self.assertTrue('not b[2,3]\nC-Ry b[0,1,2,3], q[1], 0.654321\nnot b[2,3]\n' in result)

    def test_generate_cqasm_correct_output_rotation_z(self):
        qc = QuantumCircuit(2, 2)
        qc.rz(np.pi / 2, 0)
        result = self._generate_cqasm_from_circuit(qc)
        self.assertTrue('Rz q[0], 1.570796\n' in result)

        qc = QuantumCircuit(2, 2)
        qc.rz(-np.pi / 2, 1)
        result = self._generate_cqasm_from_circuit(qc)
        self.assertTrue('Rz q[1], -1.570796\n' in result)

    def test_generate_cqasm_correct_output_conditional_rotation_z(self):
        q = QuantumRegister(4, "q")
        c = ClassicalRegister(4, "c")
        qc = QuantumCircuit(q, c, name="test")
        qc.rz(np.pi / 2, 0).c_if(c, 1)
        result = self._generate_cqasm_from_circuit(qc)
        self.assertTrue('not b[1,2,3]\nC-Rz b[0,1,2,3], q[0], 1.570796\nnot b[1,2,3]\n' in result)

        q = QuantumRegister(4, "q")
        c = ClassicalRegister(4, "c")
        qc = QuantumCircuit(q, c, name="test")
        qc.rz(-np.pi / 2, 1).c_if(c, 1)
        result = self._generate_cqasm_from_circuit(qc)
        self.assertTrue('not b[1,2,3]\nC-Rz b[0,1,2,3], q[1], -1.570796\nnot b[1,2,3]\n' in result)

    def test_generate_cqasm_correct_output_unknown_gate(self):
        instructions = [{'name': 'bla', 'qubits': [1], 'params': [-np.pi / 2]}]
        self.assertRaisesRegex(ApiError, "Gate 'bla' not supported", self._generate_cqasm_from_instructions,
                               instructions, 2)

    def test_generate_cqasm_correct_output_unknown_controlled_gate(self):
        instructions = [{'mask': '0xF', 'name': 'bfunc', 'register': 17, 'relation': '==', 'val': '0x1'},
                        {'conditional': 17, 'name': 'bla', 'qubits': [1], 'params': [-np.pi / 2]}]
        self.assertRaisesRegex(ApiError, "Conditional gate 'c-bla' not supported",
                               self._generate_cqasm_from_instructions, instructions, 2)

    def test_generate_cqasm_correct_output_no_bit_negation(self):
        q = QuantumRegister(4, "q")
        c = ClassicalRegister(4, "c")
        qc = QuantumCircuit(q, c, name="test")
        qc.rx(-np.pi / 2, 1).c_if(c, 15)
        result = self._generate_cqasm_from_circuit(qc)
        self.assertTrue('C-Rx b[0,1,2,3], q[1], -1.570796\n' in result)
        self.assertFalse('not\n' in result)

    def test_generate_cqasm_correct_output_one_bit_condition(self):
        q1 = QuantumRegister(1, "q1")
        q2 = QuantumRegister(1, "q2")
        c1 = ClassicalRegister(1, "c1")
        c2 = ClassicalRegister(1, "c2")
        qc = QuantumCircuit(q1, q2, c1, c2, name="test")
        qc.rx(-np.pi / 2, q2).c_if(c1, 1)
        result = self._generate_cqasm_from_circuit(qc)
        self.assertTrue('C-Rx b[0], q[1], -1.570796\n' in result)
        self.assertFalse('not\n' in result)

        q1 = QuantumRegister(1, "q1")
        q2 = QuantumRegister(1, "q2")
        c1 = ClassicalRegister(1, "c1")
        c2 = ClassicalRegister(1, "c2")
        qc = QuantumCircuit(q1, q2, c1, c2, name="test")
        qc.rx(-np.pi / 2, q2).c_if(c2, 1)
        result = self._generate_cqasm_from_circuit(qc)
        self.assertTrue('C-Rx b[1], q[1], -1.570796\n' in result)
        self.assertFalse('not\n' in result)

        q1 = QuantumRegister(6, "q1")
        q2 = QuantumRegister(1, "q2")
        c1 = ClassicalRegister(6, "c1")
        c2 = ClassicalRegister(1, "c2")
        qc = QuantumCircuit(q1, q2, c1, c2, name="test")
        qc.rx(-np.pi / 2, 1).c_if(c2, 1)
        result = self._generate_cqasm_from_circuit(qc)
        self.assertTrue('C-Rx b[6], q[1], -1.570796\n' in result)
        self.assertFalse('not\n' in result)

        q1 = QuantumRegister(6, "q1")
        q2 = QuantumRegister(1, "q2")
        c1 = ClassicalRegister(6, "c1")
        c2 = ClassicalRegister(1, "c2")
        qc = QuantumCircuit(q1, q2, c1, c2, name="test")
        qc.rx(-np.pi / 2, 1).c_if(c2, 0)
        result = self._generate_cqasm_from_circuit(qc)
        self.assertTrue('not b[6]\nC-Rx b[6], q[1], -1.570796\nnot b[6]\n' in result)

    def test_generate_cqasm_correct_output_more_bit_condition(self):
        q1 = QuantumRegister(3, "q1")
        q2 = QuantumRegister(3, "q2")
        c1 = ClassicalRegister(3, "c1")
        c2 = ClassicalRegister(3, "c2")
        qc = QuantumCircuit(q1, q2, c1, c2, name="test")
        qc.y(2).c_if(c2, 3)
        result = self._generate_cqasm_from_circuit(qc)
        self.assertTrue('not b[5]\nC-Y b[3,4,5], q[2]\nnot b[5]\n' in result)

        q1 = QuantumRegister(1, "q1")
        q2 = QuantumRegister(7, "q2")
        c1 = ClassicalRegister(1, "c1")
        c2 = ClassicalRegister(7, "c2")
        qc = QuantumCircuit(q1, q2, c1, c2, name="test")
        qc.y(2).c_if(c2, 12)
        result = self._generate_cqasm_from_circuit(qc)
        self.assertTrue('not b[1,2,5,6,7]\nC-Y b[1,2,3,4,5,6,7], q[2]\nnot b[1,2,5,6,7]\n' in result)

        q1 = QuantumRegister(1, "q1")
        q2 = QuantumRegister(7, "q2")
        c1 = ClassicalRegister(1, "c1")
        c2 = ClassicalRegister(7, "c2")
        qc = QuantumCircuit(q1, q2, c1, c2, name="test")
        qc.y(2).c_if(c2, 27)
        result = self._generate_cqasm_from_circuit(qc)
        self.assertTrue('not b[3,6,7]\nC-Y b[1,2,3,4,5,6,7], q[2]\nnot b[3,6,7]\n' in result)

        q1 = QuantumRegister(5, "q1")
        q2 = QuantumRegister(2, "q2")
        c1 = ClassicalRegister(5, "c1")
        c2 = ClassicalRegister(2, "c2")
        qc = QuantumCircuit(q1, q2, c1, c2, name="test")
        qc.y(2).c_if(c2, 2)
        result = self._generate_cqasm_from_circuit(qc)
        self.assertTrue('not b[5]\nC-Y b[5,6], q[2]\nnot b[5]\n' in result)

    def test_generate_cqasm_correct_output_unknown_type(self):
        instructions = [{'mask': '0xF', 'name': 'bfunc', 'register': 18, 'relation': '!=', 'val': '0x1'},
                        {'conditional': 18, 'name': 'rx', 'qubits': [1], 'params': [-np.pi / 2]}]
        self.assertRaisesRegex(ApiError, 'Conditional statement with relation != not supported',
                               self._generate_cqasm_from_instructions, instructions, 2)

    def test_generate_cqasm_correct_output_no_mask(self):
        instructions = [{'mask': '0x0', 'name': 'bfunc', 'register': 18, 'relation': '==', 'val': '0x1'},
                        {'conditional': 18, 'name': 'rx', 'qubits': [1], 'params': [-np.pi / 2]}]
        self.assertRaisesRegex(ApiError, 'Conditional statement rx without a mask',
                               self._generate_cqasm_from_instructions, instructions, 2)

    def test_generate_cqasm_register_no_match(self):
        instructions = [{'mask': '0xF', 'name': 'bfunc', 'register': 1, 'relation': '==', 'val': '0x3'},
                        {'conditional': 2, 'name': 'rx', 'qubits': [1], 'params': [-np.pi / 2]}]
        self.assertRaisesRegex(ApiError, 'Conditional not found: reg_idx = 2',
                               self._generate_cqasm_from_instructions, instructions, 2)

    def test_get_mask_data(self):
        mask = 0
        lowest_mask_bit, mask_length = CircuitToString.get_mask_data(mask)
        self.assertEqual(lowest_mask_bit, -1)
        self.assertEqual(mask_length, 0)

        mask = 56
        lowest_mask_bit, mask_length = CircuitToString.get_mask_data(mask)
        self.assertEqual(lowest_mask_bit, 3)
        self.assertEqual(mask_length, 3)

        mask = 1
        lowest_mask_bit, mask_length = CircuitToString.get_mask_data(mask)
        self.assertEqual(lowest_mask_bit, 0)
        self.assertEqual(mask_length, 1)

        mask = 255
        lowest_mask_bit, mask_length = CircuitToString.get_mask_data(mask)
        self.assertEqual(lowest_mask_bit, 0)
        self.assertEqual(mask_length, 8)

        mask = 510
        lowest_mask_bit, mask_length = CircuitToString.get_mask_data(mask)
        self.assertEqual(lowest_mask_bit, 1)
        self.assertEqual(mask_length, 8)

        mask = 128
        lowest_mask_bit, mask_length = CircuitToString.get_mask_data(mask)
        self.assertEqual(lowest_mask_bit, 7)
        self.assertEqual(mask_length, 1)

        mask = 192
        lowest_mask_bit, mask_length = CircuitToString.get_mask_data(mask)
        self.assertEqual(lowest_mask_bit, 6)
        self.assertEqual(mask_length, 2)
