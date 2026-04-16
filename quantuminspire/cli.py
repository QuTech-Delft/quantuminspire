from datetime import datetime
from pathlib import Path
from typing import Optional

import typer
from compute_api_client import BackendType, CompileStage, FinalResult, Job, Result
from rich.console import Console
from rich.table import Table
from typer import Typer

from quantuminspire.api import Api

app = Typer(add_completion=False, no_args_is_help=True)
projects_app = Typer(no_args_is_help=True)
backend_types_app = Typer(no_args_is_help=True)
config_app = Typer(no_args_is_help=True)
jobs_app = Typer(no_args_is_help=True)
files_app = Typer(no_args_is_help=True)

app.add_typer(projects_app, name="projects", help="Manage projects")
app.add_typer(backend_types_app, name="backends", help="Manage backends")
app.add_typer(config_app, name="config", help="Manage configuration")
app.add_typer(jobs_app, name="jobs", help="Manage jobs")
app.add_typer(files_app, name="files", help="Manage files")

console = Console()


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
    typer.echo("Login successful!")


@app.command("logout")
def logout(
    hostname: Optional[str] = typer.Argument(None, help="The hostname of the Quantum Inspire platform"),
) -> None:
    """Log out from Quantum Inspire.

    If no hostname is specified, the default host is used.
    """
    api = Api()
    api.logout(hostname)


@projects_app.command("init")
def initialize_project(
    name: str = typer.Argument(None, help="The project name"),
    description: str = typer.Argument("", help="The project description"),
    path: Optional[str] = typer.Option(
        None,
        help="Local path where the project settings should be stored. " "Uses the current directory if not provided.",
    ),
) -> None:
    """Initialize a project."""
    api = Api()
    api.initialize_project(name, description, path)
    directory = path if path else Path.cwd()
    typer.echo(f"Project '{name}' initialized successfully at '{directory}'.")


@projects_app.command("list")
def list_projects() -> None:
    """List projects."""
    api = Api()
    projects = api.get_projects()

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
def delete_projects() -> None:
    """Delete all projects."""
    typer.confirm("This will delete all projects on your account. Are you sure you want to continue?", abort=True)
    api = Api()
    api.delete_projects()
    typer.echo("All projects deleted successfully.")


@files_app.command("init-algorithm")
def initialize_algorithm(
    name: str = typer.Argument(help="The algorithm name"),
    path: str = typer.Argument(help="The path to the algorithm file."),
    backend_type_id: int = typer.Argument(help="The ID of the backend type to use"),
    num_shots: Optional[int] = typer.Option(None, help="The number of shots to use"),
    store_raw_data: Optional[bool] = typer.Option(None, help="Whether to store the raw data or not"),
) -> None:
    """Initialize an algorithm."""
    api = Api()
    api.initialize_algorithm(name, Path(path), backend_type_id, num_shots, store_raw_data)
    typer.echo(f"Algorithm '{name}' initialized successfully in local config.")


@files_app.command("compile")
def compile_file(
    file: Optional[Path] = typer.Option(None, help="The path to the algorithm file to compile."),
    name: Optional[str] = typer.Option(
        None, help="The name of a previously initialized algorithm whose settings will be used."
    ),
    backend_type_id: Optional[int] = typer.Option(None, help="The ID of the backend type to target."),
    compile_stage: Optional[CompileStage] = typer.Option(
        None, help="The stage up to which the algorithm should be compiled."
    ),
) -> None:
    """Compile an algorithm file."""
    api = Api()
    api.compile_file(file, name, backend_type_id, compile_stage)
    typer.echo("File compiled successfully!")


@backend_types_app.command("list")
def get_backend_types() -> None:
    """List all backend types."""
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


@jobs_app.command("run")
def run_job(
    file: Optional[Path] = typer.Option(None, help="The Path to the hybrid algorithm or quantum circuit."),
    backend_type_id: Optional[int] = typer.Option(None, help="The backend type id."),
    num_shots: Optional[int] = typer.Option(None, help="The Number of shots"),
    store_raw_data: Optional[bool] = typer.Option(None, help="Whether to store data for each shot."),
    name: Optional[str] = typer.Option(None, help="The name of the algorithm."),
    persist: bool = typer.Option(False, help="Store the project and algorithm the file is uploaded to."),
) -> None:
    """Run a new job on Quantum Inspire."""
    api = Api()
    api.execute_algorithm(file, backend_type_id, num_shots, store_raw_data, name, persist)

    if file is not None:
        typer.echo(f"Running job for file '{file}'...")
    if persist:
        typer.echo("The project and algorithm have been stored.")
    typer.echo("Job submitted successfully!")


@jobs_app.command("inspect")
def inspect_job(
    job_id: int = typer.Argument(..., help="The ID of the job to retrieve."),
) -> None:
    """Retrieve information about a specific job."""
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
    job_id: Optional[int] = typer.Option(None, help="The ID of the job to retrieve the status of the job."),
    algorithm_name: Optional[str] = typer.Option(
        None, help="The name of the algorithm. The status of the latest job for the algorithm will be retrieved."
    ),
    wait: bool = typer.Option(False, help="Wait for the job to complete."),
    timeout: float = typer.Option(60, help="Timeout for the job to complete."),
) -> None:
    """Retrieve the status of a job."""
    api = Api()
    status = api.get_job_status(algorithm_name, job_id, wait, timeout)
    if job_id is not None:
        typer.echo(f"Job {job_id} status: '{status.value}'")
    if algorithm_name is not None:
        typer.echo(f"Latest job of {algorithm_name} status: '{status.value}'")


@jobs_app.command("results")
def get_results(
    job_id: Optional[int] = typer.Option(None, help="The ID of the job to retrieve the result for."),
    algorithm_name: Optional[str] = typer.Option(
        None, help="The name of the algorithm. The results of the latest job for the algorithm will be retrieved."
    ),
    save: Optional[bool] = typer.Option(None, help="Save the results to a file."),
) -> None:
    """Retrieve information about a specific result."""
    api = Api()
    typer.secho(f"Retrieving result with ID '{job_id}'...", fg=typer.colors.BLUE)
    results: list[Result] = api.get_results(algorithm_name, job_id)

    if save:
        file_identifier = job_id if job_id else algorithm_name
        datetime_string = datetime.now().strftime("%Y%m%d-%H%M%S")
        file_name = f"{datetime_string}_{file_identifier}_job_results.json"
        file_path = Path.cwd() / file_name

        typer.echo(
            f"{typer.style(
                'Saving results to', fg=typer.colors.BLUE
            )} '{typer.style(file_path, fg=typer.colors.GREEN)}'"
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


@jobs_app.command("final-result")
def get_final_result(
    job_id: Optional[int] = typer.Option(None, help="The ID of the job to retrieve the result for."),
    algorithm_name: Optional[str] = typer.Option(
        None, help="The name of the algorithm. The final result of the latest job for the algorithm will be retrieved."
    ),
    save: Optional[bool] = typer.Option(None, help="Save the final result to a file."),
) -> None:
    """Retrieve information about a specific final result."""
    api = Api()

    typer.secho(f"Retrieving final result with ID '{job_id}'...", fg=typer.colors.BLUE)
    final_result: FinalResult | None = api.get_final_result(algorithm_name, job_id)

    if final_result is None:
        typer.echo("None")
    else:
        if save:
            file_identifier = job_id if job_id else algorithm_name
            datetime_string = datetime.now().strftime("%Y%m%d-%H%M%S")
            file_name = f"{datetime_string}_{file_identifier}_job_final_result.json"
            file_path = Path.cwd() / file_name

            typer.echo(
                f"{typer.style(
                    'Saving final result to', fg=typer.colors.BLUE
                )} '{typer.style(file_path, fg=typer.colors.GREEN)}'"
            )

            with open(file_path, "w") as f:
                f.write(final_result.model_dump_json(indent=4))
        else:
            console.print(final_result.model_dump())


@config_app.command("set")
def set_config(
    key: str = typer.Argument(..., help="The configuration key to set."),
    value: str = typer.Argument(..., help="The value to set for the configuration key."),
    algorithm: Optional[str] = typer.Option(None, help="name of the algorithm to set the value for."),
    user: bool = typer.Option(False, help="Set the configuration for the user."),
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


if __name__ == "__main__":
    app()
