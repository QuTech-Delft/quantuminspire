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
import logging
import time
import uuid
from collections import defaultdict

from qiskit._result import Result
from qiskit.backends import BaseBackend
from quantuminspire.exceptions import QisKitBackendError
from quantuminspire.qiskit.circuit_parser import CircuitToString


class QiSimulatorPy(BaseBackend):
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
                | name (str)*            | The name of the simulator or quantum system.
                | url (str)              | The URL of the server for connecting to the backend system. Not used.
                | description (str)*     | A short description of the configuration and system.
                | qi_backend_name (str)* | The name of the quantum inspire backend. The API can list the name of each
                                           available backend using the function api.list_backend_types(). One of the
                                           listed names must be used.
                | basis_gates (str)      | A comma-separated set of basis gates to compile to.
                | coupling_map (dict)    | A map to target the connectivity for specific device. Currently not used.
                | simulator (bool)       | Specifies whether the backend is a simulator or a quantum system. Not used.
                | local (bool)           | Indicates whether the system is running locally or remotely. Not used.
        """
        super().__init__(configuration or QiSimulatorPy.DEFAULT_CONFIGURATION)
        self.__backend_name = self.configuration['qi_backend_name']
        self.__backend = api.get_backend_type_by_name(self.__backend_name)
        self.__logger = logger
        self.__api = api

    def run(self, job):
        """ Runs a quantum job on the Quantum Inspire platform.

        Args:
            job (dict): The quantum job with the qiskit algorithm and quantum inspire backend.

        Returns:
            Result: The result of the executed job.
        """
        start_time = time.time()

        QiSimulatorPy.__validate(job)
        circuits = job['circuits']
        number_of_shots = job['config']['shots']
        job_identifier = str(uuid.uuid4())
        result_list = [self._run_circuit(circuit, number_of_shots) for circuit in circuits]

        execution_time = time.time() - start_time
        result = {'backend': self.__backend_name, 'id': job['id'], 'job_id': job_identifier,
                  'result': result_list, 'status': 'COMPLETED', 'success': True,
                  'time_taken': execution_time}
        return Result(result)

    def _generate_cqasm(self, compiled_circuits):
        """ Generates the CQASM from the qiskit algorithm.

        Args: compiled_circuits (dict): The compiled circuits from qiskit.

        Returns:
            str: The CQASM code that can be sent to the Quantum Inspire API.
        """
        parser = CircuitToString()
        number_of_qubits = compiled_circuits['header']['number_of_qubits']
        operations = compiled_circuits['operations']
        self.__logger.info('generate_cqasm: %d qubits\n' % number_of_qubits)

        with io.StringIO() as stream:
            stream.write('version 1.0\n')
            stream.write('# cqasm generated by QI backend for QisKit\n')
            stream.write('qubits %d\n' % number_of_qubits)
            for circuit in operations:
                gate_name = '_%s' % circuit['name'].lower()
                gate_function = getattr(parser, gate_name)
                line = gate_function(circuit)
                if isinstance(line, str):
                    stream.write(line)

            return stream.getvalue()

    def _run_circuit(self, circuit, number_of_shots):
        """Run a circuit and return a single Result object.

        Args:
            circuit (dict): JSON circuit from quantum object with circuits list.
            number_of_shots (int): The number of times the algorithm is executed.

        Raises:
            QisKitBackendError: if an error occurred during execution by the backend.

        Returns:
            Dict: A dictionary with results; containing the data, execution time, status, etc.
        """
        start_time = time.time()
        self.__logger.info('\nRunning circuit... ({00} shots)'.format(number_of_shots))

        compiled_circuit = circuit['compiled_circuit']
        compiled_qasm = self._generate_cqasm(compiled_circuit)
        execution_results = self.__api.execute_qasm(compiled_qasm, number_of_shots, self.__backend)

        if len(execution_results['histogram']) == 0:
            raise QisKitBackendError('Result from backend contains no histogram data!')
        histogram = QiSimulatorPy.__convert_histogram(execution_results, compiled_circuit, number_of_shots)
        data = {'counts': histogram, 'snapshots': {}}

        execution_time = time.time() - start_time
        self.__logger.info('Execution done in {0:.2g} seconds.\n'.format(execution_time))
        return {'name': circuit['name'], 'seed': None, 'shots': number_of_shots,
                'data': data, 'status': 'DONE', 'success': True, 'time_taken': execution_time}

    @staticmethod
    def __validate(job):
        """ Validates the number of shots, classical bits and compiled qiskit circuits.

        Args:
            job (dict): The quantum job with the qiskit algorithm and quantum inspire backend.
        """
        QiSimulatorPy.__validate_number_of_shots(job)
        circuits = job['circuits']
        for circuit in circuits:
            compiled_circuit = circuit['compiled_circuit']
            QiSimulatorPy.__validate_number_of_clbits(compiled_circuit)
            QiSimulatorPy.__validate_no_gates_after_measure(compiled_circuit)

    @staticmethod
    def __validate_number_of_shots(job):
        """ Checks whether the number of shots has a valid value.

        Args:
            job (dict): The quantum job with the qiskit algorithm and quantum inspire backend.

        Raises:
            QisKitBackendError: When the value is not correct.
        """
        number_of_shots = job['config']['shots']
        if number_of_shots < 1:
            raise QisKitBackendError('Invalid shots (number_of_shots={})'.format(number_of_shots))

    @staticmethod
    def __validate_number_of_clbits(compiled_circuit):
        """ Checks whether the number of classical bits has a valid value.

        Args:
            compiled_circuit (dict): The circuit properties with gate operations and header.

        Raises:
            QisKitBackendError: When the value is not correct.
        """
        header = compiled_circuit['header']
        number_of_clbits = header['number_of_clbits']
        if number_of_clbits < 1:
            raise QisKitBackendError("Invalid amount of classical bits ({})!".format(number_of_clbits))

    @staticmethod
    def __validate_no_gates_after_measure(compiled_circuit):
        """ Checks whether the number of classical bits has a valid value.

        Args:
            compiled_circuit (dict): The circuit properties with gate operations and header.

        Raises:
            QisKitBackendError: When the value is not correct.
        """
        operations = compiled_circuit['operations']
        operation_names = [operation['name'] for operation in operations]
        has_measure_operation = False
        for name in operation_names:
            if name == 'measure':
                has_measure_operation = True
            elif has_measure_operation:
                raise QisKitBackendError('Operation after measurement!')

    @staticmethod
    def __collect_measurements(compiled_circuit):
        """ Determines the measured qubits and classical bits. The full-state measured
            qubits is returned when no measurements are present in the compiled circuit.

        Args:
            compiled_circuit (dict): The circuit properties with gate operations and header.

        Returns:
            List: A list of lists, for each measurement List contains a list of [qubit_index, classical_bit_index]
        """
        header = compiled_circuit['header']
        number_of_qubits = header['number_of_qubits']
        number_of_clbits = header['number_of_clbits']

        operations = compiled_circuit['operations']
        measurements = [[number_of_qubits - 1 - m['qubits'][0],
                         number_of_clbits - 1 - m['clbits'][0]]
                        for m in operations if m['name'] == 'measure']
        if measurements:
            used_classical_bits = [item[1] for item in measurements]
            if any([bit for bit in used_classical_bits if used_classical_bits.count(bit) > 1]):
                raise QisKitBackendError("Classical bit is used to measure multiple qubits!")
        else:
            measurements = [[index, index] for index in range(number_of_qubits)]
        return measurements

    @staticmethod
    def __convert_histogram(result, compiled_circuit, number_of_shots):
        """ The quantum inspire backend always uses full state projection. The SDK user
            can measure not all qubits and change the combined classical bits. This function
            converts the histogram output, such that it represents the counts measured with the
            classical bits.

            Args:
                result (dict): The result output from the quantum inspire backend with full-
                               state projection histogram output.
                compiled_circuit (dict): The circuit properties with gate operations and header.
                number_of_shots (int): The number of times the algorithm is executed.

            Returns:
                Dict: The result with converted histogram.
        """
        header = compiled_circuit['header']
        number_of_qubits = header['number_of_qubits']
        measurements = QiSimulatorPy.__collect_measurements(compiled_circuit)

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
