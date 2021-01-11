import os
import random
from getpass import getpass
from quantuminspire.credentials import load_account, get_token_authentication, get_basic_authentication

from qiskit.circuit import QuantumRegister, ClassicalRegister, QuantumCircuit
from qiskit import execute

from quantuminspire.qiskit import QI

from qiskit.providers.aer.noise import NoiseModel
from qiskit.providers.aer.noise import QuantumError, ReadoutError
from qiskit.providers.aer.noise import pauli_error

import matplotlib.pyplot as plt

QI_EMAIL = os.getenv('QI_EMAIL')
QI_PASSWORD = os.getenv('QI_PASSWORD')
QI_URL = os.getenv('API_URL', 'https://api.quantum-inspire.com/')


def do_simulation(p_error):
    QI.set_authentication(get_token_authentication(load_account()), QI_URL)
    qi_backend = QI.get_backend('QX single-node simulator')

    nbits = 3
    q = QuantumRegister(nbits)
    b = ClassicalRegister(nbits)
    circuit = QuantumCircuit(q, b)

    circuit.cx(q[0], q[1])
    circuit.cx(q[0], q[2])

    # ERROR PHASE
    for i in range(nbits):
        if random.random() < p_error:
            print("qubit ", i, " flipped")
            circuit.x(q[i])

    circuit.cx(q[0], q[1])
    circuit.cx(q[0], q[2])
    circuit.ccx(q[2], q[1], q[0])

    qi_job = execute(circuit, backend=qi_backend, shots=1)
    qi_result = qi_job.result()
    histogram = qi_result.get_counts(circuit)

    final_state = 2
    for state, counts in histogram.items():
        print("The initial state was 0, and after the process it is ", state[2])
        final_state = int(state[2])

    assert final_state != 2
    return final_state


if __name__ == '__main__':
    ########################################################################################
    # set these parameters to your liking. Remember: 100 repetitions takes +/- 8 minutes
    p_error = 0.0
    repetitions = 100
    ########################################################################################

    correct = 0
    wrong = 0

    for i in range(repetitions):
        print("run", i)
        if do_simulation(p_error) == 0:
            correct += 1
        else:
            wrong += 1

    print("correct: ", correct)
    print("wrong: ", wrong)

    print("The error rate is now", wrong/repetitions, "instead of the underlying", p_error)



