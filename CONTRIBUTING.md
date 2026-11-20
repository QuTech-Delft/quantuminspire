# Contributing

Thank you for contributing to Quantum Inspire. Please read the following information about how to set up the development environment and which conditions need to be met by your pull request. 

## Set up the development environment

The project supports Python 3.10 through 3.13 and uses Poetry to manage its dependencies. From the repository root, install the project and development dependencies:

```bash
poetry install --with dev
```

Use `poetry run` to run project commands in the Poetry environment.

## Lint and type-check

Run the same checks used by the repository's `tox` environments:

```bash
poetry run black --check .
poetry run docformatter --check --black --recursive --wrap-summaries=119 --wrap-descriptions=119 .
poetry run ruff check .
poetry run mypy .
```

(Alternatively, you can run `poetry run tox -e lint,type`.)

## Run tests and coverage

Run the unit tests (excluding the separately configured end-to-end test):

```bash
poetry run pytest -v --ignore=tests/e2e_test.py
```

Coverage is enabled by the pytest configuration. The project requires **100% test coverage**, with branch coverage enabled; the test command fails if the threshold is not met. Add tests for new behavior and for each meaningful branch introduced by a change.

For a focused test run without the repository-wide coverage threshold, use:

```bash
poetry run pytest --no-cov -q tests/path/to/test_file.py
```

## Use a development host

Set `QI2_DEV_HOST` to direct the CLI or SDK to a development or test host. This is a runtime override: it takes precedence over the configured default host and is not persisted in the settings file.

For example:

```bash
export QI2_DEV_HOST=http://localhost:8000
poetry run qi login
```

Use a host you are authorized to access. To stop using the override, unset it:

```bash
unset QI2_DEV_HOST
```

Tests that depend on this environment variable should set or clear it in the test itself (for example, with pytest's `monkeypatch` fixture) rather than relying on a developer's shell environment.

## Continuous integration

The GitHub Actions workflow in [`.github/workflows/tests.yaml`](.github/workflows/tests.yaml) runs on pushes to
`master` and on every pull request. It invokes the shared Poetry test workflow and supplies the staging and end-to-end test configuration. Pull requests should pass the required CI checks before they are merged.
