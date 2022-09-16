# Quantum Inspire SDK
#
# Copyright 2022 QuTech Delft
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Module credentials
==================

The following functions use a resource file to store credentials information
for the user. The default location of this resource file is
:file:`.quantuminspire/qirc` in the user's home directory.
This default location is indicated with `DEFAULT_QIRC_FILE` in the following function signatures.

.. autofunction:: load_account(filename: str = DEFAULT_QIRC_FILE) -> Optional[str]
.. autofunction:: read_account(filename: str = DEFAULT_QIRC_FILE) -> Optional[str]
.. autofunction:: store_account(token: str, filename: str = DEFAULT_QIRC_FILE, overwrite: bool = False) -> None
.. autofunction:: delete_account(token: str, filename: str = DEFAULT_QIRC_FILE) -> None
.. autofunction:: save_account(token: str, filename: str = DEFAULT_QIRC_FILE) -> None
.. autofunction:: enable_account(token: str) -> None:
.. autofunction:: get_token_authentication(token: Optional[str] = None) -> TokenAuthentication:
.. autofunction:: get_basic_authentication(email: str, password: str) -> BasicAuthentication:
.. autofunction:: get_authentication() -> Union[TokenAuthentication, BasicAuthentication]:

"""

from getpass import getpass
import json
import os
from typing import Optional, Union
import warnings

from coreapi.auth import BasicAuthentication, TokenAuthentication

DEFAULT_QIRC_FILE = os.path.join(os.path.expanduser("~"), '.quantuminspire', 'qirc')


def load_account(filename: str = DEFAULT_QIRC_FILE) -> Optional[str]:
    """ Try to load an earlier stored Quantum Inspire token from file or environment.

    Load the token when found. This method looks for the token in two locations, in the following order:

        1. In the environment variable (:envvar:`QI_TOKEN`).
        2. In the file with `filename` given or, when not given, the default resource file
           :file:`.quantuminspire/qirc` in the user's home directory.

    :param filename: full path to the resource file. If no `filename` is given, the default resource file
        :file:`.quantuminspire/qirc` in the user's home directory is used.
    :return:
        The Quantum Inspire token or None when no token is found.
    """
    token = os.environ.get('QI_TOKEN', None) or read_account(filename)
    return token


def read_account(filename: str = DEFAULT_QIRC_FILE) -> Optional[str]:
    """ Try to read an earlier stored Quantum Inspire token from file.

    his method looks for the token in the file with `filename` given or,
    when no `filename` is given, the default resource file :file:`.quantuminspire/qirc` in the user's home directory.

    :param filename: full path to the resource file. If no filename is given, the default resource file
        :file:`.quantuminspire/qirc` in the user's home directory is used.

    :return:
        The Quantum Inspire token or None when no token is found or token is empty.
    """
    try:
        with open(filename, 'r', encoding='utf-8') as file:
            accounts = json.load(file)
            token: Optional[str] = accounts['token']
    except (OSError, KeyError, ValueError):  # file does not exist or is empty/invalid
        token = None
    return token if token else None


def store_account(token: str, filename: str = DEFAULT_QIRC_FILE, overwrite: bool = False) -> None:
    """Store the token in a resource file.

    Replace an existing token only when overwrite=True.

    :param token: the Quantum Inspire token to store to disk.
    :param filename: full path to the resource file. If no `filename` is given, the default resource file
        :file:`.quantuminspire/qirc` in the user's home directory is used.
    :param overwrite: overwrite an existing token.
    """
    stored_token = read_account(filename)
    if stored_token and stored_token != token and not overwrite:
        warnings.warn('Token already present. Set overwrite=True to overwrite.')
        return
    save_account(token, filename)


def delete_account(token: str, filename: str = DEFAULT_QIRC_FILE) -> None:
    """Remove the token from the resource file.

    :param token: the Quantum Inspire token to remove.
    :param filename: full path to the resource file. If no `filename` is given, the default resource file
        :file:`.quantuminspire/qirc` in the user's home directory is used.
    """
    stored_token = read_account(filename)
    if stored_token == token:
        save_account('', filename)


def save_account(token: str, filename: str = DEFAULT_QIRC_FILE) -> None:
    """Save the token to a file.

    Save the token to the file with `filename` given, otherwise save to the default resource file.
    An existing token is overwritten. Use :meth:`~.store_account` to prevent overwriting an existing token.

    :param token: the Quantum Inspire token to save.
    :param filename: full path to the resource file. If no `filename` is given, the default resource file
        :file:`.quantuminspire/qirc` in the user's home directory is used.
    """
    accounts = {'token': token}
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, 'w', encoding='utf-8') as config_file:
        json.dump(accounts, config_file, indent=2)


def enable_account(token: str) -> None:
    """Save the token to the internal environment, that will be used by load_account for the session.

    When a token was already loaded from the system environment it is overwritten.
    The system environment is not effected.

    :param token: the Quantum Inspire token to be used by :meth:`~.load_account` for the session.
    """
    os.environ['QI_TOKEN'] = token


def get_token_authentication(token: Optional[str] = None) -> TokenAuthentication:
    """Set up token authentication for Quantum Inspire to be used in the API.

    :param token: the Quantum Inspire token to set in TokenAuthentication. When no token is given,
        the token returned from :meth:`~.load_account` is used.

    :return:
        The token authentication for Quantum Inspire.
    """
    if not token:
        token = load_account()
    return TokenAuthentication(token, scheme="token")


def get_basic_authentication(email: str, password: str) -> BasicAuthentication:
    """Set up basic authentication for Quantum Inspire to be used in the API.

    :param email: a valid email address.
    :param password: password for the account.

    :return:
        The basic authentication for Quantum Inspire.
    """
    return BasicAuthentication(email, password)


def get_authentication() -> Union[TokenAuthentication, BasicAuthentication]:
    """ Gets the authentication for connecting to the Quantum Inspire API.

        First it tries to load a token, saved earlier. When a token is not found it tries to login
        with basic authentication read from the environment variables QI_EMAIL and QI_PASSWORD. When the environment
        variables are not both set, email and password are read from standard input.

    :return:
        The token or basic authentication for Quantum Inspire.
    """
    token = load_account()
    if token is not None:
        return get_token_authentication(token)

    email = os.environ.get('QI_EMAIL', None)
    password = os.environ.get('QI_PASSWORD', None)
    if email is None or password is None:
        print('Enter email:')
        email = input()
        print('Enter password')
        password = getpass()

    return get_basic_authentication(email, password)
