# Quantum Inspire

[![License](https://img.shields.io/github/license/qutech-delft/qiskit-quantuminspire.svg?style=popout-square)](https://opensource.org/licenses/Apache-2.0)

Welcome to the repository for the Quantum Inspire tool. The goal of this project to offer basic support for interacting with the Quantum Inspire platform.
Currently, functionality of the tool is still limited, but the tool is required for logging in to the Quantum Inspire systems. For example, if you would like to use the QI [Qiskit](https://github.com/QuTech-Delft/qiskit-quantuminspire) or [Pennylane](https://github.com/QuTech-Delft/pennylane-quantuminspire) plugins.

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

## Upload files

The CLI can be used to upload files to Quantum Inspire. These files can both be hybrid and quantum circuits.

**IMPORTANT**: Submitting a (python) `.py` file for hybrid algorithms requires a [specific format](https://qutech-delft.github.io/qiskit-quantuminspire/hybrid/basics.html).
Not all `.py` files are valid for submission.

```bash
qi files upload <filename> <backend_id>
```

The CLI will assume that files with the extension `.cq` are quantum circuits, while files with a `.py` extension are python files.

The list of backends (and their properties)
can be retrieved using the following command, from which id field can be read.

```bash
qi backends list
```

## Get results

The previous command outputs a job ID for the job that was just started. Use this job ID when querying for results.

```bash
qi results get <job_id>
```


## List projects

List all projects belonging to the current user. You can optionally filter projects by name, either using substring matching (default) or exact matching.

### Usage

```bash
qi projects list
```

### Options

* `--print, -p`
  Print the full project list as a table.

* `--name <name>`
  Filter projects by name or description using substring matching.

* `--exact`
  When used with `--name`, only return projects whose name exactly matches the given value.

### Examples

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

Print the full project list:

```bash
qi projects list --print
```

---

## Delete projects

Delete one or more projects by ID, by name, or delete all projects after confirmation.

> ⚠️ **Deleting projects is irreversible.**
> You will always be prompted for confirmation before deletion.

### Usage

```bash
qi projects delete [PROJECT_IDS...]
```

### Options

* `PROJECT_IDS`
  One or more project IDs to delete.

* `--name <name>`
  Delete projects matching this name or description pattern.

* `--exact`
  When used with `--name`, only delete projects whose name exactly matches the given value.

### Behavior and precedence

* If **project IDs are provided**, `--name` and `--exact` are ignored.
* If no IDs are provided:

  * `--name` filters projects by substring match
  * `--name` + `--exact` performs an exact name match
* If **no IDs and no name** are provided, **all projects** will be deleted after confirmation.

### Examples

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

Delete **all projects**:

```bash
qi projects delete
```

> You will be asked to confirm before deletion.

**Note**: Mostly useful for quantum circuits.

## Get final results

A job also always contains a final result. This object can be queried with the following command.

```bash
qi final_results get <job_id>
```

**Note**: This object will always be generated. In the case of a quantum circuit, the result and final result will be the same. For hybrid algorithms, the final result is a free form datastructure that could for example be used for the aggregation of data. This is generated in the `finalize` step.
