"""Example Hybrid Quantum/Classical Algorithm for Quantum Inspire.

The algorithm is the Quantum Approximate Optimization Algorithm, as documented on
https://www.quantuminspire.com/kbase/qaoa/
"""

from typing import Any, Callable, Dict, List

import networkx as nx
import numpy as np
from networkx import Graph
from opensquirrel.circuit_builder import CircuitBuilder
from opensquirrel.ir import Bit, Float, Qubit
from opensquirrel.writer import writer
from scipy.optimize import Bounds, minimize

MATRIX = np.matrix([[0, 1], [1, 0]])
GRAPH = nx.from_numpy_array(MATRIX)
positions = nx.circular_layout(GRAPH)
GRAPH.pos = positions
P = 2
SHOTS = 1024
MAX_ITER = 100
APPROXIMATED_MAXCUT_SIZE = None


def cut_size(measurement: str, graph: Graph) -> int:
    """Returns the size of the cut.

    Args:
        measurement: The measured bit string.
        graph: The original graph.

    Returns:
        The cut.
    """
    cut = 0
    end = len(measurement) - 1
    for i, j in graph.edges():
        if measurement[end - i] != measurement[end - j]:
            cut += 1
    return cut


def compute_maxcut_energy(counts: Dict[str, int], graph: Graph) -> float:
    """Compute the maxcut energy based on the results of running the quantum circuit. This is just the negative of the
    average cut size. Since we are going to use the minimize function from scipy.

    Args:
        counts: The measured qubit states and their counts.
        graph: The original graph.

    Returns:
        The maxcut energy.
    """
    energy = 0
    total_counts = 0
    for measurement, count in counts.items():
        size = cut_size(measurement, graph)
        # we use a minimizer so the energy should lower for bigger cuts
        energy -= size * count
        total_counts += count
    return energy / total_counts


def qaoa_circuit(graph: Graph, beta: np.ndarray, gamma: np.ndarray) -> str:
    """Generate the cQASM circuit.

    Args:
        graph: The original graph.
        beta: an array of angles.
        gamma: another array of angles.

    Returns:
        cQASM string representing the quantum circuit used to compute the energies in the QAOA algorithm.
    """
    builder = CircuitBuilder(qubit_register_size=2, bit_register_size=2)
    for i in graph.nodes:
        builder.H(Qubit(i))

    for i in range(P):
        for edge in graph.edges():
            builder.CNOT(Qubit(edge[0]), Qubit(edge[1]))
            builder.Rz(Qubit(edge[1]), Float(2 * gamma[i]))
            builder.CNOT(Qubit(edge[0]), Qubit(edge[1]))

        for j in graph.nodes():
            builder.Rx(Qubit(j), Float(2 * beta[i]))

    for i in graph.nodes:
        builder.measure(Qubit(i), Bit(i))

    return writer.circuit_to_string(builder.to_circuit())


def generate_objective_function(qi, graph) -> Callable:
    """This takes as input a graph and returns the objective function for scipy to minimize."""

    def f(theta):
        """The actual function to minimize.

        The first half of theta are the betas, the second half are the gammas.
        """
        beta = theta[:P]
        gamma = theta[P:]
        circuit = qaoa_circuit(graph, beta, gamma)

        result = qi.execute_circuit(circuit, SHOTS)
        counts = result.results
        energy = compute_maxcut_energy(counts, graph)
        # right now the platform has no way to make intermediate results
        # available to the finalize function so we do it ourselves.
        # qi.results[f"custom result: {len(qi.results)}"] = [energy, counts]
        # return the energy
        return energy

    return f


def execute(qi) -> None:
    """Run the entire qaoa alogrithm.

    Args:
        results: The results from iteration n-1.
        shots_requested: The number of shots requested by the user for the previous iteration.
        shots_done: The number of shots actually run.

    Returns:
        cQASM string representing the QAOA algorithm.
    """
    # right now the platform has no documented way of passing information from the execute function
    # to the finalize function, one way like it is done now is by storing it in a global variable
    # the other way would be to add it to qi.results
    global APPROXIMATED_MAXCUT_SIZE

    lb = np.zeros(2 * P)
    ub = np.hstack([np.full(P, np.pi), np.full(P, 2 * np.pi)])
    bounds = Bounds(lb, ub)
    initial_point = np.random.uniform(lb, ub, 2 * P)
    f = generate_objective_function(qi, GRAPH)
    result = minimize(f, initial_point, method="COBYLA", bounds=bounds, options={"maxiter": MAX_ITER})
    APPROXIMATED_MAXCUT_SIZE = -result["fun"]


def finalize(list_of_measurements: Dict[int, List[Any]]) -> Dict[str, Any]:
    """Aggregate the results from all iterations into one final result.

    Args:
        list_of_measurements: List of all results from the previous iterations.

    Returns:
        A free-form result, with a `property`: `value` structure. Value can
        be everything serializable.
    """
    print(list_of_measurements)
    return {"maxcut_size": APPROXIMATED_MAXCUT_SIZE, "measurements": list_of_measurements}


if __name__ == "__main__":
    # Run the individual steps for debugging

    beta = np.asarray([0.98318806, 2.35354757])
    gamma = np.asarray([1.12923927, 2.26709203])
    print("=== Qaoa circuit ===", qaoa_circuit(GRAPH, beta, gamma))
    # Now the beginning of the circuit always looks like
    """
    # Generated by OpenQL 0.11.1 for program qaoa
    version 1.0

    qubits 10
    """
    # independently of the actual qubits used.
    # this also means that the results look like
    """
    {
      "0000000000": 128.0,
      "0000000001": 203.0,
      "0000000010": 203.0,
      "0000000011": 490.0
    }
    """
    # even if we only use 2 qubits.
    # also note that 'endianness' of the results is the reverse of the endianness in the cqasm file
