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

import numpy as np


class CircuitToString:
    """ Contains the translational elements to convert the qiskit circuits to CQASM code."""

    _u1_operator_switch = {
        np.pi / 2: 'S',
        np.pi / 4: 'T',
        -np.pi / 4: 'Tdag'
    }

    _u_operator_switch = {
        np.pi / 2: 'S',
        -np.pi / 2: 'Sdag',
    }

    def _cx(self, circuit):
        """ Translates the controlled X element.

        Args: circuit (dict): The qiskit circuit with CX element.

        Returns:
            Str: CQASM code string.
        """
        qubit_indices = tuple(circuit['qubits'])
        return 'CNOT q[%d], q[%d]\n' % qubit_indices

    def _ccx(self, circuit):
        """ Translates the Toffoli element.

        Args: circuit (dict): The qiskit circuit with CCX element.

        Returns:
            Str: CQASM code string.
        """
        qubit_indices = tuple(circuit['qubits'])
        return 'Toffoli q[%d], q[%d], q[%d]\n' % qubit_indices

    def _measure(self, circuit):
        """ Translates the measure element. Not used!

        Args: circuit (dict): The qiskit circuit with measure element.

        Returns:
            None.
        """
        return None

    def _h(self, circuit):
        """ Translates the H element.

        Args: circuit (dict): The qiskit circuit with Hadamard element.

        Returns:
            Str: CQASM code string.
        """
        qubit_indices = tuple(circuit['qubits'])
        return 'H q[%d]\n' % qubit_indices

    def _barrier(self, circuit):
        """ Translates the | element. Not used!

        Args: circuit (dict): The qiskit circuit with barrier element.

        Returns:
            None.
        """
        return None

    def _id(self, circuit):
        """ Translates the ID element. Not used!

        Args: circuit (dict): The qiskit circuit with identity element.

        Returns:
            None.
        """
        return None

    def _x(self, circuit):
        """ Translates the X element.

        Args: circuit (dict): The qiskit circuit with X element.

        Returns:
            Str: CQASM code string.
        """
        qubit_indices = tuple(circuit['qubits'])
        return 'X q[%d]\n' % qubit_indices

    def _y(self, circuit):
        """ Translates the Y element.

        Args: circuit (dict): The qiskit circuit with Y element.

        Returns:
            Str: CQASM code string.
        """
        qubit_indices = tuple(circuit['qubits'])
        return 'Y q[%d]\n' % qubit_indices

    def _z(self, circuit):
        """ Translates the Z element.

        Args: circuit (dict): The qiskit circuit with Z element.

        Returns:
            Str: CQASM code string.
        """
        qubit_indices = tuple(circuit['qubits'])
        return 'Z q[%d]\n' % qubit_indices

    def _u(self, circuit):
        """ Translates the U element.

        Args: circuit (dict): The qiskit circuit with U element.

        Raises:
            ValueError: When the provided rotation angles are invalid!

        Returns:
            Str: CQASM code string.
        """
        parameters = circuit['params']
        angles_q0_q1 = parameters[:2]
        angle_q2 = parameters[2]
        qubit_indices = tuple(circuit['qubits'])
        operator = CircuitToString._u_operator_switch.get(angle_q2)
        if angles_q0_q1 != [0, 0] or operator is None:
            raise ValueError('Gate U with parameters not implemented (parameters=%s)!' % parameters)
        return '%s q[%d]\n' % (operator, *qubit_indices)

    def _u0(self, circuit):
        """ Translates the U0 element. Not used!

        Args: circuit (dict): The qiskit circuit with U0 element.

        Returns:
            None.
        """
        return None

    def _u1(self, circuit):
        """ Translates the U1 element.

        Args: circuit (dict): The qiskit circuit with U1 element.

        Raises:
            ValueError: When the provided rotation angles are invalid!

        Returns:
            Str: CQASM code string.
        """
        angle_q0 = circuit['params'][0]
        qubit_indices = tuple(circuit['qubits'])
        operator = CircuitToString._u1_operator_switch.get(angle_q0)
        parameters = circuit['params']
        if operator is None:
            raise ValueError('Gate U1 with parameters not implemented (parameters=%s)!' % parameters)
        return '%s q[%d]\n' % (operator, *qubit_indices)

    def _u2(self, circuit):
        """ Translates the U2 element. Not usable!

        Args: circuit (dict): The qiskit circuit with U2 element.

        Raises:
            ValueError: When the provided rotation angles are invalid!
        """
        parameters = circuit['params']
        raise ValueError('Gate U2 not implemented (parameters=%s)!' % parameters)

    def _u3(self, circuit):
        """ Translates the U3 element.

        Args: circuit (dict): The qiskit circuit with U3 element.

        Returns:
            Str: CQASM code string.
        """
        gates = ['Rz', 'Ry', 'Rz']
        angles = circuit['params'][:3]
        index_q0 = [circuit['qubits'][0]] * 3
        return ''.join('%s q[%d], %f\n' % pair for pair in zip(gates, index_q0, angles))
