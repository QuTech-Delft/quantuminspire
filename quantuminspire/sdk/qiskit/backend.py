"""
This code is based in part on:
 https://github.com/QuTech-Delft/quantuminspire/tree/dev/src/quantuminspire/qiskit

 Quantum Inspire SDK

 Copyright 2022 QuTech Delft

 Licensed under the Apache License, Version 2.0 (the "License");
 you may not use this file except in compliance with the License.
 You may obtain a copy of the License at

    https://www.apache.org/licenses/LICENSE-2.0

 Unless required by applicable law or agreed to in writing, software
 distributed under the License is distributed on an "AS IS" BASIS,
 WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 See the License for the specific language governing permissions and
 limitations under the License.
"""

import copy
import io
import uuid
from typing import Any, Dict, List, Optional, Union

from qiskit.circuit import QuantumCircuit
from qiskit.compiler import assemble
from qiskit.providers import BackendV1 as Backend
from qiskit.providers import JobV1 as Job
from qiskit.providers import Options
from qiskit.providers.jobstatus import JobStatus
from qiskit.providers.models import QasmBackendConfiguration
from qiskit.providers.models.backendconfiguration import GateConfig
from qiskit.providers.models.backendstatus import BackendStatus
from qiskit.qobj import QasmQobjExperiment
from qiskit.result.models import ExperimentResult, ExperimentResultData
from qiskit.result.result import Result

from quantuminspire.sdk.qiskit.circuit_parser import CircuitToString
from quantuminspire.sdk.qiskit.exceptions import QiskitBackendError
from quantuminspire.sdk.qiskit.measurements import Measurements
from quantuminspire.util.api.quantum_interface import ExecuteCircuitResult, QuantumInterface


class QiskitQuantumInspireJob(Job):  # type: ignore
    """Qiskit Job for Quantum Inspire."""

    def __init__(self, qi: QuantumInterface, backend: Optional[Backend], job_id: str, **kwargs: Any) -> None:
        super().__init__(backend, job_id, **kwargs)
        self.experiments = None
        self.__results: List[ExecuteCircuitResult] = []
        del qi

    def submit(self) -> None:
        pass

    def result(self) -> Result:

        job_results = []
        for circuit_result in self.__results:

            exp_data = ExperimentResultData(counts=circuit_result.results, snapshots=circuit_result.results)

            exp = ExperimentResult(circuit_result.shots_done, circuit_result.shots_done > 0, exp_data)

            job_results.append(exp)

        return Result("QuantumInspireBackend", "2.0", 0, 0, len(job_results) > 0, job_results, None, status="COMPLETED")

    def status(self) -> JobStatus:
        return JobStatus.DONE

    def add_result(self, result: ExecuteCircuitResult) -> None:
        """Add a run result to the job."""
        self.__results.append(result)


class QuantumInspireBackend(Backend):  # type: ignore
    """Qiskit backend definition for Quantum Inspire."""

    DEFAULT_CONFIGURATION = QasmBackendConfiguration(
        backend_name="quantum_inspire_2",
        backend_version="2.0",
        n_qubits=6,
        basis_gates=[
            "x",
            "y",
            "z",
            "h",
            "rx",
            "ry",
            "rz",
            "s",
            "sdg",
            "t",
            "tdg",
            "cx",
            "ccx",
            "p",
            "u",
            "id",
            "swap",
            "cz",
            "snapshot",
            "delay",
            "barrier",
            "reset",
        ],
        gates=[GateConfig(name="NotUsed", parameters=["NaN"], qasm_def="NaN")],
        local=False,
        simulator=True,
        conditional=True,
        open_pulse=False,
        memory=True,
        max_shots=1024,
        max_experiments=1,
        coupling_map=[[0, 1], [0, 2], [1, 3], [2, 3], [3, 4], [4, 5]],
        multiple_measurements=False,
        parallel_computing=False,
    )
    qobj_warning_issued = False

    def __init__(self, qi: QuantumInterface, configuration: Optional[QasmBackendConfiguration] = None) -> None:

        super().__init__(configuration=(configuration or QuantumInspireBackend.DEFAULT_CONFIGURATION), provider=None)
        self.__qi: QuantumInterface = qi

    @classmethod
    def _default_options(cls) -> Options:
        """Returns default runtime options.

        Only the options that are relevant to Quantum Inspire backends are added.
        """
        return Options(shots=1024, memory=True)

    def _get_run_config(self, **kwargs: Any) -> Dict[str, Any]:
        """Return the consolidated runtime configuration. Run arguments overwrite the values of the default runtime
        options. Run arguments (not None) that are not defined as options are added to the runtime configuration.

        :param kwargs: The runtime arguments (arguments given with the run method).
        :return: A dictionary of runtime arguments for the run.
        """
        run_config_dict: Dict[str, Any] = copy.copy(self.options.__dict__)
        for key, val in kwargs.items():
            if val is not None:
                run_config_dict[key] = val
        return run_config_dict

    @property
    def backend_name(self) -> str:
        """Return backend name."""
        return self.name()  # type: ignore

    def run(  # pylint: disable=too-many-locals
        self,
        run_input: Union[QuantumCircuit, List[QuantumCircuit]],
        shots: Optional[int] = None,
        memory: Optional[bool] = None,
        allow_fsp: bool = True,
        **run_config: Dict[str, Any],
    ) -> QiskitQuantumInspireJob:
        run_config_dict = self._get_run_config(shots=shots, memory=memory, **run_config)

        qobj = assemble(run_input, self, **run_config_dict)
        number_of_shots = qobj.config.shots
        self.__validate_number_of_shots(number_of_shots)

        identifier = uuid.uuid1()
        job_id = f"qi-sdk-project-{identifier}"

        experiments = qobj.experiments
        job = QiskitQuantumInspireJob(self.__qi, self, job_id)
        for experiment in experiments:
            measurements = Measurements.from_experiment(experiment)
            if Backend.configuration(self).conditional:
                self.__validate_nr_of_clbits_conditional_gates(experiment)

            measurements.validate_unsupported_measurements()
            result = self._submit_experiment(experiment, number_of_shots, measurements, allow_fsp)
            job.add_result(result)

        job.experiments = experiments
        return job

    def status(self) -> BackendStatus:
        """Return the backend status. Pending jobs is always 0. This information is currently not known.

        Returns:
            BackendStatus: the status of the backend. Pending jobs is always 0.
        """
        return BackendStatus(
            backend_name=self.name(),
            backend_version="2.0",
            operational=True,
            pending_jobs=0,
            status_msg="online",
        )

    def _generate_cqasm(
        self, experiment: QasmQobjExperiment, measurements: Measurements, full_state_projection: bool = True
    ) -> str:
        """Generates the cQASM from the Qiskit experiment.

        :param experiment: The experiment that contains instructions to be converted to cQASM.
        :param measurements: The measurement instance containing measurement information and measurement functionality.
        :raises QiskitBackendError: If a Qiskit instruction is not in the basis gates set of Quantum Inspire backend.
        :return: The cQASM code that can be sent to the Quantum Inspire API.
        """
        parser = CircuitToString(Backend.configuration(self).basis_gates, measurements, full_state_projection)
        number_of_qubits = experiment.header.n_qubits
        instructions = experiment.instructions
        with io.StringIO() as stream:
            stream.write("version 1.0\n")
            stream.write("# cQASM generated by QI backend for Qiskit\n")
            stream.write(f"qubits {number_of_qubits}\n")
            for instruction in instructions:
                parser.parse(stream, instruction)
            return stream.getvalue()

    def _submit_experiment(
        self,
        experiment: QasmQobjExperiment,
        number_of_shots: int,
        measurements: Measurements,
        allow_fsp: bool = True,
    ) -> ExecuteCircuitResult:
        compiled_qasm = self._generate_cqasm(experiment, measurements, allow_fsp)

        result = self.__qi.execute_circuit(compiled_qasm, number_of_shots)
        return result

    def __validate_number_of_shots(self, number_of_shots: int) -> None:
        """Checks whether the number of shots has a valid value.

        :param number_of_shots: The number of shots to check.
        :raises QiskitBackendError: When the value is not correct.
        """
        if number_of_shots < 1 or number_of_shots > self.configuration().max_shots:
            raise QiskitBackendError(f"Invalid shots (number_of_shots={number_of_shots})")

    def __validate_nr_of_clbits_conditional_gates(self, experiment: QasmQobjExperiment) -> None:
        """Validate the number of classical bits in the algorithm when conditional gates are used.

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
            if any(hasattr(instruction, "conditional") for instruction in experiment.instructions):
                # no problem when there are no conditional gate operations
                raise QiskitBackendError(
                    "Number of classical bits must be less than or equal to the"
                    " number of qubits when using conditional gate operations"
                )
