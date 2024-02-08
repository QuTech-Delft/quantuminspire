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

import time
from typing import List, Optional, Any, Dict, Callable, TYPE_CHECKING

from qiskit.providers import JobError, JobTimeoutError, JobV1 as Job
from qiskit.providers.jobstatus import JobStatus, JOB_FINAL_STATES
from qiskit.result.models import ExperimentResult
from qiskit.qobj import QasmQobj, QasmQobjExperiment
from quantuminspire.api import QuantumInspireAPI
from quantuminspire.job import QuantumInspireJob
from quantuminspire.qiskit.qi_result import QIResult
from quantuminspire.version import __version__ as quantum_inspire_version

if TYPE_CHECKING:
    from backend_qx import QuantumInspireBackend


class QIJob(Job):  # type: ignore
    """
    A Qiskit job that is executed on the Quantum Inspire platform. A QIJob is normally created by calling
    ``run`` on QuantumInspireBackend ``qi_backend``.

    .. code-block:: python

        qc = QuantumCircuit(5, 5)
        qc.h(0)
        qc.cx(0, range(1, 5))
        qc.measure_all()

        qc = transpile(qc, qi_backend)
        job = qi_backend.run(qc, shots=1024)
        result = job.result()

    The return value of ``run`` is an instance of QIJob (Qiskit job) and is the equivalent to the Quantum
    Inspire project. It is a container to handle one or more (asynchronous) Qiskit circuits or experiments.
    A Qiskit circuit is equivalent to a Quantum Inspire job.

    To get the Quantum Inspire project-id from ``job`` do:

    .. code::

        qi_project_id = job.job_id()

    To get the list of Quantum Inspire jobs (in dictionary format) from ``job`` do:

    .. code::

        qi_jobs = job.get_jobs()

    QIJob can also be recreated using a ``job_id``, being a Quantum Inspire project-id:

    .. code::

        qi_backend = QI.get_backend('QX single-node simulator')
        job = qi_backend.retrieve_job(job_id)

    """

    def __init__(self, backend: QuantumInspireBackend, job_id: str, api: QuantumInspireAPI,
                 qobj: Optional[QasmQobj] = None) -> None:
        """
        A QIJob object is normally not constructed directly.

        :param backend: A Quantum Inspire backend.
        :param job_id: Id of the job as provided by the Quantum Inspire API.
        :param api: A Quantum Inspire API.
        :param qobj: A Qiskit quantum object.
        """
        self._api: QuantumInspireAPI = api
        super().__init__(backend, job_id)
        self.experiments: Optional[List[QasmQobjExperiment]] = None
        self.jobs: List[QuantumInspireJob] = []
        self._status: JobStatus = JobStatus.INITIALIZING
        self._qobj: Optional[QasmQobj] = qobj
        if self._qobj is not None:
            self._job_id = ''  # invalidate _job_id
        else:
            self.status()

    def set_job_id(self, job_id: str) -> None:
        """ Overwrite the job_id with a new id.

        :param job_id: New id for the QIJob. Used in the use case for linking the job to the user-given QI project that
            must contain the job.

        """
        self._job_id = job_id

    def submit(self) -> None:
        """
        Submit a job to the Quantum Inspire platform.

        :raises JobError: An error if the job has already been submitted.
        """
        if self._job_id:
            raise JobError('Job has already been submitted!')
        self._job_id = self._backend.run(circuits=self._qobj)

    def _result(self, result_function: Callable[[Job], List[ExperimentResult]], timeout: Optional[float] = None,
                wait: float = 0.5) -> QIResult:
        """ Return the result for the experiments.

        :param result_function: backend function for fetching the requested results.
        :param timeout: Timeout in seconds.
        :param wait: Wait time between queries to the Quantum Inspire platform.

        :return:
            Result object containing results from the experiments.

        :raises JobTimeoutError: If timeout is reached.
        :raises QiskitBackendError: If an error occurs during simulation.
        """
        start_time = time.time()
        while self.status() not in JOB_FINAL_STATES:
            elapsed_time = time.time() - start_time
            if timeout is not None and elapsed_time > timeout:
                raise JobTimeoutError('Failed getting result: timeout reached.')
            time.sleep(wait)

        experiment_results = result_function(self)
        total_time_taken = sum(getattr(experiment_result, "time_taken", 0.0) for
                               experiment_result in experiment_results)

        return QIResult(backend_name=self._backend.backend_name, backend_version=quantum_inspire_version,
                        job_id=self.job_id(), qobj_id=self.job_id(), success=True, results=experiment_results,
                        status=self.status().name, time_taken=total_time_taken)

    def result(self, timeout: Optional[float] = None, wait: float = 0.5) -> QIResult:
        """ Return the result for the experiments in the latest run for this project.

        :param timeout: Timeout in seconds.
        :param wait: Wait time between queries to the Quantum Inspire platform.

        :return:
            QIResult object containing the result.

        :raises JobTimeoutError: If timeout is reached.
        :raises QiskitBackendError: If an error occurs during simulation.
        """
        return self._result(self._backend.get_experiment_results_from_latest_run, timeout, wait)

    def result_all_jobs(self, timeout: Optional[float] = None, wait: float = 0.5) -> QIResult:
        """ Return the result for the experiments for all the existing jobs in the project.

        :param timeout: Timeout in seconds.
        :param wait: Wait time between queries to the Quantum Inspire platform.

        :return:
            QIResult object containing the result.

        :raises JobTimeoutError: If timeout is reached.
        :raises QiskitBackendError: If an error occurs during simulation.
        """
        return self._result(self._backend.get_experiment_results_from_all_jobs, timeout, wait)

    def cancel(self) -> None:
        """ Cancel the job and delete the project. """
        self._api.delete_project(int(self._job_id))

    def get_jobs(self) -> List[Dict[str, Any]]:
        """ Gets the Quantum Inspire jobs that were submitted in the latest run. These job were added with add_job.

        :return:
            List of jobs with their properties for the jobs that were added for the experiments submitted when running
            this instance of QIJob.
            An empty list is returned when there were no jobs added.

        :raises ApiError: If the job for the job identified does not exist.
        """
        ret = [self._api.get_job(job.get_job_identifier()) for job in self.jobs]
        return ret

    def add_job(self, job: QuantumInspireJob) -> None:
        """ Add a Quantum Inspire job to the list. The list contains the (Quantum Inspire) jobs created for the
        submitted experiments in this particular QIJob.

        :param job: QuantumInspireJob (submitted) that has to be added to the list of jobs created for the experiments
         in QIJob.
        """
        self.jobs.append(job)

    def queue_position(self, refresh: bool = False) -> Optional[int]:
        """
        Return the position for this Job in the Quantum Inspire queue (when in status QUEUED).
        Currently, we don't have this info available.

        :param refresh: If ``True``, re-query the server to get the latest value.
                Otherwise, return the cached value, when available. Not used.

        :return:
            The queue position of the job. Currently, None (not available).
        """
        return None

    def status(self) -> JobStatus:
        """
        Check the status of the jobs submitted in the latest run.

        :return:
            The status of the job.
        """
        jobs = self.get_jobs()
        number_of_jobs = len(jobs)
        cancelled = len([job for job in jobs if job['status'] == 'CANCELLED'])
        running = len([job for job in jobs if job['status'] == 'RUNNING'])
        completed = len([job for job in jobs if job['status'] == 'COMPLETE'])

        if number_of_jobs == 0:
            self._status = JobStatus.INITIALIZING
        elif 0 < cancelled < number_of_jobs:
            self._status = JobStatus.ERROR
        elif cancelled == number_of_jobs:
            self._status = JobStatus.CANCELLED
        elif running > 0 or (0 < completed < number_of_jobs):
            self._status = JobStatus.RUNNING
        elif completed == number_of_jobs:
            self._status = JobStatus.DONE
        else:
            self._status = JobStatus.QUEUED
        return self._status
