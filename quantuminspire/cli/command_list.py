"""Module containing the commands for the Quantum Inspire 2 CLI."""
from enum import Enum
from pathlib import Path
from typing import Optional

import typer
from typer import Typer

from quantuminspire.sdk.models.hybrid_algorithm import HybridAlgorithm
from quantuminspire.util.api.local_runtime import LocalRuntime
from quantuminspire.util.api.remote_runtime import RemoteRuntime

app = Typer(add_completion=False, no_args_is_help=True)
algorithms_app = Typer(no_args_is_help=True)
app.add_typer(algorithms_app, name="algorithms", help="Manage algorithms")
configuration_app = Typer(no_args_is_help=True)
app.add_typer(configuration_app, name="config", help="Manage configuration")
projects_app = Typer(no_args_is_help=True)
app.add_typer(projects_app, name="projects", help="Manage projects")
files_app = Typer(no_args_is_help=True)
app.add_typer(files_app, name="files", help="Manage files")
results_app = Typer(no_args_is_help=True)
app.add_typer(results_app, name="results", help="Manage results")


class Destination(str, Enum):
    """Enumeration of potential destinations for projects."""

    LOCAL = "local"
    REMOTE = "remote"


@algorithms_app.command("create")
def create_algorithm(
    name: str = typer.Argument(..., help="The name of the algorithm"),
    hybrid: bool = typer.Option(False, help="Whether the template should be hybrid or only quantum"),
) -> None:
    """Create a new algorithm.

    Create an algorithm with a name. Depending on the hybrid flag, either the "hybrid algorithm" or the "quantum
    circuit" template is used.
    """
    if hybrid:
        typer.echo(f"Creating hybrid quantum/classical algorithm '{name}'")
    else:
        typer.echo(f"Creating quantum circuit '{name}'")


@algorithms_app.command("commit")
def commit_algorithm() -> None:
    """Commit algorithm to API.

    The algorithm is uploaded to the remote API. The algorithm is selected on the folder, the user is currently in.
    """
    typer.echo("Commit algorithm to API")


@algorithms_app.command("delete")
def delete_algorithm(remote: bool = typer.Option(False, help="Also delete the remote resource")) -> None:
    """Delete algorithm.

    The algorithm is deleted from the local disk. The algorithm is selected on the folder, the user is currently in.
    Based on the argument, the remote algorithm can also be deleted.
    """
    if remote:
        typer.echo("Delete local and remote algorithm")
    else:
        typer.echo("Delete local algorithm only")


@algorithms_app.command("describe")
def describe_algorithm(remote: bool = typer.Option(False, help="Use the remote resource as source of truth")) -> None:
    """Describe algorithm.

    Describe the algorithm. Both metadata and data from the algorithm itself are shown. The algorithm is selected on
    the folder the user is currently in. Based on the argument, the remote algorithm can also be described.
    """
    if remote:
        typer.echo("Describe remote algorithm")
    else:
        typer.echo("Describe local algorithm")


@algorithms_app.command("execute")
def execute_algorithm() -> None:
    """Execute algorithm.

    Send all selected algorithms to the configured execution environment (e.g. remote or native). If no algorithms are
    selected, the algorithm in the directory the user is currently in will be "selected" and executed.
    """
    typer.echo("Execute algorithm")


@algorithms_app.command("list")
def list_algorithms(
    local: bool = typer.Option(False, help="List all algorithms on the local system"),
    project: Optional[str] = typer.Option(None, help="Override the selected (default) project"),
    remote: bool = typer.Option(False, help="List all algorithms on the remote system"),
) -> None:
    """List algorithms.

    List all algorithms known on that environment for the currently selected project. If no environment is chosen
    (either local or remote), an empty list is shown. If both environments are chosen, both lists are merged with all
    algorithms being distinct. With the project flag, a different project can be selected to list all algorithms for.
    """
    if local and remote:
        target = "remote and local"
    elif remote:
        target = "remote"
    elif local:
        target = "local"
    else:
        target = "no"

    if project is None:
        project = "default"
    typer.echo(f"List {target} algorithms for project '{project}'")


@algorithms_app.command("select")
def select_algorithm() -> None:
    """Select algorithm.

    Select an algorithm for execution. The selected algorithms will be added to a `BatchRun` on execution. If the
    algorithm has already been selected before, the algorithm will be unselected on re-calling this method (i.e. the
    method acts as a toggle). The algorithm is selected on the folder the user is currently in.
    """
    typer.echo("Select algorithm")


@configuration_app.command("get")
def get_config(key: str = typer.Argument(..., help="The name of the configuration to get.")) -> None:
    """Get config.

    Get the configured value via a key. If no explicit value is set, the default value will be returned.
    """
    typer.echo(f"Get config for '{key}'")


@configuration_app.command("list")
def list_config(full: bool = typer.Option(False, help="List both custom and default key-values")) -> None:
    """List config.

    Get all key value combinations.
    """
    if full:
        typer.echo("List config, custom and default")
    else:
        typer.echo("List custom config only")


@configuration_app.command("set")
def set_config(
    key: str = typer.Argument(..., help="The name of the configuration to set"),
    value: str = typer.Argument(..., help="The value of the configuration to set"),
) -> None:
    """Set config.

    Set a key value combination for the configuration. Both the key and value are validated.
    """
    typer.echo(f"Set config '{key}={value}'")


@projects_app.command("create")
def create_project(name: str = typer.Argument(..., help="The name of the project")) -> None:
    """Create project.

    Create a project based on the name. This project is only created locally at first. The sync method will upload the
    project to the remote target.
    """
    typer.echo(f"Create project '{name}'")


@projects_app.command("delete")
def delete_project(remote: bool = typer.Option(False, help="Also delete the remote resource")) -> None:
    """Delete project.

    Delete a project from disk. Based on the argument, the remote project can also be deleted.
    """
    if remote:
        typer.echo("Delete remote and local project")
    else:
        typer.echo("Delete local project")


@projects_app.command("describe")
def describe_project(remote: bool = typer.Option(False, help="Use the remote resource as source of truth")) -> None:
    """Describe project.

    Describe the project. Both metadata and data from the project itself are shown. Based on the argument, the remote
    project can also be described.
    """
    if remote:
        typer.echo("Describe remote project")
    else:
        typer.echo("Describe local project")


@projects_app.command("list")
def list_projects(
    local: bool = typer.Option(False, help="List all projects on the local system"),
    remote: bool = typer.Option(False, help="List all projects on the remote system"),
) -> None:
    """List project.

    List all projects known on that environment. If no environment is chosen (either local or remote), an empty list is
    shown. If both environments are chosen, both lists are merged with all projects being distinct.
    """
    if local and remote:
        target = "remote and local"
    elif remote:
        target = "remote"
    elif local:
        target = "local"
    else:
        target = "no"

    typer.echo(f"List {target} projects")


@projects_app.command("sync")
def sync_projects(
    dest: Destination = typer.Option(Destination.LOCAL, help="The target system with which to synchronize the projects")
) -> None:
    """Sync project.

    All projects from the original location are synced to the `destination`. In the case of existing projects, the
    metadata of the target project is updated.
    """
    typer.echo(f"Sync projects with {dest.value}")


@files_app.command("upload")
def upload_files(
    name: str = typer.Argument(..., help="The name of the file to upload"),
    runtime_type_id: int = typer.Argument(
        ..., help="The id of the runtime type on which this algorithm should be executed"
    ),
) -> None:
    """Upload a file to the QI API.

    Upload a Hybrid Quantum/Classical Algorithm to the Quantum Inspire API. This file is marked as a hybrid algorithm
    when sent to the API.
    """
    runtime = RemoteRuntime()
    program = HybridAlgorithm(platform_name="spin-2", program_name=name)
    program.read_file(Path(name))
    run_id = runtime.run(program, runtime_type_id=runtime_type_id)
    typer.echo(f"Upload file with name: {name}")
    typer.echo(f"run_id {run_id}")


@files_app.command("run")
def run_file(
    name: str = typer.Argument(..., help="The full path of the file to run"),
) -> None:
    """Run a file locally.

    Run a Hybrid Quantum/Classical Algorithm locally. The quantum part will be run with QXEmulator.
    """
    algorithm = HybridAlgorithm("test", "test")
    algorithm.read_file(Path(name))

    local_runtime = LocalRuntime()
    run_id = local_runtime.run(algorithm, 0)
    results = local_runtime.get_results(run_id)
    typer.echo(f"{results}")


@results_app.command("get")
def get_results(run_id: int = typer.Argument(..., help="The id of the run")) -> None:
    """Retrieve the results for a run.

    Takes the id as returned by upload_files and retrieves the results for that run, if it's finished.
    """
    runtime = RemoteRuntime()
    results = runtime.get_results(run_id)

    if results is None:
        typer.echo("No results.")
        raise typer.Exit(1)

    typer.echo("Raw results:")
    typer.echo(results)


@app.command("login")
def login(
    host: str = typer.Argument(
        "https://api.qi2.quantum-inspire.com", help="The URL of the platform to which to connect"
    )
) -> None:
    """Log in to Quantum Inspire.

    Log in to the Quantum Inspire platform. The host can be overwritten, so that the user can connect to different
    instances. If no host is specified, the production environment will be used.
    """
    typer.echo(f"Login to {host}")


@app.command("logout")
def logout(
    host: str = typer.Argument(
        "https://api.qi2.quantum-inspire.com", help="The URL of the platform from which to log out"
    )
) -> None:
    """Log out of Quantum Inspire.

    Log out of a Quantum Inspire platform. This option will delete the local information needed for authentication, for
    a specific host. If no host is specified, the production environment will be used.
    """
    typer.echo(f"Logout from {host}")
