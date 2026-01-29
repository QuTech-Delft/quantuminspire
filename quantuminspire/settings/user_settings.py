import time
from pathlib import Path
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

from quantuminspire.settings.base_settings import BaseConfigSettings
from quantuminspire.settings.models import Url


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
