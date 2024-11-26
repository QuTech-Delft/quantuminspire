"""Module containing the Quantum Algorithm class."""

from compute_api_client import AlgorithmType

from quantuminspire.sdk.models.file_algorithm import FileAlgorithm


class CqasmAlgorithm(FileAlgorithm):
    """A container object, reading the python algorithm and keeping metadata.

    The CqasmAlgorithm reads the python file describing the algorithm and stores it in `.content`.
    """

    @property
    def content_type(self) -> AlgorithmType:
        return AlgorithmType.QUANTUM

    @property
    def language_name(self) -> str:
        return "cQASM"
