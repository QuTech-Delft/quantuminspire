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
import os
import json
from unittest import TestCase
from unittest.mock import MagicMock, patch, mock_open

from coreapi.auth import BasicAuthentication
from quantuminspire.credentials import save_token, load_token, get_token_authentication, get_basic_authentication
DEFAULT_QIRC_FILE = os.path.join(os.path.expanduser("~"), '.quantuminspire', 'qirc')


class TestCredentials(TestCase):

    def test_get_token_authentication(self):
        secret_token = 'secret'
        auth = get_token_authentication(secret_token)
        # TokenAuthentication doesn't have __equal__ implemented, so check fields
        self.assertEqual(auth.token, secret_token)
        self.assertEqual(auth.scheme, 'token')

    def test_get_basic_authentication(self):
        email = 'bla@bla.bla'
        secret_password = 'secret'
        auth = get_basic_authentication(email, secret_password)
        auth_expected = BasicAuthentication(email, secret_password)
        self.assertEqual(auth, auth_expected)

    def test_save_and_load_token_default_rc(self):
        os.makedirs = MagicMock()
        json.load = MagicMock()
        expected_token = 'secret'
        json.load.return_value = {'token': expected_token}
        with patch("builtins.open", mock_open()) as mock_file:
            with patch('os.makedirs', os.makedirs):
                save_token(expected_token)
                mock_file.assert_called_with(DEFAULT_QIRC_FILE, 'w')
                handle = mock_file()
                handle.write.assert_any_call('{')
                handle.write.assert_any_call('"token"')
                handle.write.assert_any_call('"'+expected_token+'"')
                handle.write.assert_any_call('{')
                token = load_token()
                self.assertEqual(expected_token, token)

    def test_save_and_load_token_filename(self):
        filename = 'path/to/open/dummyqi.rc'
        os.makedirs = MagicMock()
        json.load = MagicMock()
        expected_token = 'secret'
        json.load.return_value = {'token': expected_token}
        with patch("builtins.open", mock_open()) as mock_file:
            with patch('os.makedirs', os.makedirs):
                save_token(expected_token, filename)
                mock_file.assert_called_with(filename, 'w')
                handle = mock_file()
                handle.write.assert_any_call('{')
                handle.write.assert_any_call('"token"')
                handle.write.assert_any_call('"'+expected_token+'"')
                handle.write.assert_any_call('{')
                token = load_token(filename)
                self.assertEqual(expected_token, token)

    def test_load_token_env(self):
        expected_token = 'secret'
        json.load = MagicMock()
        json.load.return_value = {'faulty_key': expected_token}
        os.getenv = MagicMock()
        os.getenv.return_value = expected_token
        with patch("builtins.open", mock_open()):
            token = load_token()
            self.assertEqual(expected_token, token)
