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
import sys
import inspect
import random
from collections import defaultdict
from functools import reduce
from typing import List, Dict, Iterator, Union, Optional, Tuple, Any

from projectq.cengines import BasicEngine
from projectq.meta import LogicalQubitIDTag, get_control_count
from projectq.ops import (NOT, Allocate, Barrier, Deallocate, FlushGate, H,
                          Measure, Ph, Rx, Ry, Rz, S, Sdag, Swap, T, Tdag, X,
                          Y, Z, Command, CZ, C, R, CNOT, Toffoli)
from projectq.types import Qubit
from quantuminspire.api import QuantumInspireAPI
from quantuminspire.exceptions import AuthenticationError
from quantuminspire.exceptions import ProjectQBackendError
# shortcut for Controlled Phase-shift gate (CR)
CR = C(R)


class QIBackend(BasicEngine):  # type: ignore
    """ Backend for Quantum Inspire

    """

    def __init__(self, num_runs: int = 1024, verbose: int = 0, quantum_inspire_api: Optional[QuantumInspireAPI] = None,
                 backend_type: Optional[Union[int, str]] = None) -> None:
        """
        Initialize the Backend object.

        Args:
            num_runs: Number of runs to collect statistics (default is 1024).
            verbose: Verbosity level, defaults to 0, which produces no extra output.
            quantum_inspire_api: Connection to QI platform, optional parameter.
            backend_type: Backend to use for execution. When no backend_type is provided, the default backend will be
                          used.
        """
        BasicEngine.__init__(self)
        self._flushed: bool = False
        """ Because engines are meant to be 'single use' by the way ProjectQ is designed,
        any additional gates received after a FlushGate triggers an exception. """
        self._clear: bool = True
        self._reset()
        self._verbose: int = verbose
        self._cqasm: str = str()
        self._measured_states: Dict[int, float] = {}
        self._measured_ids: List[int] = []
        self._allocation_map: List[Tuple[int, int]] = []
        self._max_qubit_id: int = -1
        if quantum_inspire_api is None:
            try:
                quantum_inspire_api = QuantumInspireAPI()
            except AuthenticationError as ex:
                raise AuthenticationError('Make sure you have saved your token credentials on disk or '
                                          'provide a QuantumInspireAPI instance as parameter to QIBackend') from ex
        self._quantum_inspire_api: QuantumInspireAPI = quantum_inspire_api
        self._backend_type: Dict[str, Any] = self._quantum_inspire_api.get_backend_type(backend_type)
        if num_runs < 1 or num_runs > self._backend_type['max_number_of_shots']:
            raise ProjectQBackendError(f'Invalid number of runs (num_runs={num_runs})')
        self._num_runs: int = num_runs
        self._full_state_projection = not self._backend_type["is_hardware_backend"]
        self._is_simulation_backend = not self._backend_type["is_hardware_backend"]
        self._max_number_of_qubits: int = self._backend_type["number_of_qubits"]
        self._one_qubit_gates: Tuple[Any, ...] = self._get_one_qubit_gates()
        self._two_qubit_gates: Tuple[Any, ...] = self._get_two_qubit_gates()
        self._three_qubit_gates: Tuple[Any, ...] = self._get_three_qubit_gates()

    def _get_one_qubit_gates(self) -> Tuple[Any, ...]:
        allowed_operations = self._backend_type['allowed_operations']
        if len(allowed_operations) > 0:
            one_qubit_gates = []
            for gate_set in ['single_gates', 'parameterized_single_gates']:
                if gate_set in allowed_operations:
                    for gate in allowed_operations[gate_set]:
                        if gate in ['x', 'y', 'z', 'h', 's', 'sdag', 't', 'tdag', 'rx', 'ry', 'rz']:
                            one_qubit_gates += [getattr(sys.modules[__name__], gate.capitalize())]
        else:
            one_qubit_gates = [X, Y, Z, H, S, Sdag, T, Tdag, Rx, Ry, Rz]
        return tuple(one_qubit_gates)

    def _get_two_qubit_gates(self) -> Tuple[Any, ...]:
        allowed_operations = self._backend_type['allowed_operations']
        if len(allowed_operations) > 0:
            two_qubit_gates = []
            for gate_set in ['dual_gates', 'parameterized_dual_gates']:
                if gate_set in allowed_operations:
                    for gate in allowed_operations[gate_set]:
                        if gate in ['cz', 'cnot', 'cr']:
                            two_qubit_gates += [getattr(sys.modules[__name__], gate.upper())]
                        elif gate == 'swap':
                            two_qubit_gates += [Swap]
        else:
            two_qubit_gates = [CZ, CNOT, CR, Swap]
        return tuple(two_qubit_gates)

    def _get_three_qubit_gates(self) -> Tuple[Any, ...]:
        allowed_operations = self._backend_type['allowed_operations']
        if len(allowed_operations) > 0:
            three_qubit_gates = []
            for gate_set in ['triple_gates']:
                if gate_set in allowed_operations:
                    for gate in allowed_operations[gate_set]:
                        if gate == 'toffoli':
                            three_qubit_gates += [Toffoli]
        else:
            three_qubit_gates = [Toffoli]
        return tuple(three_qubit_gates)

    @property
    def one_qubit_gates(self) -> Tuple[Any, ...]:
        """ Return the one qubit gates as a tuple """
        return self._one_qubit_gates

    @property
    def two_qubit_gates(self) -> Tuple[Any, ...]:
        """ Return the two qubit gates as a tuple """
        return self._two_qubit_gates

    @property
    def three_qubit_gates(self) -> Tuple[Any, ...]:
        """ Return the three qubit gates as a tuple """
        return self._three_qubit_gates

    def cqasm(self) -> str:
        """ Return cqasm code that is generated last. """
        return self._cqasm

    def is_available(self, cmd: Command) -> bool:
        """
        Via this method the ProjectQ framework determines which commands (gates) are available in the backend.

        Args:
            cmd: Command with a gate for which to check availability.

        Returns:
            True when the gate in the command is available on the Quantum Inspire backend.
        """
        count = get_control_count(cmd)
        g = cmd.gate
        if self._verbose >= 3:
            print(f'call to is_available with cmd {cmd} (gate {g})')
        if g in (Measure, Allocate, Deallocate, Barrier):
            return True
        if g == NOT and count == 2:
            return Toffoli in self.three_qubit_gates
        if g == NOT and count == 1:
            return CNOT in self.two_qubit_gates
        if g == Z and count == 1:
            return CZ in self.two_qubit_gates
        if (g == R or isinstance(g, (R,))) and count == 1:
            return CR in self.two_qubit_gates
        if count != 0:
            return False
        if g == Swap:
            return g in self.two_qubit_gates
        if g in (T, Tdag, S, Sdag, H, X, Y, Z):
            return g in self.one_qubit_gates
        if isinstance(g, (Rx, Ry, Rz)):
            one_qubit_types = []
            for gate in self.one_qubit_gates:
                if inspect.isclass(gate):
                    one_qubit_types.append(gate)
            return isinstance(g, tuple(one_qubit_types))
        if isinstance(g, Ph):
            return False

        return False

    def _reset(self) -> None:
        """ Reset temporary variable qasm to an initial value and set a flag to clear variables in _store
            when _store is called. """
        self._clear = True
        self.qasm = ""

    def _allocate_qubit(self, index_to_add: int) -> None:
        """ On a simulation backend it is possible to reuse qubits. The advantage of reusing qubits is that less
        qubits are needed in total for the algorithm.
        A source of reusing qubits is when qubits are used as ancilla bits. Ancilla bits are used to downgrade
        complicated quantum gates into simple gates by placing controls on ancilla bits or when doing quantum error
        correction. In projectQ, a qubit can be re-used when it is de-allocated after usage. ProjectQ sends an
        Allocate-gate for a qubit that is going to be used and a Deallocate gate for qubits that are not used anymore.

        _allocation_map is the store in which the administration is done for assigning physical qubits that are used
        with in ProjectQ to the simulation qubits, this is as they appear in the cqasm.
        _allocation_map stores the assignments as tuples (simulation_bit, physical_bit) where 'physical_bit' is
        requested by ProjectQ and simulation_bit is the assignment to a bit in the simulator.
        A de-allocated physical bit is registered as -1, which means the corresponding simulation bit can be re-used.

        We strive for x-to-x allocation for qubits, which means we want to allocate a physical qubit to its
        corresponding simulation qubit. We do this to respect as much as possible the qubits of the original algorithm
        in the generated cqasm for readability.

        Only when the requested physical bit is higher than the max number of bits supported by the backend, we try
        to search for an de-allocatd ancilla bit to re-use. When an ancilla is re-used, we have to reset the qubit
        which means we have to switch to non-full state projection.

        Example: When physical bit 0..4 are allocated in reversed order we would still get:
        (0, 0), (1, 1), (2, 2), (3, 3), (4, 4)
        and not:
        (0, 4), (1, 3), (2, 2), (3, 1), (4, 0)

        When bit 6 is allocated next we get:
        (0, 0), (1, 1), (2, 2), (3, 3), (4, 4), (6, 6)
        and when bit 6 is de-allocated again we get:
        (0, 0), (1, 1), (2, 2), (3, 3), (4, 4), (6, -1)

        At this point, when bit 5 is allocated we get:
        (0, 0), (1, 1), (2, 2), (3, 3), (4, 4), (5, 5), (6, -1)
        When a bit is allocated with an index higher than the maximum number of qubits in the simulator we try to
        allocate an earlier de-allocated bit
        When the maximum number of qubits in the simulator is 7 [0..6], allocation of bit 7 will be on position 6
        (0, 0), (1, 1), (2, 2), (3, 3), (4, 4), (5, 5), (6, 7)
        When bit 8 is allocated next, we cannot reuse another bit, so we add it as the next in line (bit 7)
        (0, 0), (1, 1), (2, 2), (3, 3), (4, 4), (5, 5), (6, 7), (7, 8)
        """
        if self._is_simulation_backend:
            # physical bit to add cannot be allocated already
            if next(iter(x for x in self._allocation_map if x[1] == index_to_add), None) is not None:
                raise RuntimeError(f"Bit {index_to_add} is already allocated.")

            # check if the corresponding simulation bit is in the _allocation_map already,
            # we strive for x-to-x allocation, so when (x, -1) we should reuse this bit
            allocation_entry = next(iter(x for x in self._allocation_map if x[0] == index_to_add), None)
            # also take into account the maximum number of bits we may use on the backend.
            if allocation_entry is None and (index_to_add < self._max_number_of_qubits):
                # map the bit to the corresponding simulation bit
                self._allocation_map.append((index_to_add, index_to_add))
            else:
                # check if the corresponding simulation bit was de-allocated (we strive for a x-to-x allocation)
                if allocation_entry is None or allocation_entry[1] != -1:
                    # The corresponding simulation bit is not found or this is a bit in the ancilla range
                    # We look for a free spot, a previously de-allocated bit (-1)
                    allocation_entry = next(iter(x for x in self._allocation_map if x[1] == -1), None)

                if allocation_entry is None:
                    # no free spot, add a new simulation qubit
                    self._allocation_map.append((max(self._allocation_map)[0] + 1, index_to_add))
                else:
                    # we are reusing a de-allocated simulation bit, this situation turns the circuit into non-FSP
                    if self._full_state_projection:
                        self._switch_fsp_to_nonfsp()

                    # to reuse a de-allocated bit we do a prep_z first, which is better implemented as a
                    # measurement and binary controlled x-gate
                    self.qasm += f"\nmeasure q[{allocation_entry[0]}]"
                    self.qasm += f"\nc-x b[{allocation_entry[0]}], q[{allocation_entry[0]}]"
                    index = self._allocation_map.index(allocation_entry)
                    self._allocation_map[index] = (allocation_entry[0], index_to_add)

            # keep track of the maximum qubit id on simulation backend
            self._max_qubit_id = max(self._allocation_map)[0]
        else:
            # keep track of the maximum qubit id on hardware backend
            self._max_qubit_id = max(self._max_qubit_id, index_to_add)

        if self._verbose >= 1:
            print(f'_store: Allocate gate {(index_to_add,)}')
            print(f'   _allocation_map {self._allocation_map}')

    def _deallocate_qubit(self, index_to_remove: int) -> None:
        """ On a simulation backend it is possible to reuse qubits.
        When a qubit is de-allocated we register -1 as physical bit id in the _allocation_map.
        """
        if self._is_simulation_backend:
            # determine the qubits that are not de-allocated
            allocation_entry = next(iter(x for x in self._allocation_map if x[1] == index_to_remove), None)
            if allocation_entry is None:
                raise RuntimeError(f"De-allocated bit {index_to_remove} was not allocated.")
            else:
                # deallocate the corresponding simulation bit
                index = self._allocation_map.index(allocation_entry)
                self._allocation_map[index] = (allocation_entry[0], -1)

        if self._verbose >= 1:
            print(f'_store: Deallocate gate {(index_to_remove,)}')
            print(f'   _allocation_map {self._allocation_map}')

    def _physical_to_simulated(self, physical_qubit_id: int) -> int:
        """
        Return the allocated location on the simulated backend of the qubit with the given physical qubit id.

        Args:
            physical_qubit_id: ID of the physical qubit whose position should be returned.

        Returns:
            Allocated simulation bit position of physical qubit with id pqb_id.
        """
        if self._is_simulation_backend:
            allocation_entry = next(iter(x for x in self._allocation_map if x[1] == physical_qubit_id), None)
            if allocation_entry is None:
                raise RuntimeError(f"Bit position in simulation backend not found for"
                                   f" physical bit {physical_qubit_id}.")
            else:
                return allocation_entry[0]
        else:
            return physical_qubit_id

    def _switch_fsp_to_nonfsp(self) -> None:
        """ We have determined that the algorithm is non-deterministic and cannot use fsp.
        At this point, measured_ids is the collection of measurement statements in the algorithm for which no
        measurement statement has been added to the qasm yet. For every measured_id a measurement statement is added.
        """
        for logical_qubit_id in self._measured_ids:
            physical_qubit_id = self._logical_to_physical(logical_qubit_id)
            sim_qubit_id = self._physical_to_simulated(physical_qubit_id)
            self.qasm += f"\nmeasure q[{sim_qubit_id}]"
        self._full_state_projection = False

    def _store(self, cmd: Command) -> None:
        """
        Temporarily store the command cmd.

        Translates the command and stores the results in local variables.

        Args:
            cmd: Command to store.
        """
        if self._verbose >= 3:
            print(f'_store {id(self)}: cmd {cmd}')

        if self._clear:
            self._clear = False
            self.qasm = ""
            self._measured_states = {}
            self._measured_ids = []
            self._full_state_projection = not self._backend_type["is_hardware_backend"]

        gate = cmd.gate

        if gate == Deallocate:
            index_to_remove = cmd.qubits[0][0].id
            self._deallocate_qubit(index_to_remove)
            return

        if self._flushed:
            raise RuntimeError("Same instance of QIBackend used for circuit after Flush.")

        if gate == Allocate:
            index_to_add = cmd.qubits[0][0].id
            self._allocate_qubit(index_to_add)
            return

        if gate == Measure:
            assert len(cmd.qubits) == 1 and len(cmd.qubits[0]) == 1
            sim_qubit_id = self._physical_to_simulated(cmd.qubits[0][0].id)
            logical_id = None
            for t in cmd.tags:
                if isinstance(t, LogicalQubitIDTag):
                    logical_id = t.logical_qubit_id
                    break
            if self.main_engine.mapper is None:
                logical_id = cmd.qubits[0][0].id  # no mapping
            assert logical_id is not None
            self._measured_ids += [logical_id]
            # do not add the measurement statement when fsp is possible
            if not self._full_state_projection:
                if self._is_simulation_backend:
                    self.qasm += f"\nmeasure q[{sim_qubit_id}]"
            return

        # when we find a gate after measurements we don't have fsp
        # add any delayed measurement statements
        if self._full_state_projection and len(self._measured_ids) != 0:
            self._switch_fsp_to_nonfsp()

        if gate == NOT and get_control_count(cmd) == 1:
            # this case also covers the CX controlled gate
            ctrl_pos = self._physical_to_simulated(cmd.control_qubits[0].id)
            qb_pos = self._physical_to_simulated(cmd.qubits[0][0].id)
            self.qasm += f"\ncnot q[{ctrl_pos}], q[{qb_pos}]"
        elif gate == Swap:
            q0 = self._physical_to_simulated(cmd.qubits[0][0].id)
            q1 = self._physical_to_simulated(cmd.qubits[1][0].id)
            self.qasm += f"\nswap q[{q0}], q[{q1}]"
        elif gate == X and get_control_count(cmd) == 2:
            ctrl_pos1 = self._physical_to_simulated(cmd.control_qubits[0].id)
            ctrl_pos2 = self._physical_to_simulated(cmd.control_qubits[1].id)
            qb_pos = self._physical_to_simulated(cmd.qubits[0][0].id)
            self.qasm += f"\ntoffoli q[{ctrl_pos1}], q[{ctrl_pos2}], q[{qb_pos}]"
        elif gate == Z and get_control_count(cmd) == 1:
            ctrl_pos = self._physical_to_simulated(cmd.control_qubits[0].id)
            qb_pos = self._physical_to_simulated(cmd.qubits[0][0].id)
            self.qasm += f"\ncz q[{ctrl_pos}], q[{qb_pos}]"
        elif gate == Barrier:
            qb_pos_list = [qb.id for qr in cmd.qubits for qb in qr]
            qb_str = ', '.join([f'q[{self._physical_to_simulated(x)}]' for x in qb_pos_list])
            self.qasm += f"\n# barrier gate {qb_str};"
        elif isinstance(gate, (Rz, R)) and get_control_count(cmd) == 1:
            ctrl_pos = self._physical_to_simulated(cmd.control_qubits[0].id)
            qb_pos = self._physical_to_simulated(cmd.qubits[0][0].id)
            gate_name = 'cr'
            self.qasm += f"\n{gate_name} q[{ctrl_pos}],q[{qb_pos}],{gate.angle:.12f}"
        elif isinstance(gate, (Rx, Ry)) and get_control_count(cmd) == 1:
            raise NotImplementedError('controlled Rx or Ry gate not implemented')
        elif isinstance(gate, (Rx, Ry, Rz)):
            assert get_control_count(cmd) == 0
            qb_pos = self._physical_to_simulated(cmd.qubits[0][0].id)
            gate_name = str(gate)[0:2].lower()
            self.qasm += f"\n{gate_name} q[{qb_pos}],{gate.angle:.12g}"
        elif gate == Tdag and get_control_count(cmd) == 0:
            qb_pos = self._physical_to_simulated(cmd.qubits[0][0].id)
            self.qasm += f"\ntdag q[{qb_pos}]"
        elif gate == Sdag and get_control_count(cmd) == 0:
            qb_pos = self._physical_to_simulated(cmd.qubits[0][0].id)
            self.qasm += f"\nsdag q[{qb_pos}]"
        elif isinstance(gate, tuple(type(gate) for gate in (X, Y, Z, H, S, T))):
            assert get_control_count(cmd) == 0
            gate_str = str(gate).lower()
            qb_pos = self._physical_to_simulated(cmd.qubits[0][0].id)
            self.qasm += f"\n{gate_str} q[{qb_pos}]"
        else:
            raise NotImplementedError(f'cmd {(cmd,)} not implemented')

    def _logical_to_physical(self, logical_qubit_id: int) -> int:
        """
        Return the physical location of the qubit with the given logical id.

        Args:
            logical_qubit_id: ID of the logical qubit whose position should be returned.

        Returns:
            Physical position of logical qubit with id qb_id.
        """
        if self.main_engine.mapper is not None:
            mapping = self.main_engine.mapper.current_mapping
            if logical_qubit_id not in mapping:
                raise RuntimeError(f"Unknown qubit id {logical_qubit_id}. Please make sure "
                                   f"eng.flush() was called and that the qubit "
                                   f"was eliminated during optimization.")

            return int(mapping[logical_qubit_id])
        else:
            return logical_qubit_id  # no mapping

    def get_probabilities(self, qureg: List[Qubit]) -> Dict[str, float]:
        """
        Return the list of basis states with corresponding probabilities.

        The measured bits are ordered according to the supplied quantum
        register, i.e., the left-most bit in the state-string corresponds to
        the first qubit in the supplied quantum register.

        Warning:
            Only call this function after the circuit has been executed!

        Args:
            qureg: Quantum register of size n determining the contents of the probability states.

        Returns:
            Dictionary mapping n-bit strings of '0' and '1' to probabilities.

        Raises:
            RuntimeError: If no data is available (i.e., if the circuit has
                not been executed). Or if a qubit was supplied which was not
                present in the circuit (might have gotten optimized away).
        """
        if len(self._measured_states) == 0:
            raise RuntimeError("Please, run the circuit first!")
        mask_bits = map(lambda qubit: self._physical_to_simulated(self._logical_to_physical(qubit.id)), qureg)

        filtered_states = QIBackend._filter_histogram(self._measured_states, mask_bits)

        probability_dict = {self._map_state_to_bit_string(state, qureg): probability
                            for state, probability in filtered_states.items()}

        return probability_dict

    def _map_state_to_bit_string(self, state: int, qureg: List[Qubit]) -> str:
        """

        Args:
            state: state represented as an integer number.
            qureg: list of qubits for which to extract the state bit.

        Returns:
            A string of '0' and '1' corresponding to the bit value in state of each Qubit in qureg.

        Examples:
            state = int('0b101010', 2)
            qureg = [Qubit(0), Qubit(1), Qubit(5)]
            print(self._map_state_to_bit_string(state, qureg)  # prints '011'

        """
        mapped_state = ''

        for qubit in qureg:
            logical_id = qubit.id
            physical_qubit_id = self._logical_to_physical(logical_id)
            sim_qubit_id = self._physical_to_simulated(physical_qubit_id)
            if int(state) & (1 << sim_qubit_id):
                mapped_state += '1'
            else:
                mapped_state += '0'

        return mapped_state

    def _run(self) -> None:
        """
        Run the circuit.

        Send the circuit via the Quantum Inspire API.
        """
        if self.qasm == "":
            return

        # Finally: add measurement commands for all measured qubits if no measurements are given.
        # Only for simulation backends, measurements after all gate operations will perform properly in FSP.
        if not self._measured_ids and self._is_simulation_backend:
            self.__add_measure_all_qubits()

        self._finalize_qasm()
        self._execute_cqasm()
        self._filter_result_by_measured_qubits()
        self._register_random_measurement_outcome()
        self._reset()

    def _finalize_qasm(self) -> None:
        """ Finalize qasm (add version and qubits line). """
        qasm = f'version 1.0\n# cQASM generated by Quantum Inspire {self.__class__} class\n' \
               f'qubits {self._number_of_qubits}\n'
        qasm += self.qasm

        if self._verbose >= 2:
            print(qasm)
        self._cqasm = qasm

    def _execute_cqasm(self) -> None:
        """ Execute self._cqasm through the API.

        Sets self._quantum_inspire_result with the result object in the API response.

        Raises:
            ProjectQBackendError: when raw_text in result from API is not empty (indicating a backend error).
        """
        self._quantum_inspire_result = self._quantum_inspire_api.execute_qasm(
            self._cqasm,
            number_of_shots=self._num_runs,
            backend_type=self._backend_type,
            full_state_projection=self._full_state_projection
        )

        if not self._quantum_inspire_result.get('histogram', {}):
            raw_text = self._quantum_inspire_result.get('raw_text', 'no raw_text in result structure')
            raise ProjectQBackendError(
                f'Result structure does not contain proper histogram. raw_text field: {raw_text}')

    def _filter_result_by_measured_qubits(self) -> None:
        """ Filters the raw result by collapsing states so that unmeasured qubits are ignored.

        Populates self._measured_states by filtering self._quantum_inspire_result['histogram'] based on
        self._measured_ids (which are supposed to be logical qubit id's).
        """
        mask_bits = map(lambda bit: self._physical_to_simulated(self._logical_to_physical(bit)), self._measured_ids)
        histogram: Dict[int, float] = {int(k): v for k, v in self._quantum_inspire_result['histogram'].items()}
        self._measured_states = QIBackend._filter_histogram(histogram, mask_bits)

    @staticmethod
    def _filter_histogram(histogram: Dict[int, float], mask_bits: Iterator[int]) -> Dict[int, float]:
        """ Filter a histogram by mask_bits.

        Args:
            histogram: input histogram mapping state to probability.
            mask_bits: list of bits that are to be kept in the filtered histogram.

        Returns:
            Collapsed histogram mapping state to probability.

        Keys in a histogram dict are the states represented as an integer number (may be int or string), values the
        probability corresponding to that state.

        The mask_bits list specifies the relevant bits, any bit not set to 1 in the mask will be ignored (masked out).
        The probabilities of equivalent states summed.

        For example, if we have two states b0010 and b0011, and mask_bits is [1] we only care about bit 1 (the second
        bit from the right). The output will specify only one state, b0010, and the probability is the sum of the
        two original probabilities.

        """
        mask = reduce(lambda x, y: x | (1 << y), mask_bits, 0)

        filtered_states: Dict[int, float] = defaultdict(lambda: 0)
        for state, probability in histogram.items():
            filtered_states[state & mask] += probability

        return dict(filtered_states)

    def _register_random_measurement_outcome(self) -> None:
        """ Samples the _measured_states for a single result and registers this as the outcome of the circuit. """

        class QB:
            def __init__(self, qubit_id: int) -> None:
                self.id: int = qubit_id

        random_measurement = self._sample_measured_states_once()

        for logical_qubit_id in self._measured_ids:
            physical_qubit_id = self._logical_to_physical(logical_qubit_id)
            sim_qubit_id = self._physical_to_simulated(physical_qubit_id)
            result = bool(random_measurement & (1 << sim_qubit_id))

            self.main_engine.set_measurement_result(QB(logical_qubit_id), result)

    def _sample_measured_states_once(self) -> int:
        """ Obtain a random state from the _measured_states, taking into account the probability distribution. """
        states = list(self._measured_states.keys())
        weights = list(self._measured_states.values())
        return random.choices(states, weights=weights)[0]

    @property
    def _number_of_qubits(self) -> int:
        """ Return the number of qubits used in the circuit. If it is a hardware backend return max nr of qubits """
        if self._is_simulation_backend:
            return self._max_qubit_id + 1
        else:
            return self._max_number_of_qubits

    def receive(self, command_list: List[Command]) -> None:
        """
        Receives a command list and, for each command, stores it until completion.

        Args:
            command_list: List of commands to execute.
        """
        for cmd in command_list:
            if not cmd.gate == FlushGate():
                self._store(cmd)
            else:
                self._run()
                self._flushed = True
                self._reset()

    def __add_measure_all_qubits(self) -> None:
        """ Adds measurements at the end of the quantum algorithm for all allocated qubits. """
        qubits_reference = self.main_engine.active_qubits.copy()
        qubits_counts = len(qubits_reference)
        for _ in range(qubits_counts):
            q = qubits_reference.pop()
            Measure | q
