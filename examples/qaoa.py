"""Example Hybrid Quantum/Classical Algorithm for Quantum Inspire 2.

The algorithm is the Quantum Approximate Optimization Algorithm, as documented on
https://www.quantuminspire.com/kbase/qaoa/
"""

from typing import Any, Dict, List

import networkx as nx
import numpy as np
from networkx import Graph

from quantuminspire.sdk.models.circuit import Circuit

MATRIX = np.matrix([[0, 1], [1, 0]])
GRAPH = nx.from_numpy_matrix(MATRIX)
positions = nx.circular_layout(GRAPH)
GRAPH.pos = positions
P = 2


def maxcut_obj(meas: str, graph: Graph) -> int:
    """Define the objective function.

    Args:
        meas: The measured bit string.
        graph: The original graph.

    Returns:
        The cut.
    """
    cut = 0
    for i, j in graph.edges():
        if meas[i] != meas[j]:
            # the edge is cut, negative value in agreement with the optimizer (which is a minimizer)
            cut -= 1
    return cut


def compute_maxcut_energy(counts: Dict[str, int], graph: Graph) -> float:
    """Estimate the expectation value based on the circuit output.

    Args:
        counts: The measured bit strings and their counts.
        graph: The original graph.

    Returns:
        The maxcut energy.
    """
    energy = 0
    total_counts = 0
    for meas, meas_count in counts.items():
        obj_for_meas = maxcut_obj(meas, graph)
        energy += obj_for_meas * meas_count
        total_counts += meas_count
    return energy / total_counts


def get_qaoa_circuit(graph: Graph, beta: np.ndarray, gamma: np.ndarray) -> str:
    """Generate the cQASM circuit.

    Args:
        graph: graph: The original graph.
        beta: an angle.
        gamma: another angle.

    Returns:
        cQASM string representing the QAOA algorithm.
    """
    with Circuit(platform_name="spin-2", program_name="qaoa") as circuit:
        init_kernel = circuit.init_kernel("initialize", graph.number_of_nodes())
        for i in graph.nodes:
            init_kernel.prepz(i)
        for i in graph.nodes:
            init_kernel.hadamard(i)

        for i in range(P):
            ug_kernel = circuit.init_kernel(f"U_gamma_{i + 1}", graph.number_of_nodes())
            ug_kernel.cnot(0, 1)
            ug_kernel.rz(1, 2 * gamma[i])
            ug_kernel.cnot(0, 1)

            ub_kernel = circuit.init_kernel(f"U_beta_{i + 1}", graph.number_of_nodes())
            for j in graph.nodes():
                ub_kernel.rx(j, 2 * beta[i])

        final_kernel = circuit.init_kernel("finalize", graph.number_of_nodes())
        for i in graph.nodes():
            final_kernel.measure(i)

    return circuit.qasm


def initialize() -> str:
    """Generate the first iteration of the classical part of the Hybrid Quantum/Classical Algorithm.

    Returns:
        cQASM string representing the QAOA algorithm.
    """
    beta = np.asarray([0.98318806, 2.35354757])
    gamma = np.asarray([1.12923927, 2.26709203])
    return get_qaoa_circuit(GRAPH, beta, gamma)


def execute(results: Dict[str, float], shots_requested: int, shots_done: int) -> str:
    """Run the next 2-n iterations of the classical part of the Hybrid Quantum/Classical Algorithm.

    Args:
        results: The results from iteration n-1.
        shots_requested: The number of shots requested by the user for the previous iteration.
        shots_done: The number of shots actually run.

    Returns:
        cQASM string representing the QAOA algorithm.
    """
    # Lower and upper bounds: beta \in {0, pi}, gamma \in {0, 2*pi}
    print(f"Shots requested: {shots_requested}")
    print(f"Shots done: {shots_done}")
    print(results.items())
    counts = {k: int(v * shots_done) for k, v in results.items()}
    compute_maxcut_energy(counts, GRAPH)

    beta = np.random.rand(P) * np.pi
    gamma = np.random.rand(P) * 2 * np.pi
    return get_qaoa_circuit(GRAPH, beta, gamma)


def finalize(list_of_measurements: Dict[int, List[Any]]) -> Dict[str, Any]:
    """Aggregate the results from all iterations into one final result.

    Args:
        list_of_measurements: List of all results from the previous iterations.

    Returns:
        A free-form result, with a `property`: `value` structure. Value can
        be everything serializable.
    """
    print(list_of_measurements)
    return {}


if __name__ == "__main__":
    # Run the individual steps for debugging
    print("=== Ansatz ===\n", initialize())
    print("=== Next iteration ===\n", execute({"01": 0.5, "10": 0.5}, 1024, 1024))
