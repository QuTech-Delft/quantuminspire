"""Module containing the handler for the Quantum Inspire persistent configuration."""

from __future__ import annotations

import asyncio
import json
import time
from os import PathLike
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Type, cast

import typer
from compute_api_client import ApiClient, Configuration, MembersApi
from pydantic import BaseModel, BeforeValidator, HttpUrl
from pydantic.fields import Field, FieldInfo
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict
from typing_extensions import Annotated

Url = Annotated[str, BeforeValidator(lambda value: str(HttpUrl(value)).rstrip("/"))]

DEFAULT_CONFIG = """
{
  "auths": {
    "https://staging.qi2.quantum-inspire.com": {
      "well_known_endpoint":  "https://auth.qi2.quantum-inspire.com/realms/oidc_staging/.well-known/openid-configuration"
    },
    "https://api.qi2.quantum-inspire.com": {
      "well_known_endpoint":  "https://auth.qi2.quantum-inspire.com/realms/oidc_production/.well-known/openid-configuration"
    }
  }
}
"""


def ensure_config_file_exists(file_path: Path, file_encoding: Optional[str] = None) -> None:
    """Create the file if it does not exist.

    Args:
        file_path: the file path.
        file_encoding: The encoding of the file.
    """
    if not file_path.exists():
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.open("w", encoding=file_encoding).write(DEFAULT_CONFIG)


class JsonConfigSettingsSource(PydanticBaseSettingsSource):
    """Settings source that loads variables from a JSON file specified in the Config class.

    Returns:
        A dictionary with the setting variables from the JSON file.
    """

    def get_field_value(self, field: FieldInfo, field_name: str) -> Tuple[Any, str, bool]:
        raise NotImplementedError

    def __call__(self) -> Any:
        encoding = self.config.get("env_file_encoding")

        assert isinstance(self.config["json_file"], PathLike)

        json_config_file = Path(self.config["json_file"])

        ensure_config_file_exists(json_config_file, encoding)

        return json.loads(json_config_file.read_text(encoding))


class TokenInfo(BaseModel):
    """A pydantic model for storing all information regarding oauth access and refresh tokens."""

    access_token: str
    expires_in: int
    refresh_token: str
    refresh_expires_in: int
    generated_at: float = Field(default_factory=time.time)

    @property
    def access_expires_at(self) -> float:
        """Timestamp containing the time when the access token will expire."""
        return self.generated_at + self.expires_in

    @property
    def refresh_expires_at(self) -> float:
        """Timestamp containing the time when the refresh token will expire."""
        return self.generated_at + self.refresh_expires_in


class AuthSettings(BaseModel):
    """Pydantic model for storing all auth related settings for a given host."""

    client_id: str = "compute-job-manager"
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


class Settings(BaseSettings):  # pylint: disable=too-few-public-methods
    """The settings class for the Quantum Inspire persistent configuration."""

    model_config = SettingsConfigDict(
        env_file_encoding="utf-8",
        env_prefix="QI2_",
        json_file=Path.joinpath(Path.home(), ".quantuminspire", "config.json"),
    )

    auths: Dict[Url, AuthSettings]

    default_host: Url = "https://staging.qi2.quantum-inspire.com"

    @property
    def default_auth_settings(self) -> AuthSettings:
        return self.auths[self.default_host]

    # R0913: Too many arguments (6/5) (too-many-arguments)
    @classmethod
    def settings_customise_sources(  # pylint: disable=R0913
        cls,
        settings_cls: Type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> Tuple[PydanticBaseSettingsSource, ...]:
        """Customise the settings sources (by adding, removing and changing the order of sources).

        Args:
            init_settings: The initial settings (Settings object creation): highest priority.
            env_settings: The configuration settings (Config inner object creation).
            file_secret_settings: The file secret settings: lowest priority

        Returns:
            The original sources, with
            - the JSON file as source added after the env settings and before the file secret settings.
            The order determines the priority!
        """
        return (
            init_settings,
            env_settings,
            JsonConfigSettingsSource(settings_cls),
            file_secret_settings,
        )

    def store_tokens(self, host: Url, tokens: TokenInfo) -> None:
        """

        :param host: the hostname of the api for which the tokens are intended
        :param tokens: OAuth access and refresh tokens
        :return: None

        This functions stores the team_member_id, access and refresh tokens in the config.json file.
        """
        self.auths[host].tokens = tokens
        member_id = self.get_team_member_id(host=host, access_token=tokens.access_token)
        self.auths[host].team_member_id = member_id
        assert isinstance(self.model_config["json_file"], PathLike)
        Path(self.model_config["json_file"]).write_text(
            self.model_dump_json(indent=2), encoding=self.model_config.get("env_file_encoding")
        )

    @staticmethod
    async def _fetch_team_member_id(host: str, access_token: str) -> int:
        config = Configuration(host=host, access_token=access_token)
        async with ApiClient(config) as api_client:
            api_instance = MembersApi(api_client)
            members_page = await api_instance.read_members_members_get()
            members = members_page.items
            if len(members) == 1:
                member_id = members[0].id
                return cast(int, member_id)

            typer.echo("Choose a member ID from the list for project configuration.")
            json_string = "[" + ",".join(member.model_dump_json(indent=4) for member in members) + "]"
            typer.echo(json_string)

            member_ids = [member.id for member in members]

            while True:
                try:
                    member_id = int(input("Please enter one of the given ids: "))
                    if member_id not in member_ids:
                        raise ValueError
                    return cast(int, member_id)
                except ValueError:
                    typer.echo("Invalid input. Please enter a valid id or CTRL + C to cancel.")

    @classmethod
    def get_team_member_id(cls, host: str, access_token: str) -> int:
        return asyncio.run(cls._fetch_team_member_id(host, access_token))
