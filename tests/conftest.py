from typing import Any

import pytest
from pytest_mock import MockerFixture

CONFIGURATION = """
{
  "auths": {
    "https://host": {
      "well_known_endpoint": "https://some_url"
    }
  },
  "default_host": "https://host"
}
"""


@pytest.fixture
def mocked_config_file(mocker: MockerFixture) -> Any:
    config_file = mocker.patch("quantuminspire.util.configuration.Path")()
    config_file.exists.return_value = True
    config_file.read_text.return_value = CONFIGURATION
    return config_file
