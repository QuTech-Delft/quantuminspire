from pathlib import Path
from typing import Any, Dict

from quantuminspire.settings.base_settings import BaseConfigSettings
from quantuminspire.settings.models import Algorithm, Job, Project


class ProjectSettings(BaseConfigSettings):

    algorithm: Algorithm = Algorithm()
    project: Project = Project()
    job: Job = Job()

    @classmethod
    def base_dir(cls) -> Path:
        return Path.cwd()

    @classmethod
    def default_factory(cls) -> Dict[str, Any]:
        return {}
