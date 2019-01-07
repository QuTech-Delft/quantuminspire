import unittest
from unittest import mock

from coreapi.auth import BasicAuthentication
from qiskit.providers import QiskitBackendNotFoundError

from quantuminspire.exceptions import ApiError
from quantuminspire.qiskit.quantum_inspire_provider import QuantumInspireProvider, QI_URL


class TestQuantumInspireProvider(unittest.TestCase):
    def test_backends(self):
        with mock.patch('quantuminspire.qiskit.quantum_inspire_provider.QuantumInspireAPI') as api:
            quantum_inpire_provider = QuantumInspireProvider()
            with self.assertRaises(ApiError):
                quantum_inpire_provider.backends(name='quantum-inspire')
            email = 'bla@bla.bla'
            secret = 'secret'
            quantum_inpire_provider.set_authentication_details(email, secret)
            authentication = BasicAuthentication(email, secret)
            api.assert_called_with(QI_URL, authentication)
            quantum_inpire_provider._api.get_backend_types.return_value = [{'name': 'qi_simulator', 'is_allowed': True}]
            backend = quantum_inpire_provider.get_backend(name='qi_simulator')
            self.assertEqual('qi_simulator', backend.name())
            with self.assertRaises(QiskitBackendNotFoundError) as error:
                quantum_inpire_provider.get_backend(name='not-quantum-inspire')
            self.assertEqual(('No backend matches the criteria',), error.exception.args)

    def test_set_authentication(self):
        with mock.patch('quantuminspire.qiskit.quantum_inspire_provider.QuantumInspireAPI') as api:
            quantum_inpire_provider = QuantumInspireProvider()
            with self.assertRaises(ApiError):
                quantum_inpire_provider.backends(name='quantum-inspire')
            email = 'bla@bla.bla'
            secret = 'secret'
            quantum_inpire_provider.set_authentication_details(email, secret)
            authentication = BasicAuthentication(email, secret)
            api.assert_called_with(QI_URL, authentication)
            quantum_inpire_provider._api.get_backend_types.return_value = [{'name': 'qi_simulator', 'is_allowed': True}]
            backend = quantum_inpire_provider.get_backend(name='qi_simulator')
            self.assertEqual('qi_simulator', backend.name())

    def test_set_authentication_with_url(self):
        with mock.patch('quantuminspire.qiskit.quantum_inspire_provider.QuantumInspireAPI') as api:
            api.get_backend_types.return_value = [{'name': 'qi_simulator', 'is_allowed': True}]
            quantum_inpire_provider = QuantumInspireProvider()
            with self.assertRaises(ApiError):
                quantum_inpire_provider.backends(name='quantum-inspire')
            email = 'bla@bla.bla'
            secret = 'secret'
            url = 'https/some-api.api'
            quantum_inpire_provider.set_authentication_details(email, secret, url)
            authentication = BasicAuthentication(email, secret)
            api.assert_called_with(url, authentication)

    def test_string_method(self):
        quantum_inpire_provider = QuantumInspireProvider()
        expected = 'QI'
        actual = str(quantum_inpire_provider)
        self.assertEqual(expected, actual)
