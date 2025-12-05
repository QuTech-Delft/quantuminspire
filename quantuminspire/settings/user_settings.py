from pathlib import Path
from typing import Any, Dict

from pydantic import Field

from quantuminspire.settings.base_settings import BaseConfigSettings
from quantuminspire.settings.models import Url


class UserSettings(BaseConfigSettings):

    default_host: Url = Field("https://api.quantum-inspire.com")

    @classmethod
    def base_dir(cls) -> Path:
        return Path.home()

    @classmethod
    def default_factory(cls) -> Dict[str, Any]:
        return {}
