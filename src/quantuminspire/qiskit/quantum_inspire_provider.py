from copy import copy

from coreapi.auth import BasicAuthentication
from qiskit.providers import BaseProvider

from quantuminspire.api import QuantumInspireAPI
from quantuminspire.exceptions import ApiError
from quantuminspire.qiskit.backend_qx import QuantumInspireBackend

QI_URL = 'https://api.quantum-inspire.com'


class QuantumInspireProvider(BaseProvider):
    """ Provides a backend and an api for a single Quantum Inspire account. """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._backends = []
        self._api = None

    def __str__(self):
        return 'QI'

    def backends(self, name=None, **kwargs):
        """
        Provides a list of backends.

        Args:
            name (str): Name of the requested backend.
            **kwargs (dict): Used for filtering, not implemented.

        Returns:
            list<QuantumInspireBackend>: List of backends that meet the filter requirements.
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

    def set_authentication_details(self, email, password, qi_url=None):
        """
        Set a single authentication for Quantum Inspire.

        Args:
            email (str): A valid email address.
            password (str): Password for the account.
            qi_url: Optional URL that points to quantum-inspire api.

        """
        authentication = BasicAuthentication(email, password)
        if qi_url is None:
            qi_url = QI_URL
        self._api = QuantumInspireAPI(qi_url, authentication)
