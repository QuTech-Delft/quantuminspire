import time

from qiskit.providers import BaseJob, JobStatus, JobError, JobTimeoutError
from qiskit.result import Result

from quantuminspire import __version__ as quantum_inspire_version


class QIJob(BaseJob):
    """
    A job that is to be executed on the Quantum-inspire platform. A QIJob is normally created by calling run on the
    QuantumInspireBackend but can also be recreated using a job_id:

            qi_backend = QI.get_backend('QX single-node simulator')
            job = qi_backend.retrieve_job(job_id)
            result = job.result()
    """

    def __init__(self, backend, job_id, api, qobj=None):
        """
        Construct a new QIJob object. Not normally called directly, use a backend object to create/retrieve jobs.

        Args:
            backend (QuantumInspireBackend): A quantum-inspire backend.
            job_id (str): Id of the job as provided by the quantum-inspire api.
            api (QuantumInspireAPI): A quantum-inspire api.
            qobj (Qobj): A qiskit quantum object.
        """
        self._api = api
        super().__init__(backend, job_id)
        self.experiments = None
        self._status = JobStatus.INITIALIZING
        if qobj is not None:
            self._job_id = None
            self._qobj = qobj
        else:
            self.status()

    def submit(self):
        """
        Submit a job to the quantum-inspire platform.

        Raises:
             JobError: An error if the job has already been submitted.
        """
        if self._job_id is not None:
            raise JobError('Job has already been submitted!')
        self._job_id = self._backend.run(self._qobj)

    def result(self, timeout=None, wait=0.5):
        """

        Args:
            timeout (float): Timeout in seconds.
            wait (float): Wait time between queries to the quantum-inspire platform.

        Returns:
            qiskit.Result: Result object containing results from the experiments.

        Raises:
            JobTimeoutError: If timeout is reached.
            QisKitBackendError: If an error occurs during simulation.
        """
        start_time = time.time()
        while self.status() != JobStatus.DONE:
            elapsed_time = time.time() - start_time
            if timeout is not None and elapsed_time > timeout:
                raise JobTimeoutError('Failed getting result: timeout reached.')
            time.sleep(wait)
        experiment_results = self._backend.get_experiment_results(self)
        return Result(backend_name=self._backend.backend_name, backend_version=quantum_inspire_version,
                      job_id=self.job_id(), qobj_id=self.job_id(), success=True, results=experiment_results)

    def cancel(self):
        """ Cancel the job and delete the project. """
        self._api.delete_project(self._job_id)

    def status(self):
        """
        Query the quantum-inspire platform for the status of the job.

        Returns:
            JobStatus: The status of the job.

        """
        jobs = self._api.get_jobs_from_project(self._job_id)
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
