import unittest
from unittest.mock import Mock

from qiskit.providers import JobStatus, JobError, JobTimeoutError
from qiskit.qobj import QasmQobj, QobjHeader, QasmQobjConfig
from qiskit.result.models import ExperimentResult, ExperimentResultData
from qiskit.validation.base import Obj

from quantuminspire.qiskit.qi_job import QIJob


class TestQIJob(unittest.TestCase):
    def setUp(self):
        experiment_result_data = ExperimentResultData.from_dict({'counts': {'0x0': 42}})
        experiment_result_data_2 = ExperimentResultData.from_dict({'counts': {'0x1': 42}})
        header_1 = Obj.from_dict({'name': 'Test1'})
        header_2 = Obj.from_dict({'name': 'Test2'})
        self.experiment_result_dictionary_1 = {'name': 'Test1', 'shots': 42, 'data': experiment_result_data,
                                               'status': 'DONE', 'success': True, 'time_taken': 0.42,
                                               'header': header_1}
        self.experiment_result_dictionary_2 = {'name': 'Test2', 'shots': 23, 'data': experiment_result_data_2,
                                               'status': 'DONE', 'success': True, 'time_taken': 0.12,
                                               'header': header_2}
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
        qobj = QasmQobj(qobj_id='id', config=QasmQobjConfig(), experiments=[], header=QobjHeader())
        job = QIJob(backend, job_id, api, qobj)

        self.assertIs(qobj, job._qobj)
        self.assertEqual(job.job_id(), '')
        self.assertEqual(api, job._api)
        self.assertIsNone(job.experiments)
        self.assertEqual(JobStatus.INITIALIZING, job._status)

    def test_submit_raises_error(self):
        api = Mock()
        api.get_jobs_from_project.return_value = []
        job_id = '42'
        backend = Mock()
        backend.run.return_value = '25'
        job = QIJob(backend, job_id, api)
        with self.assertRaises(JobError):
            job.submit()

    def test_submit(self):
        backend = Mock()
        backend.run.return_value = '25'
        api = Mock()
        job_id = '42'
        qobj = QasmQobj(qobj_id='id', config=QasmQobjConfig(), experiments=[], header=QobjHeader())
        job = QIJob(backend, job_id, api, qobj)

        job.submit()
        self.assertEqual('25', job.job_id())

    def test_result(self):
        api = Mock()
        api.get_jobs_from_project.return_value = [{'name': 'Test1', 'status': 'COMPLETE'},
                                                  {'name': 'Test2', 'status': 'COMPLETE'}]
        job_id = '42'
        backend = Mock()
        backend.get_experiment_results.return_value = [self.experiment_result_1, self.experiment_result_2]
        backend.backend_name = 'some backend'
        job = QIJob(backend, job_id, api)
        results = job.result()

        self.assertTrue(results.success)
        self.assertDictEqual({'counts': {'0x0': 42}}, results.data(0))
        self.assertDictEqual({'counts': {'0x1': 42}}, results.data(1))
        self.assertDictEqual({'0': 42}, results.get_counts(0))
        self.assertDictEqual({'1': 42}, results.get_counts(1))
        self.assertEqual('42', results.job_id)
        self.assertListEqual(['Test1', 'Test2'], [r.name for r in results.results])
        self.assertListEqual(['DONE', 'DONE'], [r.status for r in results.results])

    def test_result_timeout(self):
        api = Mock()
        api.get_jobs_from_project.return_value = [{'name': 'test_job', 'status': 'COMPLETE'},
                                                  {'name': 'other_job', 'status': 'RUNNING'}]
        job_id = '42'
        backend = Mock()
        job = QIJob(backend, job_id, api)
        with self.assertRaises(JobTimeoutError):
            job.result(timeout=1e-2, wait=0)

    def test_cancel(self):
        api = Mock()
        api.get_jobs_from_project.return_value = [{'name': 'test_job', 'status': 'COMPLETE'},
                                                  {'name': 'other_job', 'status': 'RUNNING'}]
        job_id = '42'
        backend = Mock()
        job = QIJob(backend, job_id, api)
        job.cancel()
        api.delete_project.assert_called_with(42)

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
