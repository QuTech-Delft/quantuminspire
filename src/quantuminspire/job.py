""" Quantum Inspire SDK

Copyright 2018 QuTech Delft

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""
from typing import Dict, Any
from coreapi.exceptions import ErrorMessage


class QuantumInspireJob:

    def __init__(self, api: Any, job_identifier: int) -> None:
        """ The QuantumInspire Job class encapsulates the base job of the API and has
            methods to check the status and retrieve the results from the API.

        Arguments:
            api: An instance to the API.
            job_identifier: The job identification number.
        """
        QuantumInspireJob.__check_arguments(api, job_identifier)
        self.__job_identifier: int = job_identifier
        self.__api: Any = api

    @staticmethod
    def __check_arguments(api: Any, job_identifier: int) -> None:
        """ Checks whether the supplied arguments are of correct type.

        Arguments:
            api: An instance to the API.
            job_identifier: The job identification number.

        Raises:
            ValueError: When the api is not a QuantumInspireApi or when the
            job identifier is not found.
        """
        if type(api).__name__ != 'QuantumInspireAPI':
            raise ValueError('Invalid Quantum Inspire API!')
        try:
            _ = api.get_job(job_identifier)
        except ErrorMessage as error:
            raise ValueError('Invalid job identifier!') from error

    def check_status(self) -> str:
        """ Checks the execution status of the job.

        Returns:
            The status of the job. Can be: 'NEW', 'RUNNING', 'COMPLETE', 'CANCELLED'
        """
        job = self.__api.get_job(self.__job_identifier)
        return str(job['status'])

    def retrieve_results(self) -> Dict[str, Any]:
        """ Gets the results of the job.

        Returns:
            The execution results with a histogram item containing the result
            histogram of the job. When an error has occurred the raw_text item shall not be
            an empty string.
        """
        result: Dict[str, Any] = self.__api.get_result_from_job(self.__job_identifier)
        return result

    def get_job_identifier(self) -> int:
        """ Gets the set job identification number for the wrapped job.

        Returns:
            The job identification number.
        """
        return self.__job_identifier

    def get_project_identifier(self) -> int:
        """ Gets the project identification number of the wrapped job.

        Returns:
            The project identification number.
        """
        asset = self.__api.get_asset_from_job(self.__job_identifier)
        return int(asset['project_id'])
