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
from typing import Optional
from coreapi.auth import BasicAuthentication, TokenAuthentication

DEFAULT_QIRC_FILE = os.path.join(os.path.expanduser("~"), '.quantuminspire', 'qirc')


def load_token(filename: str = DEFAULT_QIRC_FILE) -> Optional[str]:
    """ Try to load the saved Quantum Inspire token from file or environment

    Load the token found in the system. This method looks for the token in two locations, in the following order:
    1. In the file with filename given or, when not given, the default resource file in the user home directory
       (`HOME/.quantuminspire/qirc`).
    2. In the environment variable ('QI_TOKEN').

    Args
        filename: full path to the resource file. If no filename is given, the default resource file is used.

    Returns:
        The loaded Quantum Inspire token or None when no token is found.
    """
    try:
        with open(filename, 'r') as file:
            accounts = json.load(file)
            token: Optional[str] = accounts['token']
    except (OSError, KeyError, ValueError):  # file does not exist or is empty/invalid
        token = os.getenv('QI_TOKEN', None)
    return token


def save_token(token: str, filename: str = DEFAULT_QIRC_FILE) -> None:
    """ Save the token to a file with filename given, otherwise save to the default resource file.

    Args
        token: the Quantum Inspire token to save.
        filename: full path to the target file. If not given, the default resource file
                  in the user home directory is used (`HOME/.quantuminspire/qirc`).
    """
    accounts = {'token': token}
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, 'w') as config_file:
        json.dump(accounts, config_file, indent=2)


def get_token_authentication(token: str) -> TokenAuthentication:
    """ Set up token authentication for Quantum Inspire to be used in the API.

    Args
        token: the Quantum Inspire  token to set in TokenAuthentication.

    Returns:
        The token authentication for Quantum Inspire.
    """
    return TokenAuthentication(token, scheme="token")


def get_basic_authentication(email: str, password: str) -> BasicAuthentication:
    """ Set up basic authentication for Quantum Inspire to be used in the API.

    Args
        email: A valid email address.
        password: Password for the account.

    Returns:
        The basic authentication for Quantunm Inspire.
    """
    return BasicAuthentication(email, password)
