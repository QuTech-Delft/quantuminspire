from typing import Any, Dict, List

from quantuminspire.sdk.models.circuit import Circuit


def generate_circuit() -> str:
    with Circuit(platform_name="spin-2", program_name="prgm1") as circuit:
        kernel = circuit.init_kernel("new_kernel", 2)
        kernel.hadamard(0)
        kernel.cnot(0, 1)

    return circuit.content


def initialize() -> str:
    """Generate the first iteration of the classical part of the Hybrid Quantum/Classical Algorithm.

    Returns:
        cQASM string representing the test algorithm.
    """
    return generate_circuit()


def execute(results: Dict[str, float], shots_requested: int, shots_done: int) -> str:
    """Run the next 2-n iterations of the classical part of the Hybrid Quantum/Classical Algorithm.

    Args:
        results: The results from iteration n-1.
        shots_requested: The number of shots requested by the user for the previous iteration.
        shots_done: The number of shots actually run.

    Returns:
        cQASM string representing the test algorithm.
    """
    print(results)
    print(shots_requested)
    print(shots_done)
    return generate_circuit()


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
