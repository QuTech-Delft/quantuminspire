import asyncio
import time
import webbrowser
from typing import cast

import jwt
from compute_api_client import ApiClient, AuthConfigApi, Configuration, MembersApi
from compute_api_client.exceptions import ForbiddenException
from qi2_shared.utils import run_async

from quantuminspire.settings.models import Url
from quantuminspire.settings.user_settings import AuthSettings, TokenInfo, UserSettings
from quantuminspire.utils.authentication import AuthorisationError, OauthDeviceSession


class AuthManager:

    def __init__(self, user_settings: UserSettings) -> None:
        self._user_settings = user_settings

    def _is_authenticated(self, host: Url) -> bool:
        """Check whether the user is authenticated for the given host.

        Args:
            host: API host to check authentication for.

        Returns:
            True if authentication data exists for the host, False otherwise.
        """
        try:
            host_auth_settings = self._user_settings.auths[host]
            return host_auth_settings.tokens is not None
        except KeyError:
            return False

    def _is_refresh_token_valid(self, host: Url) -> bool:
        """Check whether the stored refresh token is still valid.

        Args:
            host: API host to validate the refresh token for.

        Returns:
            True if the refresh token can be used successfully, False otherwise.
        """
        try:
            self.refresh_tokens(host)
            return True
        except AuthorisationError:
            return False

    def refresh_tokens(self, host: Url) -> None:
        """Refresh OAuth tokens for the given host and store the updated values.

        Args:
            host: API host for which to refresh authentication tokens.
        """
        auth_settings = self._user_settings.auths[host]
        oauth_session = OauthDeviceSession(auth_settings)
        tokens = oauth_session.refresh()
        self._store_tokens(host, tokens)

    def login_required(self, host: Url) -> bool:
        """Return True if a full login flow is required for the host."""
        if not self._is_authenticated(host):
            return True

        if not self._is_refresh_token_valid(host):
            return True

        return False

    def login(self, host: Url, override_auth_config: bool) -> None:
        """Perform an interactive OAuth login for the given host.

        Optionally fetches authentication configuration, starts the OAuth device
        flow, stores the obtained tokens, and sets the team member ID.

        Args:
            host: API host to authenticate against.
            override_auth_config: If False, fetch auth configuration from the host
                before logging in.
        """
        if not override_auth_config:
            run_async(self._fetch_auth_settings(host))

        host_auth_settings = self._user_settings.auths[host]

        auth_session = OauthDeviceSession(host_auth_settings)

        login_info = auth_session.initialize_authorization()
        print(f"Please continue logging in by opening: {login_info['verification_uri_complete']} in your browser")
        print(f"If promped to verify a code, please confirm it is as follows: {login_info['user_code']}")
        webbrowser.open(login_info["verification_uri_complete"], new=2)
        tokens = auth_session.poll_for_tokens()
        self._store_tokens(host, tokens)
        print("Login successful!")
        print(f"Using member ID {host_auth_settings.team_member_id}")

    async def _fetch_auth_settings(self, host: Url) -> None:
        """Fetch suggested auth settings for host."""

        async with ApiClient(Configuration(host=host)) as api_client:
            auth_config = await AuthConfigApi(api_client).auth_config_auth_config_get()
            self._user_settings.auths[host] = AuthSettings(
                client_id=auth_config.client_id,
                audience=auth_config.audience,
                well_known_endpoint=auth_config.well_known_endpoint,
            )

    def _store_tokens(self, host: Url, tokens: TokenInfo) -> None:
        """Store OAuth tokens for a given host.

        Args:
            host: The hostname of the API for which the tokens are intended.
            tokens: An object containing OAuth access and refresh tokens.
        """
        self._user_settings.auths[host].tokens = tokens

        try:
            member_id = self._get_team_member_id(host=host, access_token=tokens.access_token)
        except ForbiddenException:
            raise PermissionError("Could not retrieve team member ID. Please check your host URL.")
        self._user_settings.auths[host].team_member_id = member_id
        self._user_settings.save()

    @staticmethod
    async def _fetch_team_member_id(host: str, access_token: str) -> int:
        """Retrieve or prompt for the team member ID associated with the access token.

        Args:
            host: API host to query.
            access_token: OAuth access token used for authentication.

        Returns:
            The selected team member ID.
        """
        config = Configuration(host=host, access_token=access_token)
        async with ApiClient(config) as api_client:
            api_instance = MembersApi(api_client)
            members_page = await api_instance.read_members_members_get()
            members = members_page.items
            if len(members) == 1:
                member_id = cast(int, members[0].id)
                return member_id

            print("Choose a member ID from the list for project configuration.")
            json_string = "[" + ",".join(member.model_dump_json(indent=4) for member in members) + "]"
            print(json_string)

            member_ids = [member.id for member in members]

            while True:
                try:
                    member_id = int(input("Please enter one of the given ids: "))
                    if member_id not in member_ids:
                        raise ValueError
                    return member_id
                except ValueError:
                    print("Invalid input. Please enter a valid id or CTRL + C to cancel.")

    @classmethod
    def _get_team_member_id(cls, host: str, access_token: str) -> int:
        return cast(int, run_async(cls._validate_token_and_retrieve_team_member_id(host, access_token)))

    @classmethod
    async def _validate_token_and_retrieve_team_member_id(cls, host: str, access_token: str) -> int:
        """Wait until the token is valid and retrieve the associated team member ID.

        Args:
            host: API host to query.
            access_token: OAuth access token.

        Returns:
            The resolved team member ID.
        """
        await cls._wait_until_token_becomes_valid(access_token)
        return await cls._fetch_team_member_id(host, access_token)

    @staticmethod
    async def _wait_until_token_becomes_valid(access_token: str) -> None:
        """Block until the access token becomes valid based on its issue time.

        Args:
            access_token: OAuth access token to validate.
        """
        decoded_token = jwt.decode(access_token, options={"verify_signature": False})
        token_issued_at = int(decoded_token["iat"])

        while True:
            current_time = int(time.time())
            time_diff = token_issued_at - current_time

            if time_diff > 0:
                await asyncio.sleep(time_diff)
            return
