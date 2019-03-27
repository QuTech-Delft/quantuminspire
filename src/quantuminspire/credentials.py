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

import warnings
import os
import json
from typing import Optional
from coreapi.auth import BasicAuthentication, TokenAuthentication

DEFAULT_QIRC_FILE = os.path.join(os.path.expanduser("~"), '.quantuminspire', 'qirc')


def load_account(filename: str = DEFAULT_QIRC_FILE) -> Optional[str]:
    """ Try to load an earlier stored Quantum Inspire token from file or environment

    Load the token when found. This method looks for the token in two locations, in the following order:
    1. In the environment variable ('QI_TOKEN').
    2. In the file with filename given or, when not given, the default resource file in the user home directory
       (`HOME/.quantuminspire/qirc`).

    Args:
        filename: full path to the resource file. If no filename is given, the default resource file
                  in the user home directory is used (`HOME/.quantuminspire/qirc`).

    Returns:
        The Quantum Inspire token or None when no token is found.
    """
    token = os.environ.get('QI_TOKEN', None) or read_account(filename)
    return token


def read_account(filename: str = DEFAULT_QIRC_FILE) -> Optional[str]:
    """ Try to read an earlier stored Quantum Inspire token from file

    Read the token from file. This method looks for the token in the file with filename given or,
    when no filename is given, the default resource file in the user home directory (`HOME/.quantuminspire/qirc`).

    Args:
        filename: full path to the resource file. If no filename is given, the default resource file
                  in the user home directory is used (`HOME/.quantuminspire/qirc`).

    Returns:
        The Quantum Inspire token or None when no token is found.
    """
    try:
        with open(filename, 'r') as file:
            accounts = json.load(file)
            token: Optional[str] = accounts['token']
    except (OSError, KeyError, ValueError):  # file does not exist or is empty/invalid
        token = None
    return token if (token and len(token)) else None


def store_account(token: str, filename: str = DEFAULT_QIRC_FILE, overwrite: bool = False) -> None:
    """
    Store the token in a resource file. Replace an existing token only when overwrite=True.

    Args:
        token: the Quantum Inspire token to store to disk.
        filename: full path to the resource file. If no filename is given, the default resource file
                  in the user home directory is used (`HOME/.quantuminspire/qirc`).
        overwrite: overwrite an existing token.
    """
    stored_token = read_account(filename)
    if stored_token and stored_token != token and not overwrite:
        warnings.warn('Token already present. Set overwrite=True to overwrite.')
        return
    save_account(token, filename)


def delete_account(token: str, filename: str = DEFAULT_QIRC_FILE) -> None:
    """ Remove the token from the resource file.

    Args:
        token: the Quantum Inspire token to remove.
        filename: full path to the resource file. If no filename is given, the default resource file
                  in the user home directory is used (`HOME/.quantuminspire/qirc`).
    """
    stored_token = read_account(filename)
    if stored_token == token:
        save_account('', filename)


def save_account(token: str, filename: str = DEFAULT_QIRC_FILE) -> None:
    """ Save the token to a file with filename given, otherwise save to the default resource file.
        An existing token is overwritten. Use store_account to prevent overwriting an existing token.

    Args:
        token: the Quantum Inspire token to save.
        filename: full path to the resource file. If no filename is given, the default resource file
                  in the user home directory is used (`HOME/.quantuminspire/qirc`).
    """
    accounts = {'token': token}
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, 'w') as config_file:
        json.dump(accounts, config_file, indent=2)


def enable_account(token: str) -> None:
    """ Save the token to the internal environment, that will be used by load_account for the session.
        When a token was already loaded from the system environment it is overwritten.
        The system environment is not effected.

    Args:
        token: the Quantum Inspire token to be used by load_account() for the session.
    """
    os.environ['QI_TOKEN'] = token


def get_token_authentication(token: Optional[str] = None) -> TokenAuthentication:
    """ Set up token authentication for Quantum Inspire to be used in the API.

    Args:
        token: the Quantum Inspire token to set in TokenAuthentication. When no token is given,

    Returns:
        The token authentication for Quantum Inspire.
    """
    if not token:
        token = load_account()
    return TokenAuthentication(token, scheme="token")


def get_basic_authentication(email: str, password: str) -> BasicAuthentication:
    """ Set up basic authentication for Quantum Inspire to be used in the API.

    Args:
        email: a valid email address.
        password: password for the account.

    Returns:
        The basic authentication for Quantum Inspire.
    """
    return BasicAuthentication(email, password)
