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
import copy
import numpy as np


class CircuitToString:
    """ Contains the translational elements to convert the Qiskit circuits to cQASM code."""

    def _cx(self, circuit):
        """ Translates the controlled X element.

        Args:
            circuit (dict): The Qiskit circuit with CX element.

        Returns:
            str: cQASM code string.
        """
        qubit_indices = tuple(circuit['qubits'])
        return 'CNOT q[%d], q[%d]\n' % qubit_indices

    def _ccx(self, circuit):
        """ Translates the Toffoli element.

        Args:
            circuit (dict): The Qiskit circuit with CCX element.

        Returns:
            str: cQASM code string.
        """
        qubit_indices = tuple(circuit['qubits'])
        return 'Toffoli q[%d], q[%d], q[%d]\n' % qubit_indices

    def _measure(self, circuit):
        """ Translates the measure element. Not used!

        Args:
            circuit (dict): The Qiskit circuit with measure element.

        Returns:
            None.
        """
        return None

    def _h(self, circuit):
        """ Translates the H element.

        Args:
            circuit (dict): The Qiskit circuit with Hadamard element.

        Returns:
            str: cQASM code string.
        """
        qubit_indices = tuple(circuit['qubits'])
        return 'H q[%d]\n' % qubit_indices

    def _barrier(self, circuit):
        """ Translates the | element. Not used!

        Args:
            circuit (dict): The Qiskit circuit with barrier element.

        Returns:
            None.
        """
        return None

    def _id(self, circuit):
        """ Translates the ID element. Not used!

        Args:
            circuit (dict): The Qiskit circuit with identity element.

        Returns:
            None.
        """
        return None

    def _x(self, circuit):
        """ Translates the X element.

        Args:
            circuit (dict): The Qiskit circuit with X element.

        Returns:
            str: cQASM code string.
        """
        qubit_indices = tuple(circuit['qubits'])
        return 'X q[%d]\n' % qubit_indices

    def _y(self, circuit):
        """ Translates the Y element.

        Args:
            circuit (dict): The Qiskit circuit with Y element.

        Returns:
            str: cQASM code string.
        """
        qubit_indices = tuple(circuit['qubits'])
        return 'Y q[%d]\n' % qubit_indices

    def _z(self, circuit):
        """ Translates the Z element.

        Args:
            circuit (dict): The Qiskit circuit with Z element.

        Returns:
            str: cQASM code string.
        """
        qubit_indices = tuple(circuit['qubits'])
        return 'Z q[%d]\n' % qubit_indices

    def _u(self, circuit):
        """ Translates the U element to U3.

        Args:
            circuit (dict): The Qiskit circuit with U element.

        Returns:
            str: cQASM code string.
        """
        return self._u3(circuit)

    def _u0(self, circuit):
        """ Translates the U0 element. Not used!

        Args:
            circuit (dict): The Qiskit circuit with U0 element.

        Returns:
            None.
        """
        return None

    def _u1(self, circuit):
        """ Translates the U1(lambda) element to U3(0, 0, lambda). A copy of the circuit is made to prevent
            side-effects for the caller.

        Args:
            circuit (dict): The Qiskit circuit with U1 element.

        Returns:
            str: cQASM code string.
        """
        tempcircuit = copy.deepcopy(circuit)
        tempcircuit['params'][0:0] = (0, 0)
        tempcircuit['texparams'][0:0] = ('0', '0')
        return self._u3(tempcircuit)

    def _u2(self, circuit):
        """ Translates the U2(phi, lambda) element to U3(pi/2, phi, lambda). A copy of the circuit is made to prevent
            side-effects for the caller.

        Args:
            circuit (dict): The Qiskit circuit with U2 element.

        """
        tempcircuit = copy.deepcopy(circuit)
        tempcircuit['params'].insert(0, np.pi/2)
        tempcircuit['texparams'].insert(0, '\\frac{\\pi}{2}')
        return self._u3(tempcircuit)

    def _u3(self, circuit):
        """ Translates the U3(theta, phi, lambda) element to 3 rotation gates.
            Any single qubit operation (a 2x2 unitary matrix) can be written as the product of rotations.
            As an example, a unitary single-qubit gate can be expressed as a combination of
            Rz and Ry rotations (Nielsen and Chuang, 10th edition, section 4.2).
            U(theta, phi, lambda) = Rz(phi)Ry(theta)Rz(lambda).
            Note: The expression above is the matrix multiplication, when implementing this in a gate circuit,
            the gates need to be executed in reversed order.
            Any rotation of 0 radials is left out of the resulting circuit.

        Args:
            circuit (dict): The Qiskit circuit with U3 element.

        Returns:
            str: cQASM code string.
        """
        gates = ['Rz', 'Ry', 'Rz']
        angles = list(circuit['params'][i] for i in [2, 0, 1])
        index_q0 = [circuit['qubits'][0]] * 3
        return ''.join('%s q[%d], %f\n' % triplet for triplet in zip(gates, index_q0, angles) if triplet[2] != 0)

    def __r(self, circuit, axis):
        """ Translates the Rotation element for an axis (x,y,z).

        Args:
            circuit (dict): The Qiskit circuit with rotation element for axis.
            axis (int or char): The axis for which the Rotation operator is parsed ('x', 'y' or 'z').

        Returns:
            str: cQASM code string.
        """
        angle_q0 = circuit['params'][0]
        qubit_indices = tuple(circuit['qubits'])
        return 'R%c q[%d], %f\n' % (axis, *qubit_indices, angle_q0)

    def _rx(self, circuit):
        """ Translates the Rx element.

        Args:
            circuit (dict): The Qiskit circuit with Rx element.

        Returns:
            str: cQASM code string.
        """
        return self.__r(circuit, 'x')

    def _ry(self, circuit):
        """ Translates the Ry element.

        Args:
            circuit (dict): The Qiskit circuit with Ry element.

        Returns:
            str: cQASM code string.
        """
        return self.__r(circuit, 'y')

    def _rz(self, circuit):
        """ Translates the Rz element.

        Args:
            circuit (dict): The Qiskit circuit with Rz element.

        Returns:
            str: cQASM code string.
        """
        return self.__r(circuit, 'z')
