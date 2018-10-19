# Quantum Inspire SDK

*Note: this is an initial alpha release of the SDK, it is still under
heavy development.*

The Quantum Inspire platform allows to execute quantum algorithms using the cQASM language. 

The software development kit (SDK) for the Quantum Inspire platform consists of:

* An API for the [Quantum Inspire](https://www.quantum-inspire.com/) platform (the QuantumInspireAPI class);
* Backends for:
  * the [ProjectQ SDK](https://github.com/ProjectQ-Framework/ProjectQ);
  * the [QisKit SDK](https://qiskit.org/).

For more information on Quantum Inspire see
[https://www.quantum-inspire.com/](https://www.quantum-inspire.com/). Detailed information
on cQASM can be found in the Quantum Inspire
[knowledge base](https://www.quantum-inspire.com/kbase/advanced-guide/).


## Installation

The source for the SDK can be found at Github. For the default installation execute:

```
$ pip install .
```

This does not install ProjectQ or QisKit, but will install the Quantum Inspire backends for
those projects.

If you want to include a specific SDK as a dependency, install with
(e.g. for the ProjectQ backend):

```
$ pip install .[projectq]
```

To install both ProjectQ as well as QisKit as a dependency:

```
$ pip install .[qiskit,projectq]
```

## Running

For example usage see the python scripts and Jupyter notebooks in the [docs/](docs/) directory.

For example, to run the ProjectQ example notebook:

```
cd docs
jupyter notebook example_projectq.ipynb
```

Or to perform Grover's with the ProjectQ backend from a Python script:

```
cd docs
python example_projectq_grover.py
```

It is also possible to use the API through the QuantumInspireAPI object
directly. This is for advanced users that really know what they are
doing. The intention of the QuantumInspireAPI class is that it is used
as a thin layer between existing SDK's such as ProjectQ and Qiskit,
and is not primarily meant for general use. You may want to explore this
if you intend to write a new backend for an existing SDK.

A simple example to perform entanglement between two qubits by using the
API wrapper directly:

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

## Known issues

* Authentication for the Quantum Inspire platform is currently password only; this will change
to API-token based authentication in the near future;
* There is no method to submit an algorithm and retrieve the results at a later moment. 
* Qiskit 0.6.0 compatibility is not complete
* It is not possible to simulate algorithms that do not use full state projection
* Known issues and common questions regarding the Quantum Inspire platform can be found in the [FAQ](https://www.quantum-inspire.com/faq/).
 
## Bug reports

Please submit bug-reports [on the github issue tracker](https://github.com/qutech-sd/SDK/issues).

## Testing

Run all unittests and collect the code coverage using:

```
coverage run --source="./src/quantuminspire" -m unittest discover -s src/tests -t src -v
coverage report -m
```
