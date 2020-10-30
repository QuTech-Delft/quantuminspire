from src.sat_utilities import *
from src.optimizer import *
import math


def generate_sat_qasm(expr_string, cnot_mode, sat_mode, apply_optimization=True, connected_qubit=None):
    """
    Generate the QASM needed to evaluate the SAT problem for a given boolean expression.

    Args:
        expr_string: A boolean expression as a string
        cnot_mode: The mode for CNOTs. 'normal' and 'no toffoli' are verified to be working. 'crot' and 'fancy cnot' are experimental.
              - normal: use toffoli gates and ancillary qubits for max speed
              - no toffoli: same as normal, but replace toffoli gates for 2-gate equivalent circuits. uses ancillary qubits. This mode must be used if using a backend that doesn't support toffoli gates, like starmon-5.
              - crot: no ancillary qubits or toffoli gates, but scales with 3^n gates for n bits
              - fancy cnot: no ancillary qubits or toffoli gates, scales 2^n
        sat_mode: The mode for the SAT solving circuit:
              - reuse gates: use minimal amount of gates
              - reuse qubits: use minimal amount of ancillary qubits
        apply_optimization: Whether to apply the optimization algorithm to our generated QASM, saving ~20-50% lines of code
        connected_qubit: This functionallity is meant for backends in which not all qubits are connected to each other.
        For example, in Starmon-5, only the third qubit is connected to all other qubits. In order to make the qasm work on
        this backend, connected_qubit='2' should be given as argument. Qubits are then swapped during the algorithm such that every gate is
        between the connected_qubit and another one. This function can only be used in combination with
        cnot_mode='no toffoli', to ensure no three qubit gates are present.
              - None: do not swap any gates
              - '2': swap qubits to ensure all gates involve qubit 2.

    Returns: A tuple of the following values:
        - qasm: The QASM representing the requested Grover search
        - line count: The total number of parallel lines that is executed (including grover loops)
        - qubit count: The total number of qubits required
        - data qubits: The number of data qubits
    """

    algebra = boolean.BooleanAlgebra()
    expr = algebra.parse(expr_string)

    control_names = sorted(list(expr.symbols), reverse=True)

    # note that the number of data qubits also includes an extra bit which must be 1 for the algorithm to succeed
    data_qubits = len(control_names) + 1

    expr = split_expression_evenly(expr.simplify())

    if sat_mode == "reuse gates":
        oracle_qasm, _, last_qubit_index = generate_sat_oracle_reuse_gates(expr, control_names, is_toplevel=True,
                                                                           mode=cnot_mode)
    elif sat_mode == "reuse qubits":
        oracle_qasm, _, last_qubit_index = generate_sat_oracle_reuse_qubits(expr, control_names, [], is_toplevel=True,
                                                                            mode=cnot_mode)
    else:
        raise ValueError("Invalid SAT mode: {} instead of 'reuse gates' or 'reuse qubits'".format(sat_mode))

    qubit_count = last_qubit_index + 1

    # some modes may require many ancillary qubits for the diffusion operator!
    if cnot_mode in ["normal", "no toffoli"]:
        qubit_count = max(qubit_count, data_qubits * 2 - 3)

    qasm = "version 1.0\n" \
           "qubits {}\n".format(qubit_count)

    # initialisation
    qasm += fill("H", data_qubits)

    # looping grover
    iterations = int(math.pi * math.sqrt(2 ** data_qubits - 1) / 4)
    qasm += ".grover_loop({})\n".format(iterations)

    qasm += oracle_qasm + "\n"

    # diffusion
    qasm += fill("H", data_qubits)
    qasm += fill("X", data_qubits)
    qasm += cnot_pillar(cnot_mode, data_qubits)
    qasm += fill("X", data_qubits)
    qasm += fill("H", data_qubits)

    if apply_optimization:
        qasm = apply_optimizations(qasm, qubit_count, data_qubits)

    if connected_qubit is not None:
        qasm = swap_qubits(qasm=qasm, cnot_mode=cnot_mode, apply_optimization=apply_optimization,
                           connected_qubit=connected_qubit)

    # remove blank lines
    qasm_lines = qasm.split("\n")
    qasm_lines = list(filter(lambda x: x not in ["", "{}", " "], qasm_lines))
    qasm = "\n".join(qasm_lines).replace("\n\n", "\n")

    return qasm + "\n.do_measurement\nmeasure_all", iterations * qasm.count("\n"), qubit_count, data_qubits


def execute_sat_qasm(qi, qasm, shot_count, backend, qubit_count, data_qubits, plot):
    """
    Execute the given QASM code and parse the results as though we are evaluating a SAT problem.

    Args:
        qi: An instance of the Quantum Inspire API
        qasm: The qasm program
        shot_count: The number of shots to execute on the circuit
        backend: An instance a QI API backend
        qubit_count: The total number of qubits used in the qasm program
        data_qubits: The number of qubits used by Grover's Algorithm (aka non-ancillary)
        plot: Whether to plot the results of this run

    Returns: A tuple of the following values:
        - histogram_list: a list of pairs, specifying a name and probability, as returned from QI
        - likely_solutions: a list of bit strings, all of which seem to solve the given formula, according to grover
        - runtime: The execution time on the QI backend
    """

    line_count = qasm.count("\n")
    print("Executing QASM code ({} instructions, {} qubits, {} shots)".format(line_count, qubit_count, shot_count))
    result = qi.execute_qasm(qasm, backend_type=backend, number_of_shots=shot_count)
    runtime = result["execution_time_in_seconds"]
    print("Ran on simulator in {} seconds".format(str(runtime)[:5]))

    if qubit_count > 15:
        print("No plot because of large qubit count")
        histogram_list = interpret_results(result, qubit_count, data_qubits, False)
    else:
        histogram_list = interpret_results(result, qubit_count, data_qubits, plot)

    likely_solutions = []
    print("Interpreting SAT results:")
    highest_prob = max(map(lambda _: _[1], histogram_list))
    for h in histogram_list:
        # remove all ancillaries and the first data bit
        name, prob = h[0][-data_qubits + 1:], h[1]
        if prob > highest_prob / 2:
            print("{} satisfies the SAT problem".format(name))
            likely_solutions.append(name)

    return histogram_list, likely_solutions, runtime
