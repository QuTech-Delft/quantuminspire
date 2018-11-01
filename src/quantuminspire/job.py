from coreapi.exceptions import ErrorMessage


class QuantumInspireJob:

    def __init__(self, api, job_identifier):
        """ The QuantumInstpire Job class encapsulates the base job of the API and has
            methods to check the status and retieve the results from the API.

        Arguments:
            api (QuantumInspireApi): An instance to the API.
            job_identifier (int): The job identification number.
        """
        QuantumInspireJob.__check_arguments(api, job_identifier)
        self.__job_identifier = job_identifier
        self.__api = api

    @staticmethod
    def __check_arguments(api, job_identifier):
        """ Checks whether the supplied arguments are of correct type.

        Arguments:
            api (QuantumInspireApi): An instance to the API.
            job_identifier (int): The job identification number.

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

    def check_status(self):
        """ Checks the execution status of the job.

        Returns:
            str: The status of the job.
        """
        job = self.__api.get_job(self.__job_identifier)
        return job['status']

    def retrieve_results(self):
        """ Gets the results of the job.

        Returns:
            OrderedDict: The execution results with a histogram item containing the result
            histogram of the job. When an error has occured the raw_text item shall not be
            an empty string.
        """
        job = self.__api.get_job(self.__job_identifier)
        result_uri = job['results']
        return self.__api.get(result_uri)

    def get_job_identifier(self):
        """ Gets the set job identification number for the wrapped job.

        Returns:
            int: The job identification number.
        """
        return self.__job_identifier

    def get_project_identifier(self):
        """ Gets the project identification number of the wrappered job.

        Returns:
            int: The project identification number.
        """
        job = self.__api.get_job(self.__job_identifier)
        asset = self.__api.get(job['input'])
        return asset['project_id']
