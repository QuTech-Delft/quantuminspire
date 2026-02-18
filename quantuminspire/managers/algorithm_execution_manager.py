from pathlib import Path
from typing import Any, Optional

from compute_api_client import (
    FinalResult,
    JobStatus,
    Project,
)

from quantuminspire.api import Api
from quantuminspire.managers.config_manager import ConfigManager
from quantuminspire.managers.job_manager import JobOptions
from quantuminspire.settings.models import LocalAlgorithm
from quantuminspire.settings.project_settings import ProjectSettings
from quantuminspire.settings.user_settings import UserSettings


class AlgorithmExecutionManager:

    def __init__(self, host: Optional[str] = None) -> None:

        ConfigManager.initialize(Path.cwd())

        self._host = host is not None or "https://staging.qi2.quantum-inspire.com"
        self._user_settings = UserSettings(default_host=self._host)
        self._config_manager = ConfigManager(user_settings=self._user_settings)
        self._project_settings = ProjectSettings()
        self._api = Api(config_manager=self._config_manager)
        self._api.login()

    def execute_algorithm(
        self,
        path_to_file: str,
        backend_type_id: Optional[int] = None,
        num_shots: Optional[int] = None,
        store_raw_data: Optional[bool] = False,
        algorithm_name: Optional[str] = None,
        persist: bool = False,
    ) -> JobOptions:
        """
        Executes the algorithm located at the specified path.

        Args:
            path_to_file (str): The file path to the algorithm to be executed.
            backend_type_id (int): The backend type ID to execute the algorithm on.
            num_shots (Optional[int]): The number of shots to execute the algorithm with.
            store_raw_data (Optional[bool]): Whether to store the raw data from the execution.
            algorithm_name (Optional[str]): The name of the algorithm to be used for persistence.
            Required if persist is True.
            persist (Optional[bool]): Whether to persist the algorithm in the project settings.

        Returns:
            dict: A dictionary containing the output data from the algorithm execution.
        """
        if persist:
            self.check_project_id()

            if not algorithm_name:
                raise ValueError(
                    "algorithm_name is required when you want to persist the data. "
                    "Please add it to the function call of execute_algorithm()"
                )

            algorithms = self._api.get_setting("project.algorithms")
            if algorithm_name not in algorithms.keys():
                self.init_algorithm(algorithm_name=algorithm_name, file_path=path_to_file)

        job_options = self._api.submit_job(
            file_path=path_to_file,
            algorithm_name=algorithm_name,
            backend_type_id=backend_type_id,
            num_shots=num_shots,
            store_raw_data=store_raw_data,
            persist=persist,
        )
        return job_options

    def init_project(self, project_name: str, project_description: Optional[str] = None) -> None:
        try:
            self.check_project_id()
        except RuntimeError:
            remote_project: Project = self._api.initialize_remote_project(project_name, project_description)
            self._api.set_setting("project.id", remote_project.id)
            self._api.set_setting("project.name", remote_project.name)
            self._api.set_setting("project.description", remote_project.description)
            self._api.set_setting("project.algorithms", {})

    @staticmethod
    def check_algorithm_name_validity(algorithm_name: str) -> None:
        """Sanitize algorithm name for use as JSON key and general compatibility."""
        if not algorithm_name or not algorithm_name.strip():
            raise ValueError("Algorithm name cannot be empty")

        if any(char in algorithm_name for char in ['"', "\\"]):
            raise ValueError("Algorithm name cannot contain double quotes or backslashes")

        if any(ord(char) < 32 for char in algorithm_name):
            raise ValueError("Algorithm name cannot contain control characters")

    def init_algorithm(
        self,
        algorithm_name: str,
        file_path: str = "",
        backend_type_id: Optional[int] = None,
        num_shots: Optional[int] = None,
        store_raw_data: Optional[bool] = False,
    ) -> None:
        self.check_project_id()
        project_id = self._api.get_setting("project.id")

        self.check_algorithm_name_validity(algorithm_name)

        remote_algorithm = self._api.create_remote_algorithm(project_id, algorithm_name, file_path)
        local_algorithm: LocalAlgorithm = LocalAlgorithm(
            id=remote_algorithm.id,
            file_path=file_path,
            backend_type_id=backend_type_id,
            num_shots=num_shots,
            store_raw_data=store_raw_data,
        )
        self._api.add_algorithm_to_settings(algorithm_name, local_algorithm)

    def get_status(self, algorithm_name: str, wait: Optional[bool] = False, timeout: Optional[int] = 10) -> JobStatus:
        job_id = self._api.get_algorithm_setting(algorithm_name, "job_id")

        if wait:
            try:
                return self._api.wait_for_job_completion(job_id, timeout=timeout).status
            except TimeoutError:
                print("Timeout while waiting for job completion. Returning current status.")

        return self._api.get_job(job_id).status

    def get_final_result(self, algorithm_name: str) -> FinalResult | None:
        job_id = self._api.get_algorithm_setting(algorithm_name, "job_id")
        return self._api.get_final_result(job_id)

    def check_project_id(self) -> None:
        try:
            if self._api.get_setting("project.id") is None:
                raise RuntimeError("No project found. Please create a project by calling init_project()")
        except ValueError:
            raise RuntimeError("No project found. Please create a project by calling init_project()")

    def set_algorithm_setting(self, algorithm_name: str, setting_name: str, value: Any) -> None:
        self._api.set_algorithm_setting(algorithm_name, setting_name, value)
