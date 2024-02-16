"""Example usage of the Quantum Inspire backend with the Qiskit SDK.

A simple example that demonstrates how to use the SDK to create
a circuit to demonstrate conditional gate execution.

For documentation on how to use Qiskit we refer to
[https://qiskit.org/](https://qiskit.org/).

Specific to Quantum Inspire is the creation of the QI instance, which is used to set the authentication
of the user and provides a Quantum Inspire backend that is used to execute the circuit.

Copyright 2018-2022 QuTech Delft. Licensed under the Apache License, Version 2.0.
"""
import os

from qiskit import transpile
from qiskit.providers.basic_provider import BasicProvider
from qiskit.circuit import QuantumRegister, ClassicalRegister, QuantumCircuit

from quantuminspire.credentials import get_authentication
from quantuminspire.qiskit import QI

QI_URL = os.getenv('API_URL', 'https://api.quantum-inspire.com/')


authentication = get_authentication()
QI.set_authentication(authentication, QI_URL)
qi_backend = QI.get_backend('QX single-node simulator')

q = QuantumRegister(3, "q")
c0 = ClassicalRegister(1, "c0")
c1 = ClassicalRegister(1, "c1")
c2 = ClassicalRegister(1, "c2")
qc = QuantumCircuit(q, c0, c1, c2, name="conditional")

qc.h(q[0])
qc.h(q[1]).c_if(c0, 0)  # h-gate on q[1] is executed
qc.h(q[2]).c_if(c1, 1)  # h-gate on q[2] is not executed

qc.measure(q[0], c0)
qc.measure(q[1], c1)
qc.measure(q[2], c2)

qc = transpile(qc, backend=qi_backend)
qi_job = qi_backend.run(qc, shots=1024)
qi_result = qi_job.result()
histogram = qi_result.get_counts(qc)
print("\nResult from the remote Quantum Inspire backend:\n")
print('State\tCounts')
[print('{0}\t{1}'.format(state, counts)) for state, counts in histogram.items()]

print("\nResult from the local Qiskit simulator backend:\n")
backend = BasicProvider().get_backend(name="basic_simulator")   # qasm_simulator
qc = transpile(qc, backend=backend)
job = backend.run(qc, shots=1024)

result = job.result()
print(result.get_counts(qc))
