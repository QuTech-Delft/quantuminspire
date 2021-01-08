import os
from getpass import getpass
from quantuminspire.credentials import load_account, get_token_authentication, get_basic_authentication

from qiskit.circuit import QuantumRegister, ClassicalRegister, QuantumCircuit
from qiskit import execute

from quantuminspire.qiskit import QI

import matplotlib.pyplot as plt

QI_EMAIL = os.getenv('QI_EMAIL')
QI_PASSWORD = os.getenv('QI_PASSWORD')
QI_URL = os.getenv('API_URL', 'https://api.quantum-inspire.com/')


if __name__ == '__main__':

    QI.set_authentication(get_token_authentication(load_account()), QI_URL)
    qi_backend = QI.get_backend('QX single-node simulator')

    q = QuantumRegister(3)
    b = ClassicalRegister(3)
    circuit = QuantumCircuit(q, b)

    circuit.cx(q[0], q[1])
    circuit.cx(q[0], q[2])

    ################
    # possible error
    circuit.x(q[1])
    ################

    circuit.cx(q[0], q[1])
    circuit.cx(q[0], q[2])
    circuit.ccx(q[2], q[1], q[0])

    qi_job = execute(circuit, backend=qi_backend, shots=256)
    qi_result = qi_job.result()
    histogram = qi_result.get_counts(circuit)
    print('\nState\tCounts')
    [print('{0}\t\t{1}'.format(state, counts)) for state, counts in histogram.items()]
    # Print the full state probabilities histogram
    probabilities_histogram = qi_result.get_probabilities(circuit)
    print('\nState\tProbabilities')
    [print('{0}\t\t{1}'.format(state, val)) for state, val in probabilities_histogram.items()]
