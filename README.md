# quantuminspire2

[![License](https://img.shields.io/github/license/qutech-delft/qiskit-quantuminspire.svg?style=popout-square)](https://opensource.org/licenses/Apache-2.0)

Welcome to the repository for the Quantum Inspire 2 CLI and SDK. The goal of this project to offer basic support for interacting with the Quantum Inspire 2 platform.
Currently, functionality of the CLI/SDK is still limited, but the CLI is required for logging in to the QI2 systems if you would like to use (e.g.) the QI2 [Qiskit](https://github.com/QuTech-Delft/qiskit-quantuminspire) or [Pennylane](https://github.com/QuTech-Delft/pennylane-quantuminspire2) plugins.

## Installation

The recommended way of installing the CLI is to use pipx. After following the [pipx installation instructions](https://github.com/pypa/pipx), clone this repository and run the following command in the repository root:

```bash
pipx install .
```

Afterwards, running `qi --help` should show a help menu.

## Using the CLI to login

In order to login to the platform, run the following command:

```bash
qi login
```

This will open a browser window that will allow you to login or create an account. By default this command will login to the production environment, but the command accepts an argument for a different host URL if needed (e.g. for beta testing purposes).
