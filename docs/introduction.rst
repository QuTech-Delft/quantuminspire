Introduction
============

The Quantum Inspire platform allows to execute quantum algorithms using
the cQASM language.

The software development kit (SDK) for the Quantum Inspire platform
consists of:

* An API for the `Quantum Inspire <https://www.quantum-inspire.com/>`__
  platform (the QuantumInspireAPI class);
* Backends for:

    * The `ProjectQ
      SDK <https://github.com/ProjectQ-Framework/ProjectQ>`__;
    * The `Qiskit SDK <https://qiskit.org/>`__.

For more information on Quantum Inspire see
https://www.quantum-inspire.com/. Detailed information on cQASM can be
found in the Quantum Inspire `knowledge
base <https://www.quantum-inspire.com/kbase/advanced-guide/>`__.

Examples of more complex algorithms that make use of Quantum Inspire SDK can be found in
`Quantum Inspire Examples <https://github.com/QuTech-Delft/quantum-inspire-examples>`__.

Installation
------------

The Quantum Inspire SDK can be installed from PyPI via pip:

.. code-block:: console

    pip install quantuminspire

In addition, to use Quantum Inspire through Qiskit or ProjectQ, install
either or both of the qiskit and projectq packages:

.. code-block:: console

    pip install qiskit
    pip install projectq

Installing from source
~~~~~~~~~~~~~~~~~~~~~~

The source for the SDK can also be found at Github. For the default
installation execute:

.. code-block:: console

    git clone https://github.com/QuTech-Delft/quantuminspire
    cd quantuminspire
    pip install .

This does not install ProjectQ or Qiskit, but will install the Quantum
Inspire backends for those projects.

If you want to include a specific SDK as a dependency, install with
(e.g. for the ProjectQ backend):

.. code-block:: console

    pip install .[projectq]

To install both ProjectQ as well as Qiskit as a dependency:

.. code-block:: console

    pip install .[qiskit,projectq]

Installing for generating documentation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To install the necessary packages to perform documentation activities:

.. code-block:: console

    pip install .[rtd]

The documentation generation process is dependent on pandoc. When you want to generate the
documentation and pandoc is not yet installed on your system navigate
to `Pandoc <https://pandoc.org/installing.html>`__ and follow the instructions found there to install pandoc.
To build the 'readthedocs' documentation do:

.. code-block:: console

    cd docs
    make html

The documentation is then build in 'docs/_build/html'.

Running
-------

For example usage see the python scripts and Jupyter notebooks in the
:file:`docs/examples/` directory when installed from source or the
:file:`share/doc/quantuminspire/examples/` directory in the library root
(Python's ``sys.prefix`` for system installations; ``site.USER_BASE`` for user
installations) when installed from PyPI.

For example, to run the ProjectQ example notebook after installing from
source:

.. code-block:: console

    cd docs/examples
    jupyter notebook example_projectq.ipynb

or when you want to choose which example notebook to run from the browser do:

.. code-block:: console

    jupyter notebook --notebook-dir="docs/notebooks"

and select a Jupyter notebook (file with extension ``ipynb``) to run.

To perform Grover's with the ProjectQ backend from a Python script:

.. code-block:: console

    cd docs/examples
    python example_projectq_grover.py

|Binder|

Another way to browse and run the available notebooks is by clicking the
'launch binder' button above.

It is also possible to use the API through the QuantumInspireAPI object
directly. This is for advanced users that really know what they are
doing. The intention of the QuantumInspireAPI class is that it is used
as a thin layer between existing SDK's such as ProjectQ and Qiskit, and
is not primarily meant for general use. You may want to explore this if
you intend to write a new backend for an existing SDK.

A simple example to perform entanglement between two qubits by using the
API wrapper directly:

.. code:: python

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
    Measure q[0,1]
    '''

    backend_type = qi.get_backend_type_by_name('QX single-node simulator')
    result = qi.execute_qasm(qasm, backend_type=backend_type, number_of_shots=1024)

    if result.get('histogram', {}):
        print(result['histogram'])
    else:
        reason = result.get('raw_text', 'No reason in result structure.')
        print(f'Result structure does not contain proper histogram data. {reason}')

Configure a project name for Quantum Inspire
--------------------------------------------

As a default, SDK stores the jobs in a Quantum Inspire project with the name "qi-sdk-project-" concatenated with a
unique identifier for each run. Providing a project name yourself makes it easier to find the project in the Quantum
Inspire web-interface and makes it possible to gather related jobs to the same project.

Qiskit users do something like:

.. code:: python

    from coreapi.auth import BasicAuthentication
    from quantuminspire.qiskit import QI

    authentication = BasicAuthentication("email", "password")
    QI.set_authentication(authentication, project_name='my-project-name')

or set the project name separately after setting authentication

.. code:: python

    from coreapi.auth import BasicAuthentication
    from quantuminspire.qiskit import QI

    authentication = BasicAuthentication("email", "password")
    QI.set_authentication(authentication)
    QI.set_project_name('my-project-name')

ProjectQ users set the project name while initializing QuantumInspireAPI:

.. code:: python

    from coreapi.auth import BasicAuthentication
    from quantuminspire.api import QuantumInspireAPI

    authentication = BasicAuthentication("email", "password")
    qi_api = QuantumInspireAPI(authentication=authentication, project_name='my-project-name')

Configure your token credentials for Quantum Inspire
----------------------------------------------------

1. Create a Quantum Inspire account if you do not already have one.
2. Get an API token from the Quantum Inspire website.
3. With your API token run:

   .. code:: python

       from quantuminspire.credentials import save_account
       save_account('YOUR_API_TOKEN')

   After calling save\_account(), your credentials will be stored on
   disk. Those who do not want to save their credentials to disk should
   use instead:

   .. code:: python

       from quantuminspire.credentials import enable_account
       enable_account('YOUR_API_TOKEN')

   and the token will only be active for the session.

After calling save\_account() once or enable\_account() within your
session, token authentication is done automatically when creating the
Quantum Inspire API object.

For Qiskit users this means:

.. code:: python

    from quantuminspire.qiskit import QI
    QI.set_authentication()

ProjectQ users do something like:

.. code:: python

    from quantuminspire.api import QuantumInspireAPI
    qi = QuantumInspireAPI()

To create a token authentication object yourself using the stored token
you do:

.. code:: python

    from quantuminspire.credentials import get_authentication
    authentication = get_authentication()

This ``authentication`` can then be used to initialize the Quantum Inspire API
object.

Testing
-------

Run all unit tests and collect the code coverage using:

::

    coverage run --source="./src/quantuminspire" -m unittest discover -s src/tests -t src -v
    coverage report -m

Known issues
------------

-  Known issues and common questions regarding the Quantum Inspire
   platform can be found in the
   `FAQ <https://www.quantum-inspire.com/faq/>`__.

Bug reports
-----------

Please submit bug-reports `on the github issue
tracker <https://github.com/QuTech-Delft/quantuminspire/issues>`__.

.. |Binder| image:: https://mybinder.org/badge_logo.svg
   :target: https://mybinder.org/v2/gh/QuTech-Delft/quantuminspire/master?filepath=%2Fdocs%2Fexamples
