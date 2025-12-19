import pytest

from quantuminspire.auth_manager.auth_manager import AuthManager


@pytest.fixture
def auth_manager() -> AuthManager:
    return AuthManager()


def test_login(auth_manager: AuthManager) -> None:

    auth_manager.login("https://some-example.com")
