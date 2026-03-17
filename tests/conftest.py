import inspect
from pathlib import Path
from typing import Optional

import pytest
from _pytest.monkeypatch import MonkeyPatch
from pydantic import PrivateAttr

from quantuminspire.api import Api


class TestBaseDirMixin:
    _override_base_dir: Optional[Path] = PrivateAttr(default=None)

    @classmethod
    def base_dir(cls) -> Path:
        assert cls._override_base_dir is not None
        return cls._override_base_dir


@pytest.fixture(autouse=True)
def mock_refresh_auth_tokens(request: pytest.FixtureRequest, monkeypatch: MonkeyPatch) -> None:
    """Replace every method decorated with @_refresh_auth_tokens with its
    original (unwrapped) function.  functools.wraps stores the original
    callable on the ``__wrapped__`` attribute, so we can discover all
    decorated methods without enumerating them by name.

    Tests marked with ``@pytest.mark.keep_auth_tokens_wrapper`` opt out of
    this patching so they can exercise the decorator itself.
    """
    if request.node.get_closest_marker("keep_auth_tokens_wrapper"):
        return

    for name, method in inspect.getmembers(Api, predicate=inspect.isfunction):
        if hasattr(method, "__wrapped__"):
            monkeypatch.setattr(Api, name, method.__wrapped__)
