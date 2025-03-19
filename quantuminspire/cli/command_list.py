"""Module containing the commands for the Quantum Inspire CLI."""

import webbrowser
from pathlib import Path
from typing import Optional

import typer
from compute_api_client import JobStatus
from qi2_shared.utils import run_async
from rich import print
from rich.console import Console
from rich.table import Table
from typer import Typer

from quantuminspire.sdk.models.cqasm_algorithm import CqasmAlgorithm
from quantuminspire.sdk.models.file_algorithm import FileAlgorithm
from quantuminspire.sdk.models.hybrid_algorithm import HybridAlgorithm
from quantuminspire.sdk.models.job_options import JobOptions
from quantuminspire.util.api.local_backend import LocalBackend
from quantuminspire.util.api.remote_backend import RemoteBackend
from quantuminspire.util.authentication import OauthDeviceSession
from quantuminspire.util.configuration import Settings, Url

app = Typer(add_completion=False, no_args_is_help=True)
backend_types_app = Typer(no_args_is_help=True)
app.add_typer(backend_types_app, name="backends", help="Manage backends")
files_app = Typer(no_args_is_help=True)
app.add_typer(files_app, name="files", help="Manage files")
results_app = Typer(no_args_is_help=True)
app.add_typer(results_app, name="results", help="Manage results")
final_results_app = Typer(no_args_is_help=True)
app.add_typer(final_results_app, name="final_results", help="Manage final results")

console = Console()


@backend_types_app.command("list")
def list_backend_types() -> None:
    """List backends.

    List all available backends and their configuration.
    """
    backend = RemoteBackend()
    backend_types = backend.get_backend_types().items
    table = Table("id", "name", "status", "is_hardware", "supports_raw_data", "number_of_qubits", "max_number_of_shots")
    for backend_type in backend_types:
        table.add_row(
            str(backend_type.id),
            backend_type.name,
            str(backend_type.status.name),
            str(backend_type.is_hardware),
            str(backend_type.supports_raw_data),
            str(backend_type.nqubits),
            str(backend_type.max_number_of_shots),
        )
    console.print(table)


@backend_types_app.command("get")
def get_backend_types(backend_type_id: int = typer.Argument(..., help="The id of the backend type")) -> None:
    """Get a backend.

    Get the configuration of a specific backend.
    """
    backend = RemoteBackend()
    backend_types = backend.get_backend_types().items

    backend_type = next((bt for bt in backend_types if bt.id == backend_type_id), None)
    if backend_type is None:
        console.print(f"Backend type with id {backend_type_id} not found.")
        raise typer.Exit(1)
    else:
        console.print(backend_type.model_dump())


def load_algorithm_from_file(file_path: Path) -> FileAlgorithm:
    """Load an algorithm from a file."""
    if file_path.suffix == ".py":
        algorithm: FileAlgorithm = HybridAlgorithm("", str(file_path))
    elif file_path.suffix == ".cq":
        algorithm = CqasmAlgorithm("", str(file_path))
    else:
        raise ValueError(f"Unsupported file type: {file_path.suffix}. Supported types are .py and .cq")

    algorithm.read_file(file_path)
    return algorithm


@files_app.command("upload")
def upload_files(
    name: str = typer.Argument(..., help="The name of the file to upload"),
    backend_type_id: int = typer.Argument(
        ..., help="The id of the backend type on which this algorithm should be executed"
    ),
    num_shots: int = typer.Option(
        1024, help="The number of shots to run the algorithm (only for pure cQASM algorithms)"
    ),
    store_raw_data: bool = typer.Option(
        False, help="Whether to enable shot memory for the algorithm (only for pure cQASM algorithms)"
    ),
) -> None:
    """Upload a file to the QI API.

    Upload a file containing either a Hybrid (.py) or a Quantum (.cq) algorithm, and run it on the QI platform.
    """
    backend = RemoteBackend()
    program = load_algorithm_from_file(Path(name))
    program.read_file(Path(name))
    job_options = JobOptions(number_of_shots=num_shots, raw_data_enabled=store_raw_data)
    job_id = backend.run(program, backend_type_id=backend_type_id, options=job_options)
    typer.echo(f"Upload file with name: {name}")
    typer.echo(f"job_id {job_id}")


@files_app.command("run")
def run_file(
    name: str = typer.Argument(..., help="The full path of the file to run"),
) -> None:
    """Run a file locally.

    Run a Hybrid Quantum/Classical Algorithm locally. The quantum part will be run with QXEmulator.
    """
    algorithm = HybridAlgorithm("test", "test")
    algorithm.read_file(Path(name))

    local_backend = LocalBackend()
    job_id = local_backend.run(algorithm, 0)
    results = local_backend.get_results(job_id)
    typer.echo(f"{results}")


def _has_job_failed(backend: RemoteBackend, job_id: int) -> None:
    """Check if a job has failed and exit with error_code 1 if it has."""
    job = backend.get_job(job_id)
    if job.status == JobStatus.FAILED:
        job.message = job.message or "Job failed."
        typer.echo(job.message, err=True)
        typer.echo(f"Trace id: {job.trace_id}", err=True)
        raise typer.Exit(1)


@results_app.command("get")
def get_results(job_id: int = typer.Argument(..., help="The id of the run")) -> None:
    """Retrieve the results for a run.

    Takes the id as returned by upload_files and retrieves the results for that run, if it's finished.
    """
    backend = RemoteBackend()
    _has_job_failed(backend, job_id)
    results = backend.get_results(job_id)

    if results is None:
        typer.echo("No results.")
        raise typer.Exit(1)

    typer.echo("Raw results:")
    print(results.model_dump())


@final_results_app.command("get")
def get_final_results(job_id: int = typer.Argument(..., help="The id of the run")) -> None:
    """Retrieve the final results for a run.

    Takes the id as returned by upload_files and retrieves the final results for that job, if it's finished.
    """
    backend = RemoteBackend()
    _has_job_failed(backend, job_id)
    results = backend.get_final_results(job_id)

    if results is None:
        typer.echo("No final results.")
        raise typer.Exit(1)

    typer.echo("Raw final results:")
    print(results.model_dump())


@app.command("login")
def login(
    host: Optional[str] = typer.Argument(None, help="The URL of the platform to which to connect"),
    override_auth_config: bool = typer.Option(
        False,
        help="Will ignore authentication configuration suggested by the API and use stored configuration instead",
    ),
) -> None:
    """Log in to Quantum Inspire.

    Log in to the Quantum Inspire platform. The host can be overwritten, so that the user can connect to different
    instances. If no host is specified, the production environment will be used.
    """
    settings = Settings()
    host = host or settings.default_host
    host_url = Url(host)
    settings.default_host = host_url

    if not override_auth_config:
        run_async(settings.fetch_auth_settings(host_url))

    auth_session = OauthDeviceSession(settings.auths[host_url])

    login_info = auth_session.initialize_authorization()
    typer.echo(f"Please continue logging in by opening: {login_info['verification_uri_complete']} in your browser")
    typer.echo(f"If promped to verify a code, please confirm it is as follows: {login_info['user_code']}")
    webbrowser.open(login_info["verification_uri_complete"], new=2)
    tokens = auth_session.poll_for_tokens()
    settings.store_tokens(host_url, tokens)
    typer.echo("Login successful!")
    typer.echo(f"Using member ID {settings.auths[host].team_member_id}")


@app.command("set-default-host")
def set_default_host(
    host: str = typer.Argument(help="The URL of the platform to which to connect"),
) -> None:
    """Set default_host for interacting with Quantum Inspire."""
    settings = Settings()
    settings.default_host = Url(host)
    settings.write_settings_to_file()
    typer.echo(f"Default host set to {host}")
