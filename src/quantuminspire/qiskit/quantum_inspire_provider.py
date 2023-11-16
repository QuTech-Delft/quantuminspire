# Quantum Inspire SDK
#
# Copyright 2022 QuTech Delft
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from copy import copy
from typing import List, Optional, Any, Dict

import coreapi
from qiskit.providers.models import QasmBackendConfiguration
from qiskit.providers.provider import ProviderV1 as Provider

from quantuminspire.api import QuantumInspireAPI, QI_URL
from quantuminspire.credentials import get_token_authentication, get_basic_authentication
from quantuminspire.exceptions import QiskitBackendError
from quantuminspire.qiskit.backend_qx import QuantumInspireBackend


class QuantumInspireProvider(Provider):  # type: ignore
    """ Provides a backend and an api for a single Quantum Inspire account. """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._backends: Optional[List[QuantumInspireBackend]] = None
        self._filter: Optional[str] = None
        self._api: Optional[QuantumInspireAPI] = None

    def __str__(self) -> str:
        return 'QI'

    def get_api(self) -> QuantumInspireAPI:
        """ Provides the authenticated Quantum Inspire API.

        :return:
            The authenticated API.
        """
        if self._api is None:
            raise QiskitBackendError('Authentication details have not been set.')

        return self._api

    def backends(self, name: Optional[str] = None, **kwargs: Any) -> List[QuantumInspireBackend]:
        """ Provides a list of backends.

        :param name: Name of the requested backend. When None we take all available backends
        :param kwargs: Used for filtering, not implemented.

        :return:
            List of backends that meet the filter requirements (is_allow == True).
        """
        if self._backends is not None and self._filter == name:
            return self._backends

        if self._api is None:
            raise QiskitBackendError('Authentication details have not been set.')

        available_backends = self._api.get_backend_types()
        if name is not None:
            available_backends = list(filter(lambda b: b['name'] == name, available_backends))
        self._filter = name
        self._backends = []
        for backend in available_backends:
            if backend['is_allowed']:
                config = copy(QuantumInspireBackend.DEFAULT_CONFIGURATION)
                self._adjust_backend_configuration(config, backend)
                self._backends.append(QuantumInspireBackend(self._api, provider=self, configuration=config))

        return self._backends

    @staticmethod
    def _adjust_backend_configuration(config: QasmBackendConfiguration, backend: Dict[str, Any]) -> None:
        """
        Overwrites the default configuration with the backend dependent configuration items.

        :param config: The configuration with default configuration that is adjusted.
        :param backend: The backend for which the configuration items are adjusted.
        """
        config.backend_name = backend['name']
        config.n_qubits = backend['number_of_qubits']
        if len(backend['allowed_operations']) > 0:
            config.basis_gates = []
            for keys in backend['allowed_operations']:
                if keys in ['single_gates', 'parameterized_single_gates', 'dual_gates',
                            'parameterized_dual_gates', 'triple_gates', 'wait', 'barrier', 'prep']:
                    for gate in backend['allowed_operations'][keys]:
                        if gate in ['x', 'y', 'z', 'h', 's', 't', 'rx', 'ry', 'rz', 'swap', 'cz', 'barrier']:
                            config.basis_gates += [gate]
                        elif gate == 'wait':
                            config.basis_gates += ['delay']
                        elif gate == 'i':
                            config.basis_gates += ['id']
                        elif gate == 'sdag':
                            config.basis_gates += ['sdg']
                        elif gate == 'tdag':
                            config.basis_gates += ['tdg']
                        elif gate == 'cnot':
                            config.basis_gates += ['cx']
                        elif gate == 'toffoli':
                            config.basis_gates += ['ccx']
                        elif gate == 'prep' or gate == 'prep_z':
                            config.basis_gates += ['reset']
            if 'rz' in config.basis_gates and 'ry' in config.basis_gates:
                config.basis_gates += ['u']
                config.basis_gates += ['p']

        config.simulator = not backend['is_hardware_backend']
        config.conditional = not backend['is_hardware_backend']
        config.max_shots = backend['max_number_of_shots']
        max_experiments = backend['max_number_of_simultaneous_jobs']
        config.max_experiments = max_experiments if max_experiments else 1
        coupling_map = []
        for i in range(len(backend['topology']['edges'])):
            for j in backend['topology']['edges'][i]:
                coupling_map.append([i, j])
        config.coupling_map = None if len(coupling_map) == 0 else coupling_map
        config.multiple_measurements = "flags" in backend and "multiple_measurement" in backend["flags"]
        config.parallel_computing = "flags" in backend and "parallel_computing" in backend["flags"]

    def set_authentication_details(self, email: str, password: str, qi_url: str = QI_URL) -> None:
        """Set a single authentication for Quantum Inspire.

        .. deprecated:: 0.5.0
           Replaced with method :meth:`~.set_basic_authentication`

        :param email: A valid email address.
        :param password: Password for the account.
        :param qi_url: URL that points to quantum-inspire api. Default value: 'https://api.quantum-inspire.com'.

        """
        self.set_basic_authentication(email, password, qi_url)

    def set_basic_authentication(self, email: str, password: str, qi_url: str = QI_URL) -> None:
        """Set up basic authentication for Quantum Inspire.

        :param email: A valid email address.
        :param password: Password for the account.
        :param qi_url: URL that points to quantum-inspire api. Default value: 'https://api.quantum-inspire.com'.
        """
        authentication = get_basic_authentication(email, password)
        self.set_authentication(authentication, qi_url)

    def set_token_authentication(self, token: str, qi_url: str = QI_URL) -> None:
        """
        Set up token authentication for Quantum Inspire.

        :param token: A valid token.
        :param qi_url: URL that points to quantum-inspire api. Default value: 'https://api.quantum-inspire.com'.
        """
        authentication = get_token_authentication(token)
        self.set_authentication(authentication, qi_url)

    def set_authentication(self, authentication: Optional[coreapi.auth.AuthBase] = None,
                           qi_url: str = QI_URL, project_name: Optional[str] = None) -> None:
        """
        Initializes the API and sets the authentication for Quantum Inspire.

        :param authentication: The authentication, can be one of the following coreapi authentications:

            * ``BasicAuthentication(email, password)``, HTTP authentication with valid email/password.
            * ``TokenAuthentication(token, scheme="token")``, token authentication with a valid API-token.

            When authentication is ``None``, the api will try to load a token from the default resource.

        :param qi_url: URL that points to quantum-inspire api. Default value: 'https://api.quantum-inspire.com'.
        :param project_name: The project name of the project that is used for executing the jobs.
        """
        self._api = QuantumInspireAPI(qi_url, authentication, project_name)

    def set_project_name(self, project_name: str) -> None:
        """
        Set the project name for the Quantum Inspire project that is used for executing the jobs.
        Default a generated project-name is used, but it can be overridden by the user.

        :param project_name: project name of the QI project used for executing the jobs.
        """
        if self._api is not None:
            self._api.project_name = project_name
