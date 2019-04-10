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
from io import StringIO
from typing import Optional
from qiskit.qobj import QasmQobjInstruction
from quantuminspire.exceptions import ApiError


class CircuitToString:
    """ Contains the translational elements to convert the Qiskit circuits to cQASM code."""

    @staticmethod
    def _gate_not_supported(_stream: StringIO, instruction: QasmQobjInstruction, _binary_control: Optional[str] = None)\
            -> None:
        """ Called when a gate is not supported with the backend. Throws an exception (ApiError)

        Args:
            instruction: The Qiskit instruction to translate to cQASM.

        Raises:
            ApiError: the gate is not supported by the circuit parser.

        """
        if hasattr(instruction, 'conditional'):
            raise ApiError('Conditional gate c-{} not supported'.format(instruction.name.lower()))
        else:
            raise ApiError('Gate {} not supported'.format(instruction.name.lower()))

    @staticmethod
    def _cx(stream: StringIO, instruction: QasmQobjInstruction) -> None:
        """ Translates the controlled X element.

        Args:
            stream: The string-io stream to where the resulting cQASM is written.
            instruction: The Qiskit instruction to translate to cQASM.

        """
        stream.write('CNOT q[{0}], q[{1}]\n'.format(*instruction.qubits))

    @staticmethod
    def _c_cx(stream: StringIO, instruction: QasmQobjInstruction, binary_control: str) -> None:
        """ Translates the binary-controlled controlled X element.

        Args:
            stream: The string-io stream to where the resulting cQASM is written.
            instruction: The Qiskit instruction to translate to cQASM.
            binary_control: The multi-bits control string. The gate is executed when all specified classical bits are 1.

        """
        stream.write('C-CNOT {0}q[{1}], q[{2}]\n'.format(binary_control, *instruction.qubits))

    @staticmethod
    def _ccx(stream: StringIO, instruction: QasmQobjInstruction) -> None:
        """ Translates the Toffoli element.

        Args:
            stream: The string-io stream to where the resulting cQASM is written.
            instruction: The Qiskit instruction to translate to cQASM.

        """
        stream.write('Toffoli q[{0}], q[{1}], q[{2}]\n'.format(*instruction.qubits))

    @staticmethod
    def _c_ccx(stream: StringIO, instruction: QasmQobjInstruction, binary_control: str) -> None:
        """ Translates the binary controlled Toffoli element.

        Args:
            stream: The string-io stream to where the resulting cQASM is written.
            instruction: The Qiskit instruction to translate to cQASM.
            binary_control: The multi-bits control string. The gate is executed when all specified classical bits are 1.

        """
        stream.write('C-Toffoli {0}q[{1}], q[{2}], q[{3}]\n'.format(binary_control, *instruction.qubits))

    @staticmethod
    def _h(stream: StringIO, instruction: QasmQobjInstruction) -> None:
        """ Translates the H element.

        Args:
            stream: The string-io stream to where the resulting cQASM is written.
            instruction: The Qiskit instruction to translate to cQASM.

        """
        stream.write('H q[{0}]\n'.format(*instruction.qubits))

    @staticmethod
    def _c_h(stream: StringIO, instruction: QasmQobjInstruction, binary_control: str) -> None:
        """ Translates the binary-controlled H element.

        Args:
            stream: The string-io stream to where the resulting cQASM is written.
            instruction: The Qiskit instruction to translate to cQASM.
            binary_control: The multi-bits control string. The gate is executed when all specified classical bits are 1.

        """
        stream.write('C-H {0}q[{1}]\n'.format(binary_control, *instruction.qubits))

    @staticmethod
    def _id(stream: StringIO, instruction: QasmQobjInstruction) -> None:
        """ Translates the ID element.

        Args:
            stream: The string-io stream to where the resulting cQASM is written.
            instruction: The Qiskit instruction to translate to cQASM.

        """
        stream.write('I q[{0}]\n'.format(*instruction.qubits))

    @staticmethod
    def _c_id(stream: StringIO, instruction: QasmQobjInstruction, binary_control: str) -> None:
        """ Translates the binary-controlled ID element.

        Args:
            stream: The string-io stream to where the resulting cQASM is written.
            instruction: The Qiskit instruction to translate to cQASM.
            binary_control: The multi-bits control string. The gate is executed when all specified classical bits are 1.

        """
        stream.write('C-I {0}q[{1}]\n'.format(binary_control, *instruction.qubits))

    @staticmethod
    def _s(stream: StringIO, instruction: QasmQobjInstruction) -> None:
        """ Translates the S element.

        Args:
            stream: The string-io stream to where the resulting cQASM is written.
            instruction: The Qiskit instruction to translate to cQASM.

        """
        stream.write('S q[{0}]\n'.format(*instruction.qubits))

    @staticmethod
    def _c_s(stream: StringIO, instruction: QasmQobjInstruction, binary_control: str) -> None:
        """ Translates the binary-controlled S element.

        Args:
            stream: The string-io stream to where the resulting cQASM is written.
            instruction: The Qiskit instruction to translate to cQASM.

        """
        stream.write('C-S {0}q[{1}]\n'.format(binary_control, *instruction.qubits))

    @staticmethod
    def _sdg(stream: StringIO, instruction: QasmQobjInstruction) -> None:
        """ Translates the Sdag element.

        Args:
            stream: The string-io stream to where the resulting cQASM is written.
            instruction: The Qiskit instruction to translate to cQASM.

        """
        stream.write('Sdag q[{0}]\n'.format(*instruction.qubits))

    @staticmethod
    def _c_sdg(stream: StringIO, instruction: QasmQobjInstruction, binary_control: str) -> None:
        """ Translates the binary-controlled Sdag element.

        Args:
            stream: The string-io stream to where the resulting cQASM is written.
            instruction: The Qiskit instruction to translate to cQASM.

        """
        stream.write('C-Sdag {0}q[{1}]\n'.format(binary_control, *instruction.qubits))

    @staticmethod
    def _swap(stream: StringIO, instruction: QasmQobjInstruction) -> None:
        """ Translates the SWAP element.

        Args:
            stream: The string-io stream to where the resulting cQASM is written.
            instruction: The Qiskit instruction to translate to cQASM.

        """
        stream.write('SWAP q[{0}], q[{1}]\n'.format(*instruction.qubits))

    @staticmethod
    def _c_swap(stream: StringIO, instruction: QasmQobjInstruction, binary_control: str) -> None:
        """ Translates the binary-controlled SWAP element.

        Args:
            stream: The string-io stream to where the resulting cQASM is written.
            instruction: The Qiskit instruction to translate to cQASM.

        """
        stream.write('C-SWAP {0}q[{1}], q[{2}]\n'.format(binary_control, *instruction.qubits))

    @staticmethod
    def _t(stream: StringIO, instruction: QasmQobjInstruction) -> None:
        """ Translates the T element.

        Args:
            stream: The string-io stream to where the resulting cQASM is written.
            instruction: The Qiskit instruction to translate to cQASM.

        """
        stream.write('T q[{0}]\n'.format(*instruction.qubits))

    @staticmethod
    def _c_t(stream: StringIO, instruction: QasmQobjInstruction, binary_control: str) -> None:
        """ Translates the binary-controlled T element.

        Args:
            stream: The string-io stream to where the resulting cQASM is written.
            instruction: The Qiskit instruction to translate to cQASM.

        """
        stream.write('C-T {0}q[{1}]\n'.format(binary_control, *instruction.qubits))

    @staticmethod
    def _tdg(stream: StringIO, instruction: QasmQobjInstruction) -> None:
        """ Translates the Tdag element.

        Args:
            stream: The string-io stream to where the resulting cQASM is written.
            instruction: The Qiskit instruction to translate to cQASM.

        """
        stream.write('Tdag q[{0}]\n'.format(*instruction.qubits))

    @staticmethod
    def _c_tdg(stream: StringIO, instruction: QasmQobjInstruction, binary_control: str) -> None:
        """ Translates the binary-controlled Tdag element.

        Args:
            stream: The string-io stream to where the resulting cQASM is written.
            instruction: The Qiskit instruction to translate to cQASM.

        """
        stream.write('C-Tdag {0}q[{1}]\n'.format(binary_control, *instruction.qubits))

    @staticmethod
    def _x(stream: StringIO, instruction: QasmQobjInstruction) -> None:
        """ Translates the X element.

        Args:
            stream: The string-io stream to where the resulting cQASM is written.
            instruction: The Qiskit instruction to translate to cQASM.

        """
        stream.write('X q[{0}]\n'.format(*instruction.qubits))

    @staticmethod
    def _c_x(stream: StringIO, instruction: QasmQobjInstruction, binary_control: str) -> None:
        """ Translates the binary-controlled X element.

        Args:
            stream: The string-io stream to where the resulting cQASM is written.
            instruction: The Qiskit instruction to translate to cQASM.

        """
        stream.write('C-X {0}q[{1}]\n'.format(binary_control, *instruction.qubits))

    @staticmethod
    def _y(stream: StringIO, instruction: QasmQobjInstruction) -> None:
        """ Translates the Y element.

        Args:
            stream: The string-io stream to where the resulting cQASM is written.
            instruction: The Qiskit instruction to translate to cQASM.

        """
        stream.write('Y q[{0}]\n'.format(*instruction.qubits))

    @staticmethod
    def _c_y(stream: StringIO, instruction: QasmQobjInstruction, binary_control: str) -> None:
        """ Translates the binary-controlled Y element.

        Args:
            stream: The string-io stream to where the resulting cQASM is written.
            instruction: The Qiskit instruction to translate to cQASM.
            binary_control: The multi-bits control string. The gate is executed when all specified classical bits are 1.

        """
        stream.write('C-Y {0}q[{1}]\n'.format(binary_control, *instruction.qubits))

    @staticmethod
    def _z(stream: StringIO, instruction: QasmQobjInstruction) -> None:
        """ Translates the Z element.

        Args:
            stream: The string-io stream to where the resulting cQASM is written.
            instruction: The Qiskit instruction to translate to cQASM.

        """
        stream.write('Z q[{0}]\n'.format(*instruction.qubits))

    @staticmethod
    def _c_z(stream: StringIO, instruction: QasmQobjInstruction, binary_control: str) -> None:
        """ Translates the binary-controlled Z element.

        Args:
            stream: The string-io stream to where the resulting cQASM is written.
            instruction: The Qiskit instruction to translate to cQASM.
            binary_control: The multi-bits control string. The gate is executed when all specified classical bits are 1.

        """
        stream.write('C-Z {0}q[{1}]\n'.format(binary_control, *instruction.qubits))

    @staticmethod
    def _r(stream: StringIO, instruction: QasmQobjInstruction, axis: str) -> None:
        """ Translates the Rotation element for an axis (x,y,z).

        Args:
            stream: The string-io stream to where the resulting cQASM is written.
            instruction: The Qiskit instruction to translate to cQASM.
            axis: The axis for which the Rotation operator is parsed ('x', 'y' or 'z').

        """
        angle_q0 = instruction.params[0]
        stream.write('R{0} q[{1}], {2:.6f}\n'.format(axis, *instruction.qubits, angle_q0))

    @staticmethod
    def _c_r(stream: StringIO, instruction: QasmQobjInstruction, axis: str, binary_control: str) -> None:
        """ Translates the binary-controlled Rotation element for an axis (x,y,z).

        Args:
            stream: The string-io stream to where the resulting cQASM is written.
            instruction: The Qiskit instruction to translate to cQASM.
            axis: The axis for which the Rotation operator is parsed ('x', 'y' or 'z').
            binary_control: The multi-bits control string. The gate is executed when all specified classical bits are 1.

        """
        angle_q0 = instruction.params[0]
        stream.write('C-R{0} {1}q[{2}], {3:.6f}\n'.format(axis, binary_control, *instruction.qubits, angle_q0))

    @staticmethod
    def _rx(stream: StringIO, instruction: QasmQobjInstruction) -> None:
        """ Translates the Rx element.

        Args:
            stream: The string-io stream to where the resulting cQASM is written.
            instruction: The Qiskit instruction to translate to cQASM.

        """
        CircuitToString._r(stream, instruction, 'x')

    @staticmethod
    def _c_rx(stream: StringIO, instruction: QasmQobjInstruction, binary_control: str) -> None:
        """ Translates the binary-controlled Rx element.

        Args:
            stream: The string-io stream to where the resulting cQASM is written.
            instruction: The Qiskit instruction to translate to cQASM.
            binary_control: The multi-bits control string. The gate is executed when all specified classical bits are 1.

        """
        CircuitToString._c_r(stream, instruction, 'x', binary_control)

    @staticmethod
    def _ry(stream: StringIO, instruction: QasmQobjInstruction) -> None:
        """ Translates the Ry element.

        Args:
            stream: The string-io stream to where the resulting cQASM is written.
            instruction: The Qiskit instruction to translate to cQASM.

        """
        CircuitToString._r(stream, instruction, 'y')

    @staticmethod
    def _c_ry(stream: StringIO, instruction: QasmQobjInstruction, binary_control: str) -> None:
        """ Translates the binary-controlled Ry element.

        Args:
            stream: The string-io stream to where the resulting cQASM is written.
            instruction: The Qiskit instruction to translate to cQASM.
            binary_control: The multi-bits control string. The gate is executed when all specified classical bits are 1.

        """
        CircuitToString._c_r(stream, instruction, 'y', binary_control)

    @staticmethod
    def _rz(stream: StringIO, instruction: QasmQobjInstruction) -> None:
        """ Translates the Rz element.

        Args:
            stream: The string-io stream to where the resulting cQASM is written.
            instruction: The Qiskit instruction to translate to cQASM.

        """
        CircuitToString._r(stream, instruction, 'z')

    @staticmethod
    def _c_rz(stream: StringIO, instruction: QasmQobjInstruction, binary_control: str) -> None:
        """ Translates the binary-controlled Rz element.

        Args:
            stream: The string-io stream to where the resulting cQASM is written.
            instruction: The Qiskit instruction to translate to cQASM.
            binary_control: The multi-bits control string. The gate is executed when all specified classical bits are 1.

        """
        CircuitToString._c_r(stream, instruction, 'z', binary_control)

    @staticmethod
    def _u(stream: StringIO, instruction: QasmQobjInstruction) -> None:
        """ Translates the U element to U3. The u element is used by qiskit for the u_base gate and when a u0-gate
            is used in the circuit but not supported as a basis gate for the backend.

        Args:
            stream: The string-io stream to where the resulting cQASM is written.
            instruction: The Qiskit instruction to translate to cQASM.

        """
        CircuitToString._u3(stream, instruction)

    @staticmethod
    def _c_u(stream: StringIO, instruction: QasmQobjInstruction, binary_control: str) -> None:
        """ Translates the binary-controlled U element to binary-controlled U3.

        Args:
            stream: The string-io stream to where the resulting cQASM is written.
            instruction: The Qiskit instruction to translate to cQASM.
            binary_control: The multi-bits control string. The gate is executed when all specified classical bits are 1.

        """
        CircuitToString._c_u3(stream, instruction, binary_control)

    @staticmethod
    def _u1(stream: StringIO, instruction: QasmQobjInstruction) -> None:
        """ Translates the U1(lambda) element to U3(0, 0, lambda). A copy of the circuit is made to prevent
            side-effects for the caller.

        Args:
            stream: The string-io stream to where the resulting cQASM is written.
            instruction: The Qiskit instruction to translate to cQASM.

        """
        temp_instruction = copy.deepcopy(instruction)
        temp_instruction.params[0:0] = (0, 0)
        temp_instruction.texparams[0:0] = ('0', '0')
        CircuitToString._u3(stream, temp_instruction)

    @staticmethod
    def _c_u1(stream: StringIO, instruction: QasmQobjInstruction, binary_control: str) -> None:
        """ Translates the binary-controlled U1(lambda) element to U3(0, 0, lambda). A copy of the circuit is
        made to prevent side-effects for the caller.

        Args:
            stream: The string-io stream to where the resulting cQASM is written.
            instruction: The Qiskit instruction to translate to cQASM.
            binary_control: The multi-bits control string. The gate is executed when all specified classical bits are 1.

        """
        temp_instruction = copy.deepcopy(instruction)
        temp_instruction.params[0:0] = (0, 0)
        temp_instruction.texparams[0:0] = ('0', '0')
        CircuitToString._c_u3(stream, temp_instruction, binary_control)

    @staticmethod
    def _u2(stream: StringIO, instruction: QasmQobjInstruction) -> None:
        """ Translates the U2(phi, lambda) element to U3(pi/2, phi, lambda). A copy of the circuit is made to prevent
            side-effects for the caller.

        Args:
            stream: The string-io stream to where the resulting cQASM is written.
            instruction: The Qiskit instruction to translate to cQASM.

        """
        temp_instruction = copy.deepcopy(instruction)
        temp_instruction.params.insert(0, np.pi/2)
        temp_instruction.texparams.insert(0, '\\frac{\\pi}{2}')
        CircuitToString._u3(stream, temp_instruction)

    @staticmethod
    def _c_u2(stream: StringIO, instruction: QasmQobjInstruction, binary_control: str) -> None:
        """ Translates the binary-controlled U2(phi, lambda) element to U3(pi/2, phi, lambda). A copy of the
        circuit is made to prevent side-effects for the caller.

        Args:
            stream: The string-io stream to where the resulting cQASM is written.
            instruction: The Qiskit instruction to translate to cQASM.
            binary_control: The multi-bits control string. The gate is executed when all specified classical bits are 1.

        """
        temp_instruction = copy.deepcopy(instruction)
        temp_instruction.params.insert(0, np.pi/2)
        temp_instruction.texparams.insert(0, '\\frac{\\pi}{2}')
        CircuitToString._c_u3(stream, temp_instruction, binary_control)

    @staticmethod
    def _u3(stream: StringIO, instruction: QasmQobjInstruction) -> None:
        """ Translates the U3(theta, phi, lambda) element to 3 rotation gates.
            Any single qubit operation (a 2x2 unitary matrix) can be written as the product of rotations.
            As an example, a unitary single-qubit gate can be expressed as a combination of
            Rz and Ry rotations (Nielsen and Chuang, 10th edition, section 4.2).
            U(theta, phi, lambda) = Rz(phi)Ry(theta)Rz(lambda).
            Note: The expression above is the matrix multiplication, when implementing this in a gate circuit,
            the gates need to be executed in reversed order.
            Any rotation of 0 radials is left out of the resulting circuit.

        Args:
            stream: The string-io stream to where the resulting cQASM is written.
            instruction: The Qiskit instruction to translate to cQASM.

        """
        gates = ['Rz', 'Ry', 'Rz']
        angles = list(instruction.params[i] for i in [2, 0, 1])
        index_q0 = [instruction.qubits[0]] * 3
        for triplet in zip(gates, index_q0, angles):
            if triplet[2] != 0:
                stream.write('{0} q[{1}], {2:.6f}\n'.format(*triplet))

    @staticmethod
    def _c_u3(stream: StringIO, instruction: QasmQobjInstruction, binary_control: str) -> None:
        """ Translates the binary-controlled U3(theta, phi, lambda) element to 3 rotation gates.
            See gate _u3 for more information.

        Args:
            stream: The string-io stream to where the resulting cQASM is written.
            instruction: The Qiskit instruction to translate to cQASM.
            binary_control: The multi-bits control string. The gate is executed when all specified classical bits are 1.

        """
        gates = ['C-Rz', 'C-Ry', 'C-Rz']
        binary_controls = [binary_control] * 3
        angles = list(instruction.params[i] for i in [2, 0, 1])
        index_q0 = [instruction.qubits[0]] * 3
        for quadruplets in zip(gates, binary_controls, index_q0, angles):
            if quadruplets[3] != 0:
                stream.write('{0} {1}q[{2}], {3:.6f}\n'.format(*quadruplets))

    @staticmethod
    def _barrier(stream: StringIO, instruction: QasmQobjInstruction) -> None:
        """ Translates the | element. No cQASM is added for this gate.

        Args:
            stream: The string-io stream to where the resulting cQASM is written.
            instruction: The Qiskit instruction to translate to cQASM.

        """
        pass

    @staticmethod
    def _c_barrier(stream: StringIO, instruction: QasmQobjInstruction, binary_control: str) -> None:
        """ Translates the binary-controlled | element. No cQASM is added for this gate.

        Args:
            stream: The string-io stream to where the resulting cQASM is written.
            instruction: The Qiskit instruction to translate to cQASM.
            binary_control: The multi-bits control string. The gate is executed when all specified classical bits are 1.

        """
        pass

    @staticmethod
    def _measure(stream: StringIO, instruction: QasmQobjInstruction) -> None:
        """ Translates the measure element. No cQASM is added for this gate.

        Args:
            stream: The string-io stream to where the resulting cQASM is written.
            instruction: The Qiskit instruction to translate to cQASM.

        """
        pass

    def _parse_bin_ctrl_gate(self, stream: StringIO, instruction: QasmQobjInstruction) -> None:
        """ Parses a binary controlled gate. A binary controlled gate name is preceded by 'c-'.
            The gate is executed when a specific measurement is true. Multiple measurement outcomes are used
            to control the quantum operation. This measurement is a combination of classical bits being 1 and others
            being 0. Because cQASM only supports measurement outcomes of 1, any other bits in the
            masked bit pattern first have to be inverted with the not-operator. The same inversion also has to
            take place after the binary controlled quantum operation.
            The resulting stream will be expanded with something like:
            not b[the 0-bits changed to 1]
            c-gate [classical bits], other arguments
            not b[the 0-bits reset to 0 again]
            When the c-gate results in an empty string (e.g. binary controlled u(0, 0, 0) or barrier gate),
            nothing is added to the stream.

        Args:
            stream: The string-io stream to where the resulting cQASM is written.
            instruction: The Qiskit instruction to translate to cQASM.

        """
        conditional_type = instruction.conditional.type
        if conditional_type != 'equals':
            raise ApiError('Conditional statement with type {} not supported'.format(conditional_type))
        mask = int(instruction.conditional.mask, 16)
        if mask == 0:
            raise ApiError('Conditional statement {} without a mask'.format(instruction.name.lower()))
        nr_of_classical_bits = int(np.log2(mask + 1))
        val = int(instruction.conditional.val, 16)
        masked_val = mask & val

        # form the negation to the 0-values of the measurement registers, when mask == val no bits are negated
        negate_zeroes_line = ''
        if masked_val != mask:
            negate_zeroes_line = 'not b[' + ','.join(
                str(i) for i in range(nr_of_classical_bits) if not (masked_val & (1 << i))) + ']\n'

        # form multi bits control - qasm-single-gate-multiple-qubits
        binary_control = 'b[0:{}], '.format(nr_of_classical_bits - 1)

        with StringIO() as gate_stream:
            # add the gate
            gate_name = '_c_%s' % instruction.name.lower()
            gate_function = getattr(self, gate_name, getattr(self, "_gate_not_supported"))
            gate_function(gate_stream, instruction, binary_control)
            line = gate_stream.getvalue()
            if len(line) != 0:
                # negate the measurement registers that has to be 0
                stream.write(negate_zeroes_line)
                stream.write(line)
                # reverse the measurement registers that had to be 0
                stream.write(negate_zeroes_line)

    def parse(self, stream: StringIO, instruction: QasmQobjInstruction) -> None:
        """ Parses a gate. For each type of gate a separate (private) parsing method is defined and called.
            The resulting cQASM code is written to the stream. When the gate is a binary controlled
            gate, the parsing is forwarded to method _parse_bin_ctrl_gate. When a gate is not supported
            _gate_not_supported is called which raises an exception.

        Args:
            stream: The string-io stream to where the resulting cQASM is written.
            instruction: The Qiskit instruction to translate to cQASM.
        """
        if hasattr(instruction, 'conditional'):
            self._parse_bin_ctrl_gate(stream, instruction)
        else:
            gate_name = '_%s' % instruction.name.lower()
            gate_function = getattr(self, gate_name, getattr(self, "_gate_not_supported"))
            gate_function(stream, instruction)
