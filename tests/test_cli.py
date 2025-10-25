from typer.testing import CliRunner

from quantuminspire.cli import app

runner = CliRunner()


def test_login() -> None:
    result = runner.invoke(app, ["login"])

    assert result.exit_code == 0, repr(result.exception)
    assert "Login successful!" in result.stdout


def test_login_with_host() -> None:
    result = runner.invoke(app, ["login", "https://host"])

    assert "Login successful!" in result.stdout


def test_logout() -> None:
    result = runner.invoke(app, ["logout"])

    assert "Logout successful!" in result.stdout


def test_logout_with_host() -> None:
    result = runner.invoke(app, ["logout", "https://host"])

    assert "Logout successful!" in result.stdout


def test_run_job() -> None:
    result = runner.invoke(app, ["jobs", "run", "path/to/file"])

    assert "Running job for file 'path/to/file'..." in result.stdout
    assert "Job submitted successfully!" in result.stdout


def test_run_job_persisting_id() -> None:
    result = runner.invoke(app, ["jobs", "run", "path/to/file", "--persist"])

    assert "Running job for file 'path/to/file'..." in result.stdout
    assert "The project and algorithm have been stored." in result.stdout
    assert "Job submitted successfully!" in result.stdout


def test_get_job() -> None:
    result = runner.invoke(app, ["jobs", "get", "123"])

    assert "Retrieving job with ID '123'..." in result.stdout
    assert "Job details: {...}" in result.stdout


def test_get_job_without_id() -> None:
    result = runner.invoke(app, ["jobs", "get"])

    assert "Retrieving job with ID 'None'..." in result.stdout
    assert "Job details: {...}" in result.stdout


def test_get_result() -> None:
    result = runner.invoke(app, ["results", "get", "456"])

    assert "Retrieving result with ID '456'..." in result.stdout
    assert "Result details: {...}" in result.stdout


def test_get_result_without_id() -> None:
    result = runner.invoke(app, ["results", "get"])

    assert "Retrieving result with ID 'None'..." in result.stdout
    assert "Result details: {...}" in result.stdout


def test_get_final_result() -> None:
    result = runner.invoke(app, ["final-results", "get", "789"])

    assert "Retrieving final result with ID '789'..." in result.stdout
    assert "Final result details: {...}" in result.stdout


def test_get_final_result_without_id() -> None:
    result = runner.invoke(app, ["final-results", "get"])

    assert "Retrieving final result with ID 'None'..." in result.stdout
    assert "Final result details: {...}" in result.stdout


def test_set_local_config() -> None:
    result = runner.invoke(app, ["config", "set", "key", "value"])

    assert "Configuration 'key' set to 'value'." in result.stdout


def test_set_user_config() -> None:
    result = runner.invoke(app, ["config", "set", "--user", "user_key", "user_value"])

    assert "User configuration 'user_key' set to 'user_value'." in result.stdout


def test_get_local_config() -> None:
    result = runner.invoke(app, ["config", "get", "key"])

    assert "key: value" in result.stdout


def test_get_user_config() -> None:
    result = runner.invoke(app, ["config", "get", "user_key"])

    assert "user_key: value" in result.stdout
