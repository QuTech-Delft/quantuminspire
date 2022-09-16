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

from typing import Any, Dict, List, Union
from qiskit.exceptions import QiskitError
from qiskit.result import postprocess, Result
from qiskit.result.models import ExperimentResult

from quantuminspire.exceptions import QiskitBackendError


class QIResult(Result):  # type: ignore
    """
    A result object returned by QIJob:
        qi_backend = QI.get_backend('QX single-node simulator')
        job = qi_backend.retrieve_job(job_id)
        qi_result = job.result()
    """
    def __init__(self, backend_name: str, backend_version: str, qobj_id: str, job_id: str, success: bool,
                 results: List[ExperimentResult], date: Any = None, status: Any = None, header: Any = None,
                 **kwargs: Any) -> None:
        """
        Construct a new QIResult object. Not normally called directly, use a QIJob to get the QIResult.
        Based on Qiskit Result.

        :param backend_name: backend name.
        :param backend_version: backend version, in the form X.Y.Z.
        :param qobj_id: user-generated Qobj id.
        :param job_id: unique execution id from the backend.
        :param success: True if complete input qobj executed correctly. (Implies each experiment success)
        :param results: corresponding results for array of experiments of the input qobj
        :param date: date to be added to the result object
        :param status: status to be added to the result object
        :param header: header to be added to the result object
        :param kwargs: other parameters (added as metadata to the result object)
        """
        super().__init__(backend_name, backend_version, qobj_id, job_id, success,
                         results, date, status, header, **kwargs)

    def get_raw_result(self, field_name: str, experiment: Any = None) -> Union[List[Dict[str, Any]],
                                                                               List[List[List[str]]],
                                                                               List[List[Dict[str, float]]]]:
        """
        Get the specific and unprocessed result data of an experiment.
        Can handle single and multi measurement results.

        :param field_name: the specific result that is requested
            Can be one of 'calibration', 'counts', 'memory', 'probabilities' or the multi measurement results
            'counts_multiple_measurement', 'memory_multiple_measurement', 'probabilities_multiple_measurement'

        :param experiment: the index of the experiment (str or QuantumCircuit or Schedule or int or None),
            as specified by ``get_data()``.

        :return:
            A list with result structures which holds the specific unprocessed result for each experiment.

        :raises QiskitBackendError: raised if the results requested are not in the results for the experiment(s).
        """
        results_list = []

        if experiment is None:
            exp_keys = range(len(self.results))
        else:
            exp_keys = [experiment]  # type: ignore

        for key in exp_keys:
            if field_name in self.data(key).keys():
                result_values = self.data(key)[field_name]
                results_list.append(result_values)
            else:
                raise QiskitBackendError(f'Result does not contain {field_name} data for experiment "{key}"')
        return results_list

    def get_probabilities(self, experiment: Any = None) -> Union[Dict[str, float], List[Dict[str, float]]]:

        """Get the probability data of an experiment. The probability data is added as a separate result by
        Quantum Inspire backend.

        :param experiment: the index of the experiment (str or QuantumCircuit or Schedule or int or None),
            as specified by ``get_data()``.

        :return:
            A single or a list of dictionaries which holds the states and probabilities for respectively 1 or more
            experiment result.

        :raises QiskitBackendError: raised if there are no probabilities in a result for the experiment(s).
        """
        if experiment is None:
            exp_keys = range(len(self.results))
        else:
            exp_keys = [experiment]  # type: ignore

        dict_list: List[Dict[str, float]] = []
        for key in exp_keys:
            exp = self._get_experiment(key)
            try:
                header = exp.header.to_dict()
            except (AttributeError, QiskitError):  # header is not available
                header = None

            if "probabilities" in self.data(key).keys():
                probabilities = self.data(key)["probabilities"]
                dict_list.append(postprocess.format_counts(probabilities, header))
            else:
                raise QiskitBackendError(f'No probabilities for experiment "{key}"')

        # Return first item of dict_list if size is 1
        if len(dict_list) == 1:
            return dict_list[0]

        return dict_list

    def get_probabilities_multiple_measurement(self, experiment: Any = None) -> Union[List[Dict[str, float]],
                                                                                      List[List[Dict[str, float]]]]:
        """
        Get the probability data of an experiment for all measurement blocks.
        The probability data is added as a separate result by Quantum Inspire backend.

        :param experiment: the index of the experiment (str or QuantumCircuit or Schedule or int or None),
            as specified by ``get_data()``.

        :return:
            One list or a list of list of dictionaries which holds the states and probabilities for each measurement
            block for respectively 1 or more experiment result.

        :raises QiskitBackendError: raised if there are no multi measurement probabilities in a result for the
            experiment(s).
        """
        if experiment is None:
            exp_keys = range(len(self.results))
        else:
            exp_keys = [experiment]  # type: ignore

        list_of_dict_list: List[List[Dict[str, float]]] = []

        for key in exp_keys:
            exp = self._get_experiment(key)
            try:
                header = exp.header.to_dict()
            except (AttributeError, QiskitError):  # header is not available
                header = None

            if "probabilities_multiple_measurement" in self.data(key).keys():
                dict_list: List[Dict[str, float]] = []
                for probabilities in self.data(key)["probabilities_multiple_measurement"]:
                    dict_list.append(postprocess.format_counts(probabilities, header))
                list_of_dict_list.append(dict_list)
            else:
                raise QiskitBackendError(f'No probabilities_multiple_measurement for experiment "{key}"')

        # Return first item of list_dict_list if size is 1
        if len(list_of_dict_list) == 1:
            return list_of_dict_list[0]

        return list_of_dict_list

    def get_calibration(self, experiment: Any = None) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        """Get the calibration data of an experiment. The calibration data is added as a separate result item by
        Quantum Inspire backend.

        :param experiment: the index of the experiment, as specified by ``get_data()``.
                experiment can be: str or QuantumCircuit or Schedule or int or None

        :return:
            Single or a list of dictionaries which holds the calibration data for respectively 1 or more experiment(s).
            Exact format depends on the backend. A simulator backend has no calibration data (None is returned)

        :raises QiskitBackendError: raised if there is no calibration data in a result for the experiment(s).
        """
        if experiment is None:
            exp_keys = range(len(self.results))
        else:
            exp_keys = [experiment]  # type: ignore

        dict_list: List[Dict[str, float]] = []
        for key in exp_keys:
            if "calibration" in self.data(key).keys():
                calibration = self.data(key)["calibration"]
                dict_list.append(calibration)
            else:
                raise QiskitBackendError(f'No calibration data for experiment "{key}"')

        # Return first item of dict_list if size is 1
        if len(dict_list) == 1:
            return dict_list[0]

        return dict_list
