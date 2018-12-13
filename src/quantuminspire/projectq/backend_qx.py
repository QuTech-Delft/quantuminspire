""" Quantum Inspire SDK

This file contains code modified from https://github.com/ProjectQ-Framework/ProjectQ in the QIBackend class.
The ProjectQ code is under the Apache License 2.0.


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

import random
from collections import defaultdict
from functools import reduce

from projectq.cengines import BasicEngine
from projectq.meta import LogicalQubitIDTag, get_control_count
from projectq.ops import (NOT, Allocate, Barrier, Deallocate, FlushGate, H,
                          Measure, Ph, Rx, Ry, Rz, S, Sdag, Swap, T, Tdag, X,
                          Y, Z)

from quantuminspire.exceptions import ProjectQBackendError


class QIBackend(BasicEngine):
    """ Backend for Quantum Inspire

    """

    def __init__(self, num_runs=1024, verbose=0, quantum_inspire_api=None,
                 backend_type=None):
        """
        Initialize the Backend object.

        Args:
            num_runs (int): Number of runs to collect statistics.
                (default is 1024)
            verbose (int): Verbosity level
            quantum_inspire_api (QuantumInspireAPI or None): connection to QI platform
            backend_type (dict or str or None): Backend to use for execution.
        """
        BasicEngine.__init__(self)
        self._reset()
        self._num_runs = num_runs
        self._verbose = verbose
        self._cqasm = str()
        self._measured_states = {}
        self.quantum_inspire_api = quantum_inspire_api
        self.backend_type = backend_type

    def cqasm(self):
        """ Return cqasm code that as generated last """
        return self._cqasm

    def is_available(self, cmd):
        """
        Return true if the command can be executed.

        Args:
            cmd (Command): Command for which to check availability
        """
        count = get_control_count(cmd)
        g = cmd.gate
        if self._verbose:
            print('call to is_available with cmd %s (gate %s)' % (cmd, g))
        if g == NOT and count <= 2:
            return True
        if g == Z and count <= 1:
            return True
        if g in (Measure, Allocate, Deallocate, Barrier):
            return True
        if count != 0:
            return False
        if g in (T, Tdag, S, Sdag, H, X, Y, Z):
            return True
        elif isinstance(g, (Rx, Ry, Rz)):
            return True
        elif isinstance(g, Ph):
            return False
        else:
            return False

    def _reset(self):
        """ Reset all temporary variables (after flush gate). """
        self._allocated_qubits = set()
        self._max_qubit_id = -1
        self._clear = True
        self.qasm = ""

    def _store(self, cmd):
        """
        Temporarily store the command cmd.

        Translates the command and stores it in a local variable (self._cmds).

        Args:
            cmd: Command to store
        """
        if self._verbose >= 2:
            print('_store {0}: cmd {1}'.format(id(self), cmd))
            print('   _allocated_qubits {0}'.format(self._allocated_qubits))

        if self._clear:
            self._measured_states = {}
            self._clear = False
            self.qasm = ""
            self._measured_ids = []
            self._allocated_qubits = set()

        gate = cmd.gate

        self._gate = gate
        if gate == Allocate:
            self._allocated_qubits.add(cmd.qubits[0][0].id)
            self._max_qubit_id = max(self._max_qubit_id, cmd.qubits[0][0].id)
            if self._verbose >= 2:
                print('_store: Allocate gate {0}'.format((cmd.qubits[0][0].id,)))
            return

        if gate == Deallocate:
            if self._verbose >= 2:
                print('_store: Deallocate gate {0}'.format((gate,)))
            index_to_remove = cmd.qubits[0][0].id
            self._allocated_qubits.discard(index_to_remove)
            return

        if gate == Measure:
            assert len(cmd.qubits) == 1 and len(cmd.qubits[0]) == 1
            logical_id = None
            for t in cmd.tags:
                if isinstance(t, LogicalQubitIDTag):
                    logical_id = t.logical_qubit_id
                    break
            assert logical_id is not None
            self._measured_ids += [logical_id]
        elif gate == NOT and get_control_count(cmd) == 1:
            # this case also covers the CX controlled gate
            ctrl_pos = cmd.control_qubits[0].id
            qb_pos = cmd.qubits[0][0].id
            self.qasm += "\nCNOT q[{}], q[{}]".format(ctrl_pos, qb_pos)
        elif gate == Swap:
            q0 = cmd.qubits[0][0].id
            q1 = cmd.qubits[1][0].id
            self.qasm += "\nswap q[{}], q[{}]".format(q0, q1)
        elif gate == X and get_control_count(cmd) == 2:
            ctrl_pos1 = cmd.control_qubits[0].id
            ctrl_pos2 = cmd.control_qubits[1].id
            qb_pos = cmd.qubits[0][0].id
            self.qasm += "\nToffoli q[{}], q[{}], q[{}]".format(ctrl_pos1, ctrl_pos2, qb_pos)
        elif gate == Z and get_control_count(cmd) == 1:
            ctrl_pos = cmd.control_qubits[0].id
            qb_pos = cmd.qubits[0][0].id
            self.qasm += "\nCZ q[{}], q[{}]".format(ctrl_pos, qb_pos)
        elif gate == Barrier:
            qb_pos = [qb.id for qr in cmd.qubits for qb in qr]
            self.qasm += "\n# barrier gate "
            qb_str = ""
            for pos in qb_pos:
                qb_str += "q[{}], ".format(pos)
            self.qasm += qb_str[:-2] + ";"
        elif isinstance(gate, Rz) and get_control_count(cmd) == 1:
            ctrl_pos = cmd.control_qubits[0].id
            qb_pos = cmd.qubits[0][0].id
            gatename = 'CR'
            self.qasm += "\n{} q[{}],q[{}],{:.12f}".format(gatename, ctrl_pos, qb_pos, gate.angle)
        elif isinstance(gate, (Rx, Ry)) and get_control_count(cmd) == 1:
            raise NotImplementedError('controlled Rx or Ry gate not implemented')
        elif isinstance(gate, (Rx, Ry, Rz)):
            assert get_control_count(cmd) == 0
            qb_pos = cmd.qubits[0][0].id
            gatename = str(gate)[0:2]
            self.qasm += "\n{} q[{}],{:.12g}".format(gatename, qb_pos, gate.angle)
        elif gate == Tdag and get_control_count(cmd) == 0:
            qb_pos = cmd.qubits[0][0].id
            self.qasm += "\nTdag q[{}]".format(qb_pos)
        elif isinstance(gate, tuple(type(gate) for gate in (X, Y, Z, H, S, Sdag, T, Tdag))):
            assert get_control_count(cmd) == 0
            if str(gate) in self._gate_names:
                gate_str = self._gate_names[str(gate)]
            else:
                gate_str = str(gate).lower()

            qb_pos = cmd.qubits[0][0].id
            self.qasm += "\n{} q[{}]".format(gate_str, qb_pos)
        else:
            raise NotImplementedError('cmd {0} not implemented'.format((cmd,)))

    def _logical_to_physical(self, qb_id):
        """
        Return the physical location of the qubit with the given logical id.

        Args:
            qb_id (int): ID of the logical qubit whose position should be
                returned.
        """
        assert self.main_engine.mapper is not None
        mapping = self.main_engine.mapper.current_mapping
        if qb_id not in mapping:
            raise RuntimeError("Unknown qubit id {}. Please make sure "
                               "eng.flush() was called and that the qubit "
                               "was eliminated during optimization."
                               .format(qb_id))
        return mapping[qb_id]

    def get_probabilities(self, qureg):
        """
        Return the list of basis states with corresponding probabilities.

        The measured bits are ordered according to the supplied quantum
        register, i.e., the left-most bit in the state-string corresponds to
        the first qubit in the supplied quantum register.

        Warning:
            Only call this function after the circuit has been executed!

        Args:
            qureg (list<Qubit>): Quantum register of size n determining the contents of the
                probability states.

        Returns:
            probability_dict (dict): Dictionary mapping n-bit strings of '0' and '1' to probabilities.

        Raises:
            RuntimeError: If no data is available (i.e., if the circuit has
                not been executed). Or if a qubit was supplied which was not
                present in the circuit (might have gotten optimized away).
        """
        if len(self._measured_states) == 0:
            raise RuntimeError("Please, run the circuit first!")

        mask_bits = map(lambda qubit: self._logical_to_physical(qubit.id), qureg)

        filtered_states = QIBackend._filter_histogram(self._measured_states, mask_bits)

        probability_dict = {self._map_state_to_bit_string(state, qureg): probability
                            for state, probability in filtered_states.items()}

        return probability_dict

    def _map_state_to_bit_string(self, state, qureg):
        """

        Args:
            state (int): state represented as an integer number
            qureg (list<Qubit>): list of qubits for which to extract the state bit

        Returns:
            (string): a string of '0' and '1' corresponding to the bit value in state of each Qubit in qureg

        Examples:
            state = int('0b101010', 2)
            qureg = [Qubit(0), Qubit(1), Qubit(5)]
            print(self._map_state_to_bit_string(state, qureg)  # prints '011'

        """
        mapped_state = ''

        for i in range(len(qureg)):
            logical_id = qureg[i].id
            physical_id = self._logical_to_physical(logical_id)
            if int(state) & (1 << physical_id):
                mapped_state += '1'
            else:
                mapped_state += '0'

        return mapped_state

    def _run(self):
        """
        Run the circuit.

        Send the circuit via the Quantum Inspire API
        """
        if self.qasm == "":
            return

        # finally: add measurement commands for all measured qubits if no measurements are given.
        # only measurements after all gate operations will perform properly
        if not self._measured_ids:
            self.__add_measure_all_qubits()

        self._finalize_qasm()
        self._execute_cqasm()
        self._filter_result_by_measured_qubits()
        self._register_random_measurement_outcome()
        self._reset()

    def _finalize_qasm(self):
        """ Finalize qasm (add version and qubits line) """
        qasm = 'version 1.0\n# generated by Quantum Inspire {0} class\nqubits {1}\n\n'.format(
            self.__class__, self._number_of_qubits)
        qasm += self.qasm

        self._cqasm = qasm

    def _execute_cqasm(self):
        """ Execute self._cqasm through the API.

        Sets self._quantum_inspire_result with the result object in the API response.

        Raises:
            ProjectQBackendError: when raw_text in result from API is not empty (indicating a backend error)
        """
        self._quantum_inspire_result = self.quantum_inspire_api.execute_qasm(
            self._cqasm,
            number_of_shots=self._num_runs,
            backend_type=self.backend_type
        )

        if not self._quantum_inspire_result.get('histogram', {}):
            raw_text = self._quantum_inspire_result.get('raw_text', 'no raw_text in result structure')
            raise ProjectQBackendError(
                'Result structure does not contain proper histogram. raw_text field: %s' % raw_text)

    def _filter_result_by_measured_qubits(self):
        """ Filters the raw result by collapsing states so that unmeasured qubits are ignored.

        Populates self._measured_states by filtering self._quantum_inspire_result['histogram'] based on
        self._measured_ids (which are supposed to be logical qubit id's).
        """
        mask_bits = map(lambda bit: self._logical_to_physical(bit), self._measured_ids)
        self._measured_states = QIBackend._filter_histogram(self._quantum_inspire_result['histogram'], mask_bits)

    @staticmethod
    def _filter_histogram(histogram, mask_bits):
        """ Filter a histogram (dict) by mask_bits (list)

        Args:
            histogram (dict<int|str, float>): input histogram mapping state to probability
            mask_bits (list<int>): list of bits that are to be kept in the filtered histogram

        Returns:
            (dict<int, float>): collapsed histogram mapping state to probability

        Keys in a histogram dict are the states represented as an integer number (may be int or string), values the
        probability corresponding to that state.

        The mask_bits list specifies the relevant bits, any bit not set to 1 in the mask will be ignored (masked out).
        The probabilities of equivalent states summed.

        For example, if we have two states b0010 and b0011, and mask_bits is [1] we only care about bit 1 (the second
        bit from the right). The output will specify only one state, b0010, and the probability is the sum of the
        two original probabilities.

        """
        mask = reduce(lambda x, y: x | (1 << y), mask_bits, 0)

        filtered_states = defaultdict(lambda: 0)
        for state, probability in histogram.items():
            filtered_states[int(state) & mask] += probability

        return dict(filtered_states)

    def _register_random_measurement_outcome(self):
        """ Samples the _measured_states for a single result and registers this as the outcome of the circuit. """

        class QB:
            def __init__(self, qubit_id):
                self.id = qubit_id

        random_measurement = self._sample_measured_states_once()

        for logical_qubit_id in self._measured_ids:
            physical_qubit_id = self._logical_to_physical(logical_qubit_id)

            result = bool(random_measurement & (1 << physical_qubit_id))

            self.main_engine.set_measurement_result(QB(logical_qubit_id), result)

    def _sample_measured_states_once(self):
        """ Obtain a random state from the _measured_states, taking into account the probability distribution. """
        states = list(self._measured_states.keys())
        weights = list(self._measured_states.values())
        return random.choices(states, weights=weights)[0]

    @property
    def _number_of_qubits(self):
        return self._max_qubit_id + 1

    def receive(self, command_list):
        """
        Receives a command list and, for each command, stores it until
        completion.

        Args:
            command_list: List of commands to execute
        """
        for cmd in command_list:
            if not cmd.gate == FlushGate():
                self._store(cmd)
            else:
                self._run()
                self._reset()

    def __add_measure_all_qubits(self):
        """ Adds measurements at the end of the quantum algorithm for all allocated qubits."""
        qubits_reference = self.main_engine.active_qubits.copy()
        qubits_counts = len(qubits_reference)
        for _ in range(qubits_counts):
            q = qubits_reference.pop()
            Measure | q

    """ Mapping of gate names from our gate objects to the cQASM representation."""
    _gate_names = {str(Tdag): "Tdag", str(Sdag): "Sdag"}
