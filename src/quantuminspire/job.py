from coreapi.exceptions import ErrorMessage


class QuantumInspireJob:

    def __init__(self, api, job_identifier):
        QuantumInspireJob.__check_arguments(api, job_identifier)
        self.__job_identifier = job_identifier
        self.__api = api

    @staticmethod
    def __check_arguments(api, job_identifier):
        if type(api).__name__ != 'QuantumInspireAPI':
            raise ValueError('Invalid Quantum Inspire API!')
        try:
            _ = api.get_job(job_identifier)
        except ErrorMessage:
            raise ValueError('Invalid job identifier!')

    def check_status(self):
        job = self.__api.get_job(self.__job_identifier)
        return job['status']

    def retrieve_results(self):
        job = self.__api.get_job(self.__job_identifier)
        result_uri = job['results']
        return self.__api.get(result_uri)

    def get_job_identifier(self):
        return self.__job_identifier

    def get_project_identifier(self):
        job = self.__api.get_job(self.__job_identifier)
        asset = self.__api.get(job['input'])
        return asset['project_id']
