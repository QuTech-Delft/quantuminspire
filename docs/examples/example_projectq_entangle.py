"""
This example is copied from https://github.com/ProjectQ-Framework/ProjectQ
and is covered under the Apache 2.0 license.
"""
import os

from projectq import MainEngine
from projectq.backends import ResourceCounter
from projectq.ops import CNOT, H, Measure, All
from projectq.setups import restrictedgateset

from quantuminspire.api import QuantumInspireAPI
from quantuminspire.credentials import get_authentication
from quantuminspire.projectq.backend_qx import QIBackend

QI_URL = os.getenv('API_URL', 'https://api.quantum-inspire.com/')


project_name = 'ProjectQ-entangle'
authentication = get_authentication()
qi_api = QuantumInspireAPI(QI_URL, authentication, project_name=project_name)
qi_backend = QIBackend(quantum_inspire_api=qi_api)

compiler_engines = restrictedgateset.get_engine_list(one_qubit_gates=qi_backend.one_qubit_gates,
                                                     two_qubit_gates=qi_backend.two_qubit_gates)
compiler_engines.extend([ResourceCounter()])
engine = MainEngine(backend=qi_backend, engine_list=compiler_engines)

qubits = engine.allocate_qureg(2)
q1 = qubits[0]
q2 = qubits[1]

H | q1
CNOT | (q1, q2)
All(Measure) | qubits

engine.flush()

print('\nMeasured: {0}'.format([int(q) for q in qubits]))
print('Probabilities {0}'.format(qi_backend.get_probabilities(qubits)))
