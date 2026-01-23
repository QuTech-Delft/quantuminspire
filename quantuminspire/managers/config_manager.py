from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from quantuminspire.settings.base_settings import BaseConfigSettings
from quantuminspire.settings.project_settings import ProjectSettings
from quantuminspire.settings.user_settings import UserSettings


class ConfigManager:
    """Manage configuration settings across project and user level scopes."""

    def __init__(
        self, project_settings: Optional[ProjectSettings] = None, user_settings: Optional[UserSettings] = None
    ) -> None:
        try:
            self._project_settings = project_settings or ProjectSettings()
        except FileNotFoundError:
            raise RuntimeError("Project not initialised. Please run ConfigManager.init() from project root.")
        self._user_settings = user_settings or UserSettings()
        self._configurable_keys = self._compute_flattened_keys()

    def _compute_flattened_keys(self) -> Dict[str, List[BaseConfigSettings]]:
        """Build a mapping of flattened configuration field keys to the settings objects that define them.

        This method inspects each settings object in priority order, extracts its flattened field keys,
        and produces a dictionary where each key is a dot-notation field path (e.g., "backend_type", "project.name")
        and the value is a list of settings instances that declare that field.

        Returns:
            A mapping of field paths to the settings objects that define them.
            Example:
                {
                    "backend_type": [ProjectSettings, UserSettings],
                    "project.name": [ProjectSettings],
                }
        """
        # Stores flattened keys for each settings class name
        flattened_keys_by_class: Dict[str, List[str]] = {
            setting.__class__.__name__: BaseConfigSettings.flatten_fields(setting)
            for setting in self._settings_priority
        }

        # Maps each flattened key to the settings objects that define it
        keys_to_settings: Dict[str, List[BaseConfigSettings]] = {}

        for setting in self._settings_priority:
            class_name = setting.__class__.__name__
            for field_key in flattened_keys_by_class[class_name]:
                keys_to_settings.setdefault(field_key, []).append(setting)

        return keys_to_settings

    @property
    def _settings_priority(self) -> List[BaseConfigSettings]:
        """Return the list of settings objects in priority order for resolving values.

        The first object has the highest priority when retrieving a setting, followed
        by the next in the list. Typically, the order is:

            1. Project settings (higher priority)
            2. User settings (lower priority)

        Returns:
            A list of BaseConfigSettings instances in priority order.
        """
        return [self._project_settings, self._user_settings]

    def _get_source_and_value(self, key: str) -> Tuple[str, Any]:
        """Get the value of a setting and the source settings object that provides it.

        This method searches through all configured settings objects in a defined
        priority order (typically project → user) to determine the value for a given
        key and which settings object it came from.

        The resolution follows these rules:
            1. Skip any settings object that does not have the requested attribute.
            2. Return the first non-None value found, along with its source.
            3. If all values are None but the attribute exists in at least one object,
            return the last seen source and value (even if None).

        Args:
            key: The dot-separated setting key to retrieve.

        Returns:
            A tuple (source_name, value):
                - source_name: The class name of the settings object that provided the value.
                - value: The resolved value of the setting (can be None if all values are None).

        Examples:
            # Suppose project settings has `backend_type=None` and user settings has `backend_type=2`
            source, value = config._get_source_and_value("backend_type")
            # Returns ('usersettings', 2)

            # If the attribute exists only in project settings as None
            source, value = config._get_source_and_value("project.id")
            # Returns ('projectsettings', None)
        """

        last_value = None
        last_source = None

        for setting in self._configurable_keys[key]:
            value = setting.get_value(key)

            last_value = value
            last_source = setting.__class__.__name__.lower().removesuffix("settings")

            if value is not None:
                return last_source, last_value

        assert last_source is not None
        return last_source, last_value

    def get(self, key: str) -> Any:
        """Retrieve the value of a configurable setting by key.

        Args:
            key: The dot-separated setting key to retrieve.

        Returns:
            The current value of the setting.

        Raises:
            ValueError: If the key is not a valid configurable setting.
        """
        if key not in self._configurable_keys:
            raise ValueError(f"Key '{key}' is invalid")
        _, value = self._get_source_and_value(key)
        return value

    def set(self, key: str, value: Any, is_user: bool) -> None:
        """Set the value of a configurable setting in the appropriate scope.

        Args:
            key: The dot-separated setting key to set.
            value: The value to assign to the setting.
            is_user: If True, set the setting in the user-level/global scope;
                        else set in the project-level/local scope.

        Raises:
            ValueError: If the key is not configurable or the scope is disallowed
                (e.g., setting a user-only key in project scope or vice versa).

        Notes:
            - When a shared setting is set in the user-level/global scope, it will clear the
            corresponding value in the project-level/local scope to maintain precedence.
        """

        if key not in self._configurable_keys:
            raise ValueError(f"Key '{key}' is invalid")

        key_settings = self._configurable_keys[key]

        target_setting = None

        if len(key_settings) == 2:  # shared key
            project_settings, user_settings = key_settings
            target_setting = user_settings if is_user else project_settings

            # Clear project override if setting user-level value
            if is_user:
                project_settings.clear(key)
        else:
            target_setting = key_settings[0]
            if (target_setting is self._user_settings and not is_user) or (
                target_setting is self._project_settings and is_user
            ):
                raise ValueError(
                    f"Scope mismatch for '{key}'. Expected: 'is_user={not is_user}', " f"Provided 'is_user={is_user}'."
                )

        assert target_setting is not None
        target_setting.set_value(key, value)

    def _resolve_field_values(self) -> dict[str, Any]:
        """Collect all configurable fields with their current value and source.

        Returns:
            A flat dictionary mapping each configurable key to a dict with:
                'value': the current value of the setting
                'source': the settings object it came from
        """

        flat: dict[str, Any] = {}
        for key in self._configurable_keys:
            source, value = self._get_source_and_value(key)
            flat[key] = {"value": value, "source": source}
        return flat

    def _group_fields(self, flat_fields: dict[str, Any]) -> dict[str, Any]:
        """Group flat dot-notation fields by their top-level key.

        Args:
            flat_fields: A dictionary of flat dot-notation keys to value/source dicts.

        Returns:
            A nested dictionary grouped by top-level keys.
            Example:
                Flat: {'project.name': {...}, 'project.id': {...}, 'algorithm.type': {...}}
                Grouped: {'project': {'name': {...}, 'id': {...}}, 'algorithm': {'type': {...}}}
        """

        grouped_fields: dict[str, Any] = {}
        for key, info in flat_fields.items():
            parts = key.split(".")
            if len(parts) == 1:
                grouped_fields[parts[0]] = info
            else:
                top, rest = parts[0], ".".join(parts[1:])
                grouped_fields.setdefault(top, {})[rest] = info
        return grouped_fields

    def inspect(self) -> Dict[str, Any]:
        """Return all configurable settings with their values and sources, grouped by top-level key.

        This method collects all settings from the underlying sources and returns them
        as a nested dictionary, with top-level keys grouping related fields.

        Returns:
            A nested dictionary of settings with structure:
                {'project': {'name': {'value': ..., 'source': ...}, ...},
                'algorithm': {'type': {'value': ..., 'source': ...}, ...}, ...}
        """

        return self._group_fields(self._resolve_field_values())

    @classmethod
    def initialize(cls, path: Path) -> None:
        """Initialize a project configuration in the given directory.

        This method creates the necessary project configuration file(s)
        at the specified path, by calling `ProjectSettings.initialize`.

        Args:
            path: The directory where the project configuration
                should be initialized. Defaults to the current working directory.
        """
        ProjectSettings.initialize(path)
