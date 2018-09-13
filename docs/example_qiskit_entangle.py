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
import qiskit

from getpass import getpass
from coreapi.auth import BasicAuthentication
from quantuminspire.api import QuantumInspireAPI
from quantuminspire.qiskit.backend_qx import QiSimulatorPy

if 'password' not in vars().keys():
    print('Enter mail address')
    email = input()
    print('Enter password')
    password = getpass()

server_url = r'https://api.quantum-inspire.com'
authentication = BasicAuthentication(email, password)
quantum_inspire_api = QuantumInspireAPI(server_url, authentication)

QPS_SPECS = {
    'circuits': [{
        'name': 'entangle',
        'quantum_registers': [{'name': 'q', 'size': 2}],
        'classical_registers': [{'name': 'b', 'size': 2}]
    }]
}

program = qiskit.QuantumProgram(specs=QPS_SPECS)
q = program.get_quantum_register('q')
b = program.get_classical_register('b')
circuit = program.get_circuit('entangle')

circuit.h(q[0])
circuit.cx(q[0], q[1])
circuit.measure(q[0], b[0])
circuit.measure(q[1], b[1])

qi_backend = QiSimulatorPy(quantum_inspire_api)
result = qiskit.execute(circuit, qi_backend)
print(result.get_counts())
