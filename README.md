# Quantum Inspire

[![License](https://img.shields.io/github/license/qutech-delft/qiskit-quantuminspire.svg?style=popout-square)](https://opensource.org/licenses/Apache-2.0)

Welcome to the repository for the Quantum Inspire tool. The goal of this project to offer basic support for interacting with the Quantum Inspire platform.
For example, you can manage your projects, algorithms and jobs on the Quantum Inspire system from your command line, or using the API directly in your Python code.

The tool is required for logging in to the Quantum Inspire systems. For example, if you would like to use the QI [Qiskit](https://github.com/QuTech-Delft/qiskit-quantuminspire) or [Pennylane](https://github.com/QuTech-Delft/pennylane-quantuminspire) plugins.

## Installation

The recommended way of installing the CLI is to use `pipx`. After following the [pipx installation instructions](https://pipx.pypa.io/stable/installation), run the following command:

```bash
pipx install quantuminspire
```

Afterwards, running `qi --help` should show a help menu.

> [!WARNING]
> Installing quantuminspire using pipx **inside a conda environment** may cause conflicts with other packages. This can result in unexpected behavior and prevent you from using the tool correctly. To avoid these issues,
> it is strongly recommended to install and run pipx on a system Python installation instead, downloaded from the official Python website.

> [!NOTE]
> If your python version is newer then supported by quantuminspire, please run the following command: `pipx install quantuminspire --python /path/to/python3.12`.
> Check which versions of python are supported by the tool.

## Using the CLI to login

In order to login to the platform, run the following command:

```bash
qi login
```

This will open a browser window that will allow you to login or create an account. By default this command will login to the production environment, but the command accepts an argument for a different host URL if needed (e.g. for beta testing purposes).

## Logout

To log out from the platform, run:

```bash
qi logout
```

If no hostname is specified, the default host is used.

---

## Run a job

To run a job on Quantum Inspire without persisting any settings, provide a file and a backend type ID:

```bash
qi run --file <path to .cq or .py file> --backend-type-id <int>
```

This will return a job ID. You can optionally specify `--num-shots`, `--store-raw-data`, and `--name`. Use `--persist` together with `--name` to store the project and algorithm settings locally for repeated use.
If you use the `--persist` flag, you first have to initialize a project with `qi projects init <name>`.

**IMPORTANT**: Submitting a (python) `.py` file for hybrid algorithms requires a [specific format](https://qutech-delft.github.io/qiskit-quantuminspire/hybrid/basics.html).
Not all `.py` files are valid for submission.
---

## Projects

### Initialize a project

Create a new project on the platform and store its settings locally in the current working directory (project root):

```bash
qi projects init <name> [description]
```

#### Examples

Initialize a project with only a name:

```bash
qi projects init "My Project"
```

Initialize a project with a name and description:

```bash
qi projects init "My Project" "Optional description"
```

### List projects

List all projects belonging to the current user. You can optionally filter projects by name, either using substring matching (default) or exact matching.

#### Usage

```bash
qi projects list
```

#### Options

* `--quiet, -q`
  Only print the IDs of the projects.

* `--name <name>`
  Filter projects by name or description using substring matching.

* `--exact`
  When used with `--name`, only return projects whose name exactly matches the given value.

#### Examples

List all projects:

```bash
qi projects list
```

List projects whose name or description contains `"quantum"`:

```bash
qi projects list --name quantum
```

List projects whose name is exactly `"my-project"`:

```bash
qi projects list --name my-project --exact
```

Print only the project IDs:

```bash
qi projects list --quiet
```

### Delete projects

Delete one or more projects by ID, by name, or delete all projects after confirmation.

> ⚠️ **Deleting projects is irreversible.**
> You will always be prompted for confirmation before deletion.

#### Usage

```bash
qi projects delete [PROJECT_IDS...]
```

#### Options

* `PROJECT_IDS`
  One or more project IDs to delete.

* `--name <name>`
  Delete projects matching this name or description pattern.

* `--exact`
  When used with `--name`, only delete projects whose name exactly matches the given value.

#### Behavior and precedence

* If **project IDs are provided**, `--name` and `--exact` are ignored.
* If no IDs are provided:

  * `--name` filters projects by substring match
  * `--name` + `--exact` performs an exact name match
* If **no IDs and no name** are provided, **all projects** will be deleted after confirmation.

#### Examples

Delete projects by ID:

```bash
qi projects delete 1 2 3
```

Delete projects whose name or description contains `"quantum"`:

```bash
qi projects delete --name quantum
```

Delete the project with the exact name `"my-project"`:

```bash
qi projects delete --name my-project --exact
```

Use list and delete together to delete projects by name:

```bash
qi projects delete $(qi projects list --name quantum --quiet)
```

Delete **all projects**:

```bash
qi projects delete
```

---

## Algorithms

Algorithms allow you to persist settings (file path, backend type, number of shots, raw-data flag) locally for repeated job submission. Algorithms must belong to a project initialized with `qi projects init`.
You can get the status, results and final result using the algorithm name. This will retrieve the specified resource for the latest job that was run using the algorithm. If you want to retrieve a resource for a specific job, use the `qi jobs` commands instead.

### Initialize an algorithm

```bash
qi algorithms init <name> <path> <backend_type_id>
```

### Get algorithm job status

```bash
qi algorithms status <algorithm_name>
```

Use `--wait` and `--timeout <seconds>` to wait for the job to complete.

### Get algorithm results

```bash
qi algorithms results <algorithm_name>
```

Use `--save` to save the results to a JSON file in the current directory.

### Get algorithm final result

```bash
qi algorithms final-result <algorithm_name>
```

Use `--save` to save the final result to a JSON file in the current directory.

**Note**: This object will always be generated. In the case of a quantum circuit, the result and final result will be the same. For hybrid algorithms, the final result is a free form datastructure that could for example be used for the aggregation of data. This is generated in the `finalize` step.

---

## Jobs

Jobs are created when you run `qi run`. Use the job ID printed by that command to check status and retrieve results.
You can also get the status, results and final result using the algorithm name with the `qi algorithms` commands. This will retrieve the specified resource for the latest job that was run using the algorithm.

### Inspect a job

Show all properties of a specific job:

```bash
qi jobs inspect <job_id>
```

### Get job status

```bash
qi jobs status <job_id>
```

Use `--wait` to wait for the job to complete before returning, and `--timeout <seconds>` to set the timeout (default: 60).

### Get job results

```bash
qi jobs results <job_id>
```

Use `--save` to save the results to a JSON file in the current directory.

### Get job final result

A job also always contains a final result. This object can be queried with the following command.

```bash
qi jobs final-result <job_id>
```

Use `--save` to save the final result to a JSON file in the current directory.

**Note**: This object will always be generated. In the case of a quantum circuit, the result and final result will be the same. For hybrid algorithms, the final result is a free form datastructure that could for example be used for the aggregation of data. This is generated in the `finalize` step.

---

## Backends

The list of backends (and some of their properties) can be retrieved using the following command, from which the id field can be read.

```bash
qi backends list
```

To see all properties of a specific backend, use:

```bash
qi backends get <backend-type-id>
```

---

## Compile files

The CLI can be used to compile cQASM (`.cq`) files against a specific backend type.

**IMPORTANT**: Hybrid Python (`.py`) files are not supported for compilation.

```bash
qi files compile --file <filename> --backend-type-id <int>
```

You can optionally specify a `--compile-stage` to control up to which stage the algorithm is compiled (default: Decomposition). Alternatively, provide `--name` to use the settings of a previously initialized algorithm.

---

## Config

### Get a configuration value

```bash
qi config get <key>
```

Use `--algorithm <name>` to retrieve a setting for a specific algorithm.

### Set a configuration value

```bash
qi config set <key> <value>
```

Use `--algorithm <name>` to set a setting for a specific algorithm, or `--user` to set a global user-level setting (e.g. `default_host`).
