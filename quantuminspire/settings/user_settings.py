import time
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlparse

import requests
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from qi2_shared.settings import Url

from quantuminspire.settings.base_settings import BaseConfigSettings


class TokenInfo(BaseModel):
    """A pydantic model for storing all information regarding oauth access and refresh tokens."""

    access_token: str
    expires_in: int
    refresh_token: str
    generated_at: float = Field(default_factory=time.time)

    @property
    def access_expires_at(self) -> float:
        """Timestamp containing the time when the access token will expire."""
        return self.generated_at + self.expires_in


class AuthSettings(BaseModel):
    """Pydantic model for storing all auth related settings for a given host."""

    client_id: str = "compute-job-manager"
    audience: str = "compute-job-manager"
    # Keycloak requires api-access in scope for compute-job-manager audience
    # Auth0 requires offline_access in scopefor sending a refresh token
    scope: str = "api-access openid profile email offline_access"
    code_challenge_method: str = "S256"
    code_verifyer_length: int = 64
    well_known_endpoint: Url = (
        "https://auth.qi2.quantum-inspire.com/realms/oidc_production/.well-known/openid-configuration"
    )
    tokens: Optional[TokenInfo] = None
    team_member_id: Optional[int] = None

    @property
    def owner_id(self) -> int:
        if self.team_member_id is None:
            raise ValueError("Please set the default team_member_id for this host!")
        return self.team_member_id


class UserSettings(BaseConfigSettings):
    default_host: Url = Field("https://api.quantum-inspire.com")
    auths: Dict[Url, AuthSettings]

    @field_validator("default_host", mode="before")
    @classmethod
    def validate_host(cls, value: str) -> str:
        return cls._resolve_protocol(value)

    def get_host(self) -> Url:
        """Environment variable overrides the default host from user settings."""
        return DevOverrides().dev_host or self.default_host

    @staticmethod
    def _resolve_protocol(url: str) -> str:
        """Add 'https://' protocol to the URL if not already present.

        Args:
            url: The URL to resolve.

        Returns:
            The URL prefixed with 'https://' if the host is reachable via HTTPS, otherwise prefixed with 'http://'.
        """
        parsed = urlparse(url)

        if parsed.scheme and parsed.netloc:
            return url

        # specific case to sidestep poinless probing of localhost with requests
        hostname = urlparse(f"//{url}").hostname
        if hostname in ["localhost", "127.0.0.1", "::1"]:
            return f"http://{url}"

        try:
            _ = requests.head(f"https://{url}", timeout=3, allow_redirects=True)
            return f"https://{url}"
        except requests.RequestException:
            pass

        return f"http://{url}"

    @classmethod
    def base_dir(cls) -> Path:
        return Path.home()

    @classmethod
    def default_factory(cls) -> Dict[str, Any]:
        return {"auths": {}}

    @classmethod
    def system_managed_fields(cls) -> set[str]:
        return {"auths"}

    @property
    def default_auth_settings(self) -> AuthSettings:
        return self.auths[self.default_host]


class DevOverrides(BaseSettings):
    """Developer-only runtime overrides. Read from the environment, never persisted."""

    model_config = SettingsConfigDict(env_prefix="QI2_")

    dev_host: Optional[Url] = None  # env var: QI2_DEV_HOST

    @field_validator("dev_host", mode="before")
    @classmethod
    def _resolve_dev_host(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return UserSettings.validate_host(value)
