"""
This example is copied from https://github.com/ProjectQ-Framework/ProjectQ
and is covered under the Apache 2.0 license.
"""
import math
from getpass import getpass

from coreapi.auth import BasicAuthentication
from projectq import MainEngine
from projectq.backends import ResourceCounter, Simulator
from projectq.cengines import ManualMapper
from projectq.meta import Compute, Control, Loop, Uncompute
from projectq.ops import CNOT, CZ, All, H, Measure, X, Z, Toffoli
from projectq.setups import restrictedgateset

from quantuminspire.api import QuantumInspireAPI
from quantuminspire.projectq.backend_qx import QIBackend


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


# %% Run with local ProjectQ simulator backend

if __name__ == "__main__":
    eng = MainEngine()  # use default compiler engine

    compiler_engines = restrictedgateset.get_engine_list(one_qubit_gates="any", two_qubit_gates=(CNOT, CZ))
    resource_counter = ResourceCounter()
    compiler_engines += [resource_counter]

    # make the compiler and run the circuit on the simulator backend
    eng = MainEngine(Simulator(), compiler_engines)

    # run Grover search to find a n-bit solution
    print(run_grover(eng, 3, alternating_bits_oracle))
    print(resource_counter)


# %% Run with remote Quantum-Inspire backend

if __name__ == "__main__":
    if 'password' not in vars().keys():
        print('Enter email:')
        email = input()
        print('Enter password')
        password = getpass()

    authentication = BasicAuthentication(email, password)
    qi = QuantumInspireAPI(r'https://api.quantum-inspire.com/', authentication)

    backend_type = qi.get_default_backend_type()

    compiler_engines = restrictedgateset.get_engine_list(one_qubit_gates="any", two_qubit_gates=(CNOT, CZ, Toffoli))
    compiler_engines = [ManualMapper(lambda ii: ii)] + compiler_engines
    resource_counter = ResourceCounter()
    compiler_engines += [resource_counter]

    qi_backend = QIBackend(quantum_inspire_api=qi, backend_type=backend_type, perform_execution=True)
    # create a default compiler (the back-end is a simulator)
    eng = MainEngine(backend=qi_backend, engine_list=compiler_engines)
    print(run_grover(eng, 3, alternating_bits_oracle))

    # The cqasm generated by the backend can be retrieved with: print(qi_backend.cqasm())
