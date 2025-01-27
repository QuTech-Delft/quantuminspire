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

## Upload files

The CLI can be used to upload files to Quantum Inspire. These files can both be hybrid and quantum circuits.

```bash
qi files upload <filename> <backend_id>
```

The CLI will assume that files with the extension `.cq` are quantum circuits, while files with a `.py` extension are python files. For the `backend_type` use any of the id's in the list below:

* QX emulator, id = 1
* Spin-2+, id = 2
* Starmon-7, id = 3

## Get results

The previous command outputs a job ID for the job that was just started. Use this job ID when querying for results.

```bash
qi results get <job_id>
```

**Note**: Mostly useful for quantum circuits.

## Get final results

A job also always contains a final result. This object can be queried with the following command.

```bash
qi final_results get <job_id>
```

**Note**: This object will always be generated. In the case of a quantum circuit, the result and final result will be the same. For hybrid algorithms, the final result is a free form datastructure that could for example be used for the aggregation of data. This is generated in the `finalize` step.
