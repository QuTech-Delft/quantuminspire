""" Quantum Inspire SDK

Copyright 2022 QuTech Delft

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
import unittest
from unittest.mock import Mock

from qiskit import QuantumRegister, ClassicalRegister, QuantumCircuit
from qiskit.compiler import assemble
from quantuminspire.qiskit.backend_qx import QuantumInspireBackend
from quantuminspire.exceptions import QiskitBackendError
from quantuminspire.qiskit.measurements import Measurements


class TestMeasurements(unittest.TestCase):

    @staticmethod
    def _circuit_to_qobj(circuit):
        run_config_dict = {'shots': 25, 'memory': True}
        backend = QuantumInspireBackend(Mock(), Mock())
        qobj = assemble(circuit, backend, **run_config_dict)
        return qobj

    @staticmethod
    def _circuit_to_experiment(circuit):
        qobj = TestMeasurements._circuit_to_qobj(circuit)
        return qobj.experiments[0]

    def test_from_experiment(self):
        qc = QuantumCircuit(2, 2)
        qc.cx(0, 1)
        qc.measure(0, 1)
        qc.measure(1, 0)

        experiment = self._circuit_to_experiment(qc)
        measurements = Measurements.from_experiment(experiment)
        expected_result = {'measurements_state': [[1, 0], [0, 1]],
                           'measurements_reg': [[0, 1], [1, 0]],
                           'number_of_qubits': 2,
                           'number_of_clbits': 2
                           }
        self.assertDictEqual(measurements.to_dict(), expected_result)
        self.assertEqual(measurements.nr_of_qubits, 2)
        self.assertEqual(measurements.nr_of_clbits, 2)

    def test_collect_measurements_without_measurements(self):
        qc = QuantumCircuit(2, 2)
        qc.cx(0, 1)

        experiment = self._circuit_to_experiment(qc)

        measurements = Measurements.from_experiment(experiment)
        expected_result = {'measurements_state': [[0, 0], [1, 1]],
                           'measurements_reg': [[0, 0], [1, 1]],
                           'number_of_qubits': 2,
                           'number_of_clbits': 2
                           }
        self.assertDictEqual(measurements.to_dict(), expected_result)
        self.assertEqual(measurements.nr_of_qubits, 2)
        self.assertEqual(measurements.nr_of_clbits, 2)

    def test_validate_nr_classical_qubits_less_than_needed_for_storing_measured_qubits(self):
        q = QuantumRegister(2, 'q')
        c = ClassicalRegister(1, 'c')
        qc = QuantumCircuit(q, c, name='conditional')
        qc.cx(q[0], q[1])

        experiment = self._circuit_to_experiment(qc)
        self.assertRaisesRegex(QiskitBackendError, 'Number of classical bits \(1\) is not sufficient for storing the '
                                                   'outcomes of the experiment',
                               Measurements.from_experiment, experiment)

    def test_invalid_number_of_classical_bits(self):
        qc = QuantumCircuit(2, 2)
        qc.measure(1, 0)

        qobj = self._circuit_to_qobj(qc)
        qobj.experiments[0].header.memory_slots = 0

        experiment = qobj.experiments[0]
        self.assertRaisesRegex(QiskitBackendError, 'Invalid number of classical bits \(0\)!',
                               Measurements.from_experiment, experiment)

    def test_max_measurement_index(self):
        qr = QuantumRegister(5)
        cr = ClassicalRegister(3)
        cr_ghz = ClassicalRegister(2)
        circuit = QuantumCircuit(qr, cr, cr_ghz)

        circuit.measure(2, 3)
        circuit.measure(3, 4)
        circuit.measure([0, 1, 4], cr)
        circuit.measure([2, 3], cr_ghz)

        experiment = self._circuit_to_experiment(circuit)

        measurements = Measurements.from_experiment(experiment)

        self.assertEqual(measurements.max_measurement_index, 4)

    def test_max_measurement_index_less_than_nr_of_clbits(self):
        qr = QuantumRegister(5)
        cr = ClassicalRegister(3)
        cr_ghz = ClassicalRegister(2)
        circuit = QuantumCircuit(qr, cr, cr_ghz)

        circuit.measure(2, 3)
        circuit.measure([0, 1, 4], cr)
        circuit.measure([2], cr_ghz[0])

        experiment = self._circuit_to_experiment(circuit)
        measurements = Measurements.from_experiment(experiment)

        self.assertEqual(measurements.max_measurement_index, 3)

    def test_get_qreg_for_conditional_creg(self):
        qr = QuantumRegister(5)
        cr = ClassicalRegister(3)
        cr_ghz = ClassicalRegister(2)
        circuit = QuantumCircuit(qr, cr, cr_ghz)

        circuit.measure(2, 3)
        circuit.measure([1, 4], [1, 2])
        circuit.measure([2], cr_ghz[0])

        experiment = self._circuit_to_experiment(circuit)
        measurements = Measurements.from_experiment(experiment)

        self.assertEqual(measurements.get_qreg_for_conditional_creg(3), 2)
        self.assertEqual(measurements.get_qreg_for_conditional_creg(1), 1)
        self.assertEqual(measurements.get_qreg_for_conditional_creg(2), 4)
        self.assertEqual(measurements.get_qreg_for_conditional_creg(0), 0)
        self.assertRaisesRegex(QiskitBackendError, 'Classical bit 4 used in a conditional gate is not measured and the '
                                                   'equivalent qubit 4 is measured to another classical bit 2',
                               measurements.get_qreg_for_conditional_creg, 4)

    def test_from_dict(self):
        input = {'measurements_state': [[0, 0], [1, 1]],
                 'measurements_reg': [[0, 0], [1, 1]],
                 'number_of_qubits': 2,
                 'number_of_clbits': 2
                 }
        measurements = Measurements.from_dict(input)

        self.assertEqual(measurements.nr_of_qubits, 2)
        self.assertEqual(measurements.nr_of_clbits, 2)
        self.assertDictEqual(measurements.to_dict(), input)

    def test_measurement_2_qubits_to_1_classical_bit(self):
        qc = QuantumCircuit(2, 2)
        qc.cx(0, 1)
        qc.measure(0, 0)
        qc.x(0)
        qc.measure(1, 0)

        experiment = self._circuit_to_experiment(qc)
        measurements = Measurements.from_experiment(experiment)

        self.assertRaisesRegex(QiskitBackendError, 'Measurement of different qubits to the same classical '
                                                   'register 0 is not supported',
                               measurements.validate_unsupported_measurements)

    def test_measurement_1_qubit_to_2_classical_bits(self):
        qc = QuantumCircuit(2, 2)
        qc.cx(0, 1)
        qc.measure(1, 1)
        qc.measure(0, 0)
        qc.x(0)
        qc.measure(1, 0)

        experiment = self._circuit_to_experiment(qc)
        measurements = Measurements.from_experiment(experiment)

        self.assertRaisesRegex(QiskitBackendError, 'Measurement of qubit 1 to different classical registers '
                                                   'is not supported',
                               measurements.validate_unsupported_measurements)

    def test_qubit_to_classical_hex(self):
        qc = QuantumCircuit(4, 4)
        qc.measure(0, 0)
        qc.measure(1, 1)
        qc.measure(2, 2)
        qc.measure(3, 3)

        experiment = self._circuit_to_experiment(qc)
        measurements = Measurements.from_experiment(experiment)

        self.assertEqual(measurements.qubit_to_classical_hex('3'), '0x3')
        self.assertEqual(measurements.qubit_to_classical_hex('7'), '0x7')
        self.assertEqual(measurements.qubit_to_classical_hex('10'), '0xa')

    def test_qubit_to_classical_hex_reversed(self):
        qc = QuantumCircuit(4, 4)
        qc.measure(0, 3)
        qc.measure(1, 2)
        qc.measure(2, 1)
        qc.measure(3, 0)

        experiment = self._circuit_to_experiment(qc)
        measurements = Measurements.from_experiment(experiment)

        self.assertEqual(measurements.qubit_to_classical_hex('3'), '0xc')
        self.assertEqual(measurements.qubit_to_classical_hex('7'), '0xe')
        self.assertEqual(measurements.qubit_to_classical_hex('10'), '0x5')
