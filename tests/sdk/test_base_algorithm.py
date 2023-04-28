import pytest

from quantuminspire.sdk.models.base_algorithm import BaseAlgorithm
from quantuminspire.sdk.models.circuit import Circuit


def test_not_initializable() -> None:
    with pytest.raises(TypeError, match="Can't instantiate abstract class BaseAlgorithm"):
        BaseAlgorithm(platform_name="platform", program_name="program")  # type: ignore
