"""Example usage of the Quantum Inspire backend with the QisKit SDK.

A simple example that demonstrates how to use the SDK to create
a circuit to create a Bell state, and simulate the circuit on
Quantum Inspire.

For documentation on how to use QisKit we refer to
[https://qiskit.org/](https://qiskit.org/).

Specific to Quantum Inspire is the creation of the QuantumInspireAPI
instance, which is used to instantiate a QiSimulatorPy backend later
on that is used to execute the circuit.

"""

from getpass import getpass
from requests.auth import HTTPBasicAuth
from quantuminspire import QuantumInspireAPI
import qiskit
from qiskit import QuantumCircuit, ClassicalRegister, QuantumRegister, QISKitError, QuantumProgram
from quantuminspire.qiskit.qiskit_backend import QiSimulatorPy
from qiskit import available_backends, execute, register, get_backend, compile


if 'password' not in vars().keys():
    print('Enter username')
    username = input()
    print('Enter password')
    password = getpass()

auth = HTTPBasicAuth(username, password)
qi = QuantumInspireAPI(server=r'https://api.quantum-inspire.com/', auth=auth)

QPS_SPECS = {
    'circuits': [{
        'name': 'entangle',
        'quantum_registers': [
            {'name': 'q', 'size': 2},
        ],
        'classical_registers': [
            {'name': 'b', 'size': 2},
        ]}]
}

program = QuantumProgram(specs=QPS_SPECS)
q = program.get_quantum_register('q')
b = program.get_classical_register('b')
circuit = program.get_circuit('entangle')

circuit.h(q[0])
circuit.cx(q[0], q[1])
circuit.measure(q[0], b[0])
circuit.measure(q[1], b[1])

backend = QiSimulatorPy(qi_api=qi)
result = execute(circuit, backend)

print(result.get_counts())
