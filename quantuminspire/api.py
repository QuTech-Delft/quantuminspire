from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, cast
from urllib.parse import urlparse

import requests
from compute_api_client import (
    Algorithm,
    AlgorithmType,
    BackendType,
    FinalResult,
    Job,
    JobStatus,
    Project,
)
from pydantic import TypeAdapter

from quantuminspire.managers.auth_manager import AuthManager
from quantuminspire.managers.config_manager import ConfigManager
from quantuminspire.managers.job_manager import JobManager, JobOptions
from quantuminspire.settings.models import AlgorithmName, LocalAlgorithm, Url
from quantuminspire.settings.user_settings import UserSettings


class Api:

    def __init__(
        self,
        config_manager: Optional[ConfigManager] = None,
        auth_manager: Optional[AuthManager] = None,
        job_manager: Optional[JobManager] = None,
        host: Optional[str] = None,
        persist_data_path: Optional[Path] = None
    ) -> None:
        if host is not None:
            init_dir = persist_data_path or Path.cwd()
            ConfigManager.initialize(init_dir)
            user_settings = UserSettings(default_host=host)
            self._config_manager = config_manager or ConfigManager(user_settings=user_settings)
        else:
            self._config_manager = config_manager or ConfigManager()

        self._auth_manager = auth_manager or AuthManager(user_settings=self._config_manager.user_settings)
        self._job_manager = job_manager or JobManager(self._config_manager)

        if host is not None:
            self.login()

    def login(self, hostname: Optional[str] = None, override_auth_config: bool = False, force: bool = False) -> None:
        host_url: Optional[Url] = None
        if hostname is not None:
            host_url = TypeAdapter(Url).validate_python(self._resolve_protocol(hostname))

        resolved_host = self._resolve(host_url, "default_host")

        if force or self.login_required(resolved_host):
            self._auth_manager.login(resolved_host, override_auth_config)
            self.set_setting("default_host", resolved_host, is_user=True)
        else:
            print("Already logged in, simply refreshing tokens")
            self._auth_manager.refresh_tokens(resolved_host)

    def login_required(self, host: Url) -> bool:
        return self._auth_manager.login_required(host)

    def execute_algorithm(
        self,
        path_to_file: str,
        backend_type_id: Optional[int] = None,
        num_shots: Optional[int] = None,
        store_raw_data: Optional[bool] = False,
        algorithm_name: Optional[str] = None,
        persist: bool = False,
    ) -> JobOptions:
        """Executes the algorithm located at the specified path.

        Args:
            path_to_file (str): The file path to the algorithm to be executed.
            backend_type_id (int): The backend type ID to execute the algorithm on.
            num_shots (Optional[int]): The number of shots to execute the algorithm with.
            store_raw_data (Optional[bool]): Whether to store the raw data from the execution.
            algorithm_name (Optional[str]): The name of the algorithm to be used for persistence.
                Required if persist is True.
            persist (bool): Whether to persist the algorithm in the project settings.

        Returns:
            JobOptions: The job options for the submitted job.
        """
        if persist:
            self.check_project_id()

            if not algorithm_name:
                raise ValueError(
                    "algorithm_name is required when you want to persist the data. "
                    "Please add it to the function call of execute_algorithm()"
                )

            algorithms = self.get_setting("project.algorithms")
            if algorithm_name not in algorithms.keys():
                self.initialize_algorithm(algorithm_name=algorithm_name, file_path=path_to_file)

        return self.submit_job(
            file_path=path_to_file,
            algorithm_name=algorithm_name,
            backend_type_id=backend_type_id,
            num_shots=num_shots,
            store_raw_data=store_raw_data,
            persist=persist,
        )

    def initialize_project(self, project_name: str, project_description: str = "", path: Optional[str] = None) -> None:
        """Initialize a remote project, storing its settings locally.

        Does nothing if a project is already initialized.

        Args:
            project_name (str): The name of the project.
            project_description (Optional[str]): An optional description for the project.
            path (Optional[str]): An optional path to initialize the ConfigManager with.
            Defaults to current working directory.
        """

        init_dir = Path(path) if path is not None else Path.cwd()
        ConfigManager.initialize(init_dir)
        try:
            self.check_project_id()
        except RuntimeError:
            remote_project: Project = self.initialize_remote_project(project_name, project_description)
            self.set_setting("project.id", remote_project.id)
            self.set_setting("project.name", remote_project.name)
            self.set_setting("project.description", remote_project.description)
            self.set_setting("project.algorithms", {})


    def initialize_algorithm(
        self,
        algorithm_name: str,
        file_path: str = "",
        backend_type_id: Optional[int] = None,
        num_shots: Optional[int] = None,
        store_raw_data: Optional[bool] = False,
    ) -> None:
        """Create a remote algorithm and register it in local settings.

        Args:
            algorithm_name (str): The name of the algorithm.
            file_path (str): Path to the algorithm file.
            backend_type_id (Optional[int]): Default backend type ID.
            num_shots (Optional[int]): Default number of shots.
            store_raw_data (Optional[bool]): Whether to store raw data by default.
        """
        self.check_project_id()
        project_id = self.get_setting("project.id")

        algorithm_name = TypeAdapter(AlgorithmName).validate_python(algorithm_name)

        remote_algorithm = self.create_remote_algorithm(project_id, algorithm_name, file_path)
        local_algorithm: LocalAlgorithm = LocalAlgorithm(
            id=remote_algorithm.id,
            file_path=file_path,
            backend_type_id=backend_type_id,
            num_shots=num_shots,
            store_raw_data=store_raw_data,
        )
        self._add_algorithm_to_settings(algorithm_name, local_algorithm)

    def get_status(
        self, algorithm_name: str, wait: Optional[bool] = False, timeout: Optional[int] = 10
    ) -> JobStatus:
        """Get the status of the most recent job for the given algorithm.

        Args:
            algorithm_name (str): The name of the algorithm.
            wait (Optional[bool]): Whether to wait for job completion before returning.
            timeout (Optional[int]): Maximum seconds to wait when wait=True.

        Returns:
            JobStatus: The current status of the job.
        """
        job_id = self.get_algorithm_setting(algorithm_name, "job_id")

        if wait:
            try:
                return self._job_manager.wait_for_job_completion(job_id, timeout=timeout).status
            except TimeoutError:
                print("Timeout while waiting for job completion. Returning current status.")

        return self.get_job(job_id).status

    def get_algorithm_final_result(self, algorithm_name: str) -> FinalResult | None:
        """Get the final result of the most recent job for the given algorithm.

        Args:
            algorithm_name (str): The name of the algorithm.

        Returns:
            FinalResult | None: The final result of the job, or None if not available.
        """
        job_id = self.get_algorithm_setting(algorithm_name, "job_id")
        return self.get_final_result(job_id)

    def check_project_id(self) -> None:
        """Verify that a project is initialized in the current settings.

        Raises:
            RuntimeError: If no project ID is found in the settings.
        """
        try:
            if self.get_setting("project.id") is None:
                raise RuntimeError("No project found. Please create a project by calling initialize_project()")
        except ValueError:
            raise RuntimeError("No project found. Please create a project by calling initialize_project()")

    def submit_job(
        self,
        file_path: str,
        algorithm_name: Optional[str],
        num_shots: Optional[int] = None,
        store_raw_data: Optional[bool] = None,
        backend_type_id: Optional[int] = None,
        persist: bool = False,
    ) -> JobOptions:

        if not persist and algorithm_name is None:
            if backend_type_id is None:
                raise ValueError("backend_type_id not provided")

            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            options: Dict[str, Any] = {
                "project_name": f"Project created on {timestamp}",
                "project_description": "Project created for non-persistent algorithm",
                "algorithm_name": f"Algorithm created on {timestamp}",
                "backend_type_id": backend_type_id,
                "number_of_shots": num_shots,
                "raw_data_enabled": store_raw_data,
            }
        elif persist and algorithm_name is None:
            raise ValueError("algorithm_name must be provided when persist is True")
        else:
            options = self._get_job_options(cast(str, algorithm_name), num_shots, store_raw_data, backend_type_id)

        job_options = self._job_manager.run_flow(JobOptions(**(options | {"file_path": Path(file_path)})))

        if persist:
            local_algorithm = LocalAlgorithm(
                id=job_options.algorithm_id,
                file_path=str(job_options.file_path),
                num_shots=job_options.number_of_shots,
                store_raw_data=job_options.raw_data_enabled,
                job_id=job_options.job_id,
                backend_type_id=backend_type_id,
            )
            self._add_algorithm_to_settings(job_options.algorithm_name, local_algorithm)

        return job_options

    def get_backend_types(self) -> List[BackendType]:
        return self._job_manager.get_backend_types()

    def get_job(self, job_id: Optional[int] = None) -> Job:
        job_id = self._resolve(job_id, "job.id")
        assert job_id is not None
        return self._job_manager.get_job(job_id)

    def get_final_result(self, job_id: Optional[int] = None) -> FinalResult | None:
        job_id = self._resolve(job_id, "job.id")
        assert job_id is not None
        return self._job_manager.get_final_result(job_id)

    def get_final_result_by_algorithm_name(self, algorithm_name: str) -> FinalResult | None:
        job_id = self.get_algorithm_setting(algorithm_name, "job_id")
        return self.get_final_result(job_id)


    def _get_local_algorithm(self, algorithm_name: str) -> LocalAlgorithm:
        algorithms = self.get_setting("project.algorithms")
        try:
            local_algorithm: LocalAlgorithm = algorithms[algorithm_name]
            return local_algorithm
        except KeyError:
            raise ValueError(f"Algorithm '{algorithm_name}' not found in settings.")

    def _add_algorithm_to_settings(self, algorithm_name: str, local_algorithm: LocalAlgorithm) -> None:
        algorithms = self.get_setting("project.algorithms")
        algorithms[algorithm_name] = local_algorithm
        self.set_setting("project.algorithms", algorithms, is_user=False)

    def initialize_remote_project(self, project_name: str, project_description: Optional[str] = "") -> Project:
        host = self.get_setting("default_host")
        owner_id = self._config_manager.user_settings.auths[host].owner_id
        return self._job_manager.create_project(owner_id, project_name, cast(str, project_description))

    def create_remote_algorithm(self, project_id: int, algorithm_name: str, file_path: str) -> Algorithm:
        if file_path:
            algorithm_type = self._job_manager.get_algorithm_type(Path(file_path))
        else:
            algorithm_type = AlgorithmType.HYBRID
        return self._job_manager.create_algorithm(project_id, algorithm_name, algorithm_type)

    def view_settings(self) -> Dict[str, Any]:
        return self._config_manager.inspect()

    def get_setting(self, key: str) -> Any:
        return self._config_manager.get(key)

    def get_algorithm_setting(self, algorithm_name: str, setting_name: str) -> Any:
        local_algorithm = self._get_local_algorithm(algorithm_name)
        return getattr(local_algorithm, setting_name)

    def set_setting(self, key: str, value: Any, is_user: bool = False) -> None:
        return self._config_manager.set(key, value, is_user)

    def set_algorithm_setting(self, algorithm_name: str, setting_name: str, value: Any) -> None:
        local_algorithm = self._get_local_algorithm(algorithm_name)
        setattr(local_algorithm, setting_name, value)
        self._add_algorithm_to_settings(algorithm_name, local_algorithm)

    def _get_job_options(
        self,
        algorithm_name: str,
        num_shots: Optional[int] = None,
        store_raw_data: Optional[bool] = None,
        backend_type_id: Optional[int] = None,
    ) -> Dict[str, Any]:

        options: Dict[str, Any] = {
            "project_id": self._config_manager.get("project.id"),
            "project_name": self._config_manager.get("project.name"),
            "project_description": self._config_manager.get("project.description"),
            "algorithm_id": self._resolve_algorithm_setting(None, "id", algorithm_name),
            "backend_type_id": self._resolve_algorithm_setting(backend_type_id, "backend_type_id", algorithm_name),
            "number_of_shots": self._resolve_algorithm_setting(num_shots, "num_shots", algorithm_name),
            "raw_data_enabled": self._resolve_algorithm_setting(store_raw_data, "store_raw_data", algorithm_name),
            "algorithm_name": algorithm_name,
        }

        return options

    def _resolve_algorithm_setting(self, override: Optional[Any], setting_name: str, algorithm_name: str) -> Any:
        local_algorithm = self._get_local_algorithm(algorithm_name)
        return override if override is not None else getattr(local_algorithm, setting_name)

    def _resolve(self, override: Optional[Any], key: str) -> Any:
        return override if override is not None else self._config_manager.get(key)

    @staticmethod
    def _resolve_protocol(url: str) -> str:
        """Add 'https://' protocol to the URL if not already present.

        Args:
            url: The URL to which to add the protocol.
        """
        parsed = urlparse(url)

        if parsed.scheme:
            return url

        try:
            response = requests.head(f"https://{url}", timeout=3, allow_redirects=True)
            if response.status_code < 400:
                return f"https://{url}"
        except requests.RequestException:
            pass

        return f"http://{url}"
