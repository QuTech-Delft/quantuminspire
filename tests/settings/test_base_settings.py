import json
from pathlib import Path
from typing import Any, Dict, Optional

import pytest
from pydantic import BaseModel, Field

from quantuminspire.settings.base_settings import BaseConfigSettings
from tests.conftest import TestBaseDirMixin


class DummyTestModel(BaseModel):
    foo: Optional[int] = Field(None)
    bar: Optional[str] = Field(None)


class DummyTestSettings(TestBaseDirMixin, BaseConfigSettings):
    """A concrete test implementation that stores settings in a temporary directory."""

    test_model: DummyTestModel = DummyTestModel()

    @classmethod
    def default_factory(cls) -> Dict[str, Any]:
        return {"test_model": {"foo": 123, "bar": "hello"}, "backend_type": None}


@pytest.fixture
def test_settings(tmp_path: Path) -> DummyTestSettings:
    DummyTestSettings._override_base_dir = tmp_path
    instance = DummyTestSettings()
    return instance


def test_json_file_exists(test_settings: DummyTestSettings) -> None:

    # Arrange & Act
    read_data = json.loads(test_settings.json_file().read_text("utf-8"))

    # Assert
    assert read_data == test_settings.default_factory()
    assert test_settings.test_model.foo == 123
    assert test_settings.test_model.bar == "hello"
    assert test_settings.backend_type is None


def test_get_value_simple_field(test_settings: DummyTestSettings) -> None:
    assert test_settings.get_value("backend_type") is None


def test_get_value_nested_field(test_settings: DummyTestSettings) -> None:
    assert test_settings.get_value("test_model.foo") == 123
    assert test_settings.get_value("test_model.bar") == "hello"


def test_set_value_simple_field(test_settings: DummyTestSettings) -> None:

    read_data_before = json.loads(test_settings.json_file().read_text("utf-8"))
    new_backend_type = 100

    # Act
    test_settings.set_value("backend_type", new_backend_type)
    read_data_after = json.loads(test_settings.json_file().read_text("utf-8"))

    # Assert
    assert test_settings.get_value("backend_type") == new_backend_type
    assert read_data_before["backend_type"] is None
    assert read_data_after["backend_type"] == new_backend_type


def test_set_value_nested_field(test_settings: DummyTestSettings) -> None:
    read_data_before = json.loads(test_settings.json_file().read_text("utf-8"))
    new_foo = 200

    # Act
    test_settings.set_value("test_model.foo", new_foo)
    read_data_after = json.loads(test_settings.json_file().read_text("utf-8"))

    # Assert
    assert test_settings.get_value("test_model.foo") == new_foo
    assert read_data_before["test_model"]["foo"] == 123
    assert read_data_after["test_model"]["foo"] == new_foo


def test_flatten_fields(test_settings: DummyTestSettings) -> None:
    # Act
    flattened_fields = BaseConfigSettings.flatten_fields(test_settings)

    # Assert
    assert flattened_fields == ["backend_type", "test_model.foo", "test_model.bar"]


def test_ensure_file_path_exists_for_coverage(tmp_path: Path) -> None:

    DummyTestSettings._override_base_dir = tmp_path
    assert not DummyTestSettings.json_file().exists()
    _ = DummyTestSettings()
    _ = DummyTestSettings()
    assert DummyTestSettings.json_file().exists()
