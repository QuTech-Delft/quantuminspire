"""Example usage of the Quantum Inspire API.

A simple example that demonstrates how to use the SDK API to delete
all projects registered for the authenticated user in Quantum Inspire.

Specific to Quantum Inspire is the creation of the QI instance, which is used to set the authentication
of the user.

To change user (token) or environment (production/staging) set environment variables QI_TOKEN and API_URL respectively.

Copyright 2018-2023 QuTech Delft. Licensed under the Apache License, Version 2.0.
"""
import os
from quantuminspire.credentials import get_token_authentication, load_account
from quantuminspire.qiskit import QI

QI_URL = os.getenv('API_URL', 'https://staging.quantum-inspire.com/')


token = load_account()
if token is not None:
    qi_authentication = get_token_authentication(token)
    QI.set_authentication(qi_authentication, QI_URL)
    api = QI.get_api()

    projects = api.get_projects()
    for project in projects:
        api.delete_project(project["id"])
