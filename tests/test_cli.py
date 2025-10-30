from typer.testing import CliRunner

from quantuminspire.cli import app

runner = CliRunner()


def test_login() -> None:
    result = runner.invoke(app, ["login"])

    assert result.exit_code == 0, repr(result.exception)
    assert "Login successful!" in result.stdout


def test_login_with_host() -> None:
    result = runner.invoke(app, ["login", "https://host"])

    assert result.exit_code == 0, repr(result.exception)
    assert "Login successful!" in result.stdout


def test_logout() -> None:
    result = runner.invoke(app, ["logout"])

    assert result.exit_code == 0, repr(result.exception)
    assert "Logout successful!" in result.stdout


def test_logout_with_host() -> None:
    result = runner.invoke(app, ["logout", "https://host"])

    assert result.exit_code == 0, repr(result.exception)
    assert "Logout successful!" in result.stdout
