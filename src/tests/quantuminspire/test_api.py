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

import sys
import logging
import json
import io
import re
from coreapi.exceptions import CoreAPIException, ErrorMessage
from collections import OrderedDict
from functools import partial
from unittest import mock, TestCase
from unittest.mock import Mock, patch, call, MagicMock, mock_open

from quantuminspire.api import QuantumInspireAPI
from quantuminspire.exceptions import ApiError, AuthenticationError
from quantuminspire.job import QuantumInspireJob


class MockApiBasicAuth:

    def __init__(self, email, password, domain=None, scheme=None):
        """ Basic mock for coreapi.auth.BasicAuthentication."""
        self.email = email
        self.password = password
        self.domain = domain
        self.scheme = scheme


class MockApiTokenAuth:

    def __init__(self, token, scheme=None, domain=None):
        """ Basic mock for coreapi.auth.TokenAuthentication."""
        self.token = token
        self.scheme = scheme
        self.domain = domain


class MockApiClient:
    handlers = dict()
    getters = dict()

    def __init__(self, auth=None):
        """ Basic mock for coreapi.Client."""
        self.authentication = auth
        self.getters['schema/'] = ''

    def get(self, url):
        if url not in self.__class__.getters:
            raise Exception("get %s not mocked" % url)
        return self.__class__.getters[url]

    def action(self, document, keys, params=None, validate=True, overrides=None,
               action=None, encoding=None, transform=None):
        if keys[0] not in self.__class__.handlers:
            raise Exception("action %s not mocked" % keys[0])
        return self.__class__.handlers[keys[0]](self, document, keys, params, validate,
                                                overrides, action, encoding, transform)


class TestQuantumInspireAPI(TestCase):

    def setUp(self):
        self.authentication = MockApiBasicAuth('user', 'unknown')
        self.token_authentication = MockApiTokenAuth('some_token', 'token')
        self.coreapi_client = MockApiClient

    def test_get_has_correct_output(self, mock_key='MockKey'):
        expected = 'Test'
        self.coreapi_client.getters[mock_key] = expected
        api = QuantumInspireAPI('FakeURL', self.authentication, coreapi_client_class=self.coreapi_client)
        actual = api._get(mock_key)
        self.assertEqual(expected, actual)

    def test_action_has_correct_output(self, mock_key='MockKey', mock_result=1234):
        def mock_result_callable(mock_api, document, keys, params=None, validate=None,
                                 overrides=None, action=None, encoding=None, transform=None):
            self.assertEqual(keys[0], mock_key)
            return mock_result

        api = QuantumInspireAPI('FakeURL', self.token_authentication, coreapi_client_class=self.coreapi_client)
        self.coreapi_client.handlers[mock_key] = mock_result_callable
        actual = api._action([mock_key])
        self.assertEqual(mock_result, actual)

    def test_no_authentication(self):
        expected_token = 'secret'
        json.load = MagicMock()
        json.load.return_value = {'token': expected_token}
        with patch.dict('os.environ', values={'QI_TOKEN': expected_token}):
            expected = 'schema/'
            base_url = 'https://api.mock.test.com/'
            url = ''.join([base_url, expected])
            self.coreapi_client.getters[url] = expected
            with patch("builtins.open", mock_open(read_data="secret_token")) as mock_file:
                api = QuantumInspireAPI(base_url, coreapi_client_class=self.coreapi_client)
                self.assertEqual(expected, api.document)

    def test_no_authentication_raises_authentication_error(self):
        expected_token = 'secret'
        json.load = MagicMock()
        json.load.return_value = {'wrong_key': expected_token}
        with patch.dict('os.environ', values={'QI_TOKEN': ''}):
            expected = 'schema/'
            base_url = 'https://api.mock.test.com/'
            url = ''.join([base_url, expected])
            self.coreapi_client.getters[url] = expected
            with patch("builtins.open", mock_open(read_data="secret_token")) as mock_file:
                self.assertRaisesRegex(AuthenticationError, 'No credentials have been provided', QuantumInspireAPI,
                                       base_url, coreapi_client_class=self.coreapi_client)

    def test_load_schema_collects_correct_schema(self):
        expected = 'schema/'
        base_url = 'https://api.mock.test.com/'
        url = ''.join([base_url, expected])
        self.coreapi_client.getters[url] = expected
        api = QuantumInspireAPI(base_url, self.token_authentication, coreapi_client_class=self.coreapi_client)
        api._load_schema()
        self.assertEqual(expected, api.document)

    def test_zload_schema_raises_exception(self):
        def raises_error(self, url):
            raise CoreAPIException

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
        if params['id'] != 1:
            raise ErrorMessage('Not found')
        return OrderedDict([('url', 'https://api.quantum-inspire.com/backendtypes/1/'),
                            ('name', 'QX Single-node Simulator'),
                            ('is_hardware_backend', False),
                            ('required_permission', 'can_simulate_single_node_qutech'),
                            ('number_of_qubits', 26),
                            ('description', 'Single-node running on a 4GB Hetzner VPS.'),
                            ('topology', '{"edges": []}'),
                            ('is_allowed', True)])

    def test_list_backend_types_has_correct_input_and_output(self):
        self.coreapi_client.handlers['backendtypes'] = self.__mock_backendtypes_handler
        api = QuantumInspireAPI('FakeURL', self.authentication, coreapi_client_class=self.coreapi_client)
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            api.list_backend_types()
            print_string = mock_stdout.getvalue()
            self.assertIn('Backend type: QX', print_string)

    def test_get_backend_types_has_correct_input_and_output(self):
        expected = self.__mock_backendtypes_handler(None, None, ['test', 'list'])
        self.coreapi_client.handlers['backendtypes'] = self.__mock_backendtypes_handler
        api = QuantumInspireAPI('FakeURL', self.authentication, coreapi_client_class=self.coreapi_client)
        actual = api.get_backend_types()
        self.assertListEqual(actual, expected)

    def test_get_backend_type_has_correct_input_and_output(self):
        identity = 1
        expected = self.__mock_backendtype_handler(None, None, ['test', 'read'], params={'id': identity})
        self.coreapi_client.handlers['backendtypes'] = self.__mock_backendtype_handler
        api = QuantumInspireAPI('FakeURL', self.authentication, coreapi_client_class=self.coreapi_client)
        actual = api.get_backend_type(identity)
        self.assertDictEqual(actual, expected)

    def test_get_backend_type_by_id_raises_api_error(self):
        identity = 3
        self.coreapi_client.handlers['backendtypes'] = self.__mock_backendtype_handler
        api = QuantumInspireAPI('FakeURL', self.authentication, coreapi_client_class=self.coreapi_client)
        self.assertRaises(ApiError, api.get_backend_type_by_id, identity)

    def test_get_backend_type_by_name_corrects_correct_backend(self):
        backend_name = 'QX Single-node Simulator'
        self.coreapi_client.handlers['backendtypes'] = self.__mock_backendtypes_handler
        api = QuantumInspireAPI('FakeURL', self.authentication, coreapi_client_class=self.coreapi_client)
        actual = api.get_backend_type_by_name(backend_name)
        self.assertEqual(actual['name'], backend_name)

    def test_get_backend_type_by_name_raises_value_error(self):
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

    def test_get_backend_type_raises_value_error(self):
        identifier = float(0.0)
        self.coreapi_client.handlers['backendtypes'] = self.__mock_backendtypes_handler
        api = QuantumInspireAPI('FakeURL', self.authentication, coreapi_client_class=self.coreapi_client)
        self.assertRaises(ValueError, api.get_backend_type, identifier)

    def __mock_list_projects_handler(self, mock_api, document, keys, params=None, validate=None,
                                     overrides=None, action=None, encoding=None, transform=None):
        self.assertEqual(keys[1], 'list')
        return [OrderedDict([('url', 'https://api.quantum-inspire.com/projects/11/'),
                             ('id', 11),
                             ('name', 'Grover algorithm - 1900-01-01 10:00'),
                             ('owner', 'https://api.quantum-inspire.com/users/1/'),
                             ('assets', 'https://api.quantum-inspire.com/projects/11/assets/'),
                             ('backend_type', 'https://api.quantum-inspire.com/backendtypes/1/'),
                             ('default_number_of_shots', 1),
                             ('user_data', '')]),
                OrderedDict([('url', 'https://api.quantum-inspire.com/projects/12/'),
                             ('id', 12),
                             ('name', 'Grover algorithm - 1900-01-01 11:00'),
                             ('owner', 'https://api.quantum-inspire.com/users/2/'),
                             ('assets', 'https://api.quantum-inspire.com/projects/12/assets/'),
                             ('backend_type', 'https://api.quantum-inspire.com/backendtypes/2/'),
                             ('default_number_of_shots', 2),
                             ('user_data', '')])]

    def __mock_project_handler(self, input_params, input_key, mock_api, document, keys, params=None,
                               validate=None, overrides=None, action=None, encoding=None, transform=None):
        self.assertDictEqual(params, input_params)
        self.assertEqual(keys[1], input_key)
        if input_key == 'read' or input_key == 'delete':
            if params['id'] != 11:
                raise ErrorMessage('Not found')
        return OrderedDict([('url', 'https://api.quantum-inspire.com/projects/11/'),
                            ('id', 11),
                            ('name', 'Grover algorithm - 1900-01-01 10:00'),
                            ('owner', 'https://api.quantum-inspire.com/users/1/'),
                            ('assets', 'https://api.quantum-inspire.com/projects/11/assets/'),
                            ('backend_type', 'https://api.quantum-inspire.com/backendtypes/1/'),
                            ('default_number_of_shots', 1)])

    def test_list_projects_has_correct_input_and_output(self):
        self.coreapi_client.handlers['projects'] = self.__mock_list_projects_handler
        api = QuantumInspireAPI('FakeURL', self.authentication, coreapi_client_class=self.coreapi_client)
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            api.list_projects()
            print_string = mock_stdout.getvalue()
            self.assertIn('Project name: Grover', print_string)
            self.assertIn('id: 11', print_string)
            self.assertIn('id: 12', print_string)

    def test_get_project_has_correct_in_and_output(self):
        identity = 11
        expected_payload = {'id': identity}
        expected = self.__mock_project_handler(expected_payload, 'read', None, None, ['test', 'read'], expected_payload)
        self.coreapi_client.handlers['projects'] = partial(self.__mock_project_handler, expected_payload, 'read')
        api = QuantumInspireAPI('FakeURL', self.authentication, coreapi_client_class=self.coreapi_client)
        actual = api.get_project(project_id=identity)
        self.assertDictEqual(actual, expected)

    def test_get_project_raises_api_error(self):
        identity = 999
        payload = {'id': identity}
        self.coreapi_client.handlers['projects'] = partial(self.__mock_project_handler, payload, 'read')
        api = QuantumInspireAPI('FakeURL', self.authentication, coreapi_client_class=self.coreapi_client)
        self.assertRaises(ApiError, api.get_project, identity)

    def test_create_project_has_correct_input_and_output(self):
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
        actual = api.create_project(name, default_number_of_shots, backend)
        self.assertDictEqual(expected, actual)

    def test_delete_project_has_correct_input_and_output(self):
        identity = 11
        expected_payload = {'id': identity}
        self.coreapi_client.handlers['projects'] = partial(self.__mock_project_handler, expected_payload, 'delete')
        api = QuantumInspireAPI('FakeURL', self.authentication, coreapi_client_class=self.coreapi_client)
        self.assertIsNone(api.delete_project(project_id=identity))

    def test_delete_project_raises_api_error(self):
        identity = 999
        expected_payload = {'id': identity}
        self.coreapi_client.handlers['projects'] = partial(self.__mock_project_handler, expected_payload, 'delete')
        api = QuantumInspireAPI('FakeURL', self.authentication, coreapi_client_class=self.coreapi_client)
        self.assertRaises(ApiError, api.delete_project, identity)

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
                             ('queued_at', '2018-08-24T11:53:41:352732Z'),
                             ('number_of_shots', 1024)]),
                OrderedDict([('url', 'https,//api.quantum-inspire.com/jobs/509/'),
                             ('name', 'qi-sdk-job-7e37c8fa-a76b-11e8-b5a0-a44cc848f1f2'),
                             ('id', 509),
                             ('status', 'COMPLETE'),
                             ('input', 'https,//api.quantum-inspire.com/assets/607/'),
                             ('backend', 'https,//api.quantum-inspire.com/backends/1/'),
                             ('backend_type', 'https,//api.quantum-inspire.com/backendtypes/1/'),
                             ('results', 'https,//api.quantum-inspire.com/jobs/509/result/'),
                             ('queued_at', '2018-08-24T07:01:21:257557Z'),
                             ('number_of_shots', 1024),
                             ('user_data', '')])]

    def __mock_job_handler(self, input_params, input_key, mock_api, document, keys, params=None,
                           validate=None, overrides=None, action=None, encoding=None, transform=None,
                           status='COMPLETE'):
        self.assertDictEqual(params, input_params)
        self.assertEqual(keys[1], input_key)
        if input_key == 'read' or input_key == 'delete' or input_key == 'jobs':
            if params['id'] != 509:
                raise ErrorMessage('Not found')
        if input_key == 'create':
            if params['name'] == 'CreateJobFail':
                raise ErrorMessage('Not created')
        return OrderedDict([('url', 'https,//api.quantum-inspire.com/jobs/509/'),
                            ('name', 'qi-sdk-job-7e37c8fa-a76b-11e8-b5a0-a44cc848f1f2'),
                            ('id', 509),
                            ('status', status),
                            ('input', 'https,//api.quantum-inspire.com/assets/171/'),
                            ('backend', 'https,//api.quantum-inspire.com/backends/1/'),
                            ('backend_type', 'https,//api.quantum-inspire.com/backendtypes/1/'),
                            ('results', 'https,//api.quantum-inspire.com/jobs/509/result/'),
                            ('queued_at', '2018-08-24T07:01:21:257557Z'),
                            ('number_of_shots', 1024),
                            ('user_data', '')])

    def __mock_assets_jobs_handler(self, input_params, input_key, mock_api, document, keys, params=None,
                                   validate=None, overrides=None, action=None, encoding=None, transform=None):
        self.assertDictEqual(params, input_params)
        self.assertEqual(keys[1], input_key)
        if input_key == 'read' or input_key == 'delete' or input_key == 'jobs':
            if params['id'] != 171:
                raise ErrorMessage('Not found')
        return [OrderedDict([('url', 'https,//api.quantum-inspire.com/jobs/530/'),
                             ('name', 'qi-sdk-job-5852eb68-a794-11e8-9447-a44cc848f1f2'),
                             ('id', 530),
                             ('status', 'COMPLETE'),
                             ('input', 'https,//api.quantum-inspire.com/assets/629/'),
                             ('backend', 'https,//api.quantum-inspire.com/backends/1/'),
                             ('backend_type', 'https,//api.quantum-inspire.com/backendtypes/1/'),
                             ('results', 'https,//api.quantum-inspire.com/jobs/530/result/'),
                             ('queued_at', '2018-08-24T11:53:41:352732Z'),
                             ('number_of_shots', 1024)]),
                OrderedDict([('url', 'https,//api.quantum-inspire.com/jobs/509/'),
                             ('name', 'qi-sdk-job-7e37c8fa-a76b-11e8-b5a0-a44cc848f1f2'),
                             ('id', 509),
                             ('status', 'COMPLETE'),
                             ('input', 'https,//api.quantum-inspire.com/assets/607/'),
                             ('backend', 'https,//api.quantum-inspire.com/backends/1/'),
                             ('backend_type', 'https,//api.quantum-inspire.com/backendtypes/1/'),
                             ('results', 'https,//api.quantum-inspire.com/jobs/509/result/'),
                             ('queued_at', '2018-08-24T07:01:21:257557Z'),
                             ('number_of_shots', 1024),
                             ('user_data', '')])]

    def test_list_jobs_has_correct_input_and_output(self):
        self.coreapi_client.handlers['jobs'] = self.__mock_list_jobs_handler
        api = QuantumInspireAPI('FakeURL', self.authentication, coreapi_client_class=self.coreapi_client)
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            api.list_jobs()
            print_string = mock_stdout.getvalue()
            self.assertIn('Job name:', print_string)
            self.assertIn('id: 530', print_string)
            self.assertIn('name: qi-sdk-job-5852eb68-a794-11e8-9447-a44cc848f1f2', print_string)
            self.assertIn('id: 509', print_string)
            self.assertIn('name: qi-sdk-job-7e37c8fa-a76b-11e8-b5a0-a44cc848f1f2', print_string)
            self.assertIn('status: COMPLETE', print_string)

    def test_get_job_has_correct_in_and_output(self):
        identity = 509
        expected_payload = {'id': identity}
        expected = self.__mock_job_handler(expected_payload, 'read', None, None, ['test', 'read'], expected_payload)
        self.coreapi_client.handlers['jobs'] = partial(self.__mock_job_handler, expected_payload, 'read')
        api = QuantumInspireAPI('FakeURL', self.authentication, coreapi_client_class=self.coreapi_client)
        actual = api.get_job(job_id=identity)
        self.assertDictEqual(actual, expected)

    def test_get_job_raises_api_error(self):
        identity = 999
        payload = {'id': identity}
        self.coreapi_client.handlers['jobs'] = partial(self.__mock_job_handler, payload, 'read')
        api = QuantumInspireAPI('FakeURL', self.authentication, coreapi_client_class=self.coreapi_client)
        self.assertRaises(ApiError, api.get_job, identity)

    def test_get_jobs_from_project_has_correct_in_and_output(self):
        identity = 509
        expected_payload = {'id': identity}
        expected = self.__mock_job_handler(expected_payload, 'read', None, None, ['test', 'read'], expected_payload)
        self.coreapi_client.handlers['projects'] = partial(self.__mock_job_handler, expected_payload, 'jobs')
        api = QuantumInspireAPI('FakeURL', self.authentication, coreapi_client_class=self.coreapi_client)
        actual = api.get_jobs_from_project(project_id=identity)
        self.assertDictEqual(actual, expected)

    def test_get_job_from_project_raises_api_error(self):
        identity = 999
        expected_payload = {'id': identity}
        self.coreapi_client.handlers['projects'] = partial(self.__mock_job_handler, expected_payload, 'jobs')
        api = QuantumInspireAPI('FakeURL', self.authentication, coreapi_client_class=self.coreapi_client)
        self.assertRaises(ApiError, api.get_jobs_from_project, project_id=identity)

    def test_get_jobs_from_asset_has_correct_in_and_output(self):
        identity = 171
        expected_payload = {'id': identity}
        expected = self.__mock_assets_jobs_handler(expected_payload, 'jobs', None, None, ['assets', 'jobs'],
                                                   expected_payload)
        self.coreapi_client.handlers['assets'] = partial(self.__mock_assets_jobs_handler, expected_payload, 'jobs')
        api = QuantumInspireAPI('FakeURL', self.authentication, coreapi_client_class=self.coreapi_client)
        actual = api.get_jobs_from_asset(asset_id=identity)
        self.assertListEqual(actual, expected)

    def test_get_jobs_from_asset_raises_api_error(self):
        identity = 999
        expected_payload = {'id': identity}
        self.coreapi_client.handlers['assets'] = partial(self.__mock_assets_jobs_handler, expected_payload, 'jobs')
        api = QuantumInspireAPI('FakeURL', self.authentication, coreapi_client_class=self.coreapi_client)
        self.assertRaises(ApiError, api.get_jobs_from_asset, asset_id=identity)

    def test_delete_job_has_correct_in_and_output(self):
        identity = 509
        expected_payload = {'id': identity}
        expected = self.__mock_job_handler(expected_payload, 'delete', None, None, ['test', 'delete'], expected_payload)
        self.coreapi_client.handlers['jobs'] = partial(self.__mock_job_handler, expected_payload, 'delete')
        api = QuantumInspireAPI('FakeURL', self.authentication, coreapi_client_class=self.coreapi_client)
        actual = api.delete_job(job_id=identity)
        self.assertEqual(actual, expected)

    def test_delete_job_raises_api_error(self):
        identity = 999
        payload = {'id': identity}
        self.coreapi_client.handlers['jobs'] = partial(self.__mock_job_handler, payload, 'delete')
        api = QuantumInspireAPI('FakeURL', self.authentication, coreapi_client_class=self.coreapi_client)
        self.assertRaises(ApiError, api.delete_job, identity)

    def test_create_job_has_correct_input_and_output_without_fsp(self):
        name = 'TestJob'
        asset = {'url': 'https://api.quantum-inspire.com/assets/1/'}
        project = {'backend_type': 'https://api.quantum-inspire.com/backendtypes/1/'}
        backend_type_sim = {'url': 'https://api.quantum-inspire.com/backendtypes/1/',
                            'name': 'QX Single-node Simulator',
                            'is_hardware_backend': False}
        backend_type_hw = {'url': 'https://api.quantum-inspire.com/backendtypes/1/',
                           'name': 'Spin-2',
                           'is_hardware_backend': True}
        number_of_shots = 1
        expected_payload = {
            'status': 'NEW',
            'name': name,
            'input': asset['url'],
            'backend_type': project['backend_type'],
            'number_of_shots': number_of_shots,
            'full_state_projection': False,
            'user_data': ''
        }
        expected = self.__mock_job_handler(expected_payload, 'create', None, None, ['test', 'create'], expected_payload)
        self.coreapi_client.handlers['jobs'] = partial(self.__mock_job_handler, expected_payload, 'create')
        api = QuantumInspireAPI('FakeURL', self.authentication, coreapi_client_class=self.coreapi_client)
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            stream_handler = logging.StreamHandler(sys.stdout)
            logging.getLogger().addHandler(stream_handler)

            api.show_fsp_warning(enable=False)  # Suppress warning about non fsp
            actual = api._create_job(name, asset, number_of_shots, backend_type_sim, full_state_projection=False)
            self.assertDictEqual(expected, actual)
            # Verify that no warning was printed
            print_string = mock_stdout.getvalue()
            self.assertTrue(len(print_string) == 0)

            api.show_fsp_warning(enable=True)  # Enable warning about non fsp
            actual = api._create_job(name, asset, number_of_shots, backend_type_hw, full_state_projection=True)
            self.assertDictEqual(expected, actual)
            # Verify warning. None on hw backend
            print_string = mock_stdout.getvalue()
            self.assertTrue(len(print_string) == 0)

            api.show_fsp_warning(enable=True)  # Enable warning about non fsp
            actual = api._create_job(name, asset, number_of_shots, backend_type_sim, full_state_projection=False)
            self.assertDictEqual(expected, actual)
            # Verify warning
            print_string = mock_stdout.getvalue()
            self.assertIn('Your experiment can not be optimized and may take longer to execute', print_string)

            logging.getLogger().removeHandler(stream_handler)

    def test_create_job_has_correct_input_and_output_with_fsp(self):
        name = 'TestJob'
        asset = {'url': 'https://api.quantum-inspire.com/assets/1/'}
        project = {'backend_type': 'https://api.quantum-inspire.com/backendtypes/1/'}
        backend_type_sim = {'url': 'https://api.quantum-inspire.com/backendtypes/1/',
                            'name': 'QX Single-node Simulator',
                            'is_hardware_backend': False}
        number_of_shots = 1
        expected_payload = {
            'status': 'NEW',
            'name': name,
            'input': asset['url'],
            'backend_type': project['backend_type'],
            'number_of_shots': number_of_shots,
            'full_state_projection': True,
            'user_data': ''
        }
        expected = self.__mock_job_handler(expected_payload, 'create', None, None, ['test', 'create'], expected_payload)
        self.coreapi_client.handlers['jobs'] = partial(self.__mock_job_handler, expected_payload, 'create')
        api = QuantumInspireAPI('FakeURL', self.authentication, coreapi_client_class=self.coreapi_client)
        actual = api._create_job(name, asset, number_of_shots, backend_type_sim, full_state_projection=True)
        self.assertDictEqual(expected, actual)

    def test_create_job_has_correct_input_and_output_without_fsp_for_hardware_backend(self):
        name = 'TestJob'
        asset = {'url': 'https://api.quantum-inspire.com/assets/1/'}
        project = {'backend_type': 'https://api.quantum-inspire.com/backendtypes/1/'}
        backend_type_hw = {'url': 'https://api.quantum-inspire.com/backendtypes/1/',
                           'name': 'QI Hardware',
                           'is_hardware_backend': True}
        number_of_shots = 1
        expected_payload = {
            'status': 'NEW',
            'name': name,
            'input': asset['url'],
            'backend_type': project['backend_type'],
            'number_of_shots': number_of_shots,
            'full_state_projection': False,
            'user_data': ''
        }
        expected = self.__mock_job_handler(expected_payload, 'create', None, None, ['test', 'create'], expected_payload)
        self.coreapi_client.handlers['jobs'] = partial(self.__mock_job_handler, expected_payload, 'create')
        api = QuantumInspireAPI('FakeURL', self.authentication, coreapi_client_class=self.coreapi_client)
        actual = api._create_job(name, asset, number_of_shots, backend_type_hw, full_state_projection=True)
        self.assertDictEqual(expected, actual)

    def test_create_job_raises_api_error(self):
        name = 'CreateJobFail'
        asset = {'url': 'https://api.quantum-inspire.com/assets/1/'}
        project = {'backend_type': 'https://api.quantum-inspire.com/backendtypes/1/'}
        backend_type_sim = {'url': 'https://api.quantum-inspire.com/backendtypes/1/',
                            'name': 'QX Single-node Simulator',
                            'is_hardware_backend': False}
        number_of_shots = 1
        payload = {
            'status': 'NEW',
            'name': name,
            'input': asset['url'],
            'backend_type': project['backend_type'],
            'number_of_shots': number_of_shots,
            'full_state_projection': True,
            'user_data': ''
        }
        self.coreapi_client.handlers['jobs'] = partial(self.__mock_job_handler, payload, 'create')
        api = QuantumInspireAPI('FakeURL', self.authentication, coreapi_client_class=self.coreapi_client)
        self.assertRaises(ApiError, api._create_job, name, asset, number_of_shots, backend_type_sim,
                          full_state_projection=True)

    def __mock_list_results_handler(self, mock_api, document, keys, params=None, validate=None,
                                    overrides=None, action=None, encoding=None, transform=None):
        self.assertEqual(keys[1], 'list')
        return [OrderedDict([('id', 502),
                             ('url', 'https,//api.quantum-inspire.com/results/502/'),
                             ('job', 'https,//api.quantum-inspire.com/jobs/10/'),
                             ('created_at', '1900-01-01T01:00:00:00000Z'),
                             ('number_of_qubits', 2),
                             ('seconds', 0.0),
                             ('raw_text', ''),
                             ('raw_data_url', 'https,//api.quantum-inspire.com/results/502/raw-data/f2b6/'),
                             ('histogram', {'3', 0.5068359375, '0', 0.4931640625}),
                             ('histogram_url', 'https,//api.quantum-inspire.com/results/502/histogram/f2b6/'),
                             ('measurement_mask', 0),
                             ('quantum_states_url',
                              'https,//api.quantum-inspire.com/results/502/quantum-states/f2b6d/'),
                             ('measurement_register_url', 'https,//api.quantum-inspire.com/results/502/f2b6d/')]),
                OrderedDict([('id', 485),
                             ('url', 'https,//api.quantum-inspire.com/results/485/'),
                             ('job', 'https,//api.quantum-inspire.com/jobs/20/'),
                             ('created_at', '1900-01-01T01:00:00:00000Z'),
                             ('number_of_qubits', 2),
                             ('seconds', 0.0),
                             ('raw_text', ''),
                             ('raw_data_url', 'https,//api.quantum-inspire.com/results/485/raw-data/162c/'),
                             ('histogram', {'0', 0.5029296875, '3', 0.4970703125}),
                             ('histogram_url', 'https,//api.quantum-inspire.com/results/485/histogram/162c/'),
                             ('measurement_mask', 0),
                             ('quantum_states_url', 'https,//api.quantum-inspire.com/results/485/quantum-states/162c/'),
                             ('measurement_register_url', 'https,//api.quantum-inspire.com/results/485/162c/')])]

    def __mock_result_handler(self, input_params, input_key, mock_api, document, keys, params=None,
                              validate=None, overrides=None, action=None, encoding=None, transform=None):
        self.assertEqual(params['id'], input_params['id'])
        self.assertTrue(keys[1] == input_key or keys[2] == input_key)
        if input_key == 'read':
            if params['id'] != 485:
                raise ErrorMessage('Not found')
        if keys[1] == 'read':
            return OrderedDict([('id', 485),
                                ('url', 'https,//api.quantum-inspire.com/results/485/'),
                                ('job', 'https,//api.quantum-inspire.com/jobs/20/'),
                                ('created_at', '1900-01-01T01:00:00:00000Z'),
                                ('number_of_qubits', 2),
                                ('seconds', 0.0),
                                ('raw_text', ''),
                                ('raw_data_url', 'https,//api.quantum-inspire.com/results/485/raw-data/162c/'),
                                ('histogram', {'0', 0.5029296875, '3', 0.4970703125}),
                                ('histogram_url', 'https,//api.quantum-inspire.com/results/485/histogram/162c/'),
                                ('measurement_mask', 0),
                                ('quantum_states_url',
                                 'https,//api.quantum-inspire.com/results/485/quantum-states/qstates/'),
                                ('measurement_register_url', 'https,//api.quantum-inspire.com/results/485/mreg/')])
        elif keys[1] == 'raw-data':
            if params['token'] != '162c':
                raise ErrorMessage('Not found')
            return [0, 3, 3, 0]
        elif keys[1] == 'quantum-states':
            if params['token'] != 'qstates':
                raise ErrorMessage('Not found')
            return [1, 2, 3, 4]
        else:
            self.assertTrue(keys[1] == 'measurement-register')
            if params['token'] != 'mreg':
                raise ErrorMessage('Not found')
            return [4, 3, 2, 1]

    def __mock_list_result_from_job_handler(self, input_params, input_key, mock_api, document, keys, params=None,
                                            validate=None, overrides=None, action=None, encoding=None, transform=None):
        self.assertEqual(params['id'], input_params['id'])
        self.assertTrue(keys[2] == input_key)
        if input_key == 'list':
            if params['id'] != 509:
                raise ErrorMessage('Not found')
        return OrderedDict([('id', 485),
                            ('url', 'https,//api.quantum-inspire.com/results/485/'),
                            ('job', 'https,//api.quantum-inspire.com/jobs/20/'),
                            ('created_at', '1900-01-01T01:00:00:00000Z'),
                            ('number_of_qubits', 2),
                            ('seconds', 0.0),
                            ('raw_text', ''),
                            ('raw_data_url', 'https,//api.quantum-inspire.com/results/485/raw-data/162c/'),
                            ('histogram', {'0', 0.5029296875, '3', 0.4970703125}),
                            ('histogram_url', 'https,//api.quantum-inspire.com/results/485/histogram/162c/'),
                            ('measurement_mask', 0),
                            ('quantum_states_url', 'https,//api.quantum-inspire.com/results/485/quantum-states/162c/'),
                            ('measurement_register_url', 'https,//api.quantum-inspire.com/results/485/162c/')])

    def __mock_errors_in_result_handler(self, input_params, input_key, mock_api, document, keys, params=None,
                                        validate=None, overrides=None, action=None, encoding=None, transform=None):
        self.assertEqual(params['id'], input_params['id'])
        self.assertTrue(keys[1] == input_key or keys[2] == input_key)
        if keys[1] == 'read':
            if params['id'] == 485:
                return OrderedDict([('id', 485),
                                    ('url', 'https,//api.quantum-inspire.com/results/485/'),
                                    ('job', 'https,//api.quantum-inspire.com/jobs/20/'),
                                    ('created_at', '1900-01-01T01:00:00:00000Z'),
                                    ('number_of_qubits', 2),
                                    ('seconds', 0.0),
                                    ('raw_text', ''),
                                    ('raw_data_url', ''),
                                    ('histogram', {'0', 0.5029296875, '3', 0.4970703125}),
                                    ('histogram_url', 'https,//api.quantum-inspire.com/results/485/histogram/162c/'),
                                    ('measurement_mask', 0),
                                    ('quantum_states_url', ''),
                                    ('measurement_register_url', '')])
            else:
                self.assertEqual(params['id'], 486)
                return OrderedDict([('id', 486),
                                    ('url', 'https,//api.quantum-inspire.com/results/485/'),
                                    ('job', 'https,//api.quantum-inspire.com/jobs/20/'),
                                    ('created_at', '1900-01-01T01:00:00:00000Z'),
                                    ('number_of_qubits', 2),
                                    ('seconds', 0.0),
                                    ('raw_text', ''),
                                    ('raw_data_url', 'https,//api.quantum-inspire.com/results/485/raw-data/999/'),
                                    ('histogram', {'0', 0.5029296875, '3', 0.4970703125}),
                                    ('histogram_url', 'https,//api.quantum-inspire.com/results/485/histogram/162c/'),
                                    ('measurement_mask', 0),
                                    ('quantum_states_url',
                                     'https,//api.quantum-inspire.com/results/485/quantum-states/999/'),
                                    ('measurement_register_url', 'https,//api.quantum-inspire.com/results/485/999/')])
        elif keys[1] == 'raw-data':
            if params['token'] != '162c':
                raise ErrorMessage('Not found')
            return [0, 3, 3, 0]
        elif keys[1] == 'quantum-states':
            if params['token'] != 'qstates':
                raise ErrorMessage('Not found')
            return [1, 2, 3, 4]
        else:
            self.assertTrue(keys[1] == 'measurement-register')
            if params['token'] != 'mreg':
                raise ErrorMessage('Not found')
            return [4, 3, 2, 1]

    def test_list_results_has_correct_output(self):
        self.coreapi_client.handlers['results'] = self.__mock_list_results_handler
        api = QuantumInspireAPI('FakeURL', self.authentication, coreapi_client_class=self.coreapi_client)
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            api.list_results()
            print_string = mock_stdout.getvalue()
            self.assertIn('Result id:', print_string)

    def test_get_results_has_correct_input_and_output(self):
        expected = self.__mock_list_results_handler(None, None, ['test', 'list'])
        self.coreapi_client.handlers['results'] = self.__mock_list_results_handler
        api = QuantumInspireAPI('FakeURL', self.authentication, coreapi_client_class=self.coreapi_client)
        actual = api.get_results()
        self.assertListEqual(actual, expected)

    def test_get_result_has_correct_input_and_output(self):
        identity = 485
        expected_payload = {'id': identity}
        expected = self.__mock_result_handler(expected_payload, 'read', None, None, ['test', 'read'], expected_payload)
        self.coreapi_client.handlers['results'] = partial(self.__mock_result_handler, expected_payload, 'read')
        api = QuantumInspireAPI('FakeURL', self.authentication, coreapi_client_class=self.coreapi_client)
        actual = api.get_result(result_id=identity)
        self.assertDictEqual(actual, expected)

    def test_get_result_raises_api_error(self):
        identity = 999
        expected_payload = {'id': identity}
        self.coreapi_client.handlers['results'] = partial(self.__mock_result_handler, expected_payload, 'read')
        api = QuantumInspireAPI('FakeURL', self.authentication, coreapi_client_class=self.coreapi_client)
        self.assertRaises(ApiError, api.get_result, result_id=identity)

    def test_get_result_from_job_has_correct_input_and_output(self):
        identity = 509
        expected_payload = {'id': identity}
        expected = self.__mock_list_result_from_job_handler(expected_payload, 'list', None, None,
                                                            ['jobs', 'result', 'list'], expected_payload)
        self.coreapi_client.handlers['jobs'] = partial(self.__mock_list_result_from_job_handler, expected_payload,
                                                       'list')
        api = QuantumInspireAPI('FakeURL', self.authentication, coreapi_client_class=self.coreapi_client)
        actual = api.get_result_from_job(identity)
        self.assertDictEqual(actual, expected)

    def test_get_result_from_job_raises_api_error(self):
        identity = 999
        expected_payload = {'id': identity}
        self.coreapi_client.handlers['jobs'] = partial(self.__mock_list_result_from_job_handler, expected_payload,
                                                       'list')
        api = QuantumInspireAPI('FakeURL', self.authentication, coreapi_client_class=self.coreapi_client)
        self.assertRaises(ApiError, api.get_result_from_job, job_id=identity)

    def test_get_raw_data_from_result_has_correct_input_and_output(self):
        identity = 485
        expected_payload = {'id': identity, 'token': '162c'}
        expected_raw_data = self.__mock_result_handler(expected_payload, 'read', None, None,
                                                       ['test', 'raw-data', 'read'], expected_payload)
        self.coreapi_client.handlers['results'] = partial(self.__mock_result_handler, expected_payload, 'read')
        api = QuantumInspireAPI('FakeURL', self.authentication, coreapi_client_class=self.coreapi_client)
        actual = api.get_raw_data_from_result(result_id=identity)
        self.assertListEqual(actual, expected_raw_data)

    def test_get_raw_data_unknown_from_result_raises_api_error(self):
        result_identity = 485
        expected_payload = {'id': result_identity}
        self.coreapi_client.handlers['results'] = partial(self.__mock_errors_in_result_handler,
                                                          expected_payload, 'read')
        api = QuantumInspireAPI('FakeURL', self.authentication, coreapi_client_class=self.coreapi_client)
        self.assertRaisesRegex(ApiError, 'Invalid raw data url for result with id 485!', api.get_raw_data_from_result,
                               result_id=result_identity)

    def test_get_raw_data_invalid_from_result_raises_api_error(self):
        result_identity = 486
        expected_payload = {'id': result_identity, 'token': '162c'}
        self.coreapi_client.handlers['results'] = partial(self.__mock_errors_in_result_handler,
                                                          expected_payload, 'read')
        api = QuantumInspireAPI('FakeURL', self.authentication, coreapi_client_class=self.coreapi_client)
        self.assertRaisesRegex(ApiError, 'Raw data for result with id 486 does not exist!',
                               api.get_raw_data_from_result, result_id=result_identity)

    def test_get_quantum_states_from_result_has_correct_input_and_output(self):
        identity = 485
        expected_payload = {'id': identity, 'token': 'qstates'}
        expected_quantum_states = self.__mock_result_handler(expected_payload, 'read', None, None,
                                                             ['test', 'quantum-states', 'read'], expected_payload)
        self.coreapi_client.handlers['results'] = partial(self.__mock_result_handler, expected_payload, 'read')
        api = QuantumInspireAPI('FakeURL', self.authentication, coreapi_client_class=self.coreapi_client)
        actual = api.get_quantum_states_from_result(result_id=identity)
        self.assertListEqual(actual, expected_quantum_states)

    def test_get_quantum_states_unknown_from_result_raises_api_error(self):
        result_identity = 485
        expected_payload = {'id': result_identity, 'token': 'qstates'}
        self.coreapi_client.handlers['results'] = partial(self.__mock_errors_in_result_handler,
                                                          expected_payload, 'read')
        api = QuantumInspireAPI('FakeURL', self.authentication, coreapi_client_class=self.coreapi_client)
        self.assertRaisesRegex(ApiError, 'Invalid quantum states url for result with id 485!',
                               api.get_quantum_states_from_result, result_id=result_identity)

    def test_get_quantum_states_invalid_from_result_raises_api_error(self):
        result_identity = 486
        expected_payload = {'id': result_identity, 'token': 'qstates'}
        self.coreapi_client.handlers['results'] = partial(self.__mock_errors_in_result_handler,
                                                          expected_payload, 'read')
        api = QuantumInspireAPI('FakeURL', self.authentication, coreapi_client_class=self.coreapi_client)
        self.assertRaisesRegex(ApiError, 'Quantum states for result with id 486 does not exist!',
                               api.get_quantum_states_from_result, result_id=result_identity)

    def test_get_measurement_register_from_result_has_correct_input_and_output(self):
        identity = 485
        expected_payload = {'id': identity, 'token': 'mreg'}
        expected_measurement_register = self.__mock_result_handler(expected_payload, 'read', None, None,
                                                                   ['test', 'measurement-register', 'read'],
                                                                   expected_payload)
        self.coreapi_client.handlers['results'] = partial(self.__mock_result_handler, expected_payload, 'read')
        api = QuantumInspireAPI('FakeURL', self.authentication, coreapi_client_class=self.coreapi_client)
        actual = api.get_measurement_register_from_result(result_id=identity)
        self.assertListEqual(actual, expected_measurement_register)

    def test_get_measurement_register_unknown_from_result_raises_api_error(self):
        result_identity = 485
        expected_payload = {'id': result_identity, 'token': 'qstates'}
        self.coreapi_client.handlers['results'] = partial(self.__mock_errors_in_result_handler,
                                                          expected_payload, 'read')
        api = QuantumInspireAPI('FakeURL', self.authentication, coreapi_client_class=self.coreapi_client)
        self.assertRaisesRegex(ApiError, 'Invalid measurement register url for result with id 485!',
                               api.get_measurement_register_from_result, result_id=result_identity)

    def test_get_measurement_register_invalid_from_result_raises_api_error(self):
        result_identity = 486
        expected_payload = {'id': result_identity, 'token': 'qstates'}
        self.coreapi_client.handlers['results'] = partial(self.__mock_errors_in_result_handler,
                                                          expected_payload, 'read')
        api = QuantumInspireAPI('FakeURL', self.authentication, coreapi_client_class=self.coreapi_client)
        self.assertRaisesRegex(ApiError, 'Measurement register for result with id 486 does not exist!',
                               api.get_measurement_register_from_result, result_id=result_identity)

    def __mock_list_assets_handler(self, mock_api, document, keys, params=None, validate=None,
                                   overrides=None, action=None, encoding=None, transform=None):
        self.assertTrue(keys[1] == 'list' or keys[2] == 'list')
        if keys[0] == 'projects':
            if params['id'] != 11:
                raise ErrorMessage('Not found')
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
        if input_key == 'read' or input_key == 'delete':
            if params['id'] != 171:
                raise ErrorMessage('Not found')
        return OrderedDict([('url', 'https,//api.quantum-inspire.com/assets/171/'),
                            ('id', 171),
                            ('name', 'Grover algorithm - 2018-07-18 13,32'),
                            ('contentType', 'text/plain'),
                            ('content', 'version 1.0\n\nqubits 9\n\n\n# Grover search algorithm\n  display'),
                            ('project', 'https,//api.quantum-inspire.com/projects/11/'),
                            ('project_id', 11)])

    def __mock_asset_from_job_handler(self, input_params, input_key, mock_api, document, keys, params=None,
                                      validate=None, overrides=None, action=None, encoding=None, transform=None,
                                      status='COMPLETE'):
        self.assertDictEqual(params, input_params)
        self.assertEqual(keys[1], input_key)
        if params['id'] == 509:
            return OrderedDict([('url', 'https,//api.quantum-inspire.com/jobs/509/'),
                                ('name', 'qi-sdk-job-7e37c8fa-a76b-11e8-b5a0-a44cc848f1f2'),
                                ('id', 509),
                                ('status', status),
                                ('input', 'https,//api.quantum-inspire.com/assets/999/'),
                                ('backend', 'https,//api.quantum-inspire.com/backends/1/'),
                                ('backend_type', 'https,//api.quantum-inspire.com/backendtypes/1/'),
                                ('results', 'https,//api.quantum-inspire.com/jobs/509/result/'),
                                ('queued_at', '2018-08-24T07:01:21:257557Z'),
                                ('number_of_shots', 1024),
                                ('user_data', '')])
        elif params['id'] == 510:
            return OrderedDict([('url', 'https,//api.quantum-inspire.com/jobs/509/'),
                                ('name', 'qi-sdk-job-7e37c8fa-a76b-11e8-b5a0-a44cc848f1f2'),
                                ('id', 510),
                                ('status', status),
                                ('input', 'https,//api.quantum-inspire.com/assets/nine_nine_nine/'),
                                ('backend', 'https,//api.quantum-inspire.com/backends/1/'),
                                ('backend_type', 'https,//api.quantum-inspire.com/backendtypes/1/'),
                                ('results', 'https,//api.quantum-inspire.com/jobs/509/result/'),
                                ('queued_at', '2018-08-24T07:01:21:257557Z'),
                                ('number_of_shots', 1024),
                                ('user_data', '')])

    def test_list_assets_has_correct_output(self):
        self.coreapi_client.handlers['assets'] = self.__mock_list_assets_handler
        api = QuantumInspireAPI('FakeURL', self.authentication, coreapi_client_class=self.coreapi_client)
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            api.list_assets()
            print_string = mock_stdout.getvalue()
            self.assertIn('Asset name:', print_string)

    def test_get_assets_has_correct_input_and_output(self):
        expected = self.__mock_list_assets_handler(None, None, ['test', 'list'])
        self.coreapi_client.handlers['assets'] = self.__mock_list_assets_handler
        api = QuantumInspireAPI('FakeURL', self.authentication, coreapi_client_class=self.coreapi_client)
        actual = api.get_assets()
        self.assertListEqual(actual, expected)

    def test_get_asset_has_correct_input_and_output(self):
        identity = 171
        expected_payload = {'id': identity}
        expected = self.__mock_asset_handler(expected_payload, 'read', None, None, ['test', 'read'], expected_payload)
        self.coreapi_client.handlers['assets'] = partial(self.__mock_asset_handler, expected_payload, 'read')
        api = QuantumInspireAPI('FakeURL', self.authentication, coreapi_client_class=self.coreapi_client)
        actual = api.get_asset(asset_id=identity)
        self.assertDictEqual(actual, expected)

    def test_get_asset_raises_api_error(self):
        identity = 999
        expected_payload = {'id': identity}
        self.coreapi_client.handlers['assets'] = partial(self.__mock_asset_handler, expected_payload, 'read')
        api = QuantumInspireAPI('FakeURL', self.authentication, coreapi_client_class=self.coreapi_client)
        self.assertRaises(ApiError, api.get_asset, asset_id=identity)

    def test_get_assets_from_project_has_correct_input_and_output(self):
        identity = 11
        expected_payload = {'id': identity}
        expected = self.__mock_list_assets_handler(None, None, ['projects', 'assets', 'list'], expected_payload)
        self.coreapi_client.handlers['projects'] = self.__mock_list_assets_handler
        api = QuantumInspireAPI('FakeURL', self.authentication, coreapi_client_class=self.coreapi_client)
        actual = api.get_assets_from_project(identity)
        self.assertListEqual(actual, expected)

    def test_get_assets_from_project_raises_api_error(self):
        identity = 11
        expected_payload = {'id': identity}
        self.coreapi_client.handlers['projects'] = self.__mock_list_assets_handler
        api = QuantumInspireAPI('FakeURL', self.authentication, coreapi_client_class=self.coreapi_client)
        other_identity = 999
        self.assertRaisesRegex(ApiError, 'Project with id 999 does not exist!', api.get_assets_from_project,
                               project_id=other_identity)

    def test_get_assets_from_job_has_correct_input_and_output(self):
        identity = 171
        expected_payload = {'id': identity}
        expected = self.__mock_asset_handler(expected_payload, 'read', None, None, ['assets', 'read'], expected_payload)
        self.coreapi_client.handlers['assets'] = partial(self.__mock_asset_handler, expected_payload, 'read')
        job_identity = 509
        expected_payload_job = {'id': job_identity}
        self.coreapi_client.handlers['jobs'] = partial(self.__mock_job_handler, expected_payload_job, 'read')
        api = QuantumInspireAPI('FakeURL', self.authentication, coreapi_client_class=self.coreapi_client)
        actual = api.get_asset_from_job(job_identity)
        self.assertDictEqual(actual, expected)

    def test_get_asset_unknown_from_job_raises_api_error(self):
        identity = 999
        expected_payload = {'id': identity}
        self.coreapi_client.handlers['assets'] = partial(self.__mock_asset_handler, expected_payload, 'read')
        job_identity = 509
        expected_payload_job = {'id': job_identity}
        self.coreapi_client.handlers['jobs'] = partial(self.__mock_asset_from_job_handler, expected_payload_job, 'read')
        api = QuantumInspireAPI('FakeURL', self.authentication, coreapi_client_class=self.coreapi_client)
        self.assertRaisesRegex(ApiError, 'Asset with id 999 does not exist!', api.get_asset_from_job,
                               job_id=job_identity)

    def test_get_asset_invalid_from_job_raises_api_error(self):
        identity = 999
        expected_payload = {'id': identity}
        self.coreapi_client.handlers['assets'] = partial(self.__mock_asset_handler, expected_payload, 'read')
        job_identity = 510
        expected_payload_job = {'id': job_identity}
        self.coreapi_client.handlers['jobs'] = partial(self.__mock_asset_from_job_handler, expected_payload_job, 'read')
        api = QuantumInspireAPI('FakeURL', self.authentication, coreapi_client_class=self.coreapi_client)
        self.assertRaisesRegex(ApiError, 'Invalid input url for job with id 510!', api.get_asset_from_job,
                               job_id=job_identity)

    def test_create_asset_has_correct_input_and_output(self):
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

    def test_wait_for_completed_job_returns_true(self):
        job_id = 509
        collect_max_tries = 3
        expected_payload = {'id': job_id}
        self.coreapi_client.handlers['jobs'] = partial(self.__mock_job_handler, expected_payload, 'read',
                                                       status='COMPLETE')
        api = QuantumInspireAPI('FakeURL', self.authentication, coreapi_client_class=self.coreapi_client)
        quantum_inspire_job = QuantumInspireJob(api, job_id)
        is_completed, message = api._wait_for_completed_job(quantum_inspire_job, collect_max_tries, sec_retry_delay=0.0)
        self.assertTrue(is_completed)
        self.assertEqual(message, 'Job completed.')

    def test_wait_for_completed_job_returns_false(self):
        job_id = 509
        collect_max_tries = 3
        expected_payload = {'id': job_id}
        self.coreapi_client.handlers['jobs'] = partial(self.__mock_job_handler, expected_payload, 'read',
                                                       status='RUNNING')
        api = QuantumInspireAPI('FakeURL', self.authentication, coreapi_client_class=self.coreapi_client)
        quantum_inspire_job = QuantumInspireJob(api, job_id)
        is_completed, message = api._wait_for_completed_job(quantum_inspire_job, collect_max_tries, sec_retry_delay=0.0)
        self.assertFalse(is_completed)
        self.assertEqual(message, 'Failed getting result: timeout reached.')

    def test_wait_for_cancelled_job_returns_false(self):
        job_id = 509
        expected_payload = {'id': job_id}
        self.coreapi_client.handlers['jobs'] = partial(self.__mock_job_handler, expected_payload, 'read',
                                                       status='CANCELLED')
        api = QuantumInspireAPI('FakeURL', self.authentication, coreapi_client_class=self.coreapi_client)
        quantum_inspire_job = QuantumInspireJob(api, job_id)
        is_completed, message = api._wait_for_completed_job(quantum_inspire_job)
        self.assertFalse(is_completed)
        self.assertEqual(message, 'Failed getting result: job cancelled.')

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
                                 ('default_number_of_shots', 4096),
                                 ('description', 'Single-node running on a 4GB Hetzner VPS.'),
                                 ('topology', '{"edges": []}'),
                                 ('is_allowed', True)]),
                    OrderedDict([('url', 'https://api.quantum-inspire.com/backendtypes/2/'),
                                 ('name', 'QX Single-node Simulator'),
                                 ('is_hardware_backend', False),
                                 ('required_permission', 'can_simulate_single_node_qutech'),
                                 ('number_of_qubits', 26),
                                 ('default_number_of_shots', 2048),
                                 ('description', 'Single-node running on a 4GB Hetzner VPS.'),
                                 ('topology', '{"edges": []}'),
                                 ('is_allowed', True)])]
        else:
            # return specified id
            return OrderedDict([('url', 'https://api.quantum-inspire.com/backendtypes/%d/' % backend_type_id),
                                ('name', 'QX Single-node Simulator'),
                                ('is_hardware_backend', False),
                                ('required_permission', 'can_simulate_single_node_qutech'),
                                ('number_of_qubits', 26),
                                ('default_number_of_shots', 4321),
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
            call_mock(keys[1], params=params)
        return OrderedDict([('url', 'https//api.quantum-inspire.com/assets/1/'),
                            ('id', 171),
                            ('name', 'Grover algorithm - 2018-07-18 13,32'),
                            ('contentType', 'text/plain'),
                            ('content', 'version 1.0\n\nqubits 9\n\n\n# Grover search algorithm\n  display'),
                            ('project', 'https//api.quantum-inspire.com/projects/1/'),
                            ('project_id', 1),
                            ('input', {'project_id': 1})])

    def __fake_job_handler(self, mock_api, document, keys, params=None, validate=None,
                           overrides=None, action=None, encoding=None, transform=None, call_mock=None):
        if call_mock:
            call_mock(keys[1], params)
        return OrderedDict([('url', 'https//api.quantum-inspire.com/jobs/509/'),
                            ('name', 'qi-sdk-job-7e37c8fa-a76b-11e8-b5a0-a44cc848f1f2'),
                            ('id', 509),
                            ('status', 'COMPLETE'),
                            ('full_state_projection', True),
                            ('input', 'https//api.quantum-inspire.com/assets/171/'),
                            ('backend', 'https//api.quantum-inspire.com/backends/1/'),
                            ('backend_type', 'https//api.quantum-inspire.com/backendtypes/1/'),
                            ('results', 'mocked_job'),
                            ('queued_at', '2018-08-24T07:01:21:257557Z'),
                            ('number_of_shots', 4096)])

    def __fake_no_results_job_handler(self, mock_api, document, keys, params=None, validate=None,
                                      overrides=None, action=None, encoding=None, transform=None, call_mock=None):
        if call_mock:
            call_mock(keys[1])
        return OrderedDict([('url', 'https//api.quantum-inspire.com/jobs/509/'),
                            ('name', 'qi-sdk-job-7e37c8fa-a76b-11e8-b5a0-a44cc848f1f2'),
                            ('id', 509),
                            ('status', 'CANCELLED'),
                            ('input', 'https//api.quantum-inspire.com/assets/607/'),
                            ('backend', 'https//api.quantum-inspire.com/backends/1/'),
                            ('backend_type', 'https//api.quantum-inspire.com/backendtypes/1/'),
                            ('results', ''),
                            ('queued_at', '2018-08-24T07:01:21:257557Z'),
                            ('number_of_shots', 1)])

    def __error_job_handler(self, mock_api, document, keys, params=None, validate=None,
                            overrides=None, action=None, encoding=None, transform=None, call_mock=None):
        if call_mock:
            call_mock(keys[1], params)
        raise TypeError('Type is not correct')

    def __mocks_for_api_execution(self, fake_no_results=False):
        if fake_no_results:
            expected_job_result = self.__fake_no_results_job_handler({}, 'read', None, None, ['test', 'read'], {})
        else:
            expected_job_result = self.__fake_job_handler({}, 'read', None, None, ['test', 'read'], {})
        self.coreapi_client.getters['mocked_job'] = expected_job_result
        expected_asset = self.__fake_asset_handler({}, 'create', None, None, ['test', 'create'], {})
        self.coreapi_client.getters['171'] = expected_asset

        job_mock = Mock()
        if fake_no_results:
            self.coreapi_client.handlers['jobs'] = partial(self.__fake_no_results_job_handler, call_mock=job_mock)
        else:
            self.coreapi_client.handlers['jobs'] = partial(self.__fake_job_handler, call_mock=job_mock)
        asset_mock = Mock()
        self.coreapi_client.handlers['assets'] = partial(self.__fake_asset_handler, call_mock=asset_mock)
        backend_mock = Mock()
        self.coreapi_client.handlers['backendtypes'] = partial(self.__fake_backendtype_handler, call_mock=backend_mock)
        project_mock = Mock()
        self.coreapi_client.handlers['projects'] = partial(self.__fake_project_handler_params, call_mock=project_mock)

        return expected_job_result, job_mock, asset_mock, backend_mock, project_mock

    def test_execute_qasm_cancelled_job(self):
        mocks = self.__mocks_for_api_execution(fake_no_results=True)
        api = QuantumInspireAPI('FakeURL', self.authentication, coreapi_client_class=self.coreapi_client)
        qasm = 'version 1.0...'
        number_of_shots = 1024
        results = api.execute_qasm(qasm, number_of_shots=number_of_shots, backend_type=1)
        self.assertEqual(results['histogram'], {})
        self.assertEqual(results['raw_text'], 'Failed getting result: job cancelled.')

    def test_execute_qasm_different_backend(self):
        mocks = self.__mocks_for_api_execution()
        project_mock = mocks[4]

        api = QuantumInspireAPI('FakeURL', self.authentication, coreapi_client_class=self.coreapi_client)
        backend_type = api.get_backend_type(identifier=2)
        qasm = 'version 1.0...'
        number_of_shots = 1024
        _ = api.execute_qasm(qasm, number_of_shots=number_of_shots, backend_type=2, collect_tries=1)
        project_call = tuple(project_mock.call_args_list[0])
        self.assertEqual(project_call[0][0], 'create')
        self.assertEqual(project_call[1]['params']['backend_type'], r'https://api.quantum-inspire.com/backendtypes/2/')

        project_mock = Mock()
        self.coreapi_client.handlers['projects'] = partial(self.__fake_project_handler_params, call_mock=project_mock)
        _ = api.execute_qasm(qasm, number_of_shots=number_of_shots, collect_tries=1)
        project_call = tuple(project_mock.call_args_list[0])
        self.assertEqual(project_call[1]['params']['backend_type'], r'https://api.quantum-inspire.com/backendtypes/1/')

        project_mock = Mock()
        self.coreapi_client.handlers['projects'] = partial(self.__fake_project_handler_params, call_mock=project_mock)
        _ = api.execute_qasm(qasm, number_of_shots=number_of_shots, backend_type='QX Single-node Simulator',
                             collect_tries=1)
        project_call = tuple(project_mock.call_args_list[0])
        self.assertEqual(project_call[1]['params']['backend_type'], r'https://api.quantum-inspire.com/backendtypes/1/')

    def __test_execute_qasm_fsp_propagates_correctly_to_job(self, full_state_projection):
        mocks = self.__mocks_for_api_execution()
        job_mock = mocks[1]

        qasm = 'version 1.0...'
        api = QuantumInspireAPI('FakeURL', self.authentication, coreapi_client_class=self.coreapi_client)
        _ = api.execute_qasm(qasm, collect_tries=1, full_state_projection=full_state_projection)

        job_mock.assert_called_with('read', {'id': 509})
        job_call_items = job_mock.call_args_list[0][0][1]
        self.assertEqual('NEW', job_call_items['status'])
        self.assertEqual(4321, job_call_items['number_of_shots'])
        self.assertEqual(full_state_projection, job_call_items['full_state_projection'])

    def test_execute_qasm_with_fsp_creates_job_with_fsp(self):
        self.__test_execute_qasm_fsp_propagates_correctly_to_job(True)

    def test_execute_qasm_without_fsp_creates_job_without_fsp(self):
        self.__test_execute_qasm_fsp_propagates_correctly_to_job(False)

    def test_execute_qasm_project_is_deleted(self):
        expected_job_result, job_mock, asset_mock, backend_mock, project_mock = self.__mocks_for_api_execution()

        api = QuantumInspireAPI('FakeURL', self.authentication, coreapi_client_class=self.coreapi_client)
        self.assertIsNone(api.project_name)

        qasm = 'version 1.0...'
        default_number_of_shots = 4321
        actual_job_result = api.execute_qasm(qasm, collect_tries=1)
        self.assertEqual(expected_job_result, actual_job_result)

        job_mock.assert_called_with('read', {'id': 509})
        job_call_items = job_mock.call_args_list[0][0][1]
        self.assertEqual('NEW', job_call_items['status'])
        self.assertEqual(default_number_of_shots, job_call_items['number_of_shots'])
        self.assertFalse(job_call_items['full_state_projection'])

        asset_mock.assert_any_call('create', params=mock.ANY)
        backend_mock.assert_called_with('default')
        project_mock.assert_has_calls([call('create', params=mock.ANY), call('delete', params={'id': 1})])

    @patch('quantuminspire.api.QuantumInspireAPI.get_projects')
    def test_execute_qasm_project_not_deleted_with_number_of_shots(self, get_projects_mock):
        expected_job_result, job_mock, asset_mock, backend_mock, project_mock = self.__mocks_for_api_execution()

        get_projects_mock.return_value = {}
        project_name = 'Grover algorithm - 1900-01-01 10:00'
        api = QuantumInspireAPI('FakeURL', self.authentication, project_name=project_name,
                                coreapi_client_class=self.coreapi_client)
        self.assertEqual(api.project_name, project_name)

        qasm = 'version 1.0...'
        actual_job_result = api.execute_qasm(qasm, number_of_shots=4096, collect_tries=1, full_state_projection=True)
        self.assertEqual(expected_job_result, actual_job_result)

        job_mock.assert_any_call('read', {'id': 509})
        job_mock.assert_any_call('result', {'id': 509})
        job_call_items = job_mock.call_args_list[0][0][1]
        self.assertEqual('NEW', job_call_items['status'])
        self.assertEqual(4096, job_call_items['number_of_shots'])
        self.assertTrue(job_call_items['full_state_projection'])

        asset_mock.assert_called_with('create', params=mock.ANY)
        backend_mock.assert_called_with('default')

        project_mock.assert_called_with('create', params=mock.ANY)
        self.assertTrue(call('delete') not in project_mock.call_args_list)

    @patch('quantuminspire.api.QuantumInspireAPI.get_projects')
    def test_execute_qasm_project_with_default_number_of_shots(self, get_projects_mock):
        expected_job_result, job_mock, asset_mock, backend_mock, project_mock = self.__mocks_for_api_execution()

        get_projects_mock.return_value = {}
        project_name = 'Grover algorithm - 1900-01-01 10:00'
        api = QuantumInspireAPI('FakeURL', self.authentication, project_name=project_name,
                                coreapi_client_class=self.coreapi_client)
        self.assertEqual(api.project_name, project_name)

        qasm = 'version 1.0...'
        actual_job_result = api.execute_qasm(qasm, number_of_shots=None, collect_tries=1, full_state_projection=True)
        self.assertEqual(expected_job_result, actual_job_result)

        job_call_items = job_mock.call_args_list[0][0][1]
        self.assertEqual(4321, job_call_items['number_of_shots'])
        project_call_items = project_mock.call_args_list[0][1]['params']
        self.assertEqual(4321, project_call_items['default_number_of_shots'])

    def test_execute_qasm_qasm_stripped(self):
        _, _, asset_mock, _, _ = self.__mocks_for_api_execution()

        api = QuantumInspireAPI('FakeURL', self.authentication, coreapi_client_class=self.coreapi_client)
        self.assertIsNone(api.project_name)

        qasm = '  \n version 1.0  \n	 	qubits 10\n \n	h q[0] \n 	 measure_z q[0]  \n       \n         \n'
        api.execute_qasm(qasm, collect_tries=1)

        asset_call_items = asset_mock.call_args_list[0][1]
        self.assertEqual('version 1.0\nqubits 10\n\nh q[0]\nmeasure_z q[0]\n\n\n',
                         asset_call_items['params']['content'])

    def test_execute_qasm_api_error(self):
        _ = self.__mocks_for_api_execution()
        job_mock = Mock()
        self.coreapi_client.handlers['jobs'] = partial(self.__error_job_handler, call_mock=job_mock)

        api = QuantumInspireAPI('FakeURL', self.authentication, coreapi_client_class=self.coreapi_client)
        self.assertIsNone(api.project_name)

        qasm = 'version 1.0'
        results = api.execute_qasm(qasm)

        self.assertEqual(results['histogram'], {})
        s = results['raw_text']
        self.assertTrue(
            re.match(r'Error raised while executing qasm: Job with name (.*?) not created: Type is not correct', s))
