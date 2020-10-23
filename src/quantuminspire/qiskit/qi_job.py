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
import time
from typing import List, Optional, Any

from qiskit.providers import BaseJob, JobError, JobTimeoutError
from qiskit.providers.jobstatus import JobStatus, JOB_FINAL_STATES
from qiskit.qobj import QasmQobj, QasmQobjExperiment
from quantuminspire.qiskit.qi_result import QIResult
from quantuminspire.api import QuantumInspireAPI
from quantuminspire.version import __version__ as quantum_inspire_version


class QIJob(BaseJob):  # type: ignore
    """
    A job that is to be executed on the Quantum-inspire platform. A QIJob is normally created by calling run on the
    QuantumInspireBackend but can also be recreated using a job_id:

            qi_backend = QI.get_backend('QX single-node simulator')
            job = qi_backend.retrieve_job(job_id)
            result = job.result()
    """

    def __init__(self, backend: Any, job_id: str, api: QuantumInspireAPI, qobj: Optional[QasmQobj] = None) -> None:
        """
        Construct a new QIJob object. Not normally called directly, use a backend object to create/retrieve jobs.

        Args:
            backend: A quantum-inspire backend.
            job_id: Id of the job as provided by the quantum-inspire api.
            api: A quantum-inspire api.
            qobj: A qiskit quantum object.
        """
        self._api: QuantumInspireAPI = api
        super().__init__(backend, job_id)
        self.experiments: Optional[List[QasmQobjExperiment]] = None
        self._status: JobStatus = JobStatus.INITIALIZING
        self._qobj: Optional[QasmQobj] = qobj
        if self._qobj is not None:
            self._job_id = ''  # invalidate _job_id
        else:
            self.status()

    def submit(self) -> None:
        """
        Submit a job to the quantum-inspire platform.

        Raises:
             JobError: An error if the job has already been submitted.
        """
        if self._job_id:
            raise JobError('Job has already been submitted!')
        self._job_id = self._backend.run(self._qobj)

    def result(self, timeout: Optional[float] = None, wait: float = 0.5) -> QIResult:
        """

        Args:
            timeout: Timeout in seconds.
            wait: Wait time between queries to the quantum-inspire platform.

        Returns:
            QIResult object containing results from the experiments.

        Raises:
            JobTimeoutError: If timeout is reached.
            QisKitBackendError: If an error occurs during simulation.
        """
        start_time = time.time()
        while self.status() not in JOB_FINAL_STATES:
            elapsed_time = time.time() - start_time
            if timeout is not None and elapsed_time > timeout:
                raise JobTimeoutError('Failed getting result: timeout reached.')
            time.sleep(wait)
        experiment_results = self._backend.get_experiment_results(self)
        return QIResult(backend_name=self._backend.backend_name, backend_version=quantum_inspire_version,
                        job_id=self.job_id(), qobj_id=self.job_id(), success=True, results=experiment_results)

    def cancel(self) -> None:
        """ Cancel the job and delete the project. """
        self._api.delete_project(int(self._job_id))

    def status(self) -> JobStatus:
        """
        Query the quantum-inspire platform for the status of the job.

        Returns:
            The status of the job.
        """
        jobs = self._api.get_jobs_from_project(int(self._job_id))
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
