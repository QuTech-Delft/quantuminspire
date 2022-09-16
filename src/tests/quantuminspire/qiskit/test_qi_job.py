""" Quantum Inspire SDK

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
import unittest
from unittest.mock import Mock

from qiskit.providers import JobStatus, JobError, JobTimeoutError
from qiskit.qobj import QasmQobj, QobjHeader, QasmQobjConfig
from qiskit.result.models import ExperimentResult, ExperimentResultData

from quantuminspire.qiskit.qi_job import QIJob


class TestQIJob(unittest.TestCase):
    def setUp(self):
        experiment_result_data = ExperimentResultData.from_dict({'counts': {'0x0': 42}})
        experiment_result_data_2 = ExperimentResultData.from_dict({'counts': {'0x1': 42}})
        experiment_result_data_3 = ExperimentResultData.from_dict({})
        header_1 = QobjHeader.from_dict({'name': 'Test1'})
        header_2 = QobjHeader.from_dict({'name': 'Test2'})
        header_3 = QobjHeader.from_dict({'name': 'Test3'})
        self.experiment_result_dictionary_1 = {'name': 'Test1', 'shots': 42, 'data': experiment_result_data,
                                               'status': 'DONE', 'success': True, 'time_taken': 0.42,
                                               'header': header_1}
        self.experiment_result_dictionary_2 = {'name': 'Test2', 'shots': 23, 'data': experiment_result_data_2,
                                               'status': 'DONE', 'success': True, 'time_taken': 0.12,
                                               'header': header_2}
        self.experiment_result_dictionary_3 = {'name': 'Test3', 'shots': 23, 'data': experiment_result_data_3,
                                               'status': 'CANCELLED', 'success': False, 'time_taken': 0.12,
                                               'header': header_3}
        self.experiment_result_1 = ExperimentResult(**self.experiment_result_dictionary_1)
        self.experiment_result_2 = ExperimentResult(**self.experiment_result_dictionary_2)
        self.experiment_result_3 = ExperimentResult(**self.experiment_result_dictionary_3)

    def test_constructor(self):
        api = Mock()
        api.get_jobs_from_project.return_value = []
        job_id = '42'
        backend = 'test_backend'
        job = QIJob(backend, job_id, api)

        self.assertEqual(job_id, job.job_id())
        self.assertEqual(api, job._api)
        self.assertIsNone(job.experiments)
        self.assertEqual(JobStatus.INITIALIZING, job._status)

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
        api.get_job.side_effect = [{'name': 'Test1', 'status': 'COMPLETE'},
                                   {'name': 'Test2', 'status': 'COMPLETE'},
                                   {'name': 'Test1', 'status': 'COMPLETE'},
                                   {'name': 'Test2', 'status': 'COMPLETE'}]
        job_id = '42'
        backend = Mock()
        backend.get_experiment_results_from_latest_run.return_value = \
            [self.experiment_result_1, self.experiment_result_2]
        backend.backend_name = 'some backend'

        quantuminspire_job = Mock()
        quantuminspire_job.get_job_identifier.side_effect = [1, 2, 1, 2]

        qijob = QIJob(backend, job_id, api)
        qijob.add_job(quantuminspire_job)
        qijob.add_job(quantuminspire_job)
        results = qijob.result()
        results_dict = results.to_dict()

        self.assertEqual(results_dict["status"], 'DONE')

        self.assertTrue(results.success)
        self.assertEqual(results.time_taken, 0.54)
        self.assertDictEqual({'counts': {'0x0': 42}}, results.data(0))
        self.assertDictEqual({'counts': {'0x1': 42}}, results.data(1))
        self.assertDictEqual({'0': 42}, results.get_counts(0))
        self.assertDictEqual({'1': 42}, results.get_counts(1))
        self.assertEqual('42', results.job_id)
        self.assertEqual(results.status, 'DONE')
        self.assertListEqual(['Test1', 'Test2'], [r.name for r in results.results])
        self.assertListEqual(['DONE', 'DONE'], [r.status for r in results.results])

    def test_result_all_jobs_run(self):
        api = Mock()
        api.get_job.return_value = {'name': 'all_jobs', 'status': 'COMPLETE'}
        quantuminspire_job1 = Mock()
        quantuminspire_job2 = Mock()
        quantuminspire_job1.get_job_identifier.return_value = [1]
        quantuminspire_job2.get_job_identifier.return_value = [2]
        backend = Mock()
        backend.get_experiment_results_from_all_jobs.return_value = [self.experiment_result_1, self.experiment_result_2]
        backend.backend_name = 'some backend'
        job_id = '42'
        qijob = QIJob(backend, job_id, api)
        qijob.add_job(quantuminspire_job1)
        qijob.add_job(quantuminspire_job2)
        results = qijob.result_all_jobs()

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
        api.get_job.return_value = {'name': 'other_job', 'status': 'RUNNING'}
        job_id = '42'
        backend = Mock()
        quantuminspire_job = Mock()
        quantuminspire_job.get_job_identifier.return_value = [1]
        qijob = QIJob(backend, job_id, api)
        qijob.add_job(quantuminspire_job)
        with self.assertRaises(JobTimeoutError):
            qijob.result(timeout=1e-2, wait=0)

    def test_result_cancelled(self):
        api = Mock()
        api.get_job.return_value = {'name': 'test_job', 'status': 'CANCELLED'}
        job_id = '42'
        backend = Mock()
        quantuminspire_job = Mock()
        quantuminspire_job.get_job_identifier.return_value = [1]
        backend.get_experiment_results_from_latest_run.return_value = [self.experiment_result_3]
        backend.backend_name = 'some backend'
        qijob = QIJob(backend, job_id, api)
        qijob.add_job(quantuminspire_job)
        results = qijob.result(timeout=None).results[0]
        self.assertFalse(results.success)
        self.assertEqual(results.status, 'CANCELLED')

    def test_cancel(self):
        api = Mock()
        job_id = '42'
        backend = Mock()
        job = QIJob(backend, job_id, api)
        job.cancel()
        api.delete_project.assert_called_with(42)

    def test_queue_position(self):
        api = Mock()
        api.get_job.side_effect = [{'name': 'test_job', 'status': 'NEW'},
                                   {'name': 'other_job', 'status': 'NEW'}]
        job_id = '42'
        backend = Mock()
        quantuminspire_job = Mock()
        quantuminspire_job.get_job_identifier.side_effect = [1, 2]
        qijob = QIJob(backend, job_id, api)
        qijob.add_job(quantuminspire_job)
        qijob.add_job(quantuminspire_job)
        status = qijob.status()
        self.assertEqual(JobStatus.QUEUED, status)
        queue_position = qijob.queue_position(True)
        self.assertIsNone(queue_position)
        queue_position = qijob.queue_position()
        self.assertIsNone(queue_position)

    def test_status(self):
        api = Mock()
        api.get_job.side_effect = [{'name': 'test_job', 'status': 'COMPLETE'},
                                   {'name': 'other_job', 'status': 'RUNNING'}]
        job_id = '42'
        backend = Mock()
        quantuminspire_job = Mock()
        quantuminspire_job.get_job_identifier.side_effect = [1, 2]
        qijob = QIJob(backend, job_id, api)
        qijob.add_job(quantuminspire_job)
        qijob.add_job(quantuminspire_job)
        status = qijob.status()
        self.assertEqual(JobStatus.RUNNING, status)

        api.get_job.side_effect = [{'name': 'test_job', 'status': 'COMPLETE'},
                                   {'name': 'other_job', 'status': 'COMPLETE'}]
        quantuminspire_job.get_job_identifier.side_effect = [1, 2]
        status = qijob.status()
        self.assertEqual(JobStatus.DONE, status)

        api.get_job.side_effect = [{'name': 'test_job', 'status': 'CANCELLED'},
                                   {'name': 'other_job', 'status': 'COMPLETE'}]
        quantuminspire_job.get_job_identifier.side_effect = [1, 2]
        status = qijob.status()
        self.assertEqual(JobStatus.ERROR, status)

        api.get_job.side_effect = [{'name': 'test_job', 'status': 'NEW'},
                                   {'name': 'other_job', 'status': 'NEW'}]
        quantuminspire_job.get_job_identifier.side_effect = [1, 2]
        status = qijob.status()
        self.assertEqual(JobStatus.QUEUED, status)

        api.get_job.side_effect = [{'name': 'test_job', 'status': 'CANCELLED'},
                                   {'name': 'other_job', 'status': 'CANCELLED'}]
        quantuminspire_job.get_job_identifier.side_effect = [1, 2]
        status = qijob.status()
        self.assertEqual(JobStatus.CANCELLED, status)

        api.get_job.side_effect = [{'name': 'test_job', 'status': 'NEW'},
                                   {'name': 'other_job', 'status': 'RUNNING'}]
        quantuminspire_job.get_job_identifier.side_effect = [1, 2]
        status = qijob.status()
        self.assertEqual(JobStatus.RUNNING, status)

        api.get_job.side_effect = [{'name': 'test_job', 'status': 'NEW'},
                                   {'name': 'other_job', 'status': 'COMPLETE'}]
        quantuminspire_job.get_job_identifier.side_effect = [1, 2]
        status = qijob.status()
        self.assertEqual(JobStatus.RUNNING, status)
