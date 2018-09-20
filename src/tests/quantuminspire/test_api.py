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

import unittest
from collections import OrderedDict
from functools import partial
from unittest.mock import Mock, call, patch
import io

import quantuminspire
from quantuminspire.api import QuantumInspireAPI
from quantuminspire.exceptions import ApiError


class MockApiBasicAuth:

    def __init__(self, email, password, domain=None, scheme=None):
        """ Basic mock for coreapi.auth.BasicAuthentication."""
        self.email = email
        self.password = password
        self.domain = domain
        self.scheme = scheme


class MockApiClient:

    handlers = dict()

    def __init__(self, auth=None):
        """ Basic mock for coreapi.Client."""
        self.authentication = auth

    def get(self, url):
        return url

    def action(self, document, keys, params=None, validate=True, overrides=None,
               action=None, encoding=None, transform=None):
        if keys[0] not in self.__class__.handlers:
            raise Exception("action %s not mocked" % keys[0])
        return self.__class__.handlers[keys[0]](self, document, keys, params, validate,
                                                overrides, action, encoding, transform)


class TestQuantumInspireAPI(unittest.TestCase):

    def setUp(self):
        self.authentication = MockApiBasicAuth('user', 'unknown')
        self.coreapi_client = MockApiClient

    def test_get_HasCorrectOutput(self, mock_key='MockKey'):
        api = QuantumInspireAPI('FakeURL', self.authentication, coreapi_client_class=self.coreapi_client)
        expected = mock_key
        actual = api._get(mock_key)
        self.assertEqual(expected, actual)

    def test_action_HasCorrectOutput(self, mock_key='MockKey', mock_result=1234):
        def mock_result_callable(mock_api, document, keys, params=None, validate=None,
                                 overrides=None, action=None, encoding=None, transform=None):
            self.assertEqual(keys[0], mock_key)
            return mock_result
        api = QuantumInspireAPI('FakeURL', self.authentication, coreapi_client_class=self.coreapi_client)
        self.coreapi_client.handlers[mock_key] = mock_result_callable
        actual = api._action([mock_key])
        self.assertEqual(mock_result, actual)

    def test_load_schema_CollectsCorrectSchema(self):
        base_url = 'https://api.mock.test.com/'
        expected = base_url + 'schema/'
        api = QuantumInspireAPI(base_url, self.authentication, coreapi_client_class=self.coreapi_client)
        api._load_schema()
        self.assertEqual(expected, api.document)

    def test_zload_schema_RaisesException(self):
        def raises_error(self, url):
            raise NotImplementedError
        coreapi_client = MockApiClient
        coreapi_client.get = raises_error
        self.assertRaises(Exception, QuantumInspireAPI, 'FakeURL',
                          self.authentication, coreapi_client_class=coreapi_client)

    def __mock_default_backendtype_handler(self, mock_api, document, keys, params=None, validate=None,
                                           overrides=None, action=None, encoding=None, transform=None):
        self.assertEqual(keys[1], 'default')
        self.assertEqual(keys[2], 'list')
        return OrderedDict([('url', 'https://api.quantum-inspire.com/backendtypes/1/'),
                            ('name', 'QX Single-node Simulator'),
                            ('is_hardware_backend', False),
                            ('required_permission', 'can_simulate_single_node_qutech'),
                            ('number_of_qubits', 26),
                            ('description', 'Dummy'),
                            ('topology', '{"edges": []}'),
                            ('is_allowed', True)])

    def __mock_backendtypes_handler(self, mock_api, document, keys, params=None, validate=None,
                                    overrides=None, action=None, encoding=None, transform=None):
        self.assertEqual(keys[1], 'list')
        return [OrderedDict([('url', 'https://api.quantum-inspire.com/backendtypes/1/'),
                             ('name', 'QX Single-node Simulator'),
                             ('is_hardware_backend', False),
                             ('required_permission', 'can_simulate_single_node_qutech'),
                             ('number_of_qubits', 26),
                             ('description', 'Single-node running on a 4GB Hetzner VPS.'),
                             ('topology', '{"edges": []}'),
                             ('is_allowed', True)]),
                OrderedDict([('url', 'https://api.quantum-inspire.com/backendtypes/2/'),
                             ('name', 'QX Single-node Simulator SurfSara'),
                             ('is_hardware_backend', False),
                             ('required_permission', 'can_simulate_single_node_cartesius'),
                             ('number_of_qubits', 31),
                             ('description', 'Single node simulator on Cartesius supercomputer.'),
                             ('topology', '{"edges": []}'),
                             ('is_allowed', True)])]

    def __mock_backendtype_handler(self, mock_api, document, keys, params=None, validate=None,
                                   overrides=None, action=None, encoding=None, transform=None):
        self.assertEqual(keys[1], 'read')
        self.assertEqual(params, {'id': 1})
        return OrderedDict([('url', 'https://api.quantum-inspire.com/backendtypes/1/'),
                            ('name', 'QX Single-node Simulator'),
                            ('is_hardware_backend', False),
                            ('required_permission', 'can_simulate_single_node_qutech'),
                            ('number_of_qubits', 26),
                            ('description', 'Single-node running on a 4GB Hetzner VPS.'),
                            ('topology', '{"edges": []}'),
                            ('is_allowed', True)])

    def test_list_backend_types_HasCorrectInputAndOutput(self):
        self.coreapi_client.handlers['backendtypes'] = self.__mock_backendtypes_handler
        api = QuantumInspireAPI('FakeURL', self.authentication, coreapi_client_class=self.coreapi_client)
        with unittest.mock.patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            api.list_backend_types()
            print_string = mock_stdout.getvalue()
            self.assertIn('Backend: QX', print_string)

    def test_get_backend_types_HasCorrectInputAndOutput(self):
        expected = self.__mock_backendtypes_handler(None, None, ['test', 'list'])
        self.coreapi_client.handlers['backendtypes'] = self.__mock_backendtypes_handler
        api = QuantumInspireAPI('FakeURL', self.authentication, coreapi_client_class=self.coreapi_client)
        actual = api.get_backend_types()
        self.assertListEqual(actual, expected)

    def test_get_backend_type_HasCorrectInputAndOutput(self):
        identity = 1
        expected = self.__mock_backendtype_handler(None, None, ['test', 'read'], params={'id': identity})
        self.coreapi_client.handlers['backendtypes'] = self.__mock_backendtype_handler
        api = QuantumInspireAPI('FakeURL', self.authentication, coreapi_client_class=self.coreapi_client)
        actual = api.get_backend_type(identity)
        self.assertDictEqual(actual, expected)

    def test_get_backend_type_by_name_CorrectsCorrectBackend(self):
        backend_name = 'QX Single-node Simulator'
        self.coreapi_client.handlers['backendtypes'] = self.__mock_backendtypes_handler
        api = QuantumInspireAPI('FakeURL', self.authentication, coreapi_client_class=self.coreapi_client)
        actual = api.get_backend_type_by_name(backend_name)
        self.assertEqual(actual['name'], backend_name)

    def test_get_backend_type_by_name_RaisesValueError(self):
        backend_name = 'Invalid Simulator'
        self.coreapi_client.handlers['backendtypes'] = self.__mock_backendtypes_handler
        api = QuantumInspireAPI('FakeURL', self.authentication, coreapi_client_class=self.coreapi_client)
        self.assertRaises(ApiError, api.get_backend_type_by_name, backend_name)

    def test_get_default_backend_type(self):
        self.coreapi_client.handlers['backendtypes'] = self.__mock_default_backendtype_handler
        expected = self.__mock_default_backendtype_handler(None, None, ['backendtypes', 'default', 'list'])
        api = QuantumInspireAPI('FakeURL', self.authentication, coreapi_client_class=self.coreapi_client)
        actual = api.get_default_backend_type()
        self.assertIsInstance(actual, OrderedDict)
        self.assertDictEqual(actual, expected)

    def test_get_backend_type_RaisesValueError(self):
        identifier = float(0.0)
        self.coreapi_client.handlers['backendtypes'] = self.__mock_backendtypes_handler
        api = QuantumInspireAPI('FakeURL', self.authentication, coreapi_client_class=self.coreapi_client)
        self.assertRaises(ValueError, api.get_backend_type, identifier)

    def __mock_list_projects_handler(self, mock_api, document, keys, params=None, validate=None,
                                     overrides=None, action=None, encoding=None, transform=None):
        self.assertEqual(keys[1], 'list')
        return [OrderedDict([('url', 'https://api.quantum-inspire.com/projects/1/'),
                             ('id', 11),
                             ('name', 'Grover algorithm - 1900-01-01 10:00'),
                             ('owner', 'https://api.quantum-inspire.com/users/1/'),
                             ('assets', 'https://api.quantum-inspire.com/projects/1/assets/'),
                             ('backend_type', 'https://api.quantum-inspire.com/backendtypes/1/'),
                             ('default_number_of_shots', 1)]),
                OrderedDict([('url', 'https://api.quantum-inspire.com/projects/2/'),
                             ('id', 12),
                             ('name', 'Grover algorithm - 1900-01-01 11:00'),
                             ('owner', 'https://api.quantum-inspire.com/users/2/'),
                             ('assets', 'https://api.quantum-inspire.com/projects/2/assets/'),
                             ('backend_type', 'https://api.quantum-inspire.com/backendtypes/2/'),
                             ('default_number_of_shots', 2)])]

    def __mock_project_handler(self, input_params, input_key, mock_api, document, keys, params=None,
                               validate=None, overrides=None, action=None, encoding=None, transform=None):
        self.assertDictEqual(params, input_params)
        self.assertEqual(keys[1], input_key)
        return OrderedDict([('url', 'https://api.quantum-inspire.com/projects/1/'),
                            ('id', 11),
                            ('name', 'Grover algorithm - 1900-01-01 10:00'),
                            ('owner', 'https://api.quantum-inspire.com/users/1/'),
                            ('assets', 'https://api.quantum-inspire.com/projects/1/assets/'),
                            ('backend_type', 'https://api.quantum-inspire.com/backendtypes/1/'),
                            ('default_number_of_shots', 1)])

    def test_list_projects_HasCorrectInputAndOutput(self):
        self.coreapi_client.handlers['projects'] = self.__mock_list_projects_handler
        api = QuantumInspireAPI('FakeURL', self.authentication, coreapi_client_class=self.coreapi_client)
        with unittest.mock.patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            api.list_projects()
            print_string = mock_stdout.getvalue()
            self.assertIn('Project: Grover', print_string)

    def test_get_project_HasCorrectInAndOutput(self):
        identity = 1
        expected_payload = {'id': identity}
        expected = self.__mock_project_handler({}, 'read', None, None, ['test', 'read'], {})
        self.coreapi_client.handlers['projects'] = partial(self.__mock_project_handler, expected_payload, 'read')
        api = QuantumInspireAPI('FakeURL', self.authentication, coreapi_client_class=self.coreapi_client)
        actual = api.get_project(project_id=identity)
        self.assertDictEqual(actual, expected)

    def test_create_project_HasCorrectInputAndOutput(self):
        name = 'TestProject'
        default_number_of_shots = 0
        backend = {'url': 'https://api.quantum-inspire.com/backendtypes/1/'}
        expected_payload = {
            'name': name,
            'default_number_of_shots': default_number_of_shots,
            'backend_type': backend['url'],
        }
        expected = self.__mock_project_handler({}, 'create', None, None, ['test', 'create'], {})
        self.coreapi_client.handlers['projects'] = partial(self.__mock_project_handler, expected_payload, 'create')
        api = QuantumInspireAPI('FakeURL', self.authentication, coreapi_client_class=self.coreapi_client)
        actual = api._create_project(name, default_number_of_shots, backend)
        self.assertDictEqual(expected, actual)

    def test_delete_project_HasCorrectInputAndOutput(self):
        identity = 1
        expected_payload = {'id': identity}
        self.coreapi_client.handlers['projects'] = partial(self.__mock_project_handler, expected_payload, 'delete')
        api = QuantumInspireAPI('FakeURL', self.authentication, coreapi_client_class=self.coreapi_client)
        actual = api._delete_project(project_id=identity)
        self.assertIsNone(actual)

    def __mock_list_jobs_handler(self, mock_api, document, keys, params=None, validate=None,
                                 overrides=None, action=None, encoding=None, transform=None):
        self.assertEqual(keys[1], 'list')
        return [OrderedDict([('url', 'https,//api.quantum-inspire.com/jobs/530/'),
                             ('name', 'qi-sdk-job-5852eb68-a794-11e8-9447-a44cc848f1f2'),
                             ('id', 530),
                             ('status', 'COMPLETE'),
                             ('input', 'https,//api.quantum-inspire.com/assets/629/'),
                             ('backend', 'https,//api.quantum-inspire.com/backends/1/'),
                             ('backend_type', 'https,//api.quantum-inspire.com/backendtypes/1/'),
                             ('results', 'https,//api.quantum-inspire.com/jobs/530/result/'),
                             ('queued_at', '2018-08-24T11,53,41.352732Z'),
                             ('number_of_shots', 1024)]),
                OrderedDict([('url', 'https,//api.quantum-inspire.com/jobs/509/'),
                             ('name', 'qi-sdk-job-7e37c8fa-a76b-11e8-b5a0-a44cc848f1f2'),
                             ('id', 509),
                             ('status', 'COMPLETE'),
                             ('input', 'https,//api.quantum-inspire.com/assets/607/'),
                             ('backend', 'https,//api.quantum-inspire.com/backends/1/'),
                             ('backend_type', 'https,//api.quantum-inspire.com/backendtypes/1/'),
                             ('results', 'https,//api.quantum-inspire.com/jobs/509/result/'),
                             ('queued_at', '2018-08-24T07,01,21.257557Z'),
                             ('number_of_shots', 1024)])]

    def __mock_job_handler(self, input_params, input_key, mock_api, document, keys, params=None,
                           validate=None, overrides=None, action=None, encoding=None, transform=None,
                           status='COMPLETE'):
        self.assertDictEqual(params, input_params)
        self.assertEqual(keys[1], input_key)
        return OrderedDict([('url', 'https,//api.quantum-inspire.com/jobs/509/'),
                            ('name', 'qi-sdk-job-7e37c8fa-a76b-11e8-b5a0-a44cc848f1f2'),
                            ('id', 509),
                            ('status', status),
                            ('input', 'https,//api.quantum-inspire.com/assets/607/'),
                            ('backend', 'https,//api.quantum-inspire.com/backends/1/'),
                            ('backend_type', 'https,//api.quantum-inspire.com/backendtypes/1/'),
                            ('results', 'https,//api.quantum-inspire.com/jobs/509/result/'),
                            ('queued_at', '2018-08-24T07,01,21.257557Z'),
                            ('number_of_shots', 1024)])

    def test_list_jobs_HasCorrectInputAndOutput(self):
        self.coreapi_client.handlers['jobs'] = self.__mock_list_jobs_handler
        api = QuantumInspireAPI('FakeURL', self.authentication, coreapi_client_class=self.coreapi_client)
        with unittest.mock.patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            api.list_jobs()
            print_string = mock_stdout.getvalue()
            self.assertIn('Job: name', print_string)

    def test_get_job_HasCorrectInAndOutput(self):
        identity = 1
        expected_payload = {'id': identity}
        expected = self.__mock_job_handler({}, 'read', None, None, ['test', 'read'], {})
        self.coreapi_client.handlers['jobs'] = partial(self.__mock_job_handler, expected_payload, 'read')
        api = QuantumInspireAPI('FakeURL', self.authentication, coreapi_client_class=self.coreapi_client)
        actual = api.get_job(job_id=identity)
        self.assertDictEqual(actual, expected)

    def test_create_job_HasCorrectInputAndOutput(self):
        name = 'TestJob'
        asset = {'url': 'https://api.quantum-inspire.com/assets/1/'}
        project = {'backend_type': 'https://api.quantum-inspire.com/backendtypes/1/'}
        number_of_shots = 1
        expected_payload = {
            'name': name,
            'input': asset['url'],
            'backend_type': project['backend_type'],
            'number_of_shots': number_of_shots,
            'status': 'NEW'
        }
        expected = self.__mock_job_handler({}, 'create', None, None, ['test', 'create'], {})
        self.coreapi_client.handlers['jobs'] = partial(self.__mock_job_handler, expected_payload, 'create')
        api = QuantumInspireAPI('FakeURL', self.authentication, coreapi_client_class=self.coreapi_client)
        actual = api._create_job(name, asset, project, number_of_shots)
        self.assertDictEqual(expected, actual)

    def __mock_list_results_handler(self, mock_api, document, keys, params=None, validate=None,
                                    overrides=None, action=None, encoding=None, transform=None):
        self.assertEqual(keys[1], 'list')
        return [OrderedDict([('id', 502),
                             ('url', 'https,//api.quantum-inspire.com/results/1/'),
                             ('job', 'https,//api.quantum-inspire.com/jobs/10/'),
                             ('created_at', '1900-01-01T01,00,00.00000Z'),
                             ('number_of_qubits', 2),
                             ('seconds', 0.0),
                             ('raw_text', ''),
                             ('raw_data_url', 'https,//api.quantum-inspire.com/results/1/raw-data/f2b6/'),
                             ('histogram', {'3', 0.5068359375, '0', 0.4931640625}),
                             ('histogram_url', 'https,//api.quantum-inspire.com/results/1/histogram/f2b6/'),
                             ('measurement_mask', 0),
                             ('quantum_states_url', 'https,//api.quantum-inspire.com/results/1/quantum-states/f2b6d/'),
                             ('measurement_register_url', 'https,//api.quantum-inspire.com/results/1/f2b6d/')]),
                OrderedDict([('id', 485),
                             ('url', 'https,//api.quantum-inspire.com/results/1/'),
                             ('job', 'https,//api.quantum-inspire.com/jobs/20/'),
                             ('created_at', '1900-01-01T01,00,00.00000Z'),
                             ('number_of_qubits', 2),
                             ('seconds', 0.0),
                             ('raw_text', ''),
                             ('raw_data_url', 'https,//api.quantum-inspire.com/results/2/raw-data/162c/'),
                             ('histogram', {'0', 0.5029296875, '3', 0.4970703125}),
                             ('histogram_url', 'https,//api.quantum-inspire.com/results/2/histogram/162c/'),
                             ('measurement_mask', 0),
                             ('quantum_states_url', 'https,//api.quantum-inspire.com/results/2/quantum-states/162c/'),
                             ('measurement_register_url', 'https,//api.quantum-inspire.com/results/2/162c/')])]

    def __mock_result_handler(self, input_params, input_key, mock_api, document, keys, params=None,
                              validate=None, overrides=None, action=None, encoding=None, transform=None):
        self.assertDictEqual(params, input_params)
        self.assertEqual(keys[1], input_key)
        return OrderedDict([('id', 485),
                            ('url', 'https,//api.quantum-inspire.com/results/1/'),
                            ('job', 'https,//api.quantum-inspire.com/jobs/20/'),
                            ('created_at', '1900-01-01T01,00,00.00000Z'),
                            ('number_of_qubits', 2),
                            ('seconds', 0.0),
                            ('raw_text', ''),
                            ('raw_data_url', 'https,//api.quantum-inspire.com/results/2/raw-data/162c/'),
                            ('histogram', {'0', 0.5029296875, '3', 0.4970703125}),
                            ('histogram_url', 'https,//api.quantum-inspire.com/results/2/histogram/162c/'),
                            ('measurement_mask', 0),
                            ('quantum_states_url', 'https,//api.quantum-inspire.com/results/2/quantum-states/162c/'),
                            ('measurement_register_url', 'https,//api.quantum-inspire.com/results/2/162c/')])

    def test_list_results_HasCorrectOutput(self):
        self.coreapi_client.handlers['results'] = self.__mock_list_results_handler
        api = QuantumInspireAPI('FakeURL', self.authentication, coreapi_client_class=self.coreapi_client)
        with unittest.mock.patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            api.list_results()
            print_string = mock_stdout.getvalue()
            self.assertIn('Result: id', print_string)

    def test_get_results_HasCorrectInputAndOutput(self):
        expected = self.__mock_list_results_handler(None, None, ['test', 'list'])
        self.coreapi_client.handlers['results'] = self.__mock_list_results_handler
        api = QuantumInspireAPI('FakeURL', self.authentication, coreapi_client_class=self.coreapi_client)
        actual = api.get_results()
        self.assertListEqual(actual, expected)

    def test_get_result_HasCorrectInputAndOutput(self):
        identity = 1
        expected_payload = {'id': identity}
        expected = self.__mock_result_handler({}, 'read', None, None, ['test', 'read'], {})
        self.coreapi_client.handlers['results'] = partial(self.__mock_result_handler, expected_payload, 'read')
        api = QuantumInspireAPI('FakeURL', self.authentication, coreapi_client_class=self.coreapi_client)
        actual = api.get_result(result_id=identity)
        self.assertDictEqual(actual, expected)

    def __mock_list_assets_handler(self, mock_api, document, keys, params=None, validate=None,
                                   overrides=None, action=None, encoding=None, transform=None):
        self.assertEqual(keys[1], 'list')
        return [OrderedDict([('url', 'https,//api.quantum-inspire.com/assets/31/'),
                             ('id', 31),
                             ('name', 'Grover algorithm - 2018-07-18 13,32'),
                             ('contentType', 'text/plain'),
                             ('content', 'version 1.0\n\nqubits 9\n\n\n# Grover search algorithm\n  display'),
                             ('project', 'https,//api.quantum-inspire.com/projects/11/'),
                             ('project_id', 11)]),
                OrderedDict([('url', 'https,//api.quantum-inspire.com/assets/171/'),
                             ('id', 171),
                             ('name', 'Grover algorithm - 2018-07-18 13,32'),
                             ('contentType', 'text/plain'),
                             ('content', 'version 1.0\n\nqubits 9\n\n\n# Grover search algorithm\n  display'),
                             ('project', 'https,//api.quantum-inspire.com/projects/11/'),
                             ('project_id', 11)])]

    def __mock_asset_handler(self, input_params, input_key, mock_api, document, keys, params=None,
                             validate=None, overrides=None, action=None, encoding=None, transform=None):
        self.assertDictEqual(params, input_params)
        self.assertEqual(keys[1], input_key)
        return OrderedDict([('url', 'https,//api.quantum-inspire.com/assets/171/'),
                            ('id', 171),
                            ('name', 'Grover algorithm - 2018-07-18 13,32'),
                            ('contentType', 'text/plain'),
                            ('content', 'version 1.0\n\nqubits 9\n\n\n# Grover search algorithm\n  display'),
                            ('project', 'https,//api.quantum-inspire.com/projects/11/'),
                            ('project_id', 11)])

    def test_list_assets_HasCorrectOutput(self):
        self.coreapi_client.handlers['assets'] = self.__mock_list_assets_handler
        api = QuantumInspireAPI('FakeURL', self.authentication, coreapi_client_class=self.coreapi_client)
        with unittest.mock.patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            api.list_assets()
            print_string = mock_stdout.getvalue()
            self.assertIn('Asset: name', print_string)

    def test_get_assets_HasCorrectInputAndOutput(self):
        expected = self.__mock_list_assets_handler(None, None, ['test', 'list'])
        self.coreapi_client.handlers['assets'] = self.__mock_list_assets_handler
        api = QuantumInspireAPI('FakeURL', self.authentication, coreapi_client_class=self.coreapi_client)
        actual = api.get_assets()
        self.assertListEqual(actual, expected)

    def test_get_asset_HasCorrectInputAndOutput(self):
        identity = 1
        expected_payload = {'id': identity}
        expected = self.__mock_asset_handler({}, 'read', None, None, ['test', 'read'], {})
        self.coreapi_client.handlers['assets'] = partial(self.__mock_asset_handler, expected_payload, 'read')
        api = QuantumInspireAPI('FakeURL', self.authentication, coreapi_client_class=self.coreapi_client)
        actual = api.get_asset(asset_id=identity)
        self.assertDictEqual(actual, expected)

    def test_create_asset_HasCorrectInputAndOutput(self):
        name = 'TestAsset'
        project = {'url': 'https://api.quantum-inspire.com/backendtypes/1/'}
        content = 'version 1.0\n\nqubits 9\n\n\n# Grover search algorithm\n  display'
        expected_payload = {
            'name': name,
            'contentType': 'application/qasm',
            'project': project['url'],
            'content': content,
        }
        expected = self.__mock_asset_handler({}, 'create', None, None, ['test', 'create'], {})
        self.coreapi_client.handlers['assets'] = partial(self.__mock_asset_handler, expected_payload, 'create')
        api = QuantumInspireAPI('FakeURL', self.authentication, coreapi_client_class=self.coreapi_client)
        actual = api._create_asset(name, project, content)
        self.assertDictEqual(expected, actual)

    def test_wait_for_completed_job_ReturnsTrue(self):
        job_id = 1
        collect_max_tries = 3
        expected_payload = {'id': job_id}
        self.coreapi_client.handlers['jobs'] = partial(self.__mock_job_handler, expected_payload, 'read',
                                                       status='COMPLETE')
        api = QuantumInspireAPI('FakeURL', self.authentication, coreapi_client_class=self.coreapi_client)
        is_completed = api._wait_for_completed_job(job_id, collect_max_tries, sec_retry_delay=0.0)
        self.assertTrue(is_completed)

    def test_wait_for_completed_job_ReturnsFalse(self):
        job_id = 1
        collect_max_tries = 3
        expected_payload = {'id': job_id}
        self.coreapi_client.handlers['jobs'] = partial(self.__mock_job_handler, expected_payload, 'read',
                                                       status='RUNNING')
        api = QuantumInspireAPI('FakeURL', self.authentication, coreapi_client_class=self.coreapi_client,
                                logger=Mock())
        is_completed = api._wait_for_completed_job(job_id, collect_max_tries, sec_retry_delay=0.0)
        self.assertFalse(is_completed)

    def __fake_backendtype_handler(self, mock_api, document, keys, params=None, validate=None,
                                   overrides=None, action=None, encoding=None, transform=None, call_mock=None):
        if call_mock:
            call_mock(keys[1])
        if params is None:
            backend_type_id = 1
        else:
            backend_type_id = params.get('id', 1)
        if keys[1] == 'list':
            return [OrderedDict([('url', 'https://api.quantum-inspire.com/backendtypes/1/'),
                                 ('name', 'QX Single-node Simulator'),
                                 ('is_hardware_backend', False),
                                 ('required_permission', 'can_simulate_single_node_qutech'),
                                 ('number_of_qubits', 26),
                                 ('description', 'Single-node running on a 4GB Hetzner VPS.'),
                                 ('topology', '{"edges": []}'),
                                 ('is_allowed', True)]),
                    OrderedDict([('url', 'https://api.quantum-inspire.com/backendtypes/2/'),
                                 ('name', 'QX Single-node Simulator'),
                                 ('is_hardware_backend', False),
                                 ('required_permission', 'can_simulate_single_node_qutech'),
                                 ('number_of_qubits', 26),
                                 ('description',
                                  'Single-node running on a 4GB Hetzner VPS.'),
                                 ('topology', '{"edges": []}'),
                                 ('is_allowed', True)])]
        else:
            # return specified id
            return OrderedDict([('url', 'https://api.quantum-inspire.com/backendtypes/%d/' % backend_type_id),
                                ('name', 'QX Single-node Simulator'),
                                ('is_hardware_backend', False),
                                ('required_permission', 'can_simulate_single_node_qutech'),
                                ('number_of_qubits', 26),
                                ('description', 'Single-node running on a 4GB Hetzner VPS.'),
                                ('topology', '{"edges": []}'),
                                ('is_allowed', True)])

    def __fake_project_handler(self, mock_api, document, keys, params=None, validate=None,
                               overrides=None, action=None, encoding=None, transform=None, call_mock=None):
        if call_mock:
            call_mock(keys[1])
        return OrderedDict([('url', 'https://api.quantum-inspire.com/projects/1/'),
                            ('id', 11),
                            ('name', 'Grover algorithm - 1900-01-01 10:00'),
                            ('owner', 'https://api.quantum-inspire.com/users/1/'),
                            ('assets', 'https://api.quantum-inspire.com/projects/1/assets/'),
                            ('backend_type', 'https://api.quantum-inspire.com/backendtypes/1/'),
                            ('number_of_shots', 1)])

    def __fake_project_handler_params(self, mock_api, document, keys, params=None, validate=None,
                                      overrides=None, action=None, encoding=None, transform=None, call_mock=None):
        if call_mock:
            call_mock(keys[1], params=params)
        return OrderedDict([('url', 'https://api.quantum-inspire.com/projects/1/'),
                            ('id', 11),
                            ('name', 'Grover algorithm - 1900-01-01 10:00'),
                            ('owner', 'https://api.quantum-inspire.com/users/1/'),
                            ('assets', 'https://api.quantum-inspire.com/projects/1/assets/'),
                            ('backend_type', 'https://api.quantum-inspire.com/backendtypes/1/'),
                            ('number_of_shots', 1)])

    def __fake_asset_handler(self, mock_api, document, keys, params=None, validate=None,
                             overrides=None, action=None, encoding=None, transform=None, call_mock=None):
        if call_mock:
            call_mock(keys[1])
        return OrderedDict([('url', 'https,//api.quantum-inspire.com/assets/1/'),
                            ('id', 171),
                            ('name', 'Grover algorithm - 2018-07-18 13,32'),
                            ('contentType', 'text/plain'),
                            ('content', 'version 1.0\n\nqubits 9\n\n\n# Grover search algorithm\n  display'),
                            ('project', 'https,//api.quantum-inspire.com/projects/1/'),
                            ('project_id', 1)])

    def __fake_job_handler(self, mock_api, document, keys, params=None, validate=None,
                           overrides=None, action=None, encoding=None, transform=None, call_mock=None):
        if call_mock:
            call_mock(keys[1])
        return OrderedDict([('url', 'https,//api.quantum-inspire.com/jobs/509/'),
                            ('name', 'qi-sdk-job-7e37c8fa-a76b-11e8-b5a0-a44cc848f1f2'),
                            ('id', 509),
                            ('status', 'COMPLETE'),
                            ('input', 'https,//api.quantum-inspire.com/assets/607/'),
                            ('backend', 'https,//api.quantum-inspire.com/backends/1/'),
                            ('backend_type', 'https,//api.quantum-inspire.com/backendtypes/1/'),
                            ('results', 'https://api.quantum-inspire.com/jobs/1/result/mocked'),
                            ('queued_at', '2018-08-24T07,01,21.257557Z'),
                            ('number_of_shots', 1)])

    def __fake_results_handler(self, mock_api, document, keys, params=None, validate=None,
                               overrides=None, action=None, encoding=None, transform=None, call_mock=None):
        if call_mock:
            call_mock(keys[1])
        return OrderedDict([('url', 'https,//api.quantum-inspire.com/jobs/509/'),
                            ('name', 'qi-sdk-job-7e37c8fa-a76b-11e8-b5a0-a44cc848f1f2'),
                            ('id', 509),
                            ('status', 'COMPLETE'),
                            ('input', 'https,//api.quantum-inspire.com/assets/607/'),
                            ('backend', 'https,//api.quantum-inspire.com/backends/1/'),
                            ('backend_type', 'https,//api.quantum-inspire.com/backendtypes/1/'),
                            ('results', 'https://api.quantum-inspire.com/jobs/1/result/mocked'),
                            ('queued_at', '2018-08-24T07,01,21.257557Z'),
                            ('number_of_shots', 1)])

    def test_execute_qasm_DefaultBackend(self):
        job_mock = Mock()
        self.coreapi_client.handlers['jobs'] = partial(self.__fake_job_handler, call_mock=job_mock)
        asset_mock = Mock()
        self.coreapi_client.handlers['assets'] = partial(self.__fake_asset_handler, call_mock=asset_mock)
        project_mock = Mock()
        self.coreapi_client.handlers['projects'] = partial(self.__fake_project_handler_params, call_mock=project_mock)
        backend_mock = Mock()
        self.coreapi_client.handlers['backendtypes'] = partial(self.__fake_backendtype_handler, call_mock=backend_mock)

        qasm = 'version 1.0\n'
        api = QuantumInspireAPI('FakeURL', self.authentication, coreapi_client_class=self.coreapi_client)
        backend_type = api.get_backend_type(identifier=2)
        _ = api.execute_qasm(qasm, backend_type, collect_tries=1)
        project_call = tuple(project_mock.call_args_list[0])
        self.assertEqual(project_call[0][0], 'create')
        self.assertEqual(project_call[1]['params']['backend_type'], r'https://api.quantum-inspire.com/backendtypes/2/')

        project_mock = Mock()
        self.coreapi_client.handlers['projects'] = partial(self.__fake_project_handler_params, call_mock=project_mock)
        _ = api.execute_qasm(qasm, backend_type=None, collect_tries=1)
        project_call = tuple(project_mock.call_args_list[0])
        self.assertEqual(project_call[1]['params']['backend_type'], r'https://api.quantum-inspire.com/backendtypes/1/')

        project_mock = Mock()
        self.coreapi_client.handlers['projects'] = partial(self.__fake_project_handler_params, call_mock=project_mock)
        _ = api.execute_qasm(qasm, backend_type='QX Single-node Simulator', collect_tries=1)
        project_call = tuple(project_mock.call_args_list[0])
        self.assertEqual(project_call[1]['params']['backend_type'], r'https://api.quantum-inspire.com/backendtypes/1/')

    def test_execute_qasm_CreatesNewProject(self):
        job_mock = Mock()
        self.coreapi_client.handlers['jobs'] = partial(self.__fake_job_handler, call_mock=job_mock)
        asset_mock = Mock()
        self.coreapi_client.handlers['assets'] = partial(self.__fake_asset_handler, call_mock=asset_mock)
        project_mock = Mock()
        self.coreapi_client.handlers['projects'] = partial(self.__fake_project_handler, call_mock=project_mock)
        backend_mock = Mock()
        self.coreapi_client.handlers['backendtypes'] = partial(self.__fake_backendtype_handler, call_mock=backend_mock)
        qasm = 'version 1.0...'
        api = QuantumInspireAPI('FakeURL', self.authentication, coreapi_client_class=self.coreapi_client)
        backend = api.get_backend_type(identifier=1)
        expected = 'https://api.quantum-inspire.com/jobs/1/result/mocked'
        actual = api.execute_qasm(qasm, backend, collect_tries=1)
        self.assertIsNone(api.project_name)
        job_mock.assert_has_calls([call('create'), call('read')], any_order=True)
        asset_mock.assert_called_once_with('create')
        project_mock.assert_has_calls([call('create'), call('delete')], any_order=True)
        backend_mock.assert_called_once_with('read')
        self.assertEqual(expected, actual)

    @patch('quantuminspire.api.QuantumInspireAPI.get_projects')
    def test_execute_qasm_UsesProject(self, get_projects_mock):
        job_mock = Mock()
        self.coreapi_client.handlers['jobs'] = partial(self.__fake_job_handler, call_mock=job_mock)
        asset_mock = Mock()
        self.coreapi_client.handlers['assets'] = partial(self.__fake_asset_handler, call_mock=asset_mock)
        project_mock = Mock()
        self.coreapi_client.handlers['projects'] = partial(self.__fake_project_handler, call_mock=project_mock)
        backend_mock = Mock()
        self.coreapi_client.handlers['backendtypes'] = partial(self.__fake_backendtype_handler, call_mock=backend_mock)
        get_projects_mock.return_value = {}
        qasm = 'version 1.0...'
        project_name = 'Grover algorithm - 1900-01-01 10:00'
        api = QuantumInspireAPI('FakeURL', self.authentication, project_name,
                                coreapi_client_class=self.coreapi_client)
        backend = api.get_backend_type(identifier=1)
        expected = 'https://api.quantum-inspire.com/jobs/1/result/mocked'
        actual = api.execute_qasm(qasm, backend, collect_tries=1)

        self.assertEqual(api.project_name, project_name)
        job_mock.assert_has_calls([call('create'), call('read')], any_order=True)
        asset_mock.assert_called_once_with('create')
        project_mock.assert_called_once_with('create')
        backend_mock.assert_called_once_with('read')
        self.assertEqual(expected, actual)
