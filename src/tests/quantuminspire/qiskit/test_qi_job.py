import unittest
from unittest.mock import Mock

from qiskit.backends import JobStatus, JobError, JobTimeoutError
from qiskit.qobj import Qobj, ExperimentResult

from quantuminspire.qiskit.qi_job import QIJob


class TestQIJob(unittest.TestCase):
    def setUp(self):
        self.experiment_result_dictionary_1 = {'name': 'Test1', 'seed': None, 'shots': 42, 'data': {'0': 42},
                                               'status': 'DONE', 'success': True, 'time_taken': 0.42}
        self.experiment_result_dictionary_2 = {'name': 'Test2', 'seed': None, 'shots': 23, 'data': {'1': 42},
                                               'status': 'DONE', 'success': True, 'time_taken': 0.12}
        self.experiment_result_1 = ExperimentResult(**self.experiment_result_dictionary_1)
        self.experiment_result_2 = ExperimentResult(**self.experiment_result_dictionary_2)

    def test_constructor(self):
        api = Mock()
        api.get_jobs_from_project.return_value = []
        job_id = '42'
        backend = 'test_backend'
        job = QIJob(backend, job_id, api)

        self.assertEqual(job_id, job.job_id())
        self.assertEqual(api, job._api)
        self.assertIsNone(job.experiments)
        self.assertEqual(JobStatus.CANCELLED, job._status)

    def test_constructor_with_qobj(self):
        api = Mock()
        job_id = '42'
        backend = 'test_backend'
        qobj = Qobj('id', {}, None, None)
        job = QIJob(backend, job_id, api, qobj)

        self.assertIs(qobj, job._qobj)
        self.assertIsNone(job.job_id())
        self.assertEqual(api, job._api)
        self.assertIsNone(job.experiments)
        self.assertEqual(JobStatus.INITIALIZING, job._status)

    def test_submit_raises_error(self):
        api = Mock()
        api.get_jobs_from_project.return_value = []
        job_id = '42'
        backend = 'test_backend'
        job = QIJob(backend, job_id, api)
        with self.assertRaises(JobError):
            job.submit()

    def test_submit(self):
        backend = Mock()
        backend.run.return_value = '25'
        api = Mock()
        job_id = '42'
        qobj = Qobj('id', {}, None, None)
        job = QIJob(backend, job_id, api, qobj)

        job.submit()
        self.assertEqual('25', job.job_id())

    def test_result(self):
        api = Mock()
        api.get_jobs_from_project.return_value = [{'name': 'test_job', 'status': 'COMPLETE'},
                                                  {'name': 'other_job', 'status': 'COMPLETE'}]
        job_id = '42'
        backend = Mock()
        backend.get_experiment_results.return_value = [self.experiment_result_1, self.experiment_result_2]
        job = QIJob(backend, job_id, api)
        results = job.result()

        self.assertEqual('SUCCESS = True', results.status)
        self.assertDictEqual({'0': 42}, results.get_data('test_job'))
        self.assertDictEqual({'1': 42}, results.get_data('other_job'))
        self.assertEqual('42', results.job_id())
        self.assertListEqual(['test_job', 'other_job'], results.get_names())
        self.assertListEqual(['DONE', 'DONE'], results.circuit_statuses())

    def test_result_timeout(self):
        api = Mock()
        api.get_jobs_from_project.return_value = [{'name': 'test_job', 'status': 'COMPLETE'},
                                                  {'name': 'other_job', 'status': 'RUNNING'}]
        job_id = '42'
        backend = Mock()
        job = QIJob(backend, job_id, api)
        with self.assertRaises(JobTimeoutError):
            job.result(0)

    def test_cancel(self):
        api = Mock()
        api.get_jobs_from_project.return_value = [{'name': 'test_job', 'status': 'COMPLETE'},
                                                  {'name': 'other_job', 'status': 'RUNNING'}]
        job_id = '42'
        backend = Mock()
        job = QIJob(backend, job_id, api)
        job.cancel()
        api.delete_project.assert_called_with('42')

    def test_status(self):
        api = Mock()
        api.get_jobs_from_project.return_value = [{'name': 'test_job', 'status': 'COMPLETE'},
                                                  {'name': 'other_job', 'status': 'RUNNING'}]
        job_id = '42'
        backend = Mock()
        job = QIJob(backend, job_id, api)
        status = job.status()
        self.assertEqual(JobStatus.RUNNING, status)

        api.get_jobs_from_project.return_value = [{'name': 'test_job', 'status': 'COMPLETE'},
                                                  {'name': 'other_job', 'status': 'COMPLETE'}]
        status = job.status()
        self.assertEqual(JobStatus.DONE, status)

        api.get_jobs_from_project.return_value = [{'name': 'test_job', 'status': 'CANCELLED'},
                                                  {'name': 'other_job', 'status': 'COMPLETE'}]
        status = job.status()
        self.assertEqual(JobStatus.ERROR, status)

        api.get_jobs_from_project.return_value = [{'name': 'test_job', 'status': 'NEW'},
                                                  {'name': 'other_job', 'status': 'NEW'}]
        status = job.status()
        self.assertEqual(JobStatus.QUEUED, status)

        api.get_jobs_from_project.return_value = [{'name': 'test_job', 'status': 'CANCELLED'},
                                                  {'name': 'other_job', 'status': 'CANCELLED'}]
        status = job.status()
        self.assertEqual(JobStatus.CANCELLED, status)

        api.get_jobs_from_project.return_value = [{'name': 'test_job', 'status': 'NEW'},
                                                  {'name': 'other_job', 'status': 'RUNNING'}]
        status = job.status()
        self.assertEqual(JobStatus.RUNNING, status)

        api.get_jobs_from_project.return_value = [{'name': 'test_job', 'status': 'NEW'},
                                                  {'name': 'other_job', 'status': 'COMPLETE'}]
        status = job.status()
        self.assertEqual(JobStatus.RUNNING, status)
