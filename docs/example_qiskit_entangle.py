"""Example usage of the Quantum Inspire backend with the QisKit SDK.

A simple example that demonstrates how to use the SDK to create
a circuit to create a Bell state, and simulate the circuit on
Quantum Inspire.

For documentation on how to use QisKit we refer to
[https://qiskit.org/](https://qiskit.org/).

Specific to Quantum Inspire is the creation of the QuantumInspireAPI
instance, which is used to instantiate a QiSimulatorPy backend later
on that is used to execute the circuit.


Copyright 2018 QuTech Delft. Licensed under the Apache License, Version 2.0.
"""
from getpass import getpass

from coreapi.auth import BasicAuthentication
from qiskit import QuantumRegister, ClassicalRegister, QuantumCircuit, execute

from quantuminspire.api import QuantumInspireAPI
from quantuminspire.qiskit.backend_qx import QiSimulatorPy


def get_authentication():
    """ Gets the authentication for connecting to the Quantum Inspire API."""
    if 'password' not in vars().keys():
        print('Enter email:')
        email = input()
        print('Enter password')
        password = getpass()
    return BasicAuthentication(email, password)


if __name__ == '__main__':

    authentication = get_authentication()
    uri = "https://api.quantum-inspire.com"
    qi_api = QuantumInspireAPI(uri, authentication)
    qi_backend = QiSimulatorPy(qi_api)

    q = QuantumRegister(2)
    b = ClassicalRegister(2)
    circuit = QuantumCircuit(q, b)

    circuit.h(q[0])
    circuit.cx(q[0], q[1])
    circuit.measure(q, b)

    result = execute(circuit, backend=qi_backend, shots=256)

    histogram = result.get_counts(circuit)
    print('\nState\tCounts')
    [print('{0}\t{1}'.format(state, counts)) for state, counts in histogram.items()]
