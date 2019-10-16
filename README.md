# Quantum Inspire SDK

*Note: this SDK is made available as a public beta, please report any
issues or bugs in the github issue tracker.*

The Quantum Inspire platform allows to execute quantum algorithms using the cQASM language. 

The software development kit (SDK) for the Quantum Inspire platform consists of:

* An API for the [Quantum Inspire](https://www.quantum-inspire.com/) platform (the QuantumInspireAPI class);
* Backends for:
  * the [ProjectQ SDK](https://github.com/ProjectQ-Framework/ProjectQ);
  * the [Qiskit SDK](https://qiskit.org/).

For more information on Quantum Inspire see
[https://www.quantum-inspire.com/](https://www.quantum-inspire.com/). Detailed information
on cQASM can be found in the Quantum Inspire
[knowledge base](https://www.quantum-inspire.com/kbase/advanced-guide/).


## Installation

The Quantum Inspire SDK can be installed from PyPI via pip:

```
$ pip install quantuminspire
```

In addition, to use Quantum Inspire through Qiskit or ProjectQ, install either or both of
the qiskit and projectq packages:

```
$ pip install qiskit
$ pip install projectq
```

### Installing from source

The source for the SDK can also be found at Github. For the default installation execute:

```
$ git clone https://github.com/QuTech-Delft/quantuminspire
$ cd quantuminspire
$ pip install .
```

This does not install ProjectQ or Qiskit, but will install the Quantum Inspire backends for
those projects.

If you want to include a specific SDK as a dependency, install with
(e.g. for the ProjectQ backend):

```
$ pip install .[projectq]
```

To install both ProjectQ as well as Qiskit as a dependency:

```
$ pip install .[qiskit,projectq]
```

## Running

For example usage see the python scripts and Jupyter notebooks in the [docs/](docs/) directory
when installed from source or the share/doc/quantuminspire/examples/ directory in the
library root (Python’s sys.prefix for system installations; site.USER_BASE for user
installations) when installed from PyPI.

For example, to run the ProjectQ example notebook after installing from source:

```
cd docs
jupyter notebook example_projectq.ipynb
```

Or to perform Grover's with the ProjectQ backend from a Python script:

```
cd docs
python example_projectq_grover.py
```

[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/QuTech-Delft/quantuminspire/master?filepath=docs)

Another way to browse and run the available notebooks is by clicking the 'launch binder' button above.

It is also possible to use the API through the QuantumInspireAPI object
directly. This is for advanced users that really know what they are
doing. The intention of the QuantumInspireAPI class is that it is used
as a thin layer between existing SDK's such as ProjectQ and Qiskit,
and is not primarily meant for general use. You may want to explore this
if you intend to write a new backend for an existing SDK.

A simple example to perform entanglement between two qubits by using the
API wrapper directly:

```python
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
'''

backend_type = qi.get_backend_type_by_name('QX single-node simulator')
result = qi.execute_qasm(qasm, backend_type=backend_type, number_of_shots=1024)

if result.get('histogram', {}):
    print(result['histogram'])
else:
    reason = result.get('raw_text', 'No reason in result structure.')
    print(f'Result structure does not contain proper histogram data. {reason}')
```

## Configure your token credentials for Quantum Inspire

1. Create a Quantum Inspire account if you do not already have one.
2. Get an API token from the Quantum Inspire website.
3. With your API token run: 
```python
from quantuminspire.credentials import save_account
save_account('YOUR_API_TOKEN')
```
After calling save_account(), your credentials will be stored on disk.
Those who do not want to save their credentials to disk should use instead:
```python
from quantuminspire.credentials import enable_account
enable_account('YOUR_API_TOKEN')
```
and the token will only be active for the session.

After calling save_account() once or enable_account() within your session, token authentication is done automatically
when creating the Quantum Inspire API object.

For Qiskit users this means:
```python
from quantuminspire.qiskit import QI
QI.set_authentication()
```
ProjectQ users do something like:
```python
from quantuminspire.api import QuantumInspireAPI
qi = QuantumInspireAPI()
```
To create a token authentication object yourself using the stored token you do:
```python
from quantuminspire.credentials import get_token_authentication
auth = get_token_authentication()
```
This `auth` can then be used to initialize the Quantum Inspire API object.
 ## Known issues

* Some test-cases call protected methods
* Known issues and common questions regarding the Quantum Inspire platform
  can be found in the [FAQ](https://www.quantum-inspire.com/faq/).
 
## Bug reports

Please submit bug-reports [on the github issue tracker](https://github.com/QuTech-Delft/quantuminspire/issues).

## Testing

Run all unit tests and collect the code coverage using:

```
coverage run --source="./src/quantuminspire" -m unittest discover -s src/tests -t src -v
coverage report -m
```

## Note

If you are getting import errors related to `tests.quantuminspire` when running
the above commands after a `pip install -e .`, as a workaround you should remove
the package `tests` installed by older versions of `marshmallow-polyfield` (a Qiskit
dependency):

`rm -Rf env/lib/python3.6/site-packages/tests`
