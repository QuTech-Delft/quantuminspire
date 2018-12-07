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
import logging
import uuid
from collections import defaultdict

from qiskit.backends import BaseBackend
from qiskit.qobj import ExperimentResult, Qobj, QobjExperiment

from quantuminspire.exceptions import QisKitBackendError
from quantuminspire.qiskit.circuit_parser import CircuitToString
from quantuminspire.qiskit.qi_job import QIJob


class QuantumInspireBackend(BaseBackend):
    DEFAULT_CONFIGURATION = {
        'name': 'qi_simulator',
        'url': 'https://www.quantum-inspire.com/',
        'description': 'A Quantum Inspire Simulator for QASM files',
        'qi_backend_name': 'QX single-node simulator',
        'basis_gates': 'x,y,z,h,s,cx,ccx,u1,u2,u3,id,snapshot',
        'coupling_map': 'all-to-all',
        'simulator': True,
        'local': False
    }

    def __init__(self, api, configuration=None, logger=logging):
        """ Python implementation of a quantum simulator using Quantum Inspire API.

        Args:
            api (QuantumInspireApi): The interface instance to the Quantum Inspire API.
            configuration (dict, optional): The configuration of the quantum inspire backend. The configuration must
                implement the fields given by the QiSimulatorPy.DEFAULT_CONFIGURATION. All configuration fields are
                listed in the table below. The table rows with an asterisk specify fields which can have a custom
                value and are allowed to be changed according to the description column.

                | key                    | description
                |------------------------|----------------------------------------------------------------------------
                | name (str)*            | The name of the quantum inspire backend. The API can list the name of each
                                            available backend using the function api.list_backend_types(). One of the
                                            listed names must be used.
                | url (str)              | The URL of the server for connecting to the backend system. Not used.
                | description (str)*     | A short description of the configuration and system.
                | basis_gates (str)      | A comma-separated set of basis gates to compile to.
                | coupling_map (dict)    | A map to target the connectivity for specific device. Currently not used.
                | simulator (bool)       | Specifies whether the backend is a simulator or a quantum system. Not used.
                | local (bool)           | Indicates whether the system is running locally or remotely. Not used.
        """

        super().__init__(configuration or QuantumInspireBackend.DEFAULT_CONFIGURATION, provider='QuTech Delft')
        self.__backend = api.get_backend_type_by_name(self.name())
        self.__logger = logger
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
        self.__logger.info('run')
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

    def _generate_cqasm(self, experiment):
        """ Generates the CQASM from the qiskit experiment.

        Args: experiment (QobjExperiment): The experiment that contains instructions to be converted to cqasm

        Returns:
            str: The CQASM code that can be sent to the Quantum Inspire API.
        """
        parser = CircuitToString()

        number_of_qubits = experiment.header.number_of_qubits

        instructions = experiment.instructions
        self.__logger.info('generate_cqasm: %d qubits' % number_of_qubits)

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
        user_data = json.dumps(measurements)
        job_id = self.__api.execute_qasm_async(compiled_qasm, backend_type=self.__backend,
                                               number_of_shots=number_of_shots, project=project,
                                               job_name=experiment.header.name, user_data=user_data)
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

            measurements = json.loads(job.get('user_data'))
            histogram = QuantumInspireBackend.__convert_histogram(result, measurements, result['number_of_qubits'],
                                                                  job['number_of_shots'])

            experiment_result_data = {'counts': histogram, 'snapshots': {}}

            experiment_result_dictionary = {'name': job.get('name'), 'seed': None, 'shots': job.get('number_of_shots'),
                                            'data': experiment_result_data, 'status': 'DONE', 'success': True,
                                            'time_taken': result.get('execution_time_in_seconds')}
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
        number_of_clbits = experiment.header.number_of_clbits
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
            compiled_circuit (dict): The circuit properties with gate operations and header.

        Returns:
            List: A list of lists, for each measurement List contains a list of [qubit_index, classical_bit_index]
        """
        header = experiment.header
        number_of_qubits = header.number_of_qubits
        number_of_clbits = header.number_of_clbits

        operations = experiment.instructions
        measurements = [[number_of_qubits - 1 - m.qubits[0],
                         number_of_clbits - 1 - m.clbits[0]]
                        for m in operations if m.name == 'measure']
        if measurements:
            used_classical_bits = [item[1] for item in measurements]
            if any([bit for bit in used_classical_bits if used_classical_bits.count(bit) > 1]):
                raise QisKitBackendError("Classical bit is used to measure multiple qubits!")
        else:
            measurements = [[index, index] for index in range(number_of_qubits)]
        return measurements

    @staticmethod
    def __convert_histogram(result, measurements, number_of_qubits, number_of_shots):
        """ The quantum inspire backend always uses full state projection. The SDK user
            can measure not all qubits and change the combined classical bits. This function
            converts the histogram output, such that it represents the counts measured with the
            classical bits.

            Args:
                result (dict): The result output from the quantum inspire backend with full-
                               state projection histogram output.
                measurements (dict): The circuit properties with gate operations and header.
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
            converter_list = [[item[1], qubit_state[item[0]]] for item in measurements]
            converter_list.sort(key=lambda x: x[0])
            classical_state = ''.join([item[1] for item in converter_list])
            output_histogram[classical_state] += counts

        return dict(output_histogram)
