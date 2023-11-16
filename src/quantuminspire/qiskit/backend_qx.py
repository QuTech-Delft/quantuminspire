# Quantum Inspire SDK
#
# Copyright 2022 QuTech Delft
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

import copy
import io
import json
import uuid
import warnings
from collections import defaultdict, Counter
from typing import Any, Dict, List, Tuple, Optional, Union, TYPE_CHECKING

import numpy as np

from qilib.utils.serialization import serializer

from qiskit.circuit import QuantumCircuit
from qiskit.compiler import assemble
from qiskit.providers import Options, BackendV1 as Backend
from qiskit.providers.models import QasmBackendConfiguration
from qiskit.providers.models.backendconfiguration import GateConfig
from qiskit.providers.models.backendstatus import BackendStatus
from qiskit.qobj import QasmQobj, QasmQobjExperiment, QobjExperimentHeader
from qiskit.result.models import ExperimentResult, ExperimentResultData

from quantuminspire.api import QuantumInspireAPI, V1_MEASUREMENT_BLOCK_INDEX
from quantuminspire.exceptions import QiskitBackendError, ApiError
from quantuminspire.job import QuantumInspireJob
from quantuminspire.qiskit.circuit_parser import CircuitToString
from quantuminspire.qiskit.measurements import Measurements
from quantuminspire.qiskit.qi_job import QIJob
from quantuminspire.version import __version__ as quantum_inspire_version

if TYPE_CHECKING:
    from quantum_inspire_provider import QuantumInspireProvider


class QuantumInspireBackend(Backend):  # type: ignore
    DEFAULT_CONFIGURATION = QasmBackendConfiguration(
        backend_name='qi_simulator',
        backend_version=quantum_inspire_version,
        n_qubits=26,
        basis_gates=['x', 'y', 'z', 'h', 'rx', 'ry', 'rz', 's', 'sdg', 't', 'tdg', 'cx', 'ccx', 'p', 'u',
                     'id', 'swap', 'cz', 'snapshot', 'delay', 'barrier', 'reset'],
        gates=[GateConfig(name='NotUsed', parameters=['NaN'], qasm_def='NaN')],
        local=False,
        simulator=True,
        conditional=True,
        open_pulse=False,
        memory=True,
        max_shots=1024,
        max_experiments=1,
        coupling_map=[],
        multiple_measurements=False,
        parallel_computing=False
    )
    qobj_warning_issued = False

    def __init__(self, api: QuantumInspireAPI, provider: QuantumInspireProvider,
                 configuration: Optional[QasmBackendConfiguration] = None) -> None:
        """ Python implementation of a quantum simulator using Quantum Inspire API.

        :param api: The interface instance to the Quantum Inspire API.
        :param provider: Provider for this backend.
        :param configuration: The configuration of the Quantum Inspire backend. The
                configuration must implement the fields given by the QiSimulatorPy.DEFAULT_CONFIGURATION. All
                configuration fields are listed in the table below. The table rows with an asterisk specify fields which
                can have a custom value and are allowed to be changed according to the description column.

                =================== ============= =====================================================================
                Key                 Type          Description
                =================== ============= =====================================================================
                ``backend_name`` *  str           The name of the Quantum Inspire backend. The API can list the name of
                                                  each available backend using the function api.list_backend_types().
                                                  One of the listed names must be used.
                ``backend_version`` str           Backend version in the form X.Y.Z.
                ``n_qubits``        int           Number of qubits.
                ``basis_gates``     list[str]     A list of basis gates to compile to.
                ``gates``           GateConfig    List of basis gates on the backend. Not used.
                ``local``           bool          Indicates whether the system is running locally or remotely.
                ``simulator``       bool          Specifies whether the backend is a simulator or a quantum system.
                ``conditional``     bool          Backend supports conditional operations.
                ``open_pulse``      bool          Backend supports open pulse. False.
                ``memory``          bool          Backend supports memory. True.
                ``max_shots``       int           Maximum number of shots supported.
                ``max_experiments`` int           Optional: Maximum number of experiments (circuits) per job.
                ``coupling_map``    list[list]    Define the edges.
                =================== ============= =====================================================================
        """
        super().__init__(configuration=(configuration or
                                        QuantumInspireBackend.DEFAULT_CONFIGURATION),
                         provider=provider)
        self.__backend: Dict[str, Any] = api.get_backend_type_by_name(self.name())
        self.__api: QuantumInspireAPI = api

    @classmethod
    def _default_options(cls) -> Options:
        """ Returns default runtime options. Only the options that are relevant to Quantum Inspire backends are added.
        """
        return Options(shots=1024, memory=True)

    def _get_run_config(self, **kwargs: Any) -> Dict[str, Any]:
        """ Return the consolidated runtime configuration. Run arguments overwrite the values of the default runtime
        options. Run arguments (not None) that are not defined as options are added to the runtime configuration.

        :param kwargs: The runtime arguments (arguments given with the run method).

        :return:
            A dictionary of runtime arguments for the run.
        """
        run_config_dict: Dict[str, Any] = copy.copy(self.options.__dict__)
        for key, val in kwargs.items():
            if val is not None:
                run_config_dict[key] = val
        return run_config_dict

    @property
    def backend_name(self) -> str:
        return self.name()  # type: ignore

    @staticmethod
    def strtobool(value: str) -> bool:
        """Convert a string representation of truth to true (1) or false (0).
        True values are 'y', 'yes', 't', 'true', 'on', and '1'; false values
        are 'n', 'no', 'f', 'false', 'off', and '0'.  Raises ValueError if
        'val' is anything else.
        From source code python 3.11.2 (distutils/util.py) which is deprecated from 3.12
        """
        val = value.lower()
        if val in ('y', 'yes', 't', 'true', 'on', '1'):
            return bool(1)
        elif val in ('n', 'no', 'f', 'false', 'off', '0'):
            return bool(0)
        else:
            raise ValueError(f"invalid truth value {value}")

    def run(self,
            run_input: Union[QasmQobj, QuantumCircuit, List[QuantumCircuit]],
            shots: Optional[int] = None,
            memory: Optional[bool] = None,
            allow_fsp: bool = True,
            **run_config: Dict[str, Any]
            ) -> QIJob:
        """ Submits a quantum job to the Quantum Inspire platform.

        The execution is asynchronous, and a handle to a job instance is returned.

        :param run_input: An individual or a list of :class:`~qiskit.circuits.QuantumCircuit` objects to run
                on the backend. A :class:`~qiskit.qobj.QasmQobj` object is also supported but is deprecated.
        :param shots: Number of repetitions of each circuit, for sampling. Default: 1024
                or ``max_shots`` from the backend configuration, whichever is smaller.
        :param memory: If ``True``, per-shot measurement bitstrings are returned.
        :param allow_fsp: When ``False``, never submit as full_state_projection. This means: turn off possible
                optimization when running a deterministic circuit on a simulator backend.
        :param run_config: Extra arguments used to configure the run.

        :return:
            A job that has been submitted.

        Raises:
            ApiError: If an unexpected error occurred while submitting the job to the backend.
            QiskitBackendError: If the circuit is invalid for the Quantum Inspire backend.
        """
        run_config_dict = self._get_run_config(
            shots=shots,
            memory=memory,
            **run_config)

        if isinstance(run_input, QasmQobj):
            if not self.qobj_warning_issued:
                warnings.warn("Passing a Qobj to QuantumInspireBackend.run is deprecated and will "
                              "be removed in a future release. Please pass in circuits "
                              "instead.", DeprecationWarning,
                              stacklevel=3)
                self.qobj_warning_issued = True
            qobj = run_input
        else:
            qobj = assemble(run_input, self, **run_config_dict)

        if isinstance(allow_fsp, str):
            allow_fsp = QuantumInspireBackend.strtobool(allow_fsp)

        number_of_shots = qobj.config.shots
        self.__validate_number_of_shots(number_of_shots)

        identifier = uuid.uuid1()
        project_name = f'qi-sdk-project-{identifier}'
        project: Optional[Dict[str, Any]]
        project = self.__api.create_project(project_name, number_of_shots, self.__backend)
        if not allow_fsp:
            # method run was called explicitly with allow_fsp = False. That is: full_state_projection is turned off.
            # No need to attend the user that the execution may take longer
            self.__api.show_fsp_warning(False)
        try:
            experiments = qobj.experiments
            job = QIJob(self, str(project['id']), self.__api)
            for experiment in experiments:
                measurements = Measurements.from_experiment(experiment)
                if Backend.configuration(self).conditional:
                    self.__validate_nr_of_clbits_conditional_gates(experiment)
                full_state_projection = allow_fsp and Backend.configuration(self).simulator and \
                    self.__validate_full_state_projection(experiment)
                if not full_state_projection:
                    measurements.validate_unsupported_measurements()
                job_for_experiment = self._submit_experiment(experiment, number_of_shots, measurements, project=project,
                                                             full_state_projection=full_state_projection)
                job.add_job(job_for_experiment)
                if project is not None and job_for_experiment.get_project_identifier() != project['id']:
                    self.__api.delete_project(int(project['id']))
                    project = None
                    job.set_job_id(str(job_for_experiment.get_project_identifier()))
        except (ApiError, QiskitBackendError) as error:
            # delete the empty project
            if project is not None:
                self.__api.delete_project(int(project['id']))
            raise error

        job.experiments = experiments
        return job

    def status(self) -> BackendStatus:
        """ Return the backend status. Pending jobs is always 0. This information is currently not known.

        Returns:
            BackendStatus: the status of the backend. Pending jobs is always 0.
        """
        backend: Dict[str, Any] = self.__api.get_backend_type_by_name(self.name())
        return BackendStatus(
            backend_name=self.name(),
            backend_version=quantum_inspire_version,
            operational=backend["status"] != "OFFLINE",
            pending_jobs=0,
            status_msg=backend["status_message"],
        )

    def retrieve_job(self, job_id: str) -> QIJob:
        """ Retrieve a specified job by its job_id.

        :param job_id: The job id.

        :return:
            The job that has been retrieved.

        :raises QiskitBackendError: If job not found or error occurs during retrieval of the job.
        """
        try:
            self.__api.get_project(int(job_id))
        except (ApiError, ValueError):
            raise QiskitBackendError(f"Could not retrieve job with job_id '{job_id}' ")
        return QIJob(self, job_id, self.__api)

    def _generate_cqasm(self, experiment: QasmQobjExperiment, measurements: Measurements,
                        full_state_projection: bool = False) -> str:
        """ Generates the cQASM from the Qiskit experiment.

        :param experiment: The experiment that contains instructions to be converted to cQASM.
        :param measurements: The measurement instance containing measurement information and measurement functionality.
        :param full_state_projection: When True, measurement commands are not added to the resulting cQASM

        :raises QiskitBackendError: If a Qiskit instruction is not in the basis gates set of Quantum Inspire backend.

        :return:
            The cQASM code that can be sent to the Quantum Inspire API.

        """
        parser = CircuitToString(Backend.configuration(self).basis_gates, measurements, full_state_projection)
        number_of_qubits = experiment.header.n_qubits
        instructions = experiment.instructions
        with io.StringIO() as stream:
            stream.write('version 1.0\n')
            stream.write('# cQASM generated by QI backend for Qiskit\n')
            stream.write(f'qubits {number_of_qubits}\n')
            for instruction in instructions:
                parser.parse(stream, instruction)
            return stream.getvalue()

    def generate_user_data(self, experiment: QasmQobjExperiment, measurements: Measurements) -> Dict[str, Any]:
        """
        Generates the user_data for this experiment. The user_data is saved together with the job and consists of
        data that is necessary to process the result of the experiment correctly.

        :param experiment: The experiment that contains the header information to save in the user data.
        :param measurements: The measurement instance containing measurement information and measurement functionality.

        :return:
            A structure with user data that is needed to process the result of the experiment.
        """
        return {'name': experiment.header.name, 'metadata': serializer.serialize(experiment.header.metadata),
                'qubit_labels': experiment.header.qubit_labels, 'qreg_sizes': experiment.header.qreg_sizes,
                'clbit_labels': experiment.header.clbit_labels, 'creg_sizes': experiment.header.creg_sizes,
                'global_phase': experiment.header.global_phase, 'memory_slots': experiment.header.memory_slots,
                'measurements': measurements.to_dict()}

    def _submit_experiment(self, experiment: QasmQobjExperiment, number_of_shots: int,
                           measurements: Measurements,
                           project: Optional[Dict[str, Any]] = None,
                           full_state_projection: bool = False) -> QuantumInspireJob:
        compiled_qasm = self._generate_cqasm(experiment, measurements, full_state_projection=full_state_projection)
        user_data = self.generate_user_data(experiment, measurements)
        quantum_inspire_job = self.__api.execute_qasm_async(compiled_qasm, backend_type=self.__backend,
                                                            number_of_shots=number_of_shots, project=project,
                                                            job_name=experiment.header.name,
                                                            user_data=json.dumps(user_data),
                                                            full_state_projection=full_state_projection)
        return quantum_inspire_job

    def _get_experiment_results(self, jobs: List[Dict[str, Any]]) -> List[ExperimentResult]:
        """ Get results from experiments from the Quantum Inspire platform for one or more jobs.

        :param jobs: A list of jobs

        :raises QiskitBackendError: If an error occurred while executing the job on the Quantum Inspire backend.

        :return:
            A list of experiment results; containing the data, execution time, status, etc. for the list of jobs.
        """
        results = [self.__api.get_result_from_job(job['id']) for job in jobs]
        experiment_results = []
        for result, job in zip(results, jobs):
            if not result.get('histogram', [{}])[0]:
                raise QiskitBackendError(
                    f"Result from backend contains no histogram data!\n{result.get('raw_text')}")

            if not job.get('user_data', ''):
                raise QiskitBackendError(
                    f"Job '{job.get('id')}' from backend contains no user data. "
                    f"This job was not submitted by the SDK")

            user_data = json.loads(str(job.get('user_data')))
            user_data['metadata'] = serializer.unserialize(user_data.get('metadata'))
            measurements = Measurements.from_dict(user_data.pop('measurements'))
            histogram_obj, memory_data = self.__convert_result_data(result, measurements)
            full_state_histogram_obj = self.__convert_histogram(result, measurements)
            calibration = self.__api.get_calibration_from_result(result['id'])
            experiment_result_data =\
                ExperimentResultData(counts=histogram_obj[V1_MEASUREMENT_BLOCK_INDEX],
                                     memory=memory_data[V1_MEASUREMENT_BLOCK_INDEX],
                                     probabilities=full_state_histogram_obj[V1_MEASUREMENT_BLOCK_INDEX],
                                     counts_multiple_measurement=histogram_obj,
                                     memory_multiple_measurement=memory_data,
                                     probabilities_multiple_measurement=full_state_histogram_obj,
                                     calibration=calibration)
            header = QobjExperimentHeader.from_dict(user_data)
            experiment_result_dictionary = {'name': job.get('name'), 'seed': 42, 'shots': job.get('number_of_shots'),
                                            'data': experiment_result_data, 'status': 'DONE', 'success': True,
                                            'time_taken': result.get('execution_time_in_seconds'), 'header': header}
            experiment_results.append(ExperimentResult(**experiment_result_dictionary))
        return experiment_results

    def get_experiment_results_from_latest_run(self, qi_job: QIJob) -> List[ExperimentResult]:
        """
        :param qi_job: A job that has already been submitted and which execution is completed.

        :return:
            A list of experiment results; containing the data, execution time, status, etc. for the experiments in the
            latest job run in the Quantum Inspire project.
        """
        jobs = qi_job.get_jobs()
        return self._get_experiment_results(jobs)

    def get_experiment_results_from_all_jobs(self, qi_job: QIJob) -> List[ExperimentResult]:
        """
        :param qi_job: A job that has already been submitted and which execution is completed.

        :return:
            A list of experiment results; containing the data, execution time, status, etc. for all the experiments in
            all the job runs of the Quantum Inspire project.
        """
        jobs = self.__api.get_jobs_from_project(int(qi_job.job_id()))
        return self._get_experiment_results(jobs)

    def __validate_number_of_shots(self, number_of_shots: int) -> None:
        """ Checks whether the number of shots has a valid value.

        :param number_of_shots: The number of shots to check.

        :raises QiskitBackendError: When the value is not correct.
        """
        if number_of_shots < 1 or number_of_shots > self.__backend['max_number_of_shots']:
            raise QiskitBackendError(f'Invalid shots (number_of_shots={number_of_shots})')

    def __validate_nr_of_clbits_conditional_gates(self, experiment: QasmQobjExperiment) -> None:
        """ Validate the number of classical bits in the algorithm when conditional gates are used

        1.  When binary controlled gates are used and the number of classical registers
            is greater than the number of qubits an error is raised.

            When using binary controlled gates in Qiskit, we can have something like:

            .. code::

                q = QuantumRegister(2)
                c = ClassicalRegister(4)
                circuit = QuantumCircuit(q, c)
                circuit.h(q[0]).c_if(c, 15)

            Because cQASM has the same number of classical registers as qubits (2 in this case),
            this circuit cannot be translated to valid cQASM.

        :param experiment: The experiment with gate operations and header.

        :raises QiskitBackendError: When the value is not correct.
        """
        header = experiment.header
        number_of_qubits = header.n_qubits
        number_of_clbits = header.memory_slots

        if number_of_clbits > number_of_qubits:
            if any(hasattr(instruction, 'conditional') for instruction in experiment.instructions):
                # no problem when there are no conditional gate operations
                raise QiskitBackendError('Number of classical bits must be less than or equal to the'
                                         ' number of qubits when using conditional gate operations')

    @staticmethod
    def __validate_full_state_projection(experiment: QasmQobjExperiment) -> bool:
        """ Determine if full state projection can be used

        FSP (Full State Projection) can be used when no measurements are found in the circuit or when no
        other gates are found after measurements.

        :param experiment: The experiment with gate operations and header.

        :return:
            True when FSP can be used, otherwise False.
        """
        fsp = True
        measurement_found = False
        for instruction in experiment.instructions:
            if instruction.name == 'measure':
                measurement_found = True
            elif measurement_found:
                fsp = False
                break

        return fsp

    @staticmethod
    def __convert_histogram(result: Dict[str, Any], measurements: Measurements) -> List[Dict[str, float]]:
        """Convert histogram

        The Quantum Inspire backend always measures a qubit to the respective classical bit. The SDK user
        can measure not all qubits and change the combined classical bits. This function
        converts the result to a histogram output that represents the probabilities measured with the classical bits.

        :param result: The result output from the Quantum Inspire backend with backend histogram output.
        :param measurements: measurement instance containing measurement information and measurement functionality.

        :return:
            The resulting full state histogram with probabilities.
        """
        result_histogram_probabilities: List[Dict[str, float]] = []
        for state_probability in result['histogram']:
            output_histogram_probabilities: Dict[str, float] = defaultdict(lambda: 0)
            for qubit_register, probability in state_probability.items():
                classical_state_hex = measurements.qubit_to_classical_hex(qubit_register)
                output_histogram_probabilities[classical_state_hex] += probability

            sorted_histogram_probabilities: List[Tuple[str, float]] = sorted(output_histogram_probabilities.items(),
                                                                             key=lambda kv: int(kv[0], 16))
            result_histogram_probabilities.append(dict(sorted_histogram_probabilities))

        return result_histogram_probabilities

    @staticmethod
    def __raw_qubit_register_to_raw_data_value(raw_qubit_register: List[int], number_of_qubits: int) -> int:
        """
        Convert measured raw data to integer representation. The measured qubits can have 3 values, 0, 1, or None
        meaning not measured
        """
        raw_data_value = 0
        for register_index in range(number_of_qubits):
            if raw_qubit_register[register_index] == 1:
                raw_data_value += 2 ** register_index

        return raw_data_value

    @staticmethod
    def __convert_result_single_shot(result: Dict[str, Any],
                                     measurements: Measurements) -> Tuple[List[Dict[str, int]],
                                                                          List[List[str]]]:
        """Convert result data

        The Quantum Inspire backend returns the single shot values as raw data. This function
        converts this list of single shot values to hexadecimal memory data according the Qiskit spec.
        From this memory data the counts histogram is constructed by counting the single shot values.

        .. note::
            When shots = 1, the backend returns an empty list as raw_data. This is a special case. In this case the
            resulting memory data consists of 1 value and the count histogram consists of 1 instance of this value.
            To determine this value a random float is generated in the range [0, 1). With this random number the
            value from this probabilities histogram is taken where the added probabilities is greater this random
            number.

            Example:

                Probability histogram is ``{[0x0, 0.2], [0x3, 0.4], [0x5, 0.1], [0x6, 0.3]}``.

                When random is in the range [0, 0.2) the first value of the probability histogram is taken (0x0).

                When random is in the range [0.2, 0.6) the second value of the probability histogram is taken (0x3).

                When random is in the range [0.6, 0.7) the third value of the probability histogram is taken (0x5).

                When random is in the range [0.7, 1) the last value of the probability histogram is taken (0x6).

        :param result: The result output from the Quantum Inspire backend with full-
                       state projection histogram output.
        :param measurements: The measurement instance containing measurement information and measurement functionality.

        :return:
            The result consists of two formats for the result. The first result is the histogram with count data,
            the second result is a list with converted hexadecimal memory values for each shot.
        """
        result_memory_data = []
        result_histogram_data: List[Dict[str, int]] = []

        random_probability = np.random.rand()
        for state_probabilities in result['histogram']:
            memory_data = []
            histogram_data = defaultdict(lambda: 0)
            sum_probability = 0.0
            for qubit_register, probability in state_probabilities.items():
                sum_probability += probability
                if random_probability < sum_probability:
                    classical_state_hex = measurements.qubit_to_classical_hex(qubit_register)
                    memory_data.append(classical_state_hex)
                    histogram_data[classical_state_hex] = 1
                    break
            sorted_histogram_data = sorted(histogram_data.items(),
                                           key=lambda kv: int(kv[0], 16))
            result_histogram_data.append(dict(sorted_histogram_data))
            result_memory_data.append(memory_data)
        return result_histogram_data, result_memory_data

    def __convert_result_multiple_shots(self, result: Dict[str, Any], measurements: Measurements,
                                        raw_data_list: List[List[Any]]) -> Tuple[List[Dict[str, int]],
                                                                                 List[List[str]]]:
        """Convert result data

        The Quantum Inspire backend returns the single shot values as raw data. This function
        converts this list of single shot values to hexadecimal memory data according the Qiskit spec.
        From this memory data the counts histogram is constructed by counting the single shot values.

        :param result: The result output from the Quantum Inspire backend with full state projection histogram output.
        :param measurements: The measurement instance containing measurement information and measurement functionality.
        :param raw_data_list: The raw data from the result for this experiment.

        :return:
            The result consists of two formats for the result. The first result is the histogram with count data,
            the second result is a list with converted hexadecimal memory values for each shot.
        """
        result_memory_data = []
        result_histogram_data: List[Dict[str, int]] = []
        number_of_qubits: int = result['number_of_qubits']

        nr_of_measurement_blocks = len(raw_data_list[0])
        for measurement_block_index in range(nr_of_measurement_blocks):
            memory_data = []
            for raw_data in raw_data_list:
                raw_qubit_register = raw_data[measurement_block_index]
                raw_data_value = self.__raw_qubit_register_to_raw_data_value(raw_qubit_register,
                                                                             number_of_qubits)
                classical_state_hex = measurements.qubit_to_classical_hex(str(raw_data_value))
                memory_data.append(classical_state_hex)
            histogram_data = {elem: count for elem, count in Counter(memory_data).items()}
            sorted_histogram_data = sorted(histogram_data.items(),
                                           key=lambda kv: int(kv[0], 16))
            result_histogram_data.append(dict(sorted_histogram_data))
            result_memory_data.append(memory_data)

        return result_histogram_data, result_memory_data

    def __convert_result_data(self, result: Dict[str, Any], measurements: Measurements) -> Tuple[List[Dict[str, int]],
                                                                                                 List[List[str]]]:
        """Convert result data

        The Quantum Inspire backend returns the single shot values as raw data. The method
        __convert_result_multiple_shots converts this list of single shot values to hexadecimal memory data according
        the Qiskit spec.
        From this memory data the counts histogram is constructed by counting the single shot values.

        When shots = 1, the backend returns an empty list as raw_data. This is a special case handled in method
        __convert_result_single_shot.

        :param result: The result output from the Quantum Inspire backend with full state projection histogram output.
        :param measurements: The measurement instance containing measurement information and measurement functionality.

        :return:
            The result consists of two formats for the result. The first result is the histogram with count data,
            the second result is a list with converted hexadecimal memory values for each shot.
        """
        raw_data_list = self.__api.get_raw_data_from_result(result['id'])
        if len(raw_data_list) > 0 and raw_data_list[0]:
            result_histogram_data, result_memory_data = self.__convert_result_multiple_shots(result, measurements,
                                                                                             raw_data_list)
        else:
            result_histogram_data, result_memory_data = self.__convert_result_single_shot(result, measurements)

        return result_histogram_data, result_memory_data
