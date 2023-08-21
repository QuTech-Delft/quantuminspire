from typing import Any, Dict, List

from quantuminspire.sdk.models.circuit import Circuit


def generate_circuit() -> str:
    with Circuit(platform_name="spin-2", program_name="prgm1") as circuit:
        kernel = circuit.init_kernel("new_kernel", 2)
        kernel.hadamard(0)
        kernel.cnot(0, 1)

    return circuit.content


async def execute(qi) -> None:
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
        result = await qi.execute_circuit(circuit, 1024)

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
    import asyncio

    # Run the individual steps for debugging
    print("=== Circuit ===\n", generate_circuit())

    class MockExecuteCircuitResult:
        results = {"00": 0.490234, "11": 0.509766}
        shots_requested = 1024
        shots_done = 1024

    class MockQI:
        async def execute_circuit(self, circuit: str, number_of_shots: int) -> None:
            print(f"circuit:\n {circuit}")
            return MockExecuteCircuitResult()

    print("=== Execute ===\n", asyncio.run(execute(MockQI())))
