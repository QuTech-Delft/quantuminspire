from typing import List

import pytest
from typer.testing import CliRunner

from quantuminspire.cli.command_list import app

runner = CliRunner()


@pytest.mark.parametrize(
    "args,output",
    [
        (["algorithms", "create", "Test"], "Creating quantum circuit 'Test'"),
        (["algorithms", "create", "Test", "--hybrid"], "Creating hybrid quantum/classical algorithm 'Test'"),
        (["algorithms", "commit"], "Commit algorithm to API"),
        (["algorithms", "delete"], "Delete local algorithm only"),
        (["algorithms", "delete", "--remote"], "Delete local and remote algorithm"),
        (["algorithms", "describe"], "Describe local algorithm"),
        (["algorithms", "describe", "--remote"], "Describe remote algorithm"),
        (["algorithms", "execute"], "Execute algorithm"),
        (["algorithms", "list"], "List no algorithms for project 'default'"),
        (["algorithms", "list", "--local"], "List local algorithms for project 'default'"),
        (["algorithms", "list", "--local", "--project", "Test"], "List local algorithms for project 'Test'"),
        (["algorithms", "list", "--remote"], "List remote algorithms for project 'default'"),
        (["algorithms", "list", "--remote", "--local"], "List remote and local algorithms for project 'default'"),
        (["algorithms", "select"], "Select algorithm"),
        (["config", "get", "key"], "Get config for 'key'"),
        (["config", "list"], "List custom config only"),
        (["config", "list", "--full"], "List config, custom and default"),
        (["config", "set", "key", "value"], "Set config 'key=value'"),
        (["projects", "create", "Test"], "Create project 'Test'"),
        (["projects", "delete"], "Delete local project"),
        (["projects", "delete", "--remote"], "Delete remote and local project"),
        (["projects", "describe"], "Describe local project"),
        (["projects", "describe", "--remote"], "Describe remote project"),
        (["projects", "list"], "List no projects"),
        (["projects", "list", "--local"], "List local projects"),
        (["projects", "list", "--remote"], "List remote projects"),
        (["projects", "list", "--remote", "--local"], "List remote and local projects"),
        (["projects", "sync", "--dest", "local"], "Sync projects with local"),
        (["projects", "sync", "--dest", "remote"], "Sync projects with remote"),
        (["login"], "Login to https://api.qi2.quantum-inspire.com"),
        (["login", "https://www.quantum-inspire.com"], "Login to https://www.quantum-inspire.com"),
        (["logout"], "Logout from https://api.qi2.quantum-inspire.com"),
        (["logout", "https://www.quantum-inspire.com"], "Logout from https://www.quantum-inspire.com"),
    ],
)
def test_cli_calls(args: List[str], output: str) -> None:
    result = runner.invoke(app, args)
    print(result.output)
    assert result.exit_code == 0
    assert output in result.stdout
