from typing import Optional

import typer
from typer import Typer

app = Typer(add_completion=False, no_args_is_help=True)


@app.command("login")
def login(
    hostname: Optional[str] = typer.Argument(None, help="The hostname of the Quantum Inspire platform"),
) -> None:
    """Authenticate to Quantum Inspire.

    Defaults to the production environment if no hostname is specified.
    """
    typer.echo("Login successful!")


@app.command("logout")
def logout(
    hostname: Optional[str] = typer.Argument(None, help="The hostname of the Quantum Inspire platform"),
) -> None:
    """Log out from Quantum Inspire.

    If no hostname is specified, the default host is used.
    """
    typer.echo("Logout successful!")
