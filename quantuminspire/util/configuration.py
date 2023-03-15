"""Module containing the handler for the Quantum Inspire persistent configuration."""

import json
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseSettings


def ensure_config_file_exists(file_path: Path, file_encoding: Optional[str]) -> None:
    """Create the file if it does not exist.

    Args:
        file_path: the file path.
        file_encoding: The encoding of the file.
    """
    if not file_path.exists():
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.open("w", encoding=file_encoding).write("{}")


def json_config_settings(settings: BaseSettings) -> Any:
    """Settings source that loads variables from a JSON file specified in the Config class.

    Args:
        settings: The settings class, used to determine the file encoding, based on the encoding of the
                  env_file_encoding
    Returns:
        A dictionary with the setting variables from the JSON file.
    """
    encoding: Optional[str] = settings.Config.env_file_encoding
    json_config_file: Path = settings.Config.json_config_file  # type: ignore

    ensure_config_file_exists(json_config_file, encoding)

    # The next stmt will fail if the json_config_file is something else then a regular file, and, of course, if the
    # file is not a valid JSON file.
    return json.loads(json_config_file.read_text(encoding))


class Settings(BaseSettings):
    """The settings class for the Quantum Inspire persistent configuration."""
    auths: str = "auths"


    class Config:  # pylint: disable=too-few-public-methods
        """The configuration class for the Settings class."""
        env_file_encoding = "utf-8"
        env_prefix = "QI2_"
        json_config_file = Path.joinpath(Path.home(), ".quantuminspire", "config.json")

        @classmethod
        def customise_sources(cls, init_settings: Any, env_settings: Any, file_secret_settings: Any) -> Any:
            """Customise the settings sources (by adding, removing and changing the order of sources).

            Args:
                init_settings: The initial settings (Settings object creation): highest priority.
                env_settings: The configuration settings (Config inner object creation).
                file_secret_settings: The file secret settings: lowest priority

            Returns:
                The original sources, with
                - the JSON file as source added after the initial settings and before the configuration settings.
                The order determines the priority!
            """
            return (
                init_settings,
                json_config_settings,
                env_settings,
                file_secret_settings,
            )
