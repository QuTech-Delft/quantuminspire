"""Module containing the handler for the Quantum Inspire persistent configuration."""

import json
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Type

from pydantic.fields import FieldInfo
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict


def ensure_config_file_exists(file_path: Path, file_encoding: Optional[str] = None) -> None:
    """Create the file if it does not exist.

    Args:
        file_path: the file path.
        file_encoding: The encoding of the file.
    """
    if not file_path.exists():
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.open("w", encoding=file_encoding).write(
            '{"auths": {"https://staging.qi2.quantum-inspire.com": {"user_id": 1}}}'
        )


class JsonConfigSettingsSource(PydanticBaseSettingsSource):
    """Settings source that loads variables from a JSON file specified in the Config class.

    Returns:
        A dictionary with the setting variables from the JSON file.
    """

    def get_field_value(self, field: FieldInfo, field_name: str) -> Tuple[Any, str, bool]:
        raise NotImplementedError

    def __call__(self) -> Any:
        encoding = self.config.get("env_file_encoding")
        json_config_file = Path.joinpath(Path.home(), ".quantuminspire", "config.json")

        ensure_config_file_exists(json_config_file, encoding)

        return json.loads(json_config_file.read_text(encoding))


class Settings(BaseSettings):  # pylint: disable=too-few-public-methods
    """The settings class for the Quantum Inspire persistent configuration."""

    model_config = SettingsConfigDict(
        env_file_encoding="utf-8",
        env_prefix="QI2_",
    )

    auths: Dict[str, Dict[str, Any]]

    # R0913: Too many arguments (6/5) (too-many-arguments)
    @classmethod
    def settings_customise_sources(  # pylint: disable=R0913
        cls,
        settings_cls: Type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> Tuple[PydanticBaseSettingsSource, ...]:
        """Customise the settings sources (by adding, removing and changing the order of sources).

        Args:
            init_settings: The initial settings (Settings object creation): highest priority.
            env_settings: The configuration settings (Config inner object creation).
            file_secret_settings: The file secret settings: lowest priority

        Returns:
            The original sources, with
            - the JSON file as source added after the env settings and before the file secret settings.
            The order determines the priority!
        """
        return (
            init_settings,
            env_settings,
            JsonConfigSettingsSource(settings_cls),
            file_secret_settings,
        )
