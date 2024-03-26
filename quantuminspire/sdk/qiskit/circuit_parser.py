"""Quantum Inspire SDK.

Copyright 2022 QuTech Delft

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the
License. You may obtain a copy of the License at
https://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import copy
from io import StringIO
from typing import List, Optional, Tuple

from qiskit.qobj import QasmQobjInstruction

from quantuminspire.sdk.qiskit.exceptions import CircuitError
from quantuminspire.sdk.qiskit.measurements import Measurements


class CircuitToString:
    """Contains the translational elements to convert the Qiskit circuits to cQASM code."""

    def __init__(self, basis_gates: List[str], measurements: Measurements, full_state_projection: bool = False) -> None:
        """
        :param basis_gates: List of basis gates from the configuration.
        :param measurements: The measured qubits/classical bits and the number of qubits and classical bits.
        """
        self.basis_gates = basis_gates.copy()
        if len(self.basis_gates) > 0:
            self.basis_gates.append("measure")
        self.bfunc_instructions: List[QasmQobjInstruction] = []
        self.measurements = measurements
        self.full_state_projection = full_state_projection

    @staticmethod
    def _gate_not_supported(
        _stream: StringIO, instruction: QasmQobjInstruction, _binary_control: Optional[str] = None
    ) -> None:
        """Called when a gate is not supported with the backend. Throws an exception (ApiError)

        :param instruction: The Qiskit instruction to translate to cQASM.
        :raises ApiError: the gate is not supported by the circuit parser.
        """
        if hasattr(instruction, "conditional"):
            raise CircuitError(f"Conditional gate 'c-{instruction.name.lower()}' not supported")

        raise CircuitError(f"Gate '{instruction.name.lower()}' not supported")

    @staticmethod
    def _cz(stream: StringIO, instruction: QasmQobjInstruction) -> None:
        """Translates the controlled Z element.

        :param stream: The string-io stream to where the resulting cQASM is written.
        :param instruction: The Qiskit instruction to translate to cQASM.
        """
        stream.write(f"CZ q[{instruction.qubits[0]}], " f"q[{instruction.qubits[1]}]\n")

    @staticmethod
    def _c_cz(stream: StringIO, instruction: QasmQobjInstruction, binary_control: str) -> None:
        """Translates the binary-controlled controlled Z element.

        :param stream: The string-io stream to where the resulting cQASM is written.
        :param instruction: The Qiskit instruction to translate to cQASM.
        :param binary_control: The multi-bits control string. The gate is executed when all specified classical bits
            are 1.
        """
        stream.write(f"C-CZ {binary_control}q[{instruction.qubits[0]}], " f"q[{instruction.qubits[1]}]\n")

    @staticmethod
    def _cx(stream: StringIO, instruction: QasmQobjInstruction) -> None:
        """Translates the controlled X element.

        :param stream: The string-io stream to where the resulting cQASM is written.
        :param instruction: The Qiskit instruction to translate to cQASM.
        """
        stream.write(f"CNOT q[{instruction.qubits[0]}], " f"q[{instruction.qubits[1]}]\n")

    @staticmethod
    def _c_cx(stream: StringIO, instruction: QasmQobjInstruction, binary_control: str) -> None:
        """Translates the binary-controlled controlled X element.

        :param stream: The string-io stream to where the resulting cQASM is written.
        :param instruction: The Qiskit instruction to translate to cQASM.
        :param binary_control: The multi-bits control string. The gate is executed when all specified classical bits
            are 1.
        """
        stream.write(f"C-CNOT {binary_control}q[{instruction.qubits[0]}], " f"q[{instruction.qubits[1]}]\n")

    @staticmethod
    def _ccx(stream: StringIO, instruction: QasmQobjInstruction) -> None:
        """Translates the Toffoli element.

        :param stream: The string-io stream to where the resulting cQASM is written.
        :param instruction: The Qiskit instruction to translate to cQASM.
        """
        stream.write(
            f"Toffoli q[{instruction.qubits[0]}], " f"q[{instruction.qubits[1]}], q[{instruction.qubits[2]}]\n"
        )

    @staticmethod
    def _c_ccx(stream: StringIO, instruction: QasmQobjInstruction, binary_control: str) -> None:
        """Translates the binary controlled Toffoli element.

        :param stream: The string-io stream to where the resulting cQASM is written.
        :param instruction: The Qiskit instruction to translate to cQASM.
        :param binary_control: The multi-bits control string. The gate is executed when all specified classical bits
            are 1.
        """
        stream.write(
            f"C-Toffoli {binary_control}q[{instruction.qubits[0]}], q[{instruction.qubits[1]}], "
            f"q[{instruction.qubits[2]}]\n"
        )

    @staticmethod
    def _h(stream: StringIO, instruction: QasmQobjInstruction) -> None:
        """Translates the H element.

        :param stream: The string-io stream to where the resulting cQASM is written.
        :param instruction: The Qiskit instruction to translate to cQASM.
        """
        stream.write(f"H q[{instruction.qubits[0]}]\n")

    @staticmethod
    def _c_h(stream: StringIO, instruction: QasmQobjInstruction, binary_control: str) -> None:
        """Translates the binary-controlled H element.

        :param stream: The string-io stream to where the resulting cQASM is written.
        :param instruction: The Qiskit instruction to translate to cQASM.
        :param binary_control: The multi-bits control string. The gate is executed when all specified classical bits
            are 1.
        """
        stream.write(f"C-H {binary_control}q[{instruction.qubits[0]}]\n")

    @staticmethod
    def _id(stream: StringIO, instruction: QasmQobjInstruction) -> None:
        """Translates the ID element.

        :param stream: The string-io stream to where the resulting cQASM is written.
        :param instruction: The Qiskit instruction to translate to cQASM.
        """
        stream.write(f"I q[{instruction.qubits[0]}]\n")

    @staticmethod
    def _c_id(stream: StringIO, instruction: QasmQobjInstruction, binary_control: str) -> None:
        """Translates the binary-controlled ID element.

        :param stream: The string-io stream to where the resulting cQASM is written.
        :param instruction: The Qiskit instruction to translate to cQASM.
        :param binary_control: The multi-bits control string. The gate is executed when all specified classical bits
            are 1.
        """
        stream.write(f"C-I {binary_control}q[{instruction.qubits[0]}]\n")

    @staticmethod
    def _s(stream: StringIO, instruction: QasmQobjInstruction) -> None:
        """Translates the S element.

        :param stream: The string-io stream to where the resulting cQASM is written.
        :param instruction: The Qiskit instruction to translate to cQASM.
        """
        stream.write(f"S q[{instruction.qubits[0]}]\n")

    @staticmethod
    def _c_s(stream: StringIO, instruction: QasmQobjInstruction, binary_control: str) -> None:
        """Translates the binary-controlled S element.

        :param stream: The string-io stream to where the resulting cQASM is written.
        :param instruction: The Qiskit instruction to translate to cQASM.
        """
        stream.write(f"C-S {binary_control}q[{instruction.qubits[0]}]\n")

    @staticmethod
    def _sdg(stream: StringIO, instruction: QasmQobjInstruction) -> None:
        """Translates the Sdag element.

        :param stream: The string-io stream to where the resulting cQASM is written.
        :param instruction: The Qiskit instruction to translate to cQASM.
        """
        stream.write(f"Sdag q[{instruction.qubits[0]}]\n")

    @staticmethod
    def _c_sdg(stream: StringIO, instruction: QasmQobjInstruction, binary_control: str) -> None:
        """Translates the binary-controlled Sdag element.

        :param stream: The string-io stream to where the resulting cQASM is written.
        :param instruction: The Qiskit instruction to translate to cQASM.
        """
        stream.write(f"C-Sdag {binary_control}q[{instruction.qubits[0]}]\n")

    @staticmethod
    def _swap(stream: StringIO, instruction: QasmQobjInstruction) -> None:
        """Translates the SWAP element.

        :param stream: The string-io stream to where the resulting cQASM is written.
        :param instruction: The Qiskit instruction to translate to cQASM.
        """
        stream.write(f"SWAP q[{instruction.qubits[0]}], q[{instruction.qubits[1]}]\n")

    @staticmethod
    def _c_swap(stream: StringIO, instruction: QasmQobjInstruction, binary_control: str) -> None:
        """Translates the binary-controlled SWAP element.

        :param stream: The string-io stream to where the resulting cQASM is written.
        :param instruction: The Qiskit instruction to translate to cQASM.
        """
        stream.write(f"C-SWAP {binary_control}q[{instruction.qubits[0]}], " f"q[{instruction.qubits[1]}]\n")

    @staticmethod
    def _t(stream: StringIO, instruction: QasmQobjInstruction) -> None:
        """Translates the T element.

        :param stream: The string-io stream to where the resulting cQASM is written.
        :param instruction: The Qiskit instruction to translate to cQASM.
        """
        stream.write(f"T q[{instruction.qubits[0]}]\n")

    @staticmethod
    def _c_t(stream: StringIO, instruction: QasmQobjInstruction, binary_control: str) -> None:
        """Translates the binary-controlled T element.

        :param stream: The string-io stream to where the resulting cQASM is written.
        :param instruction: The Qiskit instruction to translate to cQASM.
        """
        stream.write(f"C-T {binary_control}q[{instruction.qubits[0]}]\n")

    @staticmethod
    def _tdg(stream: StringIO, instruction: QasmQobjInstruction) -> None:
        """Translates the Tdag element.

        :param stream: The string-io stream to where the resulting cQASM is written.
        :param instruction: The Qiskit instruction to translate to cQASM.
        """
        stream.write(f"Tdag q[{instruction.qubits[0]}]\n")

    @staticmethod
    def _c_tdg(stream: StringIO, instruction: QasmQobjInstruction, binary_control: str) -> None:
        """Translates the binary-controlled Tdag element.

        :param stream: The string-io stream to where the resulting cQASM is written.
        :param instruction: The Qiskit instruction to translate to cQASM.
        """
        stream.write(f"C-Tdag {binary_control}q[{instruction.qubits[0]}]\n")

    @staticmethod
    def _x(stream: StringIO, instruction: QasmQobjInstruction) -> None:
        """Translates the X element.

        :param stream: The string-io stream to where the resulting cQASM is written.
        :param instruction: The Qiskit instruction to translate to cQASM.
        """
        stream.write(f"X q[{instruction.qubits[0]}]\n")

    @staticmethod
    def _c_x(stream: StringIO, instruction: QasmQobjInstruction, binary_control: str) -> None:
        """Translates the binary-controlled X element.

        :param stream: The string-io stream to where the resulting cQASM is written.
        :param instruction: The Qiskit instruction to translate to cQASM.
        """
        stream.write(f"C-X {binary_control}q[{instruction.qubits[0]}]\n")

    @staticmethod
    def _y(stream: StringIO, instruction: QasmQobjInstruction) -> None:
        """Translates the Y element.

        :param stream: The string-io stream to where the resulting cQASM is written.
        :param instruction: The Qiskit instruction to translate to cQASM.
        """
        stream.write(f"Y q[{instruction.qubits[0]}]\n")

    @staticmethod
    def _c_y(stream: StringIO, instruction: QasmQobjInstruction, binary_control: str) -> None:
        """Translates the binary-controlled Y element.

        :param stream: The string-io stream to where the resulting cQASM is written.
        :param instruction: The Qiskit instruction to translate to cQASM.
        :param binary_control: The multi-bits control string. The gate is executed when all specified classical bits
            are 1.
        """
        stream.write(f"C-Y {binary_control}q[{instruction.qubits[0]}]\n")

    @staticmethod
    def _z(stream: StringIO, instruction: QasmQobjInstruction) -> None:
        """Translates the Z element.

        :param stream: The string-io stream to where the resulting cQASM is written.
        :param instruction: The Qiskit instruction to translate to cQASM.
        """
        stream.write(f"Z q[{instruction.qubits[0]}]\n")

    @staticmethod
    def _c_z(stream: StringIO, instruction: QasmQobjInstruction, binary_control: str) -> None:
        """Translates the binary-controlled Z element.

        :param stream: The string-io stream to where the resulting cQASM is written.
        :param instruction: The Qiskit instruction to translate to cQASM.
        :param binary_control: The multi-bits control string. The gate is executed when all specified classical bits
            are 1.
        """
        stream.write(f"C-Z {binary_control}q[{instruction.qubits[0]}]\n")

    @staticmethod
    def _r(stream: StringIO, instruction: QasmQobjInstruction, axis: str) -> None:
        """Translates the Rotation element for an axis (x,y,z).

        :param stream: The string-io stream to where the resulting cQASM is written.
        :param instruction: The Qiskit instruction to translate to cQASM.
        :param axis: The axis for which the Rotation operator is parsed ('x', 'y' or 'z').
        """
        angle_q0 = float(instruction.params[0])
        stream.write(f"R{axis} q[{instruction.qubits[0]}], {angle_q0:.6f}\n")

    @staticmethod
    def _c_r(stream: StringIO, instruction: QasmQobjInstruction, axis: str, binary_control: str) -> None:
        """Translates the binary-controlled Rotation element for an axis (x,y,z).

        :param stream: The string-io stream to where the resulting cQASM is written.
        :param instruction: The Qiskit instruction to translate to cQASM.
        :param axis: The axis for which the Rotation operator is parsed ('x', 'y' or 'z').
        :param binary_control: The multi-bits control string. The gate is executed when all specified classical bits
            are 1.
        """
        angle_q0 = float(instruction.params[0])
        stream.write(f"C-R{axis} {binary_control}q[{instruction.qubits[0]}], {angle_q0:.6f}\n")

    @staticmethod
    def _rx(stream: StringIO, instruction: QasmQobjInstruction) -> None:
        """Translates the Rx element.

        :param stream: The string-io stream to where the resulting cQASM is written.
        :param instruction: The Qiskit instruction to translate to cQASM.
        """
        CircuitToString._r(stream, instruction, "x")

    @staticmethod
    def _c_rx(stream: StringIO, instruction: QasmQobjInstruction, binary_control: str) -> None:
        """Translates the binary-controlled Rx element.

        :param stream: The string-io stream to where the resulting cQASM is written.
        :param instruction: The Qiskit instruction to translate to cQASM.
        :param binary_control: The multi-bits control string. The gate is executed when all specified classical bits
            are 1.
        """
        CircuitToString._c_r(stream, instruction, "x", binary_control)

    @staticmethod
    def _ry(stream: StringIO, instruction: QasmQobjInstruction) -> None:
        """Translates the Ry element.

        :param stream: The string-io stream to where the resulting cQASM is written.
        :param instruction: The Qiskit instruction to translate to cQASM.
        """
        CircuitToString._r(stream, instruction, "y")

    @staticmethod
    def _c_ry(stream: StringIO, instruction: QasmQobjInstruction, binary_control: str) -> None:
        """Translates the binary-controlled Ry element.

        :param stream: The string-io stream to where the resulting cQASM is written.
        :param instruction: The Qiskit instruction to translate to cQASM.
        :param binary_control: The multi-bits control string. The gate is executed when all specified classical bits
            are 1.
        """
        CircuitToString._c_r(stream, instruction, "y", binary_control)

    @staticmethod
    def _rz(stream: StringIO, instruction: QasmQobjInstruction) -> None:
        """Translates the Rz element.

        :param stream: The string-io stream to where the resulting cQASM is written.
        :param instruction: The Qiskit instruction to translate to cQASM.
        """
        CircuitToString._r(stream, instruction, "z")

    @staticmethod
    def _c_rz(stream: StringIO, instruction: QasmQobjInstruction, binary_control: str) -> None:
        """Translates the binary-controlled Rz element.

        :param stream: The string-io stream to where the resulting cQASM is written.
        :param instruction: The Qiskit instruction to translate to cQASM.
        :param binary_control: The multi-bits control string. The gate is executed when all specified classical bits
            are 1.
        """
        CircuitToString._c_r(stream, instruction, "z", binary_control)

    @staticmethod
    def _u(stream: StringIO, instruction: QasmQobjInstruction) -> None:
        """Translates the U element to U3.

        The u element is used by Qiskit for the u_base gate and when a u0-gate is used in the circuit but not supported
        as a basis gate for the backend.

        :param stream: The string-io stream to where the resulting cQASM is written.
        :param instruction: The Qiskit instruction to translate to cQASM.
        """
        CircuitToString._u3(stream, instruction)

    @staticmethod
    def _c_u(stream: StringIO, instruction: QasmQobjInstruction, binary_control: str) -> None:
        """Translates the binary-controlled U element to binary-controlled U3.

        :param stream: The string-io stream to where the resulting cQASM is written.
        :param instruction: The Qiskit instruction to translate to cQASM.
        :param binary_control: The multi-bits control string. The gate is executed when all specified classical bits
            are 1.
        """
        CircuitToString._c_u3(stream, instruction, binary_control)

    @staticmethod
    def _u1(stream: StringIO, instruction: QasmQobjInstruction) -> None:
        """Translates the U1(lambda) element to U3(0, 0, lambda).

        A copy of the circuit is made to prevent side effects for the caller.

        :param stream: The string-io stream to where the resulting cQASM is written.
        :param instruction: The Qiskit instruction to translate to cQASM.
        """
        temp_instruction = copy.deepcopy(instruction)
        temp_instruction.params[0:0] = (0, 0)
        CircuitToString._u3(stream, temp_instruction)

    @staticmethod
    def _c_u1(stream: StringIO, instruction: QasmQobjInstruction, binary_control: str) -> None:
        """Translates the binary-controlled U1(lambda) element to U3(0, 0, lambda).

        A copy of the circuit is made to prevent side effects for the caller.

        :param stream: The string-io stream to where the resulting cQASM is written.
        :param instruction: The Qiskit instruction to translate to cQASM.
        :param binary_control: The multi-bits control string. The gate is executed when all specified classical bits
            are 1.
        """
        temp_instruction = copy.deepcopy(instruction)
        temp_instruction.params[0:0] = (0, 0)
        CircuitToString._c_u3(stream, temp_instruction, binary_control)

    @staticmethod
    def _p(stream: StringIO, instruction: QasmQobjInstruction) -> None:
        """Translates the p element to u1.

        :param stream: The string-io stream to where the resulting cQASM is written.
        :param instruction: The Qiskit instruction to translate to cQASM.
        """
        CircuitToString._u1(stream, instruction)

    @staticmethod
    def _c_p(stream: StringIO, instruction: QasmQobjInstruction, binary_control: str) -> None:
        """Translates the c-p element to c-u1.

        :param stream: The string-io stream to where the resulting cQASM is written.
        :param instruction: The Qiskit instruction to translate to cQASM.
        :param binary_control: The multi-bits control string. The gate is executed when all specified classical bits
            are 1.
        """
        CircuitToString._c_u1(stream, instruction, binary_control)

    @staticmethod
    def _u3(stream: StringIO, instruction: QasmQobjInstruction) -> None:
        """Translates the U3(theta, phi, lambda) element to 3 rotation gates.

        Any single qubit operation (a 2x2 unitary matrix) can be written as the product of rotations.
        As an example, a unitary single-qubit gate can be expressed as a combination of
        Rz and Ry rotations (Nielsen and Chuang, 10th edition, section 4.2).
        U(theta, phi, lambda) = Rz(phi)Ry(theta)Rz(lambda).
        Note: The expression above is the matrix multiplication, when implementing this in a gate circuit,
        the gates need to be executed in reversed order.
        Any rotation of 0 radials is left out of the resulting circuit.

        :param stream: The string-io stream to where the resulting cQASM is written.
        :param instruction: The Qiskit instruction to translate to cQASM.
        """
        gates = ["Rz", "Ry", "Rz"]
        angles = list(float(instruction.params[i]) for i in [2, 0, 1])
        index_q0 = [instruction.qubits[0]] * 3
        for triplet in zip(gates, index_q0, angles):
            if triplet[2] != 0:
                stream.write(f"{triplet[0]} q[{triplet[1]}], {triplet[2]:.6f}\n")

    @staticmethod
    def _c_u3(stream: StringIO, instruction: QasmQobjInstruction, binary_control: str) -> None:
        """Translates the binary-controlled U3(theta, phi, lambda) element to 3 rotation gates.

        See gate :meth:`~._u3` for more information.

        :param stream: The string-io stream to where the resulting cQASM is written.
        :param instruction: The Qiskit instruction to translate to cQASM.
        :param binary_control: The multi-bits control string. The gate is executed when all specified classical bits
        are 1.
        """
        gates = ["C-Rz", "C-Ry", "C-Rz"]
        binary_controls = [binary_control] * 3
        angles = list(float(instruction.params[i]) for i in [2, 0, 1])
        index_q0 = [instruction.qubits[0]] * 3
        for quadruplets in zip(gates, binary_controls, index_q0, angles):
            if quadruplets[3] != 0:
                stream.write(f"{quadruplets[0]} {quadruplets[1]}q[{quadruplets[2]}], {quadruplets[3]:.6f}\n")

    @staticmethod
    def _barrier(stream: StringIO, instruction: QasmQobjInstruction) -> None:
        """Translates the | element for a variable number of qubits.

        :param stream: The string-io stream to where the resulting cQASM is written.
        :param instruction: The Qiskit instruction to translate to cQASM.
        """
        stream.write(f"barrier q[{','.join(map(str, instruction.qubits))}]\n")

    @staticmethod
    def _c_barrier(stream: StringIO, instruction: QasmQobjInstruction, binary_control: str) -> None:
        """Translates the binary-controlled | element. No cQASM is added for this gate.

        :param stream: The string-io stream to where the resulting cQASM is written.
        :param instruction: The Qiskit instruction to translate to cQASM.
        :param binary_control: The multi-bits control string. The gate is executed when all specified classical bits
            are 1.
        """

    def _reset(self, stream: StringIO, instruction: QasmQobjInstruction) -> None:
        """Translates the reset element.

        :param stream: The string-io stream to where the resulting cQASM is written.
        :param instruction: The Qiskit instruction to translate to cQASM.
        """
        stream.write(f"prep_z q[{instruction.qubits[0]}]\n")

    @staticmethod
    def _delay(stream: StringIO, instruction: QasmQobjInstruction) -> None:
        """Translates the delay element for a qubit. In cQASM wait parameter is int and the unit is hardware cycles.
        Only the Qiskit default unit "dt" will work correctly with cQASM, i.e. integer time unit depending on the
        target backend.

        In qiskit/circuit/delay.py multiple units are defined for delay instruction. In qiskit/circuit/instruction.py
        assemble() method the unit of the delay instruction is not passed. Only the parameter (which is the value of
        the delay instruction) is taken. Here we cannot convert delays originally in another unit than dt to dt, which
        is the unit for wait in cQASM.

        :param stream: The string-io stream to where the resulting cQASM is written.
        :param instruction: The Qiskit instruction to translate to cQASM.
        """
        wait_period = int(instruction.params[0])
        stream.write(f"wait q[{instruction.qubits[0]}], {wait_period}\n")

    def _measure(self, stream: StringIO, instruction: QasmQobjInstruction) -> None:
        """Translates the measure element. No cQASM is added for this gate when FSP is used.

        :param stream: The string-io stream to where the resulting cQASM is written.
        :param instruction: The Qiskit instruction to translate to cQASM.
        """
        if not self.full_state_projection:
            stream.write(f"measure q[{instruction.qubits[0]}]\n")

    @staticmethod
    def get_mask_data(mask: int) -> Tuple[int, int]:
        """Get mask data.

        A mask is a continuous set of 1-bits with a certain length. This method returns the lowest bit of
        the mask and the length of the mask.

        Examples:

        ============ ====================================
        ``76543210`` bit_nr
        ============ ====================================
        ``00111000`` lowest mask bit = 3, mask_length = 3
        ``00000001`` lowest mask bit = 0, mask_length = 1
        ``11111111`` lowest mask bit = 0, mask_length = 8
        ``10000000`` lowest mask bit = 7, mask_length = 1
        ============ ====================================

        :param mask: The mask to get the mask data from.

        :return: The mask data, i.e. a tuple (lowest_bit_number, mask_length)
        """
        # Precondition: mask != 0
        if mask == 0:
            return -1, 0
        mask_length = 0
        bit_value = 1
        bit_nr = 0
        while not mask & bit_value:
            bit_value <<= 1
            bit_nr += 1
        lowest_mask_bit = bit_nr
        while mask & bit_value:
            mask_length += 1
            bit_value <<= 1
        return lowest_mask_bit, mask_length

    def _parse_bin_ctrl_gate(  # pylint: disable=too-many-locals
        self, stream: StringIO, instruction: QasmQobjInstruction
    ) -> None:
        """Parses a binary controlled gate.

        A binary controlled gate name is preceded by 'c-'.
        The gate is executed when a specific measurement is true. Multiple measurement outcomes are used
        to control the quantum operation. This measurement is a combination of classical bits being 1 and others
        being 0. Because cQASM only supports measurement outcomes of 1, any other bits in the
        masked bit pattern first have to be inverted with the not-operator. The same inversion also has to
        take place after the binary controlled quantum operation.
        The mask can be one or more bits and start at any bit depending on the instruction and the declaration
        of classical bits.
        The resulting stream will be expanded with something like:
        not b[the 0-bits in the value relative to the mask changed to 1]
        c-gate [classical bits in the mask], other arguments
        not b[the 0-bits reset to 0 again]
        When the c-gate results in an empty string (e.g. binary controlled u(0, 0, 0) or barrier gate),
        nothing is added to the stream.

        :param stream: The string-io stream to where the resulting cQASM is written.
        :param instruction: The Qiskit instruction to translate to cQASM.
        """
        conditional_reg_idx = instruction.conditional
        conditional = next((x for x in self.bfunc_instructions if x.register == conditional_reg_idx), None)
        if conditional is None:
            raise CircuitError(f"Conditional not found: reg_idx = {conditional_reg_idx}")
        self.bfunc_instructions.remove(conditional)

        conditional_type = conditional.relation
        if conditional_type != "==":
            raise CircuitError(f"Conditional statement with relation {conditional_type} not supported")
        mask = int(conditional.mask, 16)
        if mask == 0:
            raise CircuitError(f"Conditional statement {instruction.name.lower()} without a mask")
        lowest_mask_bit, mask_length = self.get_mask_data(mask)
        val = int(conditional.val, 16)
        masked_val = mask & val

        # form the negation to the 0-values of the measurement registers, when value == mask no bits are negated
        negate_zeroes_line = ""
        if masked_val != mask:
            negate_zeroes_line = (
                "not b["
                + ",".join(
                    str(self.measurements.get_qreg_for_conditional_creg(i))
                    for i in range(lowest_mask_bit, lowest_mask_bit + mask_length)
                    if not (masked_val & (1 << i))
                )
                + "]\n"
            )

        if mask_length == 1:
            binary_control = f"b[{self.measurements.get_qreg_for_conditional_creg(lowest_mask_bit)}], "
        else:
            # form multi bits control - qasm-single-gate-multiple-qubits
            binary_control = (
                "b["
                + ",".join(
                    str(self.measurements.get_qreg_for_conditional_creg(i))
                    for i in range(lowest_mask_bit, lowest_mask_bit + mask_length)
                )
                + "], "
            )

        with StringIO() as gate_stream:
            # add the gate
            gate_name = f"_c_{instruction.name.lower()}"
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
        """Parses a gate.

        For each type of gate a separate (private) parsing method is defined and called. The resulting cQASM code is
        written to the stream. When the gate is a binary controlled gate, Qiskit uses two instructions to handle it.
        The first instruction is a so-called bfunc with the conditional information (mask, value to check etc.) which
        is stored for later use. The next instruction is the actual gate which must be executed conditionally. The
        parsing is forwarded to method _parse_bin_ctrl_gate which reads the earlier stored bfunc. When a gate is not
        supported _gate_not_supported is called which raises an exception.

        :param stream: The string-io stream to where the resulting cQASM is written.
        :param instruction: The Qiskit instruction to translate to cQASM.
        """
        if instruction.name == "bfunc":
            self.bfunc_instructions.append(instruction)
        elif len(self.basis_gates) > 0 and instruction.name.lower() not in self.basis_gates:
            self._gate_not_supported(stream, instruction)
        elif hasattr(instruction, "conditional"):
            self._parse_bin_ctrl_gate(stream, instruction)
        else:
            gate_name = f"_{instruction.name.lower()}"
            gate_function = getattr(self, gate_name, getattr(self, "_gate_not_supported"))
            gate_function(stream, instruction)
