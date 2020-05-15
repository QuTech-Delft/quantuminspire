"""
This example is copied from https://github.com/ProjectQ-Framework/ProjectQ
and is covered under the Apache 2.0 license.
"""
import os
import math
from getpass import getpass

from projectq import MainEngine
from projectq.backends import ResourceCounter, Simulator
from projectq.meta import Compute, Control, Loop, Uncompute
from projectq.ops import CNOT, CZ, All, H, Measure, X, Z
from projectq.setups import restrictedgateset

from quantuminspire.credentials import load_account, get_token_authentication, get_basic_authentication
from quantuminspire.api import QuantumInspireAPI
from quantuminspire.projectq.backend_qx import QIBackend

QI_EMAIL = os.getenv('QI_EMAIL')
QI_PASSWORD = os.getenv('QI_PASSWORD')
QI_URL = os.getenv('API_URL', 'https://api.quantum-inspire.com/')


def run_grover(eng, n, oracle):
    """
    Runs Grover's algorithm on n qubit using the provided quantum oracle.

    Args:
        eng (MainEngine): Main compiler engine to run Grover on.
        n (int): Number of bits in the solution.
        oracle (function): Function accepting the engine, an n-qubit register,
            and an output qubit which is flipped by the oracle for the correct
            bit string.

    Returns:
        solution (list<int>): Solution bit-string.
    """
    x = eng.allocate_qureg(n)

    # start in uniform superposition
    All(H) | x

    # number of iterations we have to run:
    num_it = int(math.pi / 4. * math.sqrt(1 << n))

    # prepare the oracle output qubit (the one that is flipped to indicate the
    # solution. start in state 1/sqrt(2) * (|0> - |1>) s.t. a bit-flip turns
    # into a (-1)-phase.
    oracle_out = eng.allocate_qubit()
    X | oracle_out
    H | oracle_out

    # run num_it iterations
    with Loop(eng, num_it):
        # oracle adds a (-1)-phase to the solution
        oracle(eng, x, oracle_out)

        # reflection across uniform superposition
        with Compute(eng):
            All(H) | x
            All(X) | x

        with Control(eng, x[0:-1]):
            Z | x[-1]

        Uncompute(eng)

    All(Measure) | x
    Measure | oracle_out

    eng.flush()
    # return result
    return [int(qubit) for qubit in x]


def alternating_bits_oracle(eng, qubits, output):
    """
    Marks the solution string 1,0,1,0,...,0,1 by flipping the output qubit,
    conditioned on qubits being equal to the alternating bit-string.

    Args:
        eng (MainEngine): Main compiler engine the algorithm is being run on.
        qubits (Qureg): n-qubit quantum register Grover search is run on.
        output (Qubit): Output qubit to flip in order to mark the solution.
    """
    with Compute(eng):
        All(X) | qubits[1::2]
    with Control(eng, qubits):
        X | output
    Uncompute(eng)


def get_authentication():
    """ Gets the authentication for connecting to the Quantum Inspire API."""
    token = load_account()
    if token is not None:
        return get_token_authentication(token)
    else:
        if QI_EMAIL is None or QI_PASSWORD is None:
            print('Enter email:')
            email = input()
            print('Enter password')
            password = getpass()
        else:
            email, password = QI_EMAIL, QI_PASSWORD
        return get_basic_authentication(email, password)


if __name__ == '__main__':

    # Remote Quantum-Inspire backend #
    authentication = get_authentication()
    qi = QuantumInspireAPI(QI_URL, authentication)
    qi_backend = QIBackend(quantum_inspire_api=qi)

    compiler_engines = restrictedgateset.get_engine_list(one_qubit_gates=qi_backend.one_qubit_gates,
                                                         two_qubit_gates=qi_backend.two_qubit_gates,
                                                         other_gates=qi_backend.three_qubit_gates)
    compiler_engines.extend([ResourceCounter()])
    qi_engine = MainEngine(backend=qi_backend, engine_list=compiler_engines)

    # Run remote Grover search to find a n-bit solution
    result_qi = run_grover(qi_engine, 3, alternating_bits_oracle)
    print("\nResult from the remote Quantum-Inspire backend: {}".format(result_qi))

    # Local ProjectQ simulator backend #
    compiler_engines = restrictedgateset.get_engine_list(one_qubit_gates="any", two_qubit_gates=(CNOT, CZ))
    compiler_engines.append(ResourceCounter())
    local_engine = MainEngine(Simulator(), compiler_engines)

    # Run local Grover search to find a n-bit solution
    result_local = run_grover(local_engine, 3, alternating_bits_oracle)
    print("Result from the local ProjectQ simulator backend: {}\n".format(result_local))
