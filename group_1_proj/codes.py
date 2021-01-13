import os
import random
import numpy as np
import matplotlib.pyplot as plt

from qiskit.quantum_info import Operator
from quantuminspire.credentials import load_account, get_token_authentication

from qiskit.circuit import QuantumRegister, ClassicalRegister, QuantumCircuit
from qiskit import execute

from quantuminspire.qiskit import QI

QI_EMAIL = os.getenv('QI_EMAIL')
QI_PASSWORD = os.getenv('QI_PASSWORD')
QI_URL = os.getenv('API_URL', 'https://api.quantum-inspire.com/')


def generate_random_factors():
    e0 = random.random()
    e1 = random.random()
    e2 = random.random()
    e3 = random.random()

    norm = e0 ** 2 + e1 ** 2 + e2 ** 2 + e3 ** 2
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


def uniform_uncorrelated_noise(p_error):
    def apply_noise(circuit):
        for i in range(circuit.num_qubits):
            if random.random() < p_error:
                print("qubit ", i, " corrupted")
                matrix = get_random_noise_matrix()
                err_op = Operator(matrix)
                print(matrix)
                circuit.unitary(err_op, [i], label='error')
    return apply_noise


def bit_flip(apply_noise):
    QI.set_authentication(get_token_authentication(load_account()), QI_URL)
    qi_backend = QI.get_backend('QX single-node simulator')

    nbits = 3
    q = QuantumRegister(nbits)
    b = ClassicalRegister(nbits)
    circuit = QuantumCircuit(q, b)

    # ENCODING PHASE
    circuit.cx(q[0], q[1])
    circuit.cx(q[0], q[2])

    # ERROR PHASE
    apply_noise(circuit)

    # DECODING PHASE
    circuit.cx(q[0], q[1])
    circuit.cx(q[0], q[2])
    circuit.ccx(q[2], q[1], q[0])

    # SIMULATION
    qi_job = execute(circuit, backend=qi_backend, shots=1)
    qi_result = qi_job.result()
    histogram = qi_result.get_counts(circuit)

    final_state = 2
    for state, counts in histogram.items():
        print("The initial state was 0, and after the process it is ", state[2])
        final_state = int(state[2])

    assert final_state != 2
    return final_state


def shor(apply_noise):
    def cnot_next_two(circuit, q, i):
        circuit.cx(q[i], q[i + 1])
        circuit.cx(q[i], q[i + 2])

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
    apply_noise(circuit)

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

    # SIMULATION
    qi_job = execute(circuit, backend=qi_backend, shots=256)
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


def la_flamme(apply_noise):
    QI.set_authentication(get_token_authentication(load_account()), QI_URL)
    qi_backend = QI.get_backend('QX single-node simulator')

    q = QuantumRegister(5, "q")
    c = ClassicalRegister(1, "c")  # Only 1 bit for measuring the state of the qubit

    qc = QuantumCircuit(q, c, name="Laflamme logical qubit")

    qc.h(0)
    qc.h(1)
    qc.h(3)

    multi = QuantumCircuit(1,
                           name='pi phase')  # Creates a new cicuit in which the effect of the multi control/target gate is enclosed
    multi.z(0)
    multi_gate = multi.to_gate()  # Makes a gate out of the circuit

    cmulti_z_gate0 = multi_gate.control(3)  # Makes it a controlled gate, with three controls
    cmulti_z_gate1 = multi_gate.control(3,
                                        ctrl_state='010')  # Other gate, but also specifies in which state the control qubits should be in
    cmulti_z_gate2 = multi_gate.control(2)

    qc.append(cmulti_z_gate0, [1, 2, 3, 4])  # Adds the gates to the existing circuit with the [ control , target ]
    qc.append(cmulti_z_gate1, [1, 2, 3, 4])

    qc.cx(2, 4)

    multi = QuantumCircuit(2, name='c-x')  # Same as before, but this time two qubits are affected by gate
    multi.x(0)
    multi.x(1)
    multi_gate = multi.to_gate()
    cmulti_x_gate = multi_gate.control()

    qc.append(cmulti_x_gate, [0, 2, 4])

    qc.cx(3, 2)

    qc.cx(1, 4)

    qc.append(cmulti_z_gate2, [4, 3, 2])

    ########################################## Errors can occur here #######################################################

    # ERROR PHASE
    apply_noise(qc)

    qc = qc + qc.inverse()  # Decoder is the same as the encoder, so this completes the circuit

    qc.measure(q[2], c[0])

    # SIMULATION
    qi_job = execute(qc, backend=qi_backend, shots=1)
    qi_result = qi_job.result()
    histogram = qi_result.get_counts(qc)

    final_state = 2
    for state, counts in histogram.items():
        print("The initial state was 0, and after the process it is ", state[0])
        final_state = int(state[0])

    assert final_state != 2
    return final_state


def logical_qubit_error(p_error, repetitions, code):
    correct = 0
    wrong = 0
    noise_model = uniform_uncorrelated_noise(p_error)

    for i in range(repetitions):
        print("run", i)
        if code(noise_model) == 0:
            correct += 1
        else:
            wrong += 1

    print("correct: ", correct)
    print("wrong: ", wrong)

    print("The error rate is now", wrong / repetitions, "instead of the underlying", p_error)

    return wrong / repetitions


if __name__ == '__main__':
    ########################################################################################
    # set these parameters to your liking. Remember: 100 repetitions takes +/- 8 minutes
    p_error = [0.05 * i for i in range(11)]
    repetitions = 10

    codes = {"bit_flip": bit_flip,
             "shor": shor,
             "la_flamme": la_flamme}

    for c in codes:
        plt.plot(p_error, [logical_qubit_error(p, repetitions, codes[c]) for p in p_error], 'ro')
        plt.savefig(f'{c}.png')
        plt.clf()

    ########################################################################################
