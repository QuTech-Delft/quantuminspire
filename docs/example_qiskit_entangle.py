"""Example usage of the Quantum Inspire backend with the QisKit SDK.

A simple example that demonstrates how to use the SDK to create
a circuit to create a Bell state, and simulate the circuit on
Quantum Inspire.

For documentation on how to use QisKit we refer to
[https://qiskit.org/](https://qiskit.org/).

Specific to Quantum Inspire is the creation of the QI instance, which is used to set the authentication of the user and
provides a Quantum Inspire backend that is used to execute the circuit.


Copyright 2018-19 QuTech Delft. Licensed under the Apache License, Version 2.0.
"""
import os
from getpass import getpass
from quantuminspire.credentials import load_account, get_token_authentication, get_basic_authentication

from qiskit.validation.base import Obj
from qiskit.circuit import QuantumRegister, ClassicalRegister, QuantumCircuit
from qiskit import execute

from quantuminspire.qiskit import QI

QI_EMAIL = os.getenv('QI_EMAIL')
QI_PASSWORD = os.getenv('QI_PASSWORD')
QI_URL = os.getenv('API_URL', 'https://api.quantum-inspire.com/')


def get_authentication():
    """ Gets the authentication for connecting to the Quantum Inspire API."""
    token = load_account()
    if token is not None:
        return get_token_authentication(token)
    else:
        if QI_EMAIL is None or QI_PASSWORD is None:
            print('Enter email:')
            email = input()
            print('Enter password')
            password = getpass()
        else:
            email, password = QI_EMAIL, QI_PASSWORD
        return get_basic_authentication(email, password)


if __name__ == '__main__':

    authentication = get_authentication()
    QI.set_authentication(authentication, QI_URL)
    qi_backend = QI.get_backend('QX single-node simulator')

    q = QuantumRegister(2)
    b = ClassicalRegister(2)
    circuit = QuantumCircuit(q, b)

    circuit.h(q[0])
    circuit.cx(q[0], q[1])
    circuit.measure(q, b)

    qi_job = execute(circuit, backend=qi_backend, shots=256)
    qi_result = qi_job.result()
    histogram = qi_result.get_counts(circuit)
    print('\nState\tCounts')
    [print('{0}\t\t{1}'.format(state, counts)) for state, counts in histogram.items()]
    # Print the full state probabilities histogram
    probabilities_histogram = Obj.to_dict(qi_result.data(circuit)['probabilities'])
    print('\nState\tProbabilities')
    # Format the hexadecimal key to a zero-padded binary string with length of the number of classical bits
    [print('{0}\t\t{1}'.format(format(int(str(bin(int(key, 16)))[2:], 2), '0{}b'.format(b.size)),
                             val)) for key, val in probabilities_histogram.items()]
