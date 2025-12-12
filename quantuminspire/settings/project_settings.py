from pathlib import Path
from typing import Any, Dict

from quantuminspire.settings.base_settings import BaseConfigSettings, ensure_config_file_exists
from quantuminspire.settings.models import Algorithm, Job, Project


class ProjectSettings(BaseConfigSettings):

    algorithm: Algorithm = Algorithm()
    project: Project = Project()
    job: Job = Job()


    @classmethod
    def find_project_root(cls, start: Path | None = None) -> Path:
        """Search upward from start until the project marker is found."""
        if start is None:
            start = Path.cwd()

        current = start.resolve()

        while True:
            marker = current.joinpath(*cls.file_marker())
            if marker.exists():
                return current

            if current.parent == current:  # Reached filesystem root
                break

            current = current.parent

        raise FileNotFoundError("Project root not found")

    @classmethod
    def base_dir(cls) -> Path:
        return cls.find_project_root()

    @classmethod
    def default_factory(cls) -> Dict[str, Any]:
        return {}

    @classmethod
    def initialize(cls, path: Path) -> None:
        ensure_config_file_exists(
            file_path=cls.json_file(path=path),
            file_encoding=cls.model_config.get("env_file_encoding"),
            default_factory=cls.default_factory,
        )
