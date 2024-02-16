"""Example usage of the Quantum Inspire backend with the Qiskit SDK.

A simple example that demonstrates how to use the SDK to create
a circuit to create a Bell state, and simulate the circuit on
Quantum Inspire.

For documentation on how to use Qiskit we refer to
[https://qiskit.org/](https://qiskit.org/).

Specific to Quantum Inspire is the creation of the QI instance, which is used to set the authentication
of the user and provides a Quantum Inspire backend that is used to execute the circuit.

Copyright 2018-2022 QuTech Delft. Licensed under the Apache License, Version 2.0.
"""
import os

from qiskit import transpile
from qiskit.circuit import QuantumRegister, ClassicalRegister, QuantumCircuit

from quantuminspire.credentials import get_authentication
from quantuminspire.qiskit import QI

QI_URL = os.getenv('API_URL', 'https://api.quantum-inspire.com/')


project_name = 'Qiskit-entangle'
authentication = get_authentication()
QI.set_authentication(authentication, QI_URL, project_name=project_name)
qi_backend = QI.get_backend('QX single-node simulator')

q = QuantumRegister(2)
b = ClassicalRegister(2)
circuit = QuantumCircuit(q, b)

circuit.h(q[0])
circuit.cx(q[0], q[1])
circuit.measure(q, b)

circuit = transpile(circuit, backend=qi_backend)
qi_job = qi_backend.run(circuit, shots=256)
qi_result = qi_job.result()
histogram = qi_result.get_counts(circuit)
print('\nState\tCounts')
[print('{0}\t\t{1}'.format(state, counts)) for state, counts in histogram.items()]
# Print the full state probabilities histogram
probabilities_histogram = qi_result.get_probabilities(circuit)
print('\nState\tProbabilities')
[print('{0}\t\t{1}'.format(state, val)) for state, val in probabilities_histogram.items()]
