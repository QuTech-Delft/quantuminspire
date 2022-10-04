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
import os
import json
import sys
from unittest import TestCase, skipUnless
from unittest.mock import MagicMock, patch, mock_open, call

from coreapi.auth import BasicAuthentication
from quantuminspire.credentials import save_account, store_account, delete_account, enable_account, load_account,\
    get_token_authentication, get_basic_authentication, get_authentication
DEFAULT_QIRC_FILE = os.path.join(os.path.expanduser("~"), '.quantuminspire', 'qirc')


class TestCredentials(TestCase):

    def test_get_token_authentication(self):
        secret_token = 'secret'
        auth = get_token_authentication(secret_token)
        # TokenAuthentication doesn't have __equal__ implemented, so check fields
        self.assertEqual(auth.token, secret_token)
        self.assertEqual(auth.scheme, 'token')
        with patch.dict('os.environ', values={'QI_TOKEN': secret_token}):
            auth = get_token_authentication()
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
        with patch.dict('os.environ', values={'QI_TOKEN': ''}):
            expected_token = 'secret'
            json.load.return_value = {'token': expected_token}
            with patch("builtins.open", mock_open()) as mock_file:
                with patch('os.makedirs', os.makedirs):
                    save_account(expected_token)
                    mock_file.assert_called_with(DEFAULT_QIRC_FILE, 'w', encoding='utf-8')
                    handle = mock_file()
                    all_calls = handle.mock_calls
                    self.assertIn([call.write('{'), call.write('\n  '), call.write('"token"'), call.write(': '),
                                   call.write('"'+expected_token+'"'), call.write('\n'), call.write('}')], all_calls)
                    token = load_account()
                    self.assertEqual(expected_token, token)

    def test_save_and_load_token_filename(self):
        filename = 'path/to/open/dummyqi.rc'
        os.makedirs = MagicMock()
        json.load = MagicMock()
        with patch.dict('os.environ', values={'QI_TOKEN': ''}):
            expected_token = 'secret'
            json.load.return_value = {'token': expected_token}
            with patch("builtins.open", mock_open()) as mock_file:
                with patch('os.makedirs', os.makedirs):
                    save_account(expected_token, filename)
                    mock_file.assert_called_with(filename, 'w', encoding='utf-8')
                    handle = mock_file()
                    all_calls = handle.mock_calls
                    self.assertIn([call.write('{'), call.write('\n  '), call.write('"token"'), call.write(': '),
                                   call.write('"'+expected_token+'"'), call.write('\n'), call.write('}')], all_calls)
                    token = load_account(filename)
                    self.assertEqual(expected_token, token)

    def test_store_token_filename(self):
        filename = 'path/to/open/dummyqi.rc'
        os.makedirs = MagicMock()
        json.load = MagicMock()
        with patch.dict('os.environ', values={'QI_TOKEN': ''}):
            warnings = MagicMock()
            existing_token = 'secret'
            new_token = 'other'
            json.load.return_value = {'token': existing_token}
            with patch("builtins.open", mock_open()) as mock_file:
                with patch('os.makedirs', os.makedirs):
                    with patch('warnings.warn', warnings):
                        store_account(new_token, filename)           # store token, while one exists
                        warnings.assert_called_once()                # warning printed to use overwrite=True
                        mock_file.assert_called_once()
                        mock_file.assert_called_with(filename, 'r', encoding='utf-8')  # no token written,only read once
                        store_account(new_token, filename, overwrite=True)
                        warnings.assert_called_once()                # still 1, no new warning
                        mock_file.assert_called_with(filename, 'w', encoding='utf-8')  # token is written
                        handle = mock_file()
                        all_calls = handle.mock_calls
                        self.assertIn([call.write('{'), call.write('\n  '), call.write('"token"'), call.write(': '),
                                       call.write('"'+new_token+'"'), call.write('\n'), call.write('}')], all_calls)

    def test_remove_token_filename(self):
        filename = 'path/to/open/dummyqi.rc'
        os.makedirs = MagicMock()
        json.load = MagicMock()
        with patch.dict('os.environ', values={'QI_TOKEN': ''}):
            existing_token = 'secret'
            wrong_token = 'not_secret'
            no_token = ''
            json.load.return_value = {'token': existing_token}
            with patch("builtins.open", mock_open()) as mock_file:
                with patch('os.makedirs', os.makedirs):
                    delete_account(wrong_token, filename)          # remove token, while another exists
                    mock_file.assert_called_once()
                    mock_file.assert_called_with(filename, 'r', encoding='utf-8')    # file not written, only read once
                    delete_account(existing_token, filename)                         # remove token, the right one
                    mock_file.assert_called_with(filename, 'w', encoding='utf-8')    # file is written
                    handle = mock_file()
                    all_calls = handle.mock_calls                  # the empty token is written
                    self.assertIn([call.write('{'), call.write('\n  '), call.write('"token"'), call.write(': '),
                                   call.write('"'+no_token+'"'), call.write('\n'), call.write('}')], all_calls)

    def test_load_token_env(self):
        expected_token = 'secret'
        json.load = MagicMock()
        json.load.return_value = {'faulty_key': 'faulty_token'}
        with patch.dict('os.environ', values={'QI_TOKEN': expected_token}):
            with patch("builtins.open", mock_open()):
                token = load_account()
                self.assertEqual(expected_token, token)

    def test_enable_token_env(self):
        expected_token = 'secret'
        json.load = MagicMock()
        json.load.return_value = {'faulty_key': 'faulty_token'}
        environment = MagicMock()
        environment.get.return_value = expected_token
        with patch('os.environ', environment):
            enable_account(expected_token)
            all_calls = environment.mock_calls
            self.assertIn([call.__setitem__('QI_TOKEN', expected_token)], all_calls)
            token = load_account()
            all_calls = environment.mock_calls
            self.assertIn([call.get('QI_TOKEN', None)], all_calls)
            self.assertEqual(expected_token, token)

    def test_get_authentication_token(self):
        secret_token = 'secret'
        with patch.dict('os.environ', values={'QI_TOKEN': secret_token}):
            auth = get_authentication()
            self.assertEqual(auth.token, secret_token)
            self.assertEqual(auth.scheme, 'token')

    def test_get_authentication_basic(self):
        email = 'bla@bla.bla'
        secret_password = 'secret'
        with patch("builtins.open", mock_open()) as mock_file, \
                patch("quantuminspire.credentials.load_account") as mock_load_account, \
                patch.dict('os.environ', values={'QI_EMAIL': email, 'QI_PASSWORD': secret_password}):

            mock_load_account.return_value = None
            auth = get_authentication()
            auth_expected = BasicAuthentication(email, secret_password)
            self.assertEqual(auth, auth_expected)

    def test_get_authentication_basic_stdin(self):
        email = os.environ.get('QI_EMAIL', None)
        if email is not None:
            os.environ.pop('QI_EMAIL')
        email = 'bla@bla.bla'
        secret_password = 'secret'

        # somehow mocking getpass.getpass is not enough for different OS
        with patch("builtins.open", mock_open()) as mock_file, \
                patch("builtins.input") as mock_input, \
                patch("builtins.print") as mock_print, \
                patch("getpass.getpass") as mock_getpass, \
                patch("getpass.win_getpass") as mock_win_getpass, \
                patch("sys.stdin") as mock_sys_stdin, \
                patch("getpass.unix_getpass") as mock_unix_getpass, \
                patch("os.open", side_effect = OSError('foo')), \
                patch("sys.stdin.fileno", side_effect=ValueError('foo')), \
                patch("getpass._raw_input") as mock_raw_input, \
                patch("quantuminspire.credentials.load_account") as mock_load_account, \
                patch("warnings.warn") as mock_warn:
            mock_load_account.return_value = None
            mock_input.return_value = email
            mock_getpass.return_value = secret_password
            mock_raw_input.return_value = secret_password
            mock_win_getpass.return_value = secret_password
            mock_unix_getpass.return_value = secret_password
            auth = get_authentication()
            auth_expected = BasicAuthentication(email, secret_password)
            self.assertEqual(auth, auth_expected)
