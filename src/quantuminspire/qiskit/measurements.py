# Quantum Inspire SDK
#
# Copyright 2022 QuTech Delft
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

from typing import Any, Dict, List

from qiskit.qobj import QasmQobjExperiment
from quantuminspire.exceptions import QiskitBackendError


class Measurements:
    def __init__(self) -> None:
        """
        The Measurements class registers measurements and the translations of measurements of qubits to classical
        registers.
        _measurements_reg and _measurements_state are list of lists, for each measurement the lists contains
        a list of [qubit_index, classical_bit_index], which represents the measurement of a qubit to a
        classical bit.
        _measurements_reg contains the bit indices of the qubit and classical bit as used in the algorithm
        _measurements_state contains the positional indexes in the resulting qubit_state and classical_state arrays
        """
        self._number_of_qubits = 0
        self._number_of_clbits = 0
        self._measurements_reg: List[List[int]] = []
        self._measurements_state: List[List[int]] = []

    @property
    def nr_of_qubits(self) -> int:
        """
        :return: Return number of qubits in the algorithm
        """
        return self._number_of_qubits

    @nr_of_qubits.setter
    def nr_of_qubits(self, nr_of_qubits: int) -> None:
        """
        Setter for _number_of_qubits
        """
        self._number_of_qubits = nr_of_qubits

    @property
    def nr_of_clbits(self) -> int:
        """
        :return: Return number of classical bits in the algorithm
        """
        return self._number_of_clbits

    @nr_of_clbits.setter
    def nr_of_clbits(self, nr_of_clbits: int) -> None:
        """
        Setter for _number_of_clbits
        """
        self._number_of_clbits = nr_of_clbits

    @property
    def measurements_reg(self) -> List[List[int]]:
        """
        :return: Return the bit indices of the qubit and classical bit as used in the algorithm
        """
        return self._measurements_reg

    @measurements_reg.setter
    def measurements_reg(self, measurements_reg: List[List[int]]) -> None:
        """
        Setter for _measurements_reg
        """
        self._measurements_reg = measurements_reg

    @property
    def measurements_state(self) -> List[List[int]]:
        """
        :return: Return the positional indexes in the resulting qubit_state and classical_state arrays
        """
        return self._measurements_state

    @measurements_state.setter
    def measurements_state(self, measurements_state: List[List[int]]) -> None:
        """
        Setter for _measurements_state
        """
        self._measurements_state = measurements_state

    @classmethod
    def from_experiment(cls, experiment: QasmQobjExperiment) -> Measurements:
        """ Determines the measured qubits and classical bits for an experiment.

        The full-state measured qubits is returned when no measurements are present in the compiled circuit.

        .. code::

            q = QuantumRegister(3)
            c = ClassicalRegister(3)
            circuit = QuantumCircuit(q, c)

            circuit.measure(2, 0)

        for this measurement [2, 0] is added to the list _measurements_reg
        for this measurement [0, 2] is added to the list _measurements_state, qubit 2 is located at position 0
        in the resulting state array and can be indexed with [0]. classical 0 is located at position 2
        in the resulting state array and can be indexed with [2].

        :param experiment: The experiment with gate operations and header.

        :return: Instance of Measurements with collected measurements from experiment
        """
        instance = cls()
        header = experiment.header
        instance.nr_of_qubits = header.n_qubits
        instance.nr_of_clbits = header.memory_slots

        for instruction in experiment.instructions:
            if instruction.name == 'measure':
                instance.measurements_reg.append([instruction.qubits[0], instruction.memory[0]])
                instance.measurements_state.append([instance.nr_of_qubits - 1 - instruction.qubits[0],
                                                    instance.nr_of_clbits - 1 - instruction.memory[0]])

        if not instance.measurements_reg:
            instance.measurements_reg = [[index, index] for index in range(instance.nr_of_qubits)]
            instance.measurements_state = instance.measurements_reg

        # do some validations
        instance.validate_number_of_clbits()

        return instance

    @property
    def max_measurement_index(self) -> int:
        """
        :return: Return the highest classical bit that is used as a storage for a qubit measurement
        """
        return max(measurement[1] for measurement in self._measurements_reg)

    def get_qreg_for_conditional_creg(self, creg: int) -> int:
        """
        This method returns the qubit register that was measured to be stored in the classical register given

            1. Try to find a measurement where the classical bit creg is used as storage -> return the qubit index of
            this measurement.
            2. When no measurement is found for this classical bit, we assume the equivalent qubit (same index) is used
            First check if a measurement is found for this qubit to another classical register, we raise an error.
            This situation is not supported.

        :param creg: The classical register.

        :return: Returns the qubit index for the qubit that is measured to the classical register creg
        """
        for q1, c1 in self._measurements_reg:
            if c1 == creg:
                return q1

        for q1, c1 in self._measurements_reg:
            if q1 == creg:
                raise QiskitBackendError(f"Classical bit {creg} used in a conditional gate is not measured "
                                         f"and the equivalent qubit {q1} is measured to another classical bit {c1}")

        return creg

    def to_dict(self) -> Dict[str, Any]:
        """
        Translate the class instance to a (minimal) dictionary used for interpreting the results from the backend

        :return:
            Dict containing the measurement list with positional indexes in the resulting qubit_state and
            classical_state and the number of classical bits.
        """
        return {'measurements_state': self._measurements_state,
                'measurements_reg': self._measurements_reg,
                'number_of_qubits': self._number_of_qubits,
                'number_of_clbits': self._number_of_clbits}

    @classmethod
    def from_dict(cls, measurement_input: Dict[str, Any]) -> Measurements:
        """
        Translate the input dictionary to an instance of class Measurements

        :param measurement_input: A dictionary with the measurement information. See method to_dict

        :return: Instance of Measurements with input from dictionary
        """
        instance = cls()
        instance.measurements_state = measurement_input['measurements_state']
        instance.measurements_reg = measurement_input['measurements_reg']
        instance.nr_of_qubits = measurement_input['number_of_qubits']
        instance.nr_of_clbits = measurement_input['number_of_clbits']

        return instance

    def validate_number_of_clbits(self) -> None:
        """ Validate the (number of) classical bits used in the measurements are valid for the algorithm

        Checks whether the number of classical bits has a value cQASM can support.

        1.  When number of classical bits is less than 1 an error is raised.
        2.  When a classical bit is used in a  measurement with an index higher than the number of classical bits an
            error is raised.
        """
        if self._number_of_clbits < 1:
            raise QiskitBackendError(f"Invalid number of classical bits ({self._number_of_clbits})!")

        if self.max_measurement_index >= self._number_of_clbits:
            raise QiskitBackendError(f"Number of classical bits ({self._number_of_clbits}) is not sufficient for "
                                     f"storing the outcomes of the experiment")

    def validate_unsupported_measurements(self) -> None:
        """ Validate unsupported measurements (for not full state projection algorithms)

        Certain measurements cannot be handled correctly because cQASM isn't as flexible as Qiskit in measuring to
        specific classical bits. Therefore some Qiskit constructions are not supported in QI:

            1. When a quantum register is measured to different classical registers
            2. When a classical register is used for the measurement of more than one quantum register

        :raises QiskitBackendError: When the circuit contains an invalid measurement
        """
        for q1, c1 in self._measurements_reg:
            for q2, c2 in self._measurements_reg:
                if q1 == q2 and c1 != c2:
                    raise QiskitBackendError(f'Measurement of qubit {q1} to different classical registers is not '
                                             f'supported')
                if q1 != q2 and c1 == c2:
                    raise QiskitBackendError(f'Measurement of different qubits to the same classical register {c1} '
                                             f'is not supported')

    def qubit_to_classical_hex(self, qubit_register: str) -> str:
        """ This function converts the qubit register data to the hexadecimal representation of the classical state.

        :param qubit_register: The measured value of the qubits represented as int.

        :return:
            The hexadecimal value of the classical state.
        """
        qubit_state = ('{0:0{1}b}'.format(int(qubit_register), self.nr_of_qubits))
        classical_state = ['0'] * self.nr_of_clbits
        for q, c in self._measurements_state:
            classical_state[c] = qubit_state[q]
        classical_state_str = ''.join(classical_state)
        classical_state_hex = hex(int(classical_state_str, 2))
        return classical_state_hex
