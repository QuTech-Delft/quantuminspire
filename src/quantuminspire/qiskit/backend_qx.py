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
import io
import json
import uuid
from collections import defaultdict, OrderedDict, Counter
from typing import Dict, List, Tuple, Optional, Any

import numpy as np
from coreapi.exceptions import ErrorMessage
from qiskit.providers import BaseBackend
from qiskit.providers.models import QasmBackendConfiguration
from qiskit.providers.models.backendconfiguration import GateConfig
from qiskit.qobj import QasmQobj, QasmQobjExperiment
from qiskit.result.models import ExperimentResult, ExperimentResultData
from qiskit.qobj import QobjExperimentHeader

from quantuminspire.api import QuantumInspireAPI
from quantuminspire.exceptions import QisKitBackendError
from quantuminspire.job import QuantumInspireJob
from quantuminspire.qiskit.circuit_parser import CircuitToString
from quantuminspire.qiskit.qi_job import QIJob
from quantuminspire.version import __version__ as quantum_inspire_version


class QuantumInspireBackend(BaseBackend):  # type: ignore
    DEFAULT_CONFIGURATION = QasmBackendConfiguration(
        backend_name='qi_simulator',
        backend_version=quantum_inspire_version,
        n_qubits=26,
        basis_gates=['x', 'y', 'z', 'h', 'rx', 'ry', 'rz', 's', 'sdg', 't', 'tdg', 'cx', 'ccx', 'u1', 'u2', 'u3', 'id',
                     'swap', 'cz', 'snapshot'],
        gates=[GateConfig(name='NotUsed', parameters=['NaN'], qasm_def='NaN')],
        local=False,
        simulator=True,
        conditional=True,
        open_pulse=False,
        memory=True,
        max_shots=1024,
        max_experiments=1,
        coupling_map=None
    )

    def __init__(self, api: QuantumInspireAPI, provider: Any,
                 configuration: Optional[QasmBackendConfiguration] = None) -> None:
        """ Python implementation of a quantum simulator using Quantum Inspire API.

        Args:
            api: The interface instance to the Quantum Inspire API.
            provider: Provider for this backend.
            configuration: The configuration of the quantum inspire backend. The
                configuration must implement the fields given by the QiSimulatorPy.DEFAULT_CONFIGURATION. All
                configuration fields are listed in the table below. The table rows with an asterisk specify fields which
                can have a custom value and are allowed to be changed according to the description column.

                | key                        | description
                |----------------------------|-------------------------------------------------------------------------
                | backend_name (str)*        | The name of the quantum inspire backend. The API can list the name of
                |                            | each available backend using the function api.list_backend_types(). One
                |                            | of the listed names must be used.
                | backend_version (str)      | Backend version in the form X.Y.Z.
                | n_qubits (int)             | Number of qubits.
                | basis_gates (list(str))    | A list of basis gates to compile to.
                | gates (GateConfig)         | List of basis gates on the backend. Not used.
                | local (bool)               | Indicates whether the system is running locally or remotely.
                | simulator (bool)           | Specifies whether the backend is a simulator or a quantum system.
                | conditional (bool)         | Backend supports conditional operations.
                | open_pulse (bool)          | Backend supports open pulse. False.
                | memory (bool)              | Backend supports memory. True.
                | max_shots (int)            | Maximum number of shots supported.
                | max_experiments (int)      | Optional: Maximum number of experiments (circuits) per job.
                | coupling_map (list(tuple)) | Define the edges.
        """
        super().__init__(configuration=(configuration or
                                        QuantumInspireBackend.DEFAULT_CONFIGURATION),
                         provider=provider)
        self.__backend: Dict[str, Any] = api.get_backend_type_by_name(self.name())
        self.__api: QuantumInspireAPI = api

    @property
    def backend_name(self) -> str:
        return self.name()  # type: ignore

    def run(self, qobj: QasmQobj) -> QIJob:
        """ Submits a quantum job to the Quantum Inspire platform.

        Args:
            qobj: The quantum job with the Qiskit algorithm and quantum inspire backend.

        Returns:
            A job that has been submitted.
        """
        self.__validate_number_of_shots(qobj)
        number_of_shots = qobj.config.shots

        identifier = uuid.uuid1()
        project_name = 'qi-sdk-project-{}'.format(identifier)
        project = self.__api.create_project(project_name, number_of_shots, self.__backend)
        experiments = qobj.experiments
        job = QIJob(self, str(project['id']), self.__api)
        for experiment in experiments:
            self.__validate_number_of_clbits(experiment)
            full_state_projection = self.__validate_full_state_projection(experiment)
            if not full_state_projection:
                QuantumInspireBackend.__validate_unsupported_measurements(experiment)
            self._submit_experiment(experiment, number_of_shots, project=project,
                                    full_state_projection=full_state_projection)

        job.experiments = experiments
        return job

    def retrieve_job(self, job_id: str) -> QIJob:
        """ Retrieve a specified job by its job_id.

        Args:
            job_id: The job id.

        Returns:
            The job that has been retrieved.

        Raises:
            QisKitBackendError: If job not found or error occurs during retrieval of the job.
        """
        try:
            self.__api.get_project(int(job_id))
        except (ErrorMessage, ValueError):
            raise QisKitBackendError("Could not retrieve job with job_id '{}' ".format(job_id))
        return QIJob(self, job_id, self.__api)

    @staticmethod
    def _generate_cqasm(experiment: QasmQobjExperiment, full_state_projection: bool = True) -> str:
        """ Generates the cQASM from the Qiskit experiment.

        Args:
            experiment: The experiment that contains instructions to be converted to cQASM.
            full_state_projection: When False, the experiment is not suitable for full state projection

        Returns:
            The cQASM code that can be sent to the Quantum Inspire API.
        """
        parser = CircuitToString(full_state_projection)
        number_of_qubits = experiment.header.n_qubits
        instructions = experiment.instructions
        with io.StringIO() as stream:
            stream.write('version 1.0\n')
            stream.write('# cQASM generated by QI backend for Qiskit\n')
            stream.write('qubits %d\n' % number_of_qubits)
            for instruction in instructions:
                parser.parse(stream, instruction)
            return stream.getvalue()

    def _submit_experiment(self, experiment: QasmQobjExperiment, number_of_shots: int,
                           project: Optional[Dict[str, Any]] = None,
                           full_state_projection: bool = True) -> QuantumInspireJob:
        compiled_qasm = self._generate_cqasm(experiment, full_state_projection=full_state_projection)
        measurements = self._collect_measurements(experiment)
        user_data = {'name': experiment.header.name, 'memory_slots': experiment.header.memory_slots,
                     'creg_sizes': experiment.header.creg_sizes, 'measurements': measurements}
        job_id = self.__api.execute_qasm_async(compiled_qasm, backend_type=self.__backend,
                                               number_of_shots=number_of_shots, project=project,
                                               job_name=experiment.header.name, user_data=json.dumps(user_data),
                                               full_state_projection=full_state_projection)
        return job_id

    def get_experiment_results(self, qi_job: QIJob) -> List[ExperimentResult]:
        """ Get results from experiments from the Quantum-inspire platform.

        Args:
            qi_job: A job that has already been submitted and which execution is completed.

        Raises:
            QisKitBackendError: If an error occurred during execution by the backend.

        Returns:
            A list of experiment results; containing the data, execution time, status, etc.
        """
        jobs = self.__api.get_jobs_from_project(int(qi_job.job_id()))
        results = [self.__api.get_result_from_job(job['id']) for job in jobs]
        experiment_results = []
        for result, job in zip(results, jobs):
            if not result.get('histogram', {}):
                raise QisKitBackendError(
                    'Result from backend contains no histogram data!\n{}'.format(result.get('raw_text')))

            user_data = json.loads(str(job.get('user_data')))
            measurements = user_data.pop('measurements')
            histogram_obj, memory_data = self.__convert_result_data(result, measurements)
            full_state_histogram_obj = self.__convert_histogram(result, measurements)
            experiment_result_data = ExperimentResultData(counts=histogram_obj,
                                                          memory=memory_data)
            experiment_result_data.probabilities = full_state_histogram_obj
            header = QobjExperimentHeader.from_dict(user_data)
            experiment_result_dictionary = {'name': job.get('name'), 'seed': 42, 'shots': job.get('number_of_shots'),
                                            'data': experiment_result_data, 'status': 'DONE', 'success': True,
                                            'time_taken': result.get('execution_time_in_seconds'), 'header': header}
            experiment_results.append(ExperimentResult(**experiment_result_dictionary))
        return experiment_results

    def __validate_number_of_shots(self, job: QasmQobj) -> None:
        """ Checks whether the number of shots has a valid value.

        Args:
            job: The quantum job with the Qiskit algorithm and quantum inspire backend.

        Raises:
            QisKitBackendError: When the value is not correct.
        """
        number_of_shots = job.config.shots
        if number_of_shots < 1 or number_of_shots > self.__backend['max_number_of_shots']:
            raise QisKitBackendError('Invalid shots (number_of_shots={})'.format(number_of_shots))

    def __validate_number_of_clbits(self, experiment: QasmQobjExperiment) -> None:
        """ Checks whether the number of classical bits has a value cQASM can support.

            1. When number of classical bits is less than 1 an error is raised.
            2. When binary controlled gates are used and the number of classical registers > number of classical
            registers an error is raised.
                When using binary controlled gates in Qiskit, we can have something like:
                q = QuantumRegister(2)
                c = ClassicalRegister(4)
                circuit = QuantumCircuit(q, c)
                circuit.h(q[0]).c_if(c, 15)

                Because cQASM has the same number of classical registers as qubits (2 in this case),
                this circuit cannot be translated to valid cQASM.

        Args:
            experiment: The experiment with gate operations and header.

        Raises:
            QisKitBackendError: When the value is not correct.
        """
        number_of_clbits = experiment.header.memory_slots
        if number_of_clbits < 1:
            raise QisKitBackendError("Invalid amount of classical bits ({})!".format(number_of_clbits))

        if BaseBackend.configuration(self).conditional:
            number_of_qubits = experiment.header.n_qubits
            if number_of_clbits > number_of_qubits:
                # no problem when there are no conditional gate operations
                for instruction in experiment.instructions:
                    if hasattr(instruction, 'conditional'):
                        raise QisKitBackendError("Number of classical bits must be less than or equal to the"
                                                 " number of qubits when using conditional gate operations")

    @staticmethod
    def __validate_full_state_projection(experiment: QasmQobjExperiment) -> bool:
        """ FSP (Full State Projection) can be used when no measurements are found in the circuit or when no
            other gates are found after measurements.

        Args:
            experiment: The experiment with gate operations and header.

        Returns:
            True when FSP can be used, otherwise False.
        """
        fsp = True
        measurement_found = False
        for instruction in experiment.instructions:
            if instruction.name == 'measure':
                measurement_found = True
            elif measurement_found:
                fsp = False
        return fsp

    @staticmethod
    def __validate_unsupported_measurements(experiment: QasmQobjExperiment) -> None:
        """ When using non-FSP (not full state projection) certain measurements cannot be handled correctly because
            cQASM isn't as flexible as Qiskit in measuring to specific classical bits.
            Therefore some Qiskit constructions are not supported in QI:

            1. When a quantum register is measured to different classical registers
            2. When a classical register is used for the measurement of more than one quantum register

        Args:
            experiment: The experiment with gate operations and header.

        Raises:
            QisKitBackendError: When the circuit contains an invalid non-FSP measurement
        """
        measurements: List[List[int]] = []
        for instruction in experiment.instructions:
            if instruction.name == 'measure':
                for q, m in measurements:
                    if q == instruction.qubits[0] and m != instruction.memory[0]:
                        raise QisKitBackendError('Measurement of qubit {} to different classical registers '
                                                 'is not supported'.format(q))
                    if q != instruction.qubits[0] and m == instruction.memory[0]:
                        raise QisKitBackendError('Measurement of different qubits to the same classical register {0} '
                                                 'is not supported'.format(m))
                measurements.append([instruction.qubits[0], instruction.memory[0]])

    @staticmethod
    def _collect_measurements(experiment: QasmQobjExperiment) -> Dict[str, Any]:
        """ Determines the measured qubits and classical bits. The full-state measured
            qubits is returned when no measurements are present in the compiled circuit.

        Args:
            experiment: The experiment with gate operations and header.

        Returns:
            The dict contains measurements, which is a list of lists, for each measurement the list contains
            a list of [qubit_index, classical_bit_index], which represents the measurement of a qubit to a
            classical bit, and the second field in the dict is the number of classical bits (int).
        """
        header = experiment.header
        number_of_qubits = header.n_qubits
        number_of_clbits = header.memory_slots

        operations = experiment.instructions
        measurements = [[number_of_qubits - 1 - m.qubits[0],
                         number_of_clbits - 1 - m.memory[0]]
                        for m in operations if m.name == 'measure']
        if not measurements:
            measurements = [[index, index] for index in range(number_of_qubits)]
        return {'measurements': measurements, 'number_of_clbits': number_of_clbits}

    @staticmethod
    def __qubit_to_classical_hex(qubit_register: str, measurements: Dict[str, Any], number_of_qubits: int) -> str:
        """ This function converts the qubit register data to the hexadecimal representation of the classical state.

        Args:
            qubit_register: The measured value of the qubits represented as int.
            measurements: The dictionary contains a measured qubits/classical bits map (list) and the
                          number of classical bits (int).
            number_of_qubits: Number of qubits used in the algorithm.

        Returns:
            The hexadecimal value of the classical state.
        """
        qubit_state = ('{0:0{1}b}'.format(int(qubit_register), number_of_qubits))
        classical_state = ['0'] * measurements['number_of_clbits']
        for q, c in measurements['measurements']:
            classical_state[c] = qubit_state[q]
        classical_state_str = ''.join(classical_state)
        classical_state_hex = hex(int(classical_state_str, 2))
        return classical_state_hex

    @staticmethod
    def __convert_histogram(result: Dict[str, Any], measurements: Dict[str, Any]) -> Dict[str, float]:
        """ The quantum inspire backend always uses full state projection. The SDK user
            can measure not all qubits and change the combined classical bits. This function
            converts the result to a histogram output that represents the probabilities
            measured with the classical bits.

        Args:
            result: The result output from the quantum inspire backend with full-
                    state projection histogram output.
            measurements: The dictionary contains a measured qubits/classical bits map (list) and the
                          number of classical bits (int).

        Returns:
            The resulting full state histogram with probabilities.
        """
        output_histogram_probabilities: Dict[str, float] = defaultdict(lambda: 0)
        number_of_qubits = result['number_of_qubits']
        state_probability: Dict[str, float] = result['histogram']
        for qubit_register, probability in state_probability.items():
            classical_state_hex = QuantumInspireBackend.__qubit_to_classical_hex(qubit_register, measurements,
                                                                                 number_of_qubits)
            output_histogram_probabilities[classical_state_hex] += probability

        sorted_histogram_probabilities: List[Tuple[str, float]] = sorted(output_histogram_probabilities.items(),
                                                                         key=lambda kv: int(kv[0], 16))
        return dict(sorted_histogram_probabilities)

    def __convert_result_data(self, result: Dict[str, Any], measurements: Dict[str, Any]) -> Tuple[Dict[str, int],
                                                                                                   List[str]]:
        """ The quantum inspire backend returns the single shot values as raw data. This function
            converts this list of single shot values to hexadecimal memory data according the Qiskit spec.
            From this memory data the counts histogram is constructed by counting the single shot values.

        Note:
            When shots = 1, the backend returns an empty list as raw_data. This is a special case. In this case the
            resulting memory data consists of 1 value and the count histogram consists of 1 instance of this value.
            To determine this value a random float is generated in the range [0, 1). With this random number the
            value from this probabilities histogram is taken where the added probabilities is greater this random
            number.
            Example: probability histogram is {[0x0, 0.2], [0x3, 0.4], [0x5, 0.1], [0x6, 0.3]}.
            When random is in the range [0, 0.2) the first value of the probability histogram is taken (0x0).
            When random is in the range [0.2, 0.6) the second value of the probability histogram is taken (0x3).
            When random is in the range [0.6, 0.7) the third value of the probability histogram is taken (0x5).
            When random is in the range [0.7, 1) the last value of the probability histogram is taken (0x6).

        Args:
            result: The result output from the quantum inspire backend with full-
                    state projection histogram output.
            measurements: The dictionary contains a measured qubits/classical bits map (list) and the
                          number of classical bits (int).

        Returns:
            The result consists of two formats for the result. The first result is the histogram with count data,
            the second result is a list with converted hexadecimal memory values for each shot.
        """
        memory_data = []
        histogram_data: Dict[str, int] = defaultdict(lambda: 0)
        number_of_qubits: int = result['number_of_qubits']
        raw_data = self.__api.get_raw_data_from_result(result['id'])
        if raw_data:
            for raw_qubit_register in raw_data:
                classical_state_hex = QuantumInspireBackend.__qubit_to_classical_hex(str(raw_qubit_register),
                                                                                     measurements, number_of_qubits)
                memory_data.append(classical_state_hex)
            histogram_data = {elem: count for elem, count in Counter(memory_data).items()}
        else:
            state_probabilities = result['histogram']
            random_probability = np.random.rand()
            sum_probability = 0.0
            for qubit_register, probability in state_probabilities.items():
                sum_probability += probability
                if random_probability < sum_probability:
                    classical_state_hex = QuantumInspireBackend.__qubit_to_classical_hex(qubit_register, measurements,
                                                                                         number_of_qubits)
                    memory_data.append(classical_state_hex)
                    histogram_data[classical_state_hex] = 1
                    break

        sorted_histogram_data: List[Tuple[str, int]] = sorted(histogram_data.items(), key=lambda kv: int(kv[0], 16))
        histogram_obj = OrderedDict(sorted_histogram_data)
        return dict(histogram_obj), memory_data
