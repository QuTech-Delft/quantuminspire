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
from collections import defaultdict, OrderedDict

from coreapi.exceptions import ErrorMessage
from qiskit.providers import BaseBackend
from qiskit.providers.models import BackendConfiguration
from qiskit.providers.models.backendconfiguration import GateConfig
from qiskit.qobj import Qobj, QobjExperiment
from qiskit.result.models import ExperimentResult, ExperimentResultData
from qiskit.validation.base import Obj

from quantuminspire.exceptions import QisKitBackendError
from quantuminspire.qiskit.circuit_parser import CircuitToString
from quantuminspire.qiskit.qi_job import QIJob
from quantuminspire.version import __version__ as quantum_inspire_version


class QuantumInspireBackend(BaseBackend):
    DEFAULT_CONFIGURATION = BackendConfiguration(
        backend_name='qi_simulator',
        backend_version=quantum_inspire_version,
        n_qubits=26,
        basis_gates=['x', 'y', 'z', 'h', 's', 'cx', 'ccx', 'u1', 'u2', 'u3', 'id', 'snapshot'],
        gates=[GateConfig(name='NotUsed', parameters=['NaN'], qasm_def='NaN')],
        conditional=False,
        simulator=True,
        local=False,
        memory=True,
        open_pulse=False,
        max_shots=1024
    )

    def __init__(self, api, provider, configuration=None):
        """ Python implementation of a quantum simulator using Quantum Inspire API.

        Args:
            api (QuantumInspireApi): The interface instance to the Quantum Inspire API.
            provider (QuantumInspireProvider): Provider for this backend.
            configuration (BackendConfiguration, optional): The configuration of the quantum inspire backend. The
                configuration must implement the fields given by the QiSimulatorPy.DEFAULT_CONFIGURATION. All
                configuration fields are listed in the table below. The table rows with an asterisk specify fields which
                can have a custom value and are allowed to be changed according to the description column.

                | key                    | description
                |------------------------|----------------------------------------------------------------------------
                | name (str)*            | The name of the quantum inspire backend. The API can list the name of each
                                            available backend using the function api.list_backend_types(). One of the
                                            listed names must be used.
                | basis_gates (str)      | A comma-separated set of basis gates to compile to.
                | gates (GateConfig):    | List of basis gates on the backend. Not used.
                | conditional (bool)     | Backend supports conditional operations.
                | memory (bool):         | Backend supports memory. False.
                | simulator (bool)       | Specifies whether the backend is a simulator or a quantum system. Not used.
                | local (bool)           | Indicates whether the system is running locally or remotely. Not used.
                | open_pulse (bool)      | Backend supports open pulse. False.
                | max_shots (int)        | Maximum number of shots supported.
        """

        super().__init__(configuration=(configuration or
                                        QuantumInspireBackend.DEFAULT_CONFIGURATION),
                         provider=provider)
        self.__backend = api.get_backend_type_by_name(self.name())
        self.__api = api

    @property
    def backend_name(self):
        return self.name()

    def run(self, qobj):
        """ Submits a quantum job to the Quantum Inspire platform.

        Args:
            qobj (Qobj): The quantum job with the qiskit algorithm and quantum inspire backend.

        Returns:
            QIJob: A job that has been submitted.
        """
        QuantumInspireBackend.__validate(qobj)
        number_of_shots = qobj.config.shots

        identifier = uuid.uuid1()
        project_name = 'qi-sdk-project-{}'.format(identifier)
        project = self.__api.create_project(project_name, number_of_shots, self.__backend)
        experiments = qobj.experiments
        job = QIJob(self, str(project['id']), self.__api)
        [self._submit_experiment(experiment, number_of_shots, project=project) for experiment in experiments]
        job.experiments = experiments
        return job

    def retrieve_job(self, job_id):
        """
        Retrieve a specified job by its job_id

        Args:
            job_id (str): The job id.

        Returns:
            QIJob: The job that has been retrieved.

        Raises:
            QisKitBackendError: If job not found or error occurs during retrieval of the job.
        """
        try:
            self.__api.get_project(job_id)
        except ErrorMessage:
            raise QisKitBackendError("Could not retrieve job with job_id '{}' ".format(job_id))
        return QIJob(self, job_id, self.__api)

    def _generate_cqasm(self, experiment):
        """ Generates the CQASM from the qiskit experiment.

        Args: experiment (QobjExperiment): The experiment that contains instructions to be converted to cqasm

        Returns:
            str: The CQASM code that can be sent to the Quantum Inspire API.
        """
        parser = CircuitToString()

        number_of_qubits = experiment.header.n_qubits

        instructions = experiment.instructions

        with io.StringIO() as stream:
            stream.write('version 1.0\n')
            stream.write('# cqasm generated by QI backend for QisKit\n')
            stream.write('qubits %d\n' % number_of_qubits)
            for instruction in instructions:
                gate_name = '_%s' % instruction.name.lower()
                gate_function = getattr(parser, gate_name)
                line = gate_function(instruction.as_dict())
                if isinstance(line, str):
                    stream.write(line)

            return stream.getvalue()

    def _submit_experiment(self, experiment, number_of_shots, project=None):
        compiled_qasm = self._generate_cqasm(experiment)
        measurements = self._collect_measurements(experiment)
        user_data = {'name': experiment.header.name, 'memory_slots': experiment.header.memory_slots,
                     'creg_sizes': experiment.header.creg_sizes, 'measurements': measurements}
        job_id = self.__api.execute_qasm_async(compiled_qasm, backend_type=self.__backend,
                                               number_of_shots=number_of_shots, project=project,
                                               job_name=experiment.header.name, user_data=json.dumps(user_data))
        return job_id

    def get_experiment_results(self, qi_job):
        """
        Get results from experiments from the Quantum-inspire platform.
        Args:
            qi_job (QIJob): A job that has already been submitted and which execution is completed.

        Raises:
            QisKitBackendError: if an error occurred during execution by the backend.

        Returns:
            List: A list of experiment results; containing the data, execution time, status, etc.
        """

        jobs = self.__api.get_jobs_from_project(qi_job.job_id())
        results = [self.__api.get(job['results']) for job in jobs]
        experiment_results = []
        for result, job in zip(results, jobs):
            if not result.get('histogram', {}):
                raise QisKitBackendError(
                    'Result from backend contains no histogram data!\n{}'.format(result.get('raw_text')))

            user_data = json.loads(job.get('user_data'))
            measurements = user_data.pop('measurements')
            histogram = QuantumInspireBackend.__convert_histogram(result, measurements, result['number_of_qubits'],
                                                                  job['number_of_shots'])
            histogram_obj = Obj.from_dict(histogram)
            experiment_result_data = ExperimentResultData(counts=histogram_obj)
            header = Obj.from_dict(user_data)
            experiment_result_dictionary = {'name': job.get('name'), 'seed': 42, 'shots': job.get('number_of_shots'),
                                            'data': experiment_result_data, 'status': 'DONE', 'success': True,
                                            'time_taken': result.get('execution_time_in_seconds'), 'header': header}
            experiment_results.append(ExperimentResult(**experiment_result_dictionary))
        return experiment_results

    @staticmethod
    def __validate(job):
        """ Validates the number of shots, classical bits and compiled qiskit circuits.

        Args:
            job (QObj): The quantum job with the qiskit algorithm and quantum inspire backend.
        """
        QuantumInspireBackend.__validate_number_of_shots(job)

        for experiment in job.experiments:
            QuantumInspireBackend.__validate_number_of_clbits(experiment)
            QuantumInspireBackend.__validate_no_gates_after_measure(experiment)

    @staticmethod
    def __validate_number_of_shots(job):
        """ Checks whether the number of shots has a valid value.

        Args:
            job (QObj): The quantum job with the qiskit algorithm and quantum inspire backend.

        Raises:
            QisKitBackendError: When the value is not correct.
        """
        number_of_shots = job.config.shots
        if number_of_shots < 1:
            raise QisKitBackendError('Invalid shots (number_of_shots={})'.format(number_of_shots))

    @staticmethod
    def __validate_number_of_clbits(experiment):
        """ Checks whether the number of classical bits has a valid value.

        Args:
            experiment (QobjExperiment): The experiment with gate operations and header.

        Raises:
            QisKitBackendError: When the value is not correct.
        """
        number_of_clbits = experiment.header.memory_slots
        if number_of_clbits < 1:
            raise QisKitBackendError("Invalid amount of classical bits ({})!".format(number_of_clbits))

    @staticmethod
    def __validate_no_gates_after_measure(experiment):
        """ Checks whether the number of classical bits has a valid value.

        Args:
            experiment (QobjExperiment): The experiment with gate operations and header.

        Raises:
            QisKitBackendError: When the value is not correct.
        """
        measured_qubits = []
        for instruction in experiment.instructions:
            for qubit in instruction.qubits:
                if instruction.name == 'measure':
                    measured_qubits.append(qubit)
                elif qubit in measured_qubits:
                    raise QisKitBackendError('Operation after measurement!')

    @staticmethod
    def _collect_measurements(experiment):
        """ Determines the measured qubits and classical bits. The full-state measured
            qubits is returned when no measurements are present in the compiled circuit.

        Args:
            experiment (QobjExperiment): The experiment with gate operations and header.

        Returns:
            List: A list of lists, for each measurement List contains a list of [qubit_index, classical_bit_index]
        """
        header = experiment.header
        number_of_qubits = header.n_qubits
        number_of_clbits = header.memory_slots

        operations = experiment.instructions
        measurements = [[number_of_qubits - 1 - m.qubits[0],
                         number_of_clbits - 1 - m.memory[0]]
                        for m in operations if m.name == 'measure']
        if measurements:
            used_classical_bits = [item[1] for item in measurements]
            if any([bit for bit in used_classical_bits if used_classical_bits.count(bit) > 1]):
                raise QisKitBackendError("Classical bit is used to measure multiple qubits!")
        else:
            measurements = [[index, index] for index in range(number_of_qubits)]
        return {'measurements': measurements, 'number_of_clbits': number_of_clbits}

    @staticmethod
    def __convert_histogram(result, measurements, number_of_qubits, number_of_shots):
        """ The quantum inspire backend always uses full state projection. The SDK user
            can measure not all qubits and change the combined classical bits. This function
            converts the histogram output, such that it represents the counts measured with the
            classical bits.

            Args:
                result (dict): The result output from the quantum inspire backend with full-
                               state projection histogram output.
                measurements (dict): Measured qubits/classical bits map and number of classical bits
                number_of_qubits (int): number of qubits used in the algorithm
                number_of_shots (int): The number of times the algorithm is executed.

            Returns:
                Dict: The result with converted histogram.
        """
        histogram = {}
        state_probability = result['histogram']
        for qubit_register, probability in state_probability.items():
            qubit_state = ('{0:0{1}b}'.format(int(qubit_register), number_of_qubits))
            histogram[qubit_state] = probability * number_of_shots

        output_histogram = defaultdict(lambda: 0)
        for qubit_state, counts in histogram.items():
            classical_state = ['0'] * measurements['number_of_clbits']
            for q, c in measurements['measurements']:
                classical_state[c] = qubit_state[q]
            classical_state = ''.join(classical_state)
            classical_state_hex = hex(int(classical_state, 2))
            output_histogram[classical_state_hex] += int(counts)

        return OrderedDict(sorted(output_histogram.items(), key=lambda kv: int(kv[0], 16)))
