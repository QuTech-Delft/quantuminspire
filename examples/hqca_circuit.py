from typing import Any, Dict, List

from opensquirrel.circuit_builder import CircuitBuilder
from opensquirrel.ir import Bit, Qubit
from opensquirrel.writer import writer
from qi2_shared.hybrid.quantum_interface import QuantumInterface


def generate_circuit() -> str:
    builder = CircuitBuilder(qubit_register_size=2, bit_register_size=2)
    builder.H(Qubit(0))
    builder.CNOT(Qubit(0), Qubit(1))
    builder.measure(Qubit(0), Bit(0))
    builder.measure(Qubit(1), Bit(1))

    return writer.circuit_to_string(builder.to_circuit())


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
