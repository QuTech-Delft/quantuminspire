# (H2) Hydrogen molecuole ground state energy determined using VQE with a UCCSD-ansatz function.
# Compared with Hartee-Fock energies and with energies calculated by NumPyMinimumEigensolver
# This script is based on the Qiskit Chemistry tutorials
import json
import warnings
from dataclasses import dataclass
from typing import Any, Callable, Dict, List

from qiskit.primitives import BackendEstimator, Estimator
from qiskit_algorithms import NumPyMinimumEigensolverResult, VQEResult
from qiskit_algorithms.minimum_eigensolvers import VQE, NumPyMinimumEigensolver
from qiskit_algorithms.optimizers import COBYLA
from qiskit_nature.second_q.circuit.library import UCCSD, HartreeFock
from qiskit_nature.second_q.drivers import PySCFDriver
from qiskit_nature.second_q.mappers import JordanWignerMapper, ParityMapper

from quantuminspire.sdk.qiskit.backend import QuantumInspireBackend
from quantuminspire.util.api.quantum_interface import QuantumInterface


@dataclass
class _GroundStateEnergyResults:
    result: VQEResult | NumPyMinimumEigensolverResult
    nuclear_repulsion_energy: float


def calculate_H0(backend: QuantumInspireBackend, distance: float = 0.735) -> _GroundStateEnergyResults:

    mapper = ParityMapper(num_particles=(1, 1))
    molecule = f"H 0.0 0.0 0.0; H 0.0 0.0 {distance}"
    driver = PySCFDriver(molecule)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=UserWarning)
        es_problem = driver.run()

    fermionic_op = es_problem.hamiltonian.second_q_op()
    qubit_op = mapper.map(fermionic_op)
    n_particles = es_problem.num_particles
    n_spatial_orbitals = es_problem.num_spatial_orbitals

    nuclear_repulsion_energy = es_problem.nuclear_repulsion_energy

    initial_state = HartreeFock(n_spatial_orbitals, n_particles, mapper)
    ansatz = UCCSD(n_spatial_orbitals, n_particles, mapper, initial_state=initial_state)

    optimizer = COBYLA(maxiter=1)  # 10 iterations take two minutes
    estimator = BackendEstimator(backend=backend)

    algo = VQE(estimator, ansatz, optimizer)
    result = algo.compute_minimum_eigenvalue(qubit_op)

    print(f"{distance=}: nuclear_repulsion_energy={nuclear_repulsion_energy}, eigenvalue={result.eigenvalue}")
    return _GroundStateEnergyResults(result, nuclear_repulsion_energy)


def execute(qi: QuantumInterface) -> None:
    c = calculate_H0(backend=QuantumInspireBackend(qi))
    print(c)


def finalize(list_of_measurements: Dict[int, List[Any]]) -> Dict[str, Any]:
    return {"measurements": list_of_measurements}
