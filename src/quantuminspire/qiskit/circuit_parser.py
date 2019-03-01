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
from typing import Dict, Any


class CircuitToString:
    """ Contains the translational elements to convert the Qiskit circuits to cQASM code."""

    def _cx(self, circuit: Dict[str, Any]) -> str:
        """ Translates the controlled X element.

        Args:
            circuit: The Qiskit circuit with CX element.

        Returns:
            cQASM code string.
        """
        qubit_indices = tuple(circuit['qubits'])
        return 'CNOT q[{0}], q[{1}]\n'.format(*qubit_indices)

    def _ccx(self, circuit: Dict[str, Any]) -> str:
        """ Translates the Toffoli element.

        Args:
            circuit: The Qiskit circuit with CCX element.

        Returns:
            cQASM code string.
        """
        qubit_indices = tuple(circuit['qubits'])
        return 'Toffoli q[{0}], q[{1}], q[{2}]\n'.format(*qubit_indices)

    def _measure(self, circuit: Dict[str, Any]) -> None:
        """ Translates the measure element. Not used!

        Args:
            The Qiskit circuit with measure element.

        Returns:
            None.
        """
        return None

    def _h(self, circuit: Dict[str, Any]) -> str:
        """ Translates the H element.

        Args:
            circuit: The Qiskit circuit with Hadamard element.

        Returns:
            cQASM code string.
        """
        qubit_indices = tuple(circuit['qubits'])
        return 'H q[{0}]\n'.format(*qubit_indices)

    def _barrier(self, circuit: Dict[str, Any]) -> None:
        """ Translates the | element. Not used!

        Args:
            circuit: The Qiskit circuit with barrier element.

        Returns:
            None.
        """
        return None

    def _id(self, circuit: Dict[str, Any]) -> None:
        """ Translates the ID element. Not used!

        Args:
            circuit: The Qiskit circuit with identity element.

        Returns:
            None.
        """
        return None

    def _x(self, circuit: Dict[str, Any]) -> str:
        """ Translates the X element.

        Args:
            circuit: The Qiskit circuit with X element.

        Returns:
            cQASM code string.
        """
        qubit_indices = tuple(circuit['qubits'])
        return 'X q[{0}]\n'.format(*qubit_indices)

    def _y(self, circuit: Dict[str, Any]) -> str:
        """ Translates the Y element.

        Args:
            circuit: The Qiskit circuit with Y element.

        Returns:
            cQASM code string.
        """
        qubit_indices = tuple(circuit['qubits'])
        return 'Y q[{0}]\n'.format(*qubit_indices)

    def _z(self, circuit: Dict[str, Any]) -> str:
        """ Translates the Z element.

        Args:
            circuit: The Qiskit circuit with Z element.

        Returns:
            cQASM code string.
        """
        qubit_indices = tuple(circuit['qubits'])
        return 'Z q[{0}]\n'.format(*qubit_indices)

    def _u(self, circuit: Dict[str, Any]) -> str:
        """ Translates the U element to U3.

        Args:
            circuit: The Qiskit circuit with U element.

        Returns:
            cQASM code string.
        """
        return self._u3(circuit)

    def _u0(self, circuit: Dict[str, Any]) -> None:
        """ Translates the U0 element. Not used!

        Args:
            circuit: The Qiskit circuit with U0 element.

        Returns:
            None.
        """
        return None

    def _u1(self, circuit: Dict[str, Any]) -> str:
        """ Translates the U1(lambda) element to U3(0, 0, lambda). A copy of the circuit is made to prevent
            side-effects for the caller.

        Args:
            circuit: The Qiskit circuit with U1 element.

        Returns:
            cQASM code string.
        """
        tempcircuit = copy.deepcopy(circuit)
        tempcircuit['params'][0:0] = (0, 0)
        tempcircuit['texparams'][0:0] = ('0', '0')
        return self._u3(tempcircuit)

    def _u2(self, circuit: Dict[str, Any]) -> str:
        """ Translates the U2(phi, lambda) element to U3(pi/2, phi, lambda). A copy of the circuit is made to prevent
            side-effects for the caller.

        Args:
            circuit : The Qiskit circuit with U2 element.

        Returns:
            cQASM code string.
        """
        tempcircuit = copy.deepcopy(circuit)
        tempcircuit['params'].insert(0, np.pi/2)
        tempcircuit['texparams'].insert(0, '\\frac{\\pi}{2}')
        return self._u3(tempcircuit)

    def _u3(self, circuit: Dict[str, Any]) -> str:
        """ Translates the U3(theta, phi, lambda) element to 3 rotation gates.
            Any single qubit operation (a 2x2 unitary matrix) can be written as the product of rotations.
            As an example, a unitary single-qubit gate can be expressed as a combination of
            Rz and Ry rotations (Nielsen and Chuang, 10th edition, section 4.2).
            U(theta, phi, lambda) = Rz(phi)Ry(theta)Rz(lambda).
            Note: The expression above is the matrix multiplication, when implementing this in a gate circuit,
            the gates need to be executed in reversed order.
            Any rotation of 0 radials is left out of the resulting circuit.

        Args:
            circuit: The Qiskit circuit with U3 element.

        Returns:
            cQASM code string.
        """
        gates = ['Rz', 'Ry', 'Rz']
        angles = list(circuit['params'][i] for i in [2, 0, 1])
        index_q0 = [circuit['qubits'][0]] * 3
        return ''.join('%s q[%d], %f\n' % triplet for triplet in zip(gates, index_q0, angles) if triplet[2] != 0)

    def __r(self, circuit: Dict[str, Any], axis: str) -> str:
        """ Translates the Rotation element for an axis (x,y,z).

        Args:
            circuit: The Qiskit circuit with rotation element for axis.
            axis: The axis for which the Rotation operator is parsed ('x', 'y' or 'z').

        Returns:
            cQASM code string.
        """
        angle_q0 = circuit['params'][0]
        qubit_indices = tuple(circuit['qubits'])
        # return 'R%c q[%d], %f\n' % (axis, *qubit_indices, angle_q0)
        return 'R{0} q[{1}], {2:f}\n'.format(axis, *qubit_indices, angle_q0)

    def _rx(self, circuit: Dict[str, Any]) -> str:
        """ Translates the Rx element.

        Args:
            circuit: The Qiskit circuit with Rx element.

        Returns:
            cQASM code string.
        """
        return self.__r(circuit, 'x')

    def _ry(self, circuit: Dict[str, Any]) -> str:
        """ Translates the Ry element.

        Args:
            circuit: The Qiskit circuit with Ry element.

        Returns:
            cQASM code string.
        """
        return self.__r(circuit, 'y')

    def _rz(self, circuit: Dict[str, Any]) -> str:
        """ Translates the Rz element.

        Args:
            circuit: The Qiskit circuit with Rz element.

        Returns:
            cQASM code string.
        """
        return self.__r(circuit, 'z')
