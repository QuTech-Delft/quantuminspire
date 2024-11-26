"""Module containing the Hybrid Quantum/Classical Algorithm class."""

from pathlib import Path

from compute_api_client import CompileStage

from quantuminspire.sdk.models.base_algorithm import BaseAlgorithm


class FileAlgorithm(BaseAlgorithm):
    """A container object, reading the python algorithm and keeping metadata.

    The FileAlgorithm reads the python file describing the algorithm and stores it in `.content`.
    """

    def __init__(self, platform_name: str, program_name: str) -> None:
        super().__init__(platform_name, program_name)
        self._content = ""

    @property
    def content(self) -> str:
        return self._content

    @property
    def compile_stage(self) -> CompileStage:
        return CompileStage.NONE

    def read_file(self, file_pointer: Path) -> None:
        """Read the python file to the wrapper.

        Args:
            file_pointer: the file path to the file to read.
        """
        self._content = file_pointer.read_text()
