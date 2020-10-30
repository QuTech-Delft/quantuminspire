from src.run import generate_sat_qasm, execute_sat_qasm
from quantuminspire.api import QuantumInspireAPI
from quantuminspire.credentials import load_account, get_token_authentication, get_basic_authentication
import os
from getpass import getpass

QI_EMAIL = os.getenv('QI_EMAIL')
QI_PASSWORD = os.getenv('QI_PASSWORD')
QI_URL = os.getenv('API_URL', 'https://api.quantum-inspire.com/')


def get_authentication():
    """ Gets the authentication for connecting to the Quantum Inspire API."""
    token = load_account()
    if token is not None:
        return get_token_authentication(token)
    else:
        if QI_EMAIL is None or QI_PASSWORD is None:
            print('Enter email:')
            email = input()
            print('Enter password')
            password = getpass()
        else:
            email, password = QI_EMAIL, QI_PASSWORD
        return get_basic_authentication(email, password)


# Authenticate, create project and define backend
name = 'SAT_Problem'
authentication = get_authentication()
qi = QuantumInspireAPI(QI_URL, authentication, project_name=name)
backend = qi.get_backend_type_by_name(
    'QX single-node simulator')  # if the project already exists in My QI, the existing backend will be used and this line will not overwrite the backend information.
shot_count = 512

# define SAT problem
boolean_expr = "(a and not(b) and c and d) or (not(a) and b and not(c) and d)"

# choose variables; see src.run.generate_sat_qasm() for details.
# recommended settings for a simulator
cnot_mode = "normal"
sat_mode = "reuse qubits"
apply_optimization_to_qasm = False
connected_qubit = None

# # recommended settings for Starmon-5. As of now, any sat problem involving more than one variable will contain too many gates,
# # and decoherence will occur. If you try this, be sure to use a boolean_expr and sat_mode that initiates a total of 5 qubits.
# cnot_mode = "no toffoli"
# sat_mode = "reuse qubits"
# apply_optimization_to_qasm = False
# connected_qubit = '2'


# generate the qasm code that will solve the SAT problem
qasm, _, qubit_count, data_qubits = generate_sat_qasm(expr_string=boolean_expr, cnot_mode=cnot_mode, sat_mode=sat_mode,
                                                      apply_optimization=apply_optimization_to_qasm,
                                                      connected_qubit=connected_qubit)

print(qasm)

# execute the qasm code and show the results
execute_sat_qasm(qi=qi, qasm=qasm, shot_count=shot_count, backend=backend, qubit_count=qubit_count,
                 data_qubits=data_qubits, plot=True)
