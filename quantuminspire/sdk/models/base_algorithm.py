"""Module containing the Abstract Base Class for Algorithm classes."""

from abc import ABC, abstractmethod


class BaseAlgorithm(ABC):
    """A container object, used to store content and metadata for the algorithm."""

    def __init__(self, platform_name: str, program_name: str) -> None:
        self._platform_name = platform_name
        self._program_name = program_name

    @property
    def program_name(self) -> str:
        """Return the name of the program.

        Returns:
            The string representation of the program name.
        """
        return self._program_name

    @property
    def platform_name(self) -> str:
        """Return the name of the platform the algorithm is intended to run on.

        Returns:
            The string representation of the platform name.
        """
        return self._platform_name

    @property
    @abstractmethod
    def content(self) -> str:
        """Return the content.

        Returns:
            The string representation of the program.
        """

    @property
    @abstractmethod
    def content_type(self) -> str:
        """Return the content type.

        Returns:
            The string representation of the `AlgorithmType`.
        """

    @property
    @abstractmethod
    def compile_stage(self) -> str:
        """Return the compile stage.

        Returns:
            The string representation of the `CompileStage`.
        """

    @property
    @abstractmethod
    def language_name(self) -> str:
        """The name of the language the algorithm in the file is written in.

        Should match a language in the API.
        """
