from copy import copy
from typing import List, Optional, Any

import coreapi
from qiskit.providers import BaseProvider

from quantuminspire.credentials import get_token_authentication, get_basic_authentication
from quantuminspire.qiskit.backend_qx import QuantumInspireBackend
from quantuminspire.api import QuantumInspireAPI
from quantuminspire.exceptions import ApiError

QI_URL = 'https://api.quantum-inspire.com'


class QuantumInspireProvider(BaseProvider):  # type: ignore
    """ Provides a backend and an api for a single Quantum Inspire account. """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._backends: List[QuantumInspireBackend] = []
        self._api: Optional[QuantumInspireAPI] = None

    def __str__(self) -> str:
        return 'QI'

    def backends(self, name: Optional[str] = None, **kwargs: Any) -> List[QuantumInspireBackend]:
        """
        Provides a list of backends.

        Args:
            name: Name of the requested backend.
            **kwargs: Used for filtering, not implemented.

        Returns:
            List of backends that meet the filter requirements.
        """
        if self._api is None:
            raise ApiError('Authentication details have not been set.')

        available_backends = self._api.get_backend_types()
        if name is not None:
            available_backends = list(filter(lambda b: b['name'] == name, available_backends))
        backends = []
        for backend in available_backends:
            if backend['is_allowed']:
                config = copy(QuantumInspireBackend.DEFAULT_CONFIGURATION)
                config.backend_name = backend['name']
                backends.append(QuantumInspireBackend(self._api, provider=self, configuration=config))

        return backends

    def set_authentication_details(self, email: str, password: str, qi_url: str = QI_URL) -> None:
        """
        DEPRECATED(version>'0.5.0', reason="Replaced with method set_basic_authentication(email, password, qi_url)")
        Set a single authentication for Quantum Inspire.

        Args:
            email: A valid email address.
            password: Password for the account.
            qi_url: URL that points to quantum-inspire api. Default value: 'https://api.quantum-inspire.com'.

        """
        self.set_basic_authentication(email, password)

    def set_basic_authentication(self, email: str, password: str, qi_url: str = QI_URL) -> None:
        """
        Set up basic authentication for Quantum Inspire.

        Args:
            email: A valid email address.
            password: Password for the account.
            qi_url: URL that points to quantum-inspire api. Default value: 'https://api.quantum-inspire.com'.
        """
        authentication = get_basic_authentication(email, password)
        self.set_authentication(authentication, qi_url)

    def set_token_authentication(self, token: str, qi_url: str = QI_URL) -> None:
        """
        Set up token authentication for Quantum Inspire.

        Args:
            token: A valid token.
            qi_url: URL that points to quantum-inspire api. Default value: 'https://api.quantum-inspire.com'.
        """
        authentication = get_token_authentication(token)
        self.set_authentication(authentication, qi_url)

    def set_authentication(self, authentication: Optional[coreapi.auth.AuthBase] = None,
                           qi_url: str = QI_URL) -> None:
        """
        Initializes the API and sets the authentication for Quantum Inspire.

        Args:
            authentication: The authentication, can be one of the following coreapi authentications:
                            BasicAuthentication(email, password), HTTP authentication with valid email/password.
                            TokenAuthentication(token, scheme="token"), token authentication with a valid API-token.
                            When authentication is None, api will try to load a token from the default resource.
            qi_url: URL that points to quantum-inspire api. Default value: 'https://api.quantum-inspire.com'.
        """
        self._api = QuantumInspireAPI(qi_url, authentication)
