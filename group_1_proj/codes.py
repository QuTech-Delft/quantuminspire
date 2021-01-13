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
        any_corrupted = False
        for i in range(circuit.num_qubits):
            if random.random() < p_error:
                print("qubit", i, "corrupted")
                any_corrupted = True
                matrix = get_random_noise_matrix()
                err_op = Operator(matrix)
                circuit.unitary(err_op, [i], label='error')

        if not any_corrupted:
            print("no qubits corrupted")
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

    qi_job = execute(circuit, backend=qi_backend, shots=1)
    qi_result = qi_job.result()
    probabilities_histogram = qi_result.get_probabilities(circuit)

    correct_prob = 0.0
    wrong_prob = 0.0
    for state, val in probabilities_histogram.items():
        if int(state[2]) == 0:
            correct_prob += val
        else:
            wrong_prob += val

    print("The initial state was 0, and after the process it is 0 with probability", round(correct_prob, 3))
    print("The initial state was 0, and after the process it is 1 with probability", round(wrong_prob, 3))

    return correct_prob


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

    # SIMULATION (SHOTS MUST BE EQUAL TO 1 HERE!!!) (otherwise the optimization is not triggered correctly)
    qi_job = execute(circuit, backend=qi_backend, shots=1)
    qi_result = qi_job.result()
    probabilities_histogram = qi_result.get_probabilities(circuit)

    correct_prob = 0.0
    wrong_prob = 0.0
    for state, val in probabilities_histogram.items():
        if int(state[8]) == 0:
            correct_prob += val
        else:
            wrong_prob += val

    print("The initial state was 0, and after the process it is 0 with probability", round(correct_prob, 3))
    print("The initial state was 0, and after the process it is 1 with probability", round(wrong_prob, 3))

    return correct_prob


def la_flamme(apply_noise):
    QI.set_authentication(get_token_authentication(load_account()), QI_URL)
    qi_backend = QI.get_backend('QX single-node simulator')

    nbits = 5
    q = QuantumRegister(nbits, "q")
    c = ClassicalRegister(nbits, "c")
    qc = QuantumCircuit(q, c, name="Laflamme logical qubit")

    qc.h(0)
    qc.h(1)
    qc.h(3)

    # Creates a new cicuit in which the effect of the multi control/target gate is enclosed
    multi = QuantumCircuit(1, name='pi phase')
    multi.z(0)
    # Generate the actual gate
    multi_gate = multi.to_gate()

    # Makes it a controlled gate, with three controls
    cmulti_z_gate0 = multi_gate.control(3)
    # Other gate, but also specifies in which state the control qubits should be in
    cmulti_z_gate1 = multi_gate.control(3, ctrl_state='010')
    cmulti_z_gate2 = multi_gate.control(2)

    # Adds the gates to the existing circuit with the [control, target]
    qc.append(cmulti_z_gate0, [1, 2, 3, 4])
    qc.append(cmulti_z_gate1, [1, 2, 3, 4])

    qc.cx(2, 4)

    # Same as before, but this time two qubits are affected by gate
    multi2 = QuantumCircuit(2, name='c-x')
    multi2.x(0)
    multi2.x(1)
    multi_gate2 = multi2.to_gate()
    cmulti_x_gate = multi_gate2.control()

    qc.append(cmulti_x_gate, [0, 2, 4])

    qc.cx(3, 2)

    qc.cx(1, 4)

    qc.append(cmulti_z_gate2, [4, 3, 2])

    #################################################################################################
    # ERROR PHASE
    # todo: implement error here
    apply_noise(qc)
    #################################################################################################

    # Decoder is the same as the encoder, so this completes the circuit
    qc.append(cmulti_z_gate2, [4, 3, 2])
    qc.cx(1, 4)
    qc.cx(3, 2)
    qc.append(cmulti_x_gate, [0, 2, 4])
    qc.cx(2, 4)
    qc.append(cmulti_z_gate1, [1, 2, 3, 4])
    qc.append(cmulti_z_gate0, [1, 2, 3, 4])
    qc.h(3)
    qc.h(1)
    qc.h(0)

    qi_job = execute(qc, backend=qi_backend, shots=1)
    qi_result = qi_job.result()
    probabilities_histogram = qi_result.get_probabilities(qc)

    correct_prob = 0.0
    wrong_prob = 0.0
    for state, val in probabilities_histogram.items():
        if int(state[2]) == 0:
            correct_prob += val
        else:
            wrong_prob += val

    print("The initial state was 0, and after the process it is 0 with probability", round(correct_prob, 3))
    print("The initial state was 0, and after the process it is 1 with probability", round(wrong_prob, 3))

    return correct_prob


def logical_qubit_error(p_error, repetitions, code):

    noise_model = uniform_uncorrelated_noise(p_error)

    total_prob = 0
    for i in range(repetitions):
        print("run", i)
        correct_prob = code(noise_model)
        total_prob += correct_prob

    error_rate = 1 - (total_prob / repetitions)

    print("The error rate is now", round(error_rate, 5), "instead of the underlying", p_error)
    return error_rate


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
