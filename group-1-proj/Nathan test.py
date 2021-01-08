import os
from getpass import getpass
from quantuminspire.credentials import load_account, get_token_authentication, get_basic_authentication


from qiskit.circuit import *
from qiskit import *

from quantuminspire.qiskit import QI

QI.set_authentication()                                                 # Sets authentication

backend_types = ['Spin-2','QX single-node simulator','Starmon-5']
qi_backend = QI.get_backend(backend_types[1])

q = QuantumRegister(9, "q")
c = ClassicalRegister(9, "c")

qc = QuantumCircuit(q, c, name="Shor logical qubit")                    # Creates quantum circuit with quantum,clasical registers

qc.cnot(q[0],q[3])
qc.cnot(q[0],q[6])

qc.h(q[0])
qc.h(q[3])
qc.h(q[6])

qc.cnot(q[0],q[1])
qc.cnot(q[0],q[2])

qc.cnot(q[3],q[4])
qc.cnot(q[3],q[5])

qc.cnot(q[6],q[7])
qc.cnot(q[6],q[8])

qc0=qc

qc1= QuantumCircuit(q, c, name="Shor logical qubit")

qc1.cnot(q[0],q[1])
qc1.cnot(q[0],q[2])

qc1.cnot(q[3],q[4])
qc1.cnot(q[3],q[5])

qc1.cnot(q[6],q[7])
qc1.cnot(q[6],q[8])

qc1.ccx(1,2,0)
qc1.ccx(4,5,3)
qc1.ccx(7,8,6)

qc1.h(q[0])
qc1.h(q[3])
qc1.h(q[6])

qc1.cnot(q[0],q[3])
qc1.cnot(q[0],q[6])

qc1.ccx(6,3,0)

qc=qc0+qc1

qc.draw(output='mpl',filename='Circuit drawn')

qc.measure(q,c)



qi_job = execute(qc, backend=qi_backend, shots=100)
qi_result = qi_job.result()
histogram = qi_result.get_counts(qc)
print("\nResult from the remote Quantum Inspire backend:\n")
print('State\tCounts')
[print('{0}\t{1}'.format(state, counts)) for state, counts in histogram.items()]

print("\nResult from the local Qiskit simulator backend:\n")
backend = BasicAer.get_backend("qasm_simulator")
job = execute(qc, backend=backend, shots=1024)
result = job.result()
print(result.get_counts(qc))