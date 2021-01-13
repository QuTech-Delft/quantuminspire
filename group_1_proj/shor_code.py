import os
import random
import numpy as np

from qiskit.quantum_info import Operator
from quantuminspire.credentials import load_account, get_token_authentication

from qiskit.circuit import QuantumRegister, ClassicalRegister, QuantumCircuit
from qiskit import execute

from quantuminspire.qiskit import QI

QI_EMAIL = os.getenv('QI_EMAIL')
QI_PASSWORD = os.getenv('QI_PASSWORD')
QI_URL = os.getenv('API_URL', 'https://api.quantum-inspire.com/')


def cnot_next_two(circuit, q, i):
    circuit.cx(q[i], q[i + 1])
    circuit.cx(q[i], q[i + 2])


def generate_random_factors():
    e0 = random.random()
    e1 = random.random()
    e2 = random.random()
    e3 = random.random()

    norm = e0**2 + e1**2 + e2**2 + e3**2
    e0 /= norm
    e1 /= norm
    e2 /= norm
    e3 /= norm

    return e0, e1, e2, e3


def get_random_noise_matrix():
    e0, e1, e2, e3 = generate_random_factors()
    matrix = np.array([[e0 + e2, e1 - e3],
                       [e1 + e3, e0 - e2]])
    q, r = np.linalg.qr(matrix)
    return q.tolist()


def do_simulation(p_error):
    QI.set_authentication(get_token_authentication(load_account()), QI_URL)
    qi_backend = QI.get_backend('QX single-node simulator')

    nbits = 9
    q = QuantumRegister(nbits)
    b = ClassicalRegister(nbits)
    circuit = QuantumCircuit(q, b)

    # ENCODING PHASE
    circuit.cx(q[0], q[3])
    circuit.cx(q[0], q[6])

    circuit.h(q[0])
    circuit.h(q[3])
    circuit.h(q[6])

    cnot_next_two(circuit, q, 0)
    cnot_next_two(circuit, q, 3)
    cnot_next_two(circuit, q, 6)

    # ERROR PHASE
    for i in range(nbits):
        if random.random() < p_error:
            print("qubit ", i, " corrupted")
            matrix = get_random_noise_matrix()
            err_op = Operator(matrix)
            print(matrix)
            circuit.unitary(err_op, [i], label='error')

    # DECODING PHASE
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

    # SIMULATION (SHOTS MUST BE EQUAL TO 1 HERE!!!)
    qi_job = execute(circuit, backend=qi_backend, shots=1)
    qi_result = qi_job.result()
    histogram = qi_result.get_counts(circuit)

    final_state = 2
    final_states = []
    for state, counts in histogram.items():
        print("The initial state was 0, and after the process it is ", state[8])
        final_state = int(state[8])
        final_states.append(state[8])

    assert final_state != 2
    return final_state


if __name__ == '__main__':
    ########################################################################################
    # set these parameters to your liking. Remember: 100 repetitions takes +/- 8 minutes
    p_error = 0
    repetitions = 1
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

    print("The error rate is now", wrong / repetitions, "instead of the underlying", p_error)
