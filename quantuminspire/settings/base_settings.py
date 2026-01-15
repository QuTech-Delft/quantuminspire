import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Type, cast

from pydantic import BaseModel, Field
from pydantic.fields import FieldInfo
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict


def ensure_config_file_exists(
    file_path: Path,
    file_encoding: Optional[str] = None,
    default_factory: Optional[Callable[[], Dict[str, Any]]] = None,
) -> None:
    """Ensure a JSON config file exists, creating it with default content if needed.

    Args:
        file_path: Path to the config file.
        file_encoding: Optional file encoding (defaults to system default).
        default_factory: Optional callable that returns a dict to use as default content.
    """
    if not file_path.exists():
        file_path.parent.mkdir(parents=True, exist_ok=True)
        default_content = default_factory() if default_factory else {}
        file_path.write_text(json.dumps(default_content, indent=4), encoding=file_encoding)


class JsonConfigSettingsSource(PydanticBaseSettingsSource):
    """Settings source that loads variables from a JSON file specified in the Config class.

    Returns:
        A dictionary with the setting variables from the JSON file.
    """

    def __init__(self, settings_cls: type[BaseSettings]):
        super().__init__(settings_cls)
        settings_cls = cast("type[BaseConfigSettings]", settings_cls)

        self._default_factory = getattr(settings_cls, "default_factory")
        self._json_file_path = getattr(settings_cls, "json_file")()

    def get_field_value(self, field: FieldInfo, field_name: str) -> Tuple[Any, str, bool]:
        raise NotImplementedError

    def __call__(self) -> Any:
        encoding = self.config.get("env_file_encoding")

        ensure_config_file_exists(self._json_file_path, encoding, self._default_factory)
        return json.loads(self._json_file_path.read_text(encoding))


class BaseConfigSettings(BaseSettings, ABC):  # pylint: disable=too-few-public-methods
    """The settings class for the Quantum Inspire persistent configuration."""

    model_config = SettingsConfigDict(
        env_file_encoding="utf-8",
    )

    backend_type: Optional[int] = Field(None)

    @classmethod
    def file_marker(cls) -> List[str]:
        """Return the full JSON file path (base_dir + subpath)."""
        return [".quantuminspire", "config.json"]

    @classmethod
    def json_file(cls, path: Optional[Path] = None) -> Path:
        """Return the full JSON file path (base_dir + subpath)."""
        parent_dir = path or cls.base_dir()
        return Path.joinpath(parent_dir, *cls.file_marker())

    @classmethod
    @abstractmethod
    def base_dir(cls) -> Path:
        """Subclasses provide the base directory (home, cwd, etc)"""
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def default_factory(cls) -> Dict[str, Any]:
        """Return default JSON content."""
        raise NotImplementedError

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

    def _get_parent_and_attr(self, key: str) -> Tuple[BaseModel, str]:
        """Return the parent object and final attribute name for a dot-separated key."""

        parts = key.split(".")
        current: BaseModel = self

        for part in parts[:-1]:
            current = getattr(current, part)
        return current, parts[-1]

    def clear(self, key: str) -> None:
        """Clear a setting value.

        Supports nested keys using dot notation, e.g., 'project.description'.
        """

        self.set_value(key, None)

    def set_value(self, key: str, value: Any) -> None:
        """Set a setting value.

        Supports nested keys using dot notation, e.g., 'project.description'.
        """

        parent, field = self._get_parent_and_attr(key)

        setattr(parent, field, value)

        self.save()

    def get_value(self, key: str) -> Any:
        """Get a setting value.

        Supports nested keys using dot notation, e.g., 'project.description'.
        """

        parent, field = self._get_parent_and_attr(key)

        return getattr(parent, field)

    def save(self) -> None:
        """Save the model instance to its JSON file."""

        self.__class__.json_file().write_text(
            self.model_dump_json(indent=4), encoding=self.model_config.get("env_file_encoding", "utf-8")
        )

    @staticmethod
    def flatten_fields(obj: BaseModel, prefix: str = "") -> List[str]:
        """Recursively collect all field names of a BaseModel, including nested fields.

        Nested fields are represented using dot notation, e.g., 'parent.child.field'.

        Args:
            obj: The Pydantic model instance to flatten.
            prefix: Optional prefix for nested field names (used internally).

        Returns:
            A flat list of field names, with nested fields represented as "parent.child".
        """

        fields: List[str] = []

        for field_name, _ in obj.__class__.model_fields.items():
            full_key = f"{prefix}.{field_name}" if prefix else field_name

            value = getattr(obj, field_name)

            if isinstance(value, BaseModel):
                # Recurse into nested BaseModel fields
                nested_fields = BaseConfigSettings.flatten_fields(value, prefix=full_key)
                fields.extend(nested_fields)
            else:
                fields.append(full_key)

        return fields
