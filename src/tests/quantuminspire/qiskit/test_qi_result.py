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

from qiskit.qobj import QobjHeader
from qiskit.result.models import ExperimentResult, ExperimentResultData
from quantuminspire.exceptions import QiskitBackendError
from quantuminspire.qiskit.qi_result import QIResult


class TestQIResult(unittest.TestCase):
    def setUp(self):
        experiment_result_data_1 = ExperimentResultData.from_dict({'counts': {'0x0': 42, '0x3': 58},
                                                                   'probabilities': {'0x0': 0.42, '0x3': 0.58},
                                                                   'probabilities_multiple_measurement': [{'0x0': 0.42,
                                                                                                           '0x3': 0.58}
                                                                                                          ],
                                                                   'calibration': {'fridge_temperature': 26.9,
                                                                                   'unit': 'mK'}})
        experiment_result_data_2 = ExperimentResultData.from_dict({'counts': {'0x0': 24, '0x1': 25,
                                                                              '0x2': 23, '0x3': 28},
                                                                   'probabilities': {'0x0': 0.24, '0x1': 0.25,
                                                                                     '0x2': 0.23, '0x3': 0.28},
                                                                   'probabilities_multiple_measurement': [{'0x0': 0.24,
                                                                                                           '0x1': 0.25,
                                                                                                           '0x2': 0.23,
                                                                                                           '0x3': 0.28}
                                                                                                          ],
                                                                   'calibration': {'fridge_temperature': 25.0,
                                                                                   'unit': 'mK'}})
        experiment_result_data_3 = ExperimentResultData.from_dict({'counts': {'0x0': 24, '0x1': 25,
                                                                              '0x2': 23, '0x3': 28},
                                                                   'calibration': None})

        experiment_result_data_4 = ExperimentResultData.from_dict({'counts': {'0x0': 24, '0x1': 25,
                                                                              '0x2': 23, '0x3': 28}})

        header_1 = QobjHeader.from_dict({'name': 'Test1', 'memory_slots': 2, 'creg_sizes': [['c0', 2]]})
        header_2 = QobjHeader.from_dict({'name': 'Test2', 'memory_slots': 3, 'creg_sizes': [['c0', 3]]})
        header_3 = None
        header_4 = None
        self.experiment_result_dictionary_1 = {'name': 'Test1', 'shots': 42, 'data': experiment_result_data_1,
                                               'status': 'DONE', 'success': True, 'time_taken': 0.42,
                                               'header': header_1}
        self.experiment_result_dictionary_2 = {'name': 'Test2', 'shots': 23, 'data': experiment_result_data_2,
                                               'status': 'DONE', 'success': True, 'time_taken': 0.12,
                                               'header': header_2}
        self.experiment_result_dictionary_3 = {'name': 'Test3', 'shots': 23, 'data': experiment_result_data_3,
                                               'status': 'DONE', 'success': True, 'time_taken': 0.12,
                                               'header': header_3}
        self.experiment_result_dictionary_4 = {'name': 'Test4', 'shots': 21, 'data': experiment_result_data_4,
                                               'status': 'DONE', 'success': True, 'time_taken': 0.12,
                                               'header': header_4}
        self.experiment_result_1 = ExperimentResult(**self.experiment_result_dictionary_1)
        self.experiment_result_2 = ExperimentResult(**self.experiment_result_dictionary_2)
        self.experiment_result_3 = ExperimentResult(**self.experiment_result_dictionary_3)
        self.experiment_result_4 = ExperimentResult(**self.experiment_result_dictionary_4)

    def test_constructor(self):
        backend_name = 'test_backend'
        backend_version = '1.2.0'
        qobj_id = '42'
        job_id = '42'
        success = True
        date = '07-07-2020'
        experiment_result = self.experiment_result_1
        qi_result = QIResult(backend_name, backend_version, qobj_id, job_id, success, [experiment_result], date)

        self.assertEqual(date, qi_result.date)
        self.assertEqual(job_id, qi_result.job_id)
        self.assertIsNotNone(qi_result.results)
        self.assertListEqual(['Test1'], [r.name for r in qi_result.results])

    def __get_result_for_multiple_experiments(self):
        backend_name = 'test_backend'
        backend_version = '1.2.0'
        qobj_id = '42'
        job_id = '42'
        success = True
        experiment_result = [self.experiment_result_1, self.experiment_result_2]
        qi_result = QIResult(backend_name, backend_version, qobj_id, job_id, success, experiment_result)

        return qi_result

    def test_get_probabilities_for_multiple_experiments_by_name(self):
        qi_result = self.__get_result_for_multiple_experiments()

        probabilities = qi_result.get_probabilities('Test1')
        self.assertDictEqual(probabilities, {'00': 0.42, '11': 0.58})
        probabilities = qi_result.get_probabilities('Test2')
        self.assertDictEqual(probabilities, {'000': 0.24, '001': 0.25, '010': 0.23, '011': 0.28})

    def test_get_probabilities_for_multiple_experiments_by_index(self):
        qi_result = self.__get_result_for_multiple_experiments()

        probabilities = qi_result.get_probabilities(1)
        self.assertDictEqual(probabilities, {'000': 0.24, '001': 0.25, '010': 0.23, '011': 0.28})
        probabilities = qi_result.get_probabilities()
        self.assertListEqual(probabilities, [{'00': 0.42, '11': 0.58},
                                             {'000': 0.24, '001': 0.25, '010': 0.23, '011': 0.28}])

    def test_get_probabilities_mm_for_multiple_experiments_by_name(self):
        qi_result = self.__get_result_for_multiple_experiments()

        probabilities = qi_result.get_probabilities_multiple_measurement('Test1')
        self.assertListEqual(probabilities, [{'00': 0.42, '11': 0.58}])
        probabilities = qi_result.get_probabilities_multiple_measurement('Test2')
        self.assertListEqual(probabilities, [{'000': 0.24, '001': 0.25, '010': 0.23, '011': 0.28}])

    def test_get_probabilities_mm_for_multiple_experiments_by_index(self):
        qi_result = self.__get_result_for_multiple_experiments()

        probabilities = qi_result.get_probabilities_multiple_measurement(1)
        self.assertListEqual(probabilities, [{'000': 0.24, '001': 0.25, '010': 0.23, '011': 0.28}])
        probabilities = qi_result.get_probabilities_multiple_measurement()
        self.assertListEqual(probabilities, [[{'00': 0.42, '11': 0.58}],
                                             [{'000': 0.24, '001': 0.25, '010': 0.23, '011': 0.28}]])

    def test_get_calibration_for_multiple_experiments_by_name(self):
        qi_result = self.__get_result_for_multiple_experiments()

        calibration = qi_result.get_calibration('Test1')
        self.assertDictEqual(calibration, {'fridge_temperature': 26.9, 'unit': 'mK'})
        calibration = qi_result.get_calibration('Test2')
        self.assertDictEqual(calibration, {'fridge_temperature': 25.0, 'unit': 'mK'})

    def test_get_calibration_for_multiple_experiments_by_index(self):
        qi_result = self.__get_result_for_multiple_experiments()

        calibration = qi_result.get_calibration(1)
        self.assertDictEqual(calibration, {'fridge_temperature': 25.0, 'unit': 'mK'})
        calibration = qi_result.get_calibration()
        self.assertListEqual(calibration, [{'fridge_temperature': 26.9, 'unit': 'mK'},
                                           {'fridge_temperature': 25.0, 'unit': 'mK'}])

    def test_no_probabilities(self):
        backend_name = 'test_backend'
        backend_version = '1.2.0'
        qobj_id = '42'
        job_id = '42'
        success = True
        experiment_result = [self.experiment_result_3]
        qi_result = QIResult(backend_name, backend_version, qobj_id, job_id, success, experiment_result)
        self.assertRaisesRegex(QiskitBackendError, 'No probabilities for experiment "0"',
                               qi_result.get_probabilities, 0)

    def test_empty_calibration(self):
        backend_name = 'test_sim_backend'
        backend_version = '1.2.0'
        qobj_id = '42'
        job_id = '42'
        success = True
        experiment_result = [self.experiment_result_3]
        qi_result = QIResult(backend_name, backend_version, qobj_id, job_id, success, experiment_result)
        calibration = qi_result.get_calibration()
        self.assertIsNone(calibration)

    def test_no_calibration_data(self):
        backend_name = 'test_backend'
        backend_version = '1.2.0'
        qobj_id = '42'
        job_id = '42'
        success = True
        experiment_result = [self.experiment_result_4]
        qi_result = QIResult(backend_name, backend_version, qobj_id, job_id, success, experiment_result)
        self.assertRaisesRegex(QiskitBackendError, 'No calibration data for experiment "0"',
                               qi_result.get_calibration, 0)

    def test_no_probabilities_multiple_measurement_data(self):
        backend_name = 'test_backend'
        backend_version = '1.2.0'
        qobj_id = '42'
        job_id = '42'
        success = True
        experiment_result = [self.experiment_result_4]
        qi_result = QIResult(backend_name, backend_version, qobj_id, job_id, success, experiment_result)
        self.assertRaisesRegex(QiskitBackendError, 'No probabilities_multiple_measurement for experiment "0"',
                               qi_result.get_probabilities_multiple_measurement, 0)

    def test_raw_results(self):
        backend_name = 'test_backend'
        backend_version = '1.2.0'
        qobj_id = '42'
        job_id = '42'
        success = True
        experiment_result = [self.experiment_result_1, self.experiment_result_2]
        qi_result = QIResult(backend_name, backend_version, qobj_id, job_id, success, experiment_result)

        probabilities = qi_result.get_raw_result('probabilities', 'Test1')
        self.assertListEqual(probabilities, [{'0x0': 0.42, '0x3': 0.58}])
        probabilities = qi_result.get_raw_result('probabilities')
        self.assertListEqual(probabilities, [{'0x0': 0.42, '0x3': 0.58},
                                             {'0x0': 0.24, '0x1': 0.25, '0x2': 0.23, '0x3': 0.28}])

        self.assertRaisesRegex(QiskitBackendError, 'Result does not contain fake_field data for experiment "0"',
                               qi_result.get_raw_result, 'fake_field', 0)
