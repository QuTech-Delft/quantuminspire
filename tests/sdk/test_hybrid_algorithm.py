from pathlib import Path
from unittest.mock import MagicMock

import pytest

from quantuminspire.sdk.models.hybrid_algorithm import HybridAlgorithm

MOCK_HYBRID_ALGORITHM = "hybrid algorithm"


@pytest.fixture
def mock_file() -> MagicMock:
    open_mock = MagicMock(auto_spec=Path)
    open_mock.read_text.return_value = MOCK_HYBRID_ALGORITHM
    return open_mock


def test_create() -> None:
    p = HybridAlgorithm(platform_name="platform", program_name="program")
    assert p.content == ""


def test_get_program_name() -> None:
    p = HybridAlgorithm(platform_name="platform", program_name="program")
    assert p.program_name == "program"


def test_get_content_type() -> None:
    p = HybridAlgorithm(platform_name="platform", program_name="program")
    assert p.content_type.value == "hybrid"


def test_get_compile_stage() -> None:
    p = HybridAlgorithm(platform_name="platform", program_name="program")
    assert p.compile_stage.value == "none"


def test_read_algorithm(mock_file: MagicMock) -> None:
    p = HybridAlgorithm(platform_name="platform", program_name="program")
    p.read_file(mock_file)
    assert p.content == MOCK_HYBRID_ALGORITHM


def test_get_language_name() -> None:
    p = HybridAlgorithm(platform_name="platform", program_name="program")
    assert p.language_name == "Python"
