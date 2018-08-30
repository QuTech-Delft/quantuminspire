# Quantum Inspire SDK

The software development kit for the Quantum Inspire platform. The SDK consists of

* An API for the Quantum Inspire online platform `QuantumInspireAPI`
* Backends for various other SDKs. These are the IMB Q backend, ...

For more information see https://www.quantum-inspire.com/

### Authors

* Pieter Eendebak


## Installation

For the default installation:

```
pip install .
```

If you want to use another backend, install with (e.g. for the qiskit backend):
```
pip install .[qiskit]
```

Also multiple backends can be installed using one command:
```
pip install .[qiskit,projectq]
```

## Running

For example usage see the Jupyter notebooks in the [docs](docs/) directory.

``` python

from getpass import getpass
from coreapi.auth import BasicAuthentication
from quantuminspire.api import QuantumInspireAPI

print('Enter mail address')
email = input()

print('Enter password')
password = getpass()

server_url = r'https://api.quantum-inspire.com'
authentication = BasicAuthentication(email, password)
qi = QuantumInspireAPI(server_url, authentication)

qasm = '''version 1.0

qubits 2

H q[0]
CNOT q[0], q[1]
display

measure q[0]
'''

backend = qi.get_backend_type(backend_id=1)
result = qi.execute_qasm(qasm, backend, number_of_shots=128)

print(result['histogram'])
```

## Testing

Run all unittests and collect the code coverage using:
```
coverage run --source="./src/quantuminspire" -m unittest discover -s src/tests -t src -v
coverage report -m
```
