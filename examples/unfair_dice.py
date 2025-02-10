"""Copyright 2024 QuTech (TNO, TU Delft)

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
documentation files (the "Software"), to deal in the Software without restriction, including without limitation the
rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit
persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the
Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE
WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""

# Part of this code comes from ptetools:
# https://github.com/eendebakpt/ptetools/tree/main

# This example tries to match a target distribution with a variational quantum cricuit

from functools import partial
from typing import Any, Dict, List

import numpy as np
from opensquirrel.circuit_builder import CircuitBuilder
from opensquirrel.ir import Bit, Float, Qubit
from opensquirrel.writer import writer
from qi2_shared.hybrid.quantum_interface import ExecuteCircuitResult, QuantumInterface
from qiskit_algorithms.optimizers import SPSA


def counts_to_distr(counts: Dict[str, int]) -> dict[int, float]:
    """Convert Qiskit result counts to a dictionary.

    The dictionary has integers as keys, and pseudo-probabilities as values.
    """
    n_shots = sum(counts.values())
    output_distr = {int(k, 2): v / n_shots for k, v in counts.items()}
    return {k: output_distr[k] for k in sorted(output_distr)}


class AverageDecreaseTermination:
    def __init__(self, N: int, tolerance: float = 0.0):
        """Callback to terminate optimization based the average decrease.

        The average decrease over the last N data points is compared to the specified tolerance.
        The average decrease is determined by a linear fit (least squares) to the data.

        This class can be used as an argument to the Qiskit SPSA optimizer.

        Args:
            N: Number of data points to use
            tolerance: Abort if the average decrease is smaller than the specified tolerance
        """
        self.N = N
        self.tolerance = tolerance
        self.reset()

    @property
    def parameters(self):
        return self._parameters

    @property
    def values(self):
        return self._values

    def reset(self):
        """Reset the data."""
        self._values = []
        self._parameters = []

    def __call__(self, nfev, parameters, value, update, accepted) -> bool:
        """
        Args:
            nfev: Number of evaluations
            parameters: Current parameters in the optimization
            value: Value of the objective function
            update: Update step
            accepted: Whether the update was accepted

        Returns:
            True if the optimization loop should be aborted
        """
        self._values.append(value)
        self._parameters.append(parameters)

        if len(self._values) > self.N:
            last_values = self._values[-self.N :]
            pp = np.polyfit(range(self.N), last_values, 1)
            slope = pp[0] / self.N

            if slope > self.tolerance:
                return True
        return False


# globals

number_of_qubits = 2
m = 2**number_of_qubits
p0 = np.random.random(m) + 0.2
p0 = p0 / np.sum(p0)
target_distribution = {k: p0[k] for k in range(m)}
dt = AverageDecreaseTermination(N=35)
out_distribution = None


def U(builder: CircuitBuilder, q: Qubit, theta: float, phi: float, lamb: float):
    """McKay decomposition of the U gate.

    :param self: circuit object
    :param q: qubit
    :param theta: angle
    :param phi: angle
    :param lamb: angle
    :return: circuit object
    """
    builder.Rz(q, Float(phi))
    builder.Rx(q, Float(-np.pi / 2))
    builder.Rz(q, Float(theta))
    builder.Rx(q, Float(np.pi / 2))
    builder.Rz(q, Float(lamb))
    return builder


def generate_ansatz(params: List[Any]) -> str:
    builder = CircuitBuilder(qubit_register_size=number_of_qubits, bit_register_size=number_of_qubits)
    U(builder, Qubit(0), *params[0:3])
    U(builder, Qubit(1), *params[3:6])
    builder.CZ(Qubit(0), Qubit(1))
    U(builder, Qubit(0), *params[6:9])
    U(builder, Qubit(1), *params[9:12])
    for ii in range(number_of_qubits):
        builder.measure(Qubit(ii), Bit(ii))

    return writer.circuit_to_string(builder.to_circuit())


def objective_function(params: List[Any], qi: QuantumInterface, target_distribution: Dict[int, float], nshots=None):
    """Compares the output distribution of our circuit with parameters `params` to the target distribution."""
    cqasm = generate_ansatz(params)
    execute_result = qi.execute_circuit(cqasm, nshots)
    # Convert the result to a dictionary with probabilities
    output_distr = counts_to_distr(execute_result.results)
    # Calculate the cost as the distance between the output
    # distribution and the target distribution
    cost = sum(abs(target_distribution.get(i, 0) - output_distr.get(i, 0)) for i in range(2**number_of_qubits))
    return cost


def execute(qi: QuantumInterface) -> None:
    global out_distribution

    optimizer = SPSA(maxiter=100, callback=None, termination_checker=dt)

    F = partial(objective_function, qi=qi, target_distribution=target_distribution, nshots=2000)

    number_of_parameters = 12
    initial_parameters = 0.85 * np.random.rand(
        number_of_parameters,
    )
    result = optimizer.minimize(fun=F, x0=initial_parameters)

    # Run the circuit again with optimized parameters
    cqasm = generate_ansatz(result.x)
    out_distribution = counts_to_distr(qi.execute_circuit(cqasm, 2000).results)


def finalize(list_of_measurements: List[ExecuteCircuitResult]) -> Dict[str, Any]:
    global out_distribution

    return {"avg_decrease": dt.values, "target_distribution": target_distribution, "out_distribution": out_distribution}
