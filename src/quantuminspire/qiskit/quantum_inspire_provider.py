from copy import copy
from typing import List, Optional, Any

from coreapi.auth import BasicAuthentication
from qiskit.providers import BaseProvider

from quantuminspire.qiskit.backend_qx import QuantumInspireBackend
from quantuminspire.api import QuantumInspireAPI
from quantuminspire.exceptions import ApiError

QI_URL = 'https://api.quantum-inspire.com'


class QuantumInspireProvider(BaseProvider):
    """ Provides a backend and an api for a single Quantum Inspire account. """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._backends = []
        self._api = None

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
            available_backends = filter(lambda b: b['name'] == name, available_backends)
        backends = []
        for backend in available_backends:
            if backend['is_allowed']:
                config = copy(QuantumInspireBackend.DEFAULT_CONFIGURATION)
                config.backend_name = backend['name']
                backends.append(QuantumInspireBackend(self._api, provider=self, configuration=config))

        return backends

    def set_authentication_details(self, email: str, password: str, qi_url: Optional[str] = None) -> None:
        """
        Set a single authentication for Quantum Inspire.

        Args:
            email: A valid email address.
            password: Password for the account.
            qi_url: Optional URL that points to quantum-inspire api.

        """
        authentication = BasicAuthentication(email, password)
        if qi_url is None:
            qi_url = QI_URL
        self._api = QuantumInspireAPI(qi_url, authentication)
