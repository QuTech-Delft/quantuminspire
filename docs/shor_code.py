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


def cnot_next_two(circuit, q, i):
    circuit.cx(q[i], q[i + 1])
    circuit.cx(q[i], q[i + 2])


if __name__ == '__main__':

    QI.set_authentication(get_token_authentication(load_account()), QI_URL)
    qi_backend = QI.get_backend('QX single-node simulator')

    q = QuantumRegister(9)
    b = ClassicalRegister(9)
    circuit = QuantumCircuit(q, b)

    circuit.cx(q[0], q[3])
    circuit.cx(q[0], q[6])

    circuit.h(q[0])
    circuit.h(q[3])
    circuit.h(q[6])

    cnot_next_two(circuit, q, 0)
    cnot_next_two(circuit, q, 3)
    cnot_next_two(circuit, q, 6)

    ###############################
    # possible error
    circuit.x(q[0])
    ###############################

    cnot_next_two(circuit, q, 0)
    cnot_next_two(circuit, q, 3)
    cnot_next_two(circuit, q, 6)

    circuit.toffoli(q[2], q[1], q[0])
    circuit.toffoli(q[5], q[4], q[3])
    circuit.toffoli(q[8], q[7], q[6])

    circuit.h(q[0])
    circuit.h(q[3])
    circuit.h(q[6])

    circuit.cx(q[0], q[3])
    circuit.cx(q[0], q[6])
    circuit.toffoli(q[6], q[3], q[0])

    circuit.draw(output='mpl')
    plt.show()

    qi_job = execute(circuit, backend=qi_backend, shots=256)
    qi_result = qi_job.result()
    histogram = qi_result.get_counts(circuit)
    print('\nState\tCounts')
    [print('{0}\t\t{1}'.format(state, counts)) for state, counts in histogram.items()]
    # Print the full state probabilities histogram
    probabilities_histogram = qi_result.get_probabilities(circuit)
    print('\nState\tProbabilities')
    [print('{0}\t\t{1}'.format(state, val)) for state, val in probabilities_histogram.items()]
