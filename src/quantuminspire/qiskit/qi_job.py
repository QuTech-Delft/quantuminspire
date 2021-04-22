# Quantum Inspire SDK
#
# Copyright 2018 QuTech Delft
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

import time
from typing import List, Optional, Any, Dict, Callable

from qiskit.providers import BaseJob, JobError, JobTimeoutError
from qiskit.providers.jobstatus import JobStatus, JOB_FINAL_STATES
from qiskit.result.models import ExperimentResult
from qiskit.qobj import QasmQobj, QasmQobjExperiment
from quantuminspire.qiskit.qi_result import QIResult
from quantuminspire.api import QuantumInspireAPI
from quantuminspire.job import QuantumInspireJob
from quantuminspire.version import __version__ as quantum_inspire_version


class QIJob(BaseJob):  # type: ignore
    """
    A job that is to be executed on the Quantum-inspire platform. A QIJob is normally created by calling run on the
    QuantumInspireBackend but can also be recreated using a job_id:

    .. code::

        qi_backend = QI.get_backend('QX single-node simulator')
        job = qi_backend.retrieve_job(job_id)
        result = job.result()

    """

    def __init__(self, backend: Any, job_id: str, api: QuantumInspireAPI, qobj: Optional[QasmQobj] = None) -> None:
        """
        Construct a new QIJob object. Not normally called directly, use a backend object to create/retrieve jobs.

        :param backend: A quantum-inspire backend.
        :param job_id: Id of the job as provided by the quantum-inspire api.
        :param api: A quantum-inspire api.
        :param qobj: A qiskit quantum object.
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
        Submit a job to the quantum-inspire platform.

        :raises JobError: An error if the job has already been submitted.
        """
        if self._job_id:
            raise JobError('Job has already been submitted!')
        self._job_id = self._backend.run(self._qobj)

    def _result(self, result_function: Callable[[BaseJob], List[ExperimentResult]], timeout: Optional[float] = None,
                wait: float = 0.5) -> QIResult:
        """ Return the result for the experiments.

        :param result_function: backend function for fetching the requested results.
        :param timeout: Timeout in seconds.
        :param wait: Wait time between queries to the quantum-inspire platform.

        :return:
            Result object containing results from the experiments.

        :raises JobTimeoutError: If timeout is reached.
        :raises QisKitBackendError: If an error occurs during simulation.
        """
        start_time = time.time()
        while self.status() not in JOB_FINAL_STATES:
            elapsed_time = time.time() - start_time
            if timeout is not None and elapsed_time > timeout:
                raise JobTimeoutError('Failed getting result: timeout reached.')
            time.sleep(wait)

        experiment_results = result_function(self)
        return QIResult(backend_name=self._backend.backend_name, backend_version=quantum_inspire_version,
                        job_id=self.job_id(), qobj_id=self.job_id(), success=True, results=experiment_results)

    def result(self, timeout: Optional[float] = None, wait: float = 0.5) -> QIResult:
        """ Return the result for the experiments in the latest run for this project.

        :param timeout: Timeout in seconds.
        :param wait: Wait time between queries to the quantum-inspire platform.

        :return:
            QIResult object containing the result.

        :raises JobTimeoutError: If timeout is reached.
        :raises QisKitBackendError: If an error occurs during simulation.
        """
        return self._result(self._backend.get_experiment_results_from_latest_run, timeout, wait)

    def result_all_jobs(self, timeout: Optional[float] = None, wait: float = 0.5) -> QIResult:
        """ Return the result for the experiments for all the existing jobs in the project.

        :param timeout: Timeout in seconds.
        :param wait: Wait time between queries to the quantum-inspire platform.

        :return:
            QIResult object containing the result.

        :raises JobTimeoutError: If timeout is reached.
        :raises QisKitBackendError: If an error occurs during simulation.
        """
        return self._result(self._backend.get_experiment_results_from_all_jobs, timeout, wait)

    def cancel(self) -> None:
        """ Cancel the job and delete the project. """
        self._api.delete_project(int(self._job_id))

    def get_jobs(self) -> List[Dict[str, Any]]:
        """ Gets the jobs that were submitted in the latest run. These job were added with add_job.

        :return:
            List of jobs with their properties for the jobs that were added for the experiments submitted when running
            this instance of QIJob.
            An empty list is returned when there were no jobs added.

        :raises ApiError: If the job for the job identified does not exist.
        """
        ret = [self._api.get_job(job.get_job_identifier()) for job in self.jobs]
        return ret

    def add_job(self, job: QuantumInspireJob) -> None:
        """ Add a quantum inspire job to the list. The list contains the (quantum inspire) jobs created for the
        submitted experiments in this particular QIJob.

        :param job: QuatumInspireJob (submitted) that has to be added to the list of jobs created for the experiments
         in QIJob.
        """
        self.jobs.append(job)

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

        if 0 < cancelled < number_of_jobs:
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
