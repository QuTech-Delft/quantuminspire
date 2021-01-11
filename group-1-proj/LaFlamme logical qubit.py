import os
from getpass import getpass
from quantuminspire.credentials import load_account, get_token_authentication, get_basic_authentication
from qiskit.tools.visualization import circuit_drawer
import numpy as np
from qiskit.circuit import *
from qiskit import *
from qiskit.circuit.library import *
from quantuminspire.qiskit import QI
QI.set_authentication()

# For the algorithm this source is used: https://arxiv.org/pdf/quant-ph/9602019.pdf, together with
# https://arxiv.org/pdf/1208.4797.pdf to make the usage of gates more clear.
# The middle physical qubit, qubit 2, is used to initialize and readout the state of the logical qubit.


backend_types = ['Spin-2','QX single-node simulator','Starmon-5']
qi_backend = QI.get_backend(backend_types[1])                           #Sets backend type

q = QuantumRegister(5, "q")
c = ClassicalRegister(1, "c")                                           # Only 1 bit for measuring the state of the qubit

qc = QuantumCircuit(q, c, name="Laflamme logical qubit")

qc.h(0)
qc.h(1)
qc.h(3)

multi= QuantumCircuit(1, name= 'pi phase')                              # Creates a new cicuit in which the effect of the multi control/target gate is enclosed
multi.z(0)
multi_gate=multi.to_gate()                                              # Makes a gate out of the circuit

cmulti_z_gate0= multi_gate.control(3)                                   # Makes it a controlled gate, with three controls
cmulti_z_gate1=multi_gate.control(3,ctrl_state='010')                   # Other gate, but also specifies in which state the control qubits should be in
cmulti_z_gate2=multi_gate.control(2)

qc.append(cmulti_z_gate0, [1,2,3,4])                                    # Adds the gates to the existing circuit with the [ control , target ]
qc.append(cmulti_z_gate1, [1,2,3,4])

qc.cx(2,4)

multi= QuantumCircuit(2, name= 'c-x')                                   # Same as before, but this time two qubits are affected by gate
multi.x(0)
multi.x(1)
multi_gate=multi.to_gate()
cmulti_x_gate=multi_gate.control()

qc.append(cmulti_x_gate,[0,2,4])

qc.cx(3,2)

qc.cx(1,4)

qc.append(cmulti_z_gate2, [4,3,2])


########################################## Errors can occur here #######################################################

qc=qc+qc.inverse()                                                      # Decoder is the same as the encoder, so this completes the circuit

qc.measure(q[2],c[0])

print(qc)
circuit_drawer(qc,output='mpl',filename='Circuit drawn')



qi_job = execute(qc, backend=qi_backend, shots=1024)
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