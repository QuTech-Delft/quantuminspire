from datetime import datetime
from pathlib import Path
from typing import List, Optional

import typer
from compute_api_client import BackendType, CompileStage, FinalResult, Job, Result
from rich.console import Console
from rich.table import Table
from typer import Typer, rich_utils

from quantuminspire.api import Api

rich_utils.STYLE_HELPTEXT = "default not dim"
rich_utils.STYLE_HELPTEXT_FIRST_LINE = "default not dim"

app = Typer(add_completion=False, no_args_is_help=True)
projects_app = Typer(no_args_is_help=True)
algorithms_app = Typer(no_args_is_help=True)
backend_types_app = Typer(no_args_is_help=True)
config_app = Typer(no_args_is_help=True)
jobs_app = Typer(no_args_is_help=True)
files_app = Typer(no_args_is_help=True)

app.add_typer(projects_app, name="projects")
app.add_typer(algorithms_app, name="algorithms")
app.add_typer(backend_types_app, name="backends")
app.add_typer(files_app, name="files")
app.add_typer(jobs_app, name="jobs")
app.add_typer(config_app, name="config")

console = Console()


@projects_app.callback()
def projects_callback() -> None:
    """Manage projects on the Quantum Inspire platform.

    A project is the top-level container for algorithms and jobs. You must initialize a
    project locally before you can initialize algorithms or run jobs with --persist.

    \b
    Examples:
      qi projects init "My Project" "Optional description"
      qi projects list --name "My"
      qi projects delete 42
    """


@algorithms_app.callback()
def algorithms_callback() -> None:
    """Manage locally initialized algorithms.

    An algorithm stores the settings (file path, backend type, number of shots, raw-data
    flag) needed to repeatedly submit jobs without re-specifying them every time.
    Algorithms must belong to a project that was initialized with 'qi projects init'.

    \b
    Examples:
      qi algorithms init my-algo circuit.cq 3
      qi algorithms status my-algo --wait
      qi algorithms results my-algo --save True
      qi algorithms final-result my-algo
    """


@backend_types_app.callback()
def backends_callback() -> None:
    """Inspect available backend types on the Quantum Inspire platform.

    Backend types represent the simulators and quantum hardware you can run jobs on.
    Use the backend type ID when submitting jobs with 'qi run' or 'qi algorithms init'.

    \b
    Examples:
      qi backends list
      qi backends get 3
    """


@files_app.callback()
def files_callback() -> None:
    """Perform file-level operations on algorithm files.

    Currently supports compiling cQASM (.cq) files against a specific backend type.
    Hybrid Python (.py) files are not supported for compilation.

    \b
    Examples:
      qi files compile --file circuit.cq --backend-type-id 3
      qi files compile --name my-algo --compile-stage mapping
    """


@jobs_app.callback()
def jobs_callback() -> None:
    """Inspect and retrieve results for jobs on the Quantum Inspire platform.

    Jobs are created when you run 'qi run'. Use the job ID printed by that command
    to check status and retrieve results here.

    \b
    Examples:
      qi jobs inspect 101
      qi jobs status 101 --wait --timeout 120
      qi jobs results 101 --save True
      qi jobs final-result 101
    """


@config_app.callback()
def config_callback() -> None:
    """Read and write local configuration settings.

    Configuration is stored at two levels:

    \b
      Project level  Settings specific to the project in the current directory.
                     Keys: project.id, project.name, project.description,
                           project.algorithms.<name>.*
      User level     Global settings shared across all projects.
                     Keys: default_host

    \b
    Examples:
      qi config get project.name
      qi config set default_host quantuminspire.com --user
      qi config get file_path --algorithm my-algo
      qi config set backend_type_id 3 --algorithm my-algo
    """


@app.callback()
def main() -> None:
    """Quantum Inspire CLI.

        With this Quantum Inspire CLI, you can manage your projects, algorithms and jobs on the Quantum Inspire system
        from your command line. Before you start, please login to the system using:



            \b
            qi login



        If you want to simply run a job on the system and not save any settings, you can run the command:



            \b
            qi run --file <path to .cq or .py file> --backend-type-id <int>



        This will return the job ID. You can retrieve status, results and final result of the job by running:



            \b
            qi jobs status|result|final-result <job ID>



        See qi run --help for additional optional settings.



        If you want to persist the settings of an algorithm locally, the workflow is as follows:



        1. Initialize a project:



                \b
                qi projects init <project name> <optional project description>



        2a. Immediately run a job with flag --persist and mandatory algorithm name --name:



                \b
                qi run --file <path to .cq or .py file> --backend-type-id <int> --name <algorithm name> --persist



        2b.  Initialize an algorithm with the settings you want to use first, then run a job with that algorithm name:



                \b
                qi algorithms init --name <algorithm-name> --path <path to .cq or .py file> --backend-type-id <int>
    --num-shots <int> --store-raw-data <Sbool>



            Then, you can run the algorithm using:



                \b
                qi run --name <algorithm-name>



        3. Retrieve the status, results and final result of the latest job of the algorithm using:



                \b
                qi algorithms status|results|final-result <algorithm-name>



        For more details about the commands and additional flags, see qi [OPTION] --help or qi [OPTION] [COMMAND] --help
    """


@app.command("login")
def login(
    hostname: Optional[str] = typer.Argument(None, help="The hostname of the Quantum Inspire platform"),
    override_auth_config: bool = typer.Option(False, help="Whether to override existing authentication configuration."),
    force: bool = typer.Option(False, help="Force a new login even if already logged in."),
) -> None:
    """Authenticate to Quantum Inspire.

    Defaults to the production environment if no hostname is specified.
    """
    api = Api()
    api.login(hostname, override_auth_config, force)


@app.command("logout")
def logout(
    hostname: Optional[str] = typer.Argument(None, help="The hostname of the Quantum Inspire platform"),
) -> None:
    """Log out from Quantum Inspire.

    If no hostname is specified, the default host is used.
    """
    api = Api()
    api.logout(hostname)


@app.command("run")
def run_job(
    file: Optional[Path] = typer.Option(None, help="The path to the hybrid algorithm or quantum circuit."),
    backend_type_id: Optional[int] = typer.Option(None, help="The backend type id."),
    num_shots: Optional[int] = typer.Option(
        None, help="The number of shots. Uses the backend type's default if not provided."
    ),
    store_raw_data: Optional[bool] = typer.Option(False, help="Whether to store data for each shot."),
    name: Optional[str] = typer.Option(
        None, help="The name of a locally initialized algorithm whose settings will be used."
    ),
    persist: bool = typer.Option(False, help="Store the project and algorithm the file is uploaded to."),
) -> None:
    """Run a new job on Quantum Inspire.

    Provide either a file to run, or the name of a locally initialized algorithm. All other options are optional and
    will override the algorithm's stored settings when provided.
    """
    api = Api()
    api.execute_algorithm(file, backend_type_id, num_shots, store_raw_data, name, persist)
    if persist:
        typer.echo("The algorithm has been stored.")


@projects_app.command("init")
def initialize_project(
    name: str = typer.Argument(help="The project name"),
    description: str = typer.Argument("", help="The project description"),
    path: Optional[str] = typer.Option(
        None,
        help="Local path where the project settings should be stored. Uses the current directory if not provided.",
    ),
) -> None:
    """Create a new project on the platform and store its settings locally."""
    api = Api()
    api.initialize_project(name, description, path)
    directory = path if path else Path.cwd()
    typer.echo(f"Project '{name}' initialized successfully at '{directory}'.")


@projects_app.command("list")
def list_projects(
    name: Optional[str] = typer.Option(None, help="Filter projects matching this name or description pattern"),
    exact: bool = typer.Option(False, help="If set, match project name exactly instead of substring search"),
    quiet: bool = typer.Option(False, "-q", "--quiet", help="Only print the IDs of the projects."),
) -> None:
    """List all your projects, with optional name filtering."""
    api = Api()
    projects = api.get_projects(name, exact)

    if quiet:
        for project in projects:
            print(project.id)
    else:
        table = Table("id", "name", "description", "created_on", "starred")

        for project in projects:
            table.add_row(
                str(project.id),
                str(project.name),
                str(project.description),
                project.created_on.strftime("%Y-%m-%d %H:%M:%S"),
                str(project.starred),
            )
        console.print(table)


@projects_app.command("delete")
def delete_projects(
    project_ids: Optional[List[int]] = typer.Argument(None, help="Delete projects with these IDs"),
    name: Optional[str] = typer.Option(None, help="Delete projects matching this name or description pattern"),
    exact: bool = typer.Option(False, help="If set, match project name exactly instead of substring search"),
) -> None:
    """Permanently delete one or more projects by ID or name pattern."""
    if not (project_ids or name):
        confirm_message = "You did not provide a name or IDs. This will delete ALL your projects. Are you sure?"
    else:
        confirm_message = "Are you sure you want to continue?"

    if not typer.confirm(confirm_message):
        raise typer.Abort()

    api = Api()
    api.delete_projects(project_ids, name, exact)


@algorithms_app.command("init")
def initialize_algorithm(
    name: str = typer.Argument(help="The algorithm name"),
    path: str = typer.Argument(help="The path to the algorithm file."),
    backend_type_id: int = typer.Argument(help="The ID of the backend type to use"),
    num_shots: Optional[int] = typer.Option(None, help="The number of shots to use"),
    store_raw_data: Optional[bool] = typer.Option(False, help="Whether to store the raw data or not. Default False"),
) -> None:
    """Register an algorithm and save its settings to the local config."""
    api = Api()
    api.initialize_algorithm(name, Path(path), backend_type_id, num_shots, store_raw_data)
    typer.echo(f"Algorithm '{name}' initialized successfully in local config.")


@algorithms_app.command("status")
def get_algorithm_status(
    algorithm_name: str = typer.Argument(..., help="The name of the locally initialized algorithm."),
    wait: bool = typer.Option(False, help="Wait for the job to complete."),
    timeout: float = typer.Option(60, help="Timeout in seconds to wait for the job to complete."),
) -> None:
    """Retrieve the status of the latest job for a locally initialized algorithm."""
    api = Api()
    status = api.get_job_status(algorithm_name, None, wait, timeout)
    typer.echo(f"Status of latest job for '{algorithm_name}' algorithm: '{status.value}'")


@algorithms_app.command("results")
def get_algorithm_results(
    algorithm_name: str = typer.Argument(..., help="The name of the locally initialized algorithm."),
    save: Optional[bool] = typer.Option(None, help="Save the results to a file."),
) -> None:
    """Retrieve the results of the latest job for a locally initialized algorithm.

    Each result corresponds to one iteration of the job.
    """
    api = Api()
    typer.secho(f"Retrieving results for latest job of '{algorithm_name}' algorithm...", fg=typer.colors.BLUE)
    results: list[Result] = api.get_results(algorithm_name, None)
    _output_results(results, algorithm_name, save)


@algorithms_app.command("final-result")
def get_algorithm_final_result(
    algorithm_name: str = typer.Argument(..., help="The name of the locally initialized algorithm."),
    save: Optional[bool] = typer.Option(None, help="Save the final result to a file."),
) -> None:
    """Retrieve the final result of the latest job for a locally initialized algorithm.

    The final result is the aggregated version of all the results of the job.
    """
    api = Api()
    typer.secho(f"Retrieving final result for latest job of '{algorithm_name}' algorithm...", fg=typer.colors.BLUE)
    final_result: FinalResult | None = api.get_final_result(algorithm_name, None)
    _output_final_result(final_result, algorithm_name, save)


@backend_types_app.command("list")
def get_backend_types() -> None:
    """Show all available backend types and their properties."""
    api = Api()
    backend_types: list[BackendType] = api.get_backend_types()
    table = Table(
        "id", "name", "status", "is_hardware", "supports_raw_data", "number_of_qubits", "max_number_of_shots", "message"
    )

    for backend_type in backend_types:
        message = ""
        for backend in backend_type.messages.keys():
            message += f"{backend}: {backend_type.messages[backend].content}\n"

        table.add_row(
            str(backend_type.id),
            backend_type.name,
            str(backend_type.status.name),
            str(backend_type.is_hardware),
            str(backend_type.supports_raw_data),
            str(backend_type.nqubits),
            str(backend_type.max_number_of_shots),
            message.rstrip("\n"),
        )
    console.print(table)


@backend_types_app.command("get")
def get_backend_type(
    backend_type_id: int = typer.Argument(None, help="The ID of the backend type to retrieve."),
) -> None:
    """Retrieve information about a specific backend type."""
    api = Api()
    typer.secho(f"Retrieving backend type with ID '{backend_type_id}'...", fg=typer.colors.BLUE)
    backend_type = api.get_backend_type(backend_type_id)
    console.print(backend_type.model_dump())


@files_app.command("compile")
def compile_file(
    file: Optional[Path] = typer.Option(None, help="The path to the algorithm file to compile."),
    name: Optional[str] = typer.Option(
        None, help="The name of a previously initialized algorithm whose settings will be used."
    ),
    backend_type_id: Optional[int] = typer.Option(None, help="The ID of the backend type to target."),
    compile_stage: Optional[CompileStage] = typer.Option(
        None, help="The stage up to which the algorithm should be compiled. Default Decomposition."
    ),
) -> None:
    """Compile a cQASM file up to a specified compilation stage."""
    api = Api()
    api.compile_file(file, name, backend_type_id, compile_stage)
    typer.echo("File compiled successfully!")


@jobs_app.command("inspect")
def inspect_job(
    job_id: int = typer.Argument(..., help="The ID of the job to retrieve."),
) -> None:
    """Show all properties of a specific job."""
    api = Api()
    typer.secho(f"Retrieving job with ID '{job_id}'...", fg=typer.colors.BLUE)
    job: Job = api.get_job(job_id)

    table = Table(title=f"Job {job.id}", show_header=True, header_style="bold cyan")
    table.add_column("Property", style="cyan", no_wrap=True)
    table.add_column("Value", style="white")

    table.add_row("ID", str(job.id))
    table.add_row("Status", str(job.status.value))
    table.add_row("Algorithm Type", str(job.algorithm_type.value))
    table.add_row("Created On", str(job.created_on))
    table.add_row("Queued At", str(job.queued_at) if job.queued_at is not None else "N/A")
    table.add_row("Finished At", str(job.finished_at) if job.finished_at is not None else "N/A")
    table.add_row("File ID", str(job.file_id))
    table.add_row("Batch Job ID", str(job.batch_job_id))
    table.add_row("Number of Shots", str(job.number_of_shots) if job.number_of_shots is not None else "N/A")
    table.add_row("Raw Data Enabled", str(job.raw_data_enabled))
    table.add_row("Session ID", job.session_id)
    table.add_row("Trace ID", job.trace_id)
    table.add_row("Message", job.message or "N/A")
    table.add_row("Source", job.source or "N/A")

    console.print(table)


@jobs_app.command("status")
def get_job_status(
    job_id: int = typer.Argument(..., help="The ID of the job to retrieve the status of."),
    wait: bool = typer.Option(False, help="Wait for the job to complete."),
    timeout: float = typer.Option(60, help="Timeout in seconds to wait for the job to complete."),
) -> None:
    """Retrieve the status of a job by its ID."""
    api = Api()
    status = api.get_job_status(None, job_id, wait, timeout)
    typer.echo(f"Job {job_id} status: '{status.value}'")


@jobs_app.command("results")
def get_results(
    job_id: int = typer.Argument(..., help="The ID of the job to retrieve the results for."),
    save: Optional[bool] = typer.Option(None, help="Save the results to a file."),
) -> None:
    """Retrieve the results of a job by its ID.

    Each result corresponds to one iteration of the job.
    """
    api = Api()
    typer.secho(f"Retrieving results for job with ID '{job_id}'...", fg=typer.colors.BLUE)
    results: list[Result] = api.get_results(None, job_id)
    _output_results(results, str(job_id), save)


@jobs_app.command("final-result")
def get_final_result(
    job_id: int = typer.Argument(..., help="The ID of the job to retrieve the final result for."),
    save: Optional[bool] = typer.Option(None, help="Save the final result to a file."),
) -> None:
    """Retrieve the final result of a job by its ID.

    The final result is the aggregated version of all the results of the job.
    """
    api = Api()
    typer.secho(f"Retrieving final result for job with ID '{job_id}'...", fg=typer.colors.BLUE)
    final_result: FinalResult | None = api.get_final_result(None, job_id)
    _output_final_result(final_result, str(job_id), save)


@config_app.command("set")
def set_config(
    key: str = typer.Argument(..., help="The configuration key to set."),
    value: str = typer.Argument(..., help="The value to set for the configuration key."),
    algorithm: Optional[str] = typer.Option(None, help="The name of the algorithm to set the value for."),
    user: bool = typer.Option(False, help="Set the configuration for the current user."),
) -> None:
    """Set a configuration value."""
    parsed_value: int | str
    try:
        parsed_value = int(value)
    except ValueError:
        parsed_value = value

    api = Api()
    if user:
        api.set_setting(key, parsed_value, is_user=user)
        typer.echo(f"User configuration '{key}' set to '{value}'.")
    else:
        if algorithm is None:
            api.set_setting(key, parsed_value, is_user=user)
            typer.echo(f"Configuration '{key}' set to '{value}'.")
        else:
            api.set_algorithm_setting(algorithm, key, parsed_value)
            typer.echo(f"Configuration '{key}' for '{algorithm}' set to '{value}'.")


@config_app.command("get")
def get_config(
    key: str = typer.Argument(..., help="The configuration key to retrieve."),
    algorithm: Optional[str] = typer.Option(None, help="The name of the algorithm to get the value for."),
) -> None:
    """Get a configuration value."""
    api = Api()

    if algorithm is None:
        value = api.get_setting(key)
        typer.echo(f"'{key}': {value}")
    else:
        value = api.get_algorithm_setting(algorithm, key)
        typer.echo(f"'{key}' for '{algorithm}': {value}")


def _output_final_result(final_result: FinalResult | None, identifier: str, save: Optional[bool]) -> None:
    """Save a final result to a file or print it to the console.

    Args:
        final_result: The final result to output, or None if no result is available.
        identifier: A string used to identify the output file (e.g. job ID or algorithm name).
        save: If True, save the final result to a JSON file in the current directory. Otherwise print to console.
    """
    if final_result is None:
        typer.echo("None")
    else:
        if save:
            datetime_string = datetime.now().strftime("%Y%m%d-%H%M%S")
            file_name = f"{datetime_string}_{identifier}_job_final_result.json"
            file_path = Path.cwd() / file_name

            typer.echo(
                f"{typer.style('Saving final result to', fg=typer.colors.BLUE)} \
                '{typer.style(str(file_path), fg=typer.colors.GREEN)}'"
            )

            with open(file_path, "w") as f:
                f.write(final_result.model_dump_json(indent=4))
        else:
            console.print(final_result.model_dump())


def _output_results(results: list[Result], identifier: str, save: Optional[bool]) -> None:
    """Save results to a file or print them to the console.

    Args:
        results: The list of results to output.
        identifier: A string used to identify the results file (e.g. job ID or algorithm name).
        save: If True, save the results to a JSON file in the current directory. Otherwise print to console.
    """
    if save:
        datetime_string = datetime.now().strftime("%Y%m%d-%H%M%S")
        file_name = f"{datetime_string}_{identifier}_job_results.json"
        file_path = Path.cwd() / file_name

        typer.echo(
            f"{typer.style('Saving results to', fg=typer.colors.BLUE)} \
            '{typer.style(str(file_path), fg=typer.colors.GREEN)}'"
        )

        with open(file_path, "w") as f:
            if not results:
                f.write("[]")
            else:
                f.write("[")
                f.write(",\n".join(result.model_dump_json(indent=4) for result in results))
                f.write("]")
    else:
        if not results:
            typer.echo("[]")
        else:
            for result in results:
                console.print(result.model_dump())


if __name__ == "__main__":
    app()
