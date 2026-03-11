import pytest
from pydantic import TypeAdapter

from quantuminspire.settings.models import AlgorithmName


def test_empty_algorithm_name_raises_error() -> None:
    with pytest.raises(ValueError, match="Algorithm name cannot be empty"):
        TypeAdapter(AlgorithmName).validate_python("")

    with pytest.raises(ValueError, match="Algorithm name cannot be empty"):
        TypeAdapter(AlgorithmName).validate_python(" ")


@pytest.mark.parametrize(
    "invalid_chars",
    [
        'name with "',
        "name with \\",
    ],
)
def test_algorithm_name_with_double_quotes_raises_error(invalid_chars: str) -> None:
    with pytest.raises(ValueError, match="Algorithm name cannot contain double quotes or backslashes"):
        TypeAdapter(AlgorithmName).validate_python(invalid_chars)


def test_algorithm_name_with_control_characters_raises_error() -> None:
    with pytest.raises(ValueError, match="Algorithm name cannot contain control characters"):
        TypeAdapter(AlgorithmName).validate_python("name with control char \x01")

@pytest.mark.parametrize(
    "valid_name",
    [
        "simple_name",
        "name-with-dashes",
        "name.with.dots",
        "Name With Spaces",
        "name123",
        "CamelCaseName",
    ],
)
def test_valid_algorithm_names(valid_name: str) -> None:
    TypeAdapter(AlgorithmName).validate_python(valid_name)
