from pathlib import Path
from typing import Optional

from pydantic import PrivateAttr


class TestBaseDirMixin:
    _override_base_dir: Optional[Path] = PrivateAttr(default=None)

    @classmethod
    def base_dir(cls) -> Path:
        assert cls._override_base_dir is not None
        return cls._override_base_dir
