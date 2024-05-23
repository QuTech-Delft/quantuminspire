from pathlib import Path
from typing import Any, Dict, List

from opensquirrel.squirrel_ir import Qubit

from quantuminspire.sdk.models.circuit import Circuit
from quantuminspire.sdk.models.hybrid_algorithm import HybridAlgorithm
from quantuminspire.util.api.local_backend import LocalBackend
from quantuminspire.util.api.quantum_interface import QuantumInterface


def generate_circuit() -> str:
    with Circuit(platform_name="spin-2", program_name="prgm1", number_of_qubits=2) as circuit:
        circuit.ir.H(Qubit(0))
        circuit.ir.CNOT(Qubit(0), Qubit(1))

    return circuit.content


def execute(qi: QuantumInterface) -> None:
    """Run the classical part of the Hybrid Quantum/Classical Algorithm.

    Args:
        qi: A QuantumInterface instance that can be used to execute quantum circuits

    The qi object has a single method called execute_circuit, its interface is described below:

    qi.execute_circuit args:
        circuit: a string representation of a quantum circuit
        number_of_shots: how often to execute the circuit

    qi.execute_circuit return value:
        The results of executing the quantum circuit, this is an object with the following attributes
            results: The results from iteration n-1.
            shots_requested: The number of shots requested by the user for the previous iteration.
            shots_done: The number of shots actually run.
    """
    for i in range(1, 5):
        circuit = generate_circuit()
        result = qi.execute_circuit(circuit, 1024)

        print(result.results)
        print(result.shots_requested)
        print(result.shots_done)


def finalize(list_of_measurements: Dict[int, List[Any]]) -> Dict[str, Any]:
    """Aggregate the results from all iterations into one final result.

    Args:
        list_of_measurements: List of all results from the previous iterations.

    Returns:
        A free-form result, with a `property`: `value` structure. Value can
        be everything serializable.
    """
    print(list_of_measurements)
    return {"results": list_of_measurements}


if __name__ == "__main__":
    # Run the individual steps for debugging
    print("=== Circuit ===\n", generate_circuit())

    algorithm = HybridAlgorithm("test", "test")
    algorithm.read_file(Path(__file__))

    local_backend = LocalBackend()
    job_id = local_backend.run(algorithm, 0)
    results = local_backend.get_results(job_id)

    print("=== Execute ===\n", results)
