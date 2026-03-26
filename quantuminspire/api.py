from collections.abc import Callable
from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import Any, Concatenate, Dict, List, Optional, ParamSpec, TypeVar, cast
from urllib.parse import urlparse

import requests
from compute_api_client import BackendType, FinalResult, Job, JobStatus, Project, Result
from pydantic import TypeAdapter

from quantuminspire.managers.auth_manager import AuthManager
from quantuminspire.managers.config_manager import ConfigManager
from quantuminspire.managers.job_manager import JobManager, JobOptions
from quantuminspire.settings.models import AlgorithmName, LocalAlgorithm, Url

P = ParamSpec("P")
R = TypeVar("R")


class Api:

    @staticmethod
    def _refresh_auth_tokens(
        fn: Callable[Concatenate["Api", P], R],
    ) -> Callable[Concatenate["Api", P], R]:
        """Decorator that refreshes authentication tokens before calling the wrapped function.

        Args:
            fn: The function to wrap.

        Returns:
            The wrapped function with token refresh logic applied.
        """

        @wraps(fn)
        def wrapped(self: "Api", *args: P.args, **kwargs: P.kwargs) -> R:
            hostname = self._config_manager.get("default_host")

            if self._login_required(hostname):
                self.login(hostname)
            else:
                self._auth_manager.refresh_tokens(hostname)

            return fn(self, *args, **kwargs)

        return wrapped

    def __init__(
        self,
        config_manager: Optional[ConfigManager] = None,
        auth_manager: Optional[AuthManager] = None,
        job_manager: Optional[JobManager] = None,
        host: Optional[str] = None,
    ) -> None:
        """Initialize the Api instance.

        Args:
            config_manager: Manager for configuration settings. Uses default if not provided.
            auth_manager: Manager for authentication. Uses default if not provided.
            job_manager: Manager for job operations. Uses default if not provided.
            host: The host URL to connect to. Overrides the configured default host if provided.
        """
        self._config_manager = config_manager or ConfigManager()

        if host is not None:
            host_url = TypeAdapter(Url).validate_python(self._resolve_protocol(host))
            self._config_manager.set("default_host", host_url, is_user=True)

        self._auth_manager = auth_manager or AuthManager(user_settings=self._config_manager.user_settings)
        self._job_manager = job_manager or JobManager()

    def login(self, hostname: Optional[str] = None, override_auth_config: bool = False, force: bool = False) -> None:
        """Log in to the Quantum Inspire platform.

        Args:
            hostname: The host URL to log in to. Uses the configured default if not provided.
            override_auth_config: Whether to override existing authentication configuration.
            force: Force a new login even if already logged in.
        """
        host_url: Optional[Url] = None
        if hostname is not None:
            host_url = TypeAdapter(Url).validate_python(self._resolve_protocol(hostname))

        resolved_host = self._resolve(host_url, "default_host")

        if force or self._login_required(resolved_host):
            self._auth_manager.login(resolved_host, override_auth_config)
            self.set_setting("default_host", resolved_host, is_user=True)
        else:
            print("Already logged in, simply refreshing tokens")
            self._auth_manager.refresh_tokens(resolved_host)

    def _login_required(self, host: Url) -> bool:
        """Check whether a login is required for the given host.

        Args:
            host: The host URL to check.

        Returns:
            True if login is required, False otherwise.
        """
        return self._auth_manager.login_required(host)

    def execute_algorithm(
        self,
        path_to_file: Path,
        backend_type_id: Optional[int] = None,
        num_shots: Optional[int] = None,
        store_raw_data: Optional[bool] = False,
        algorithm_name: Optional[str] = None,
        persist: bool = False,
    ) -> JobOptions:
        """Execute the algorithm located at the specified path.

        Args:
            path_to_file: Path to the algorithm file to execute.
            backend_type_id: ID of the backend type to use. Required when persist is False.
            num_shots: Number of shots to run.
            store_raw_data: Whether to store raw data from the execution.
            algorithm_name: Name of the algorithm. Required when persist is True.
            persist: Whether to persist the algorithm and project settings locally.

        Returns:
            A JobOptions object containing details about the submitted job.
        """
        if persist:
            self._check_project_id()

            if not algorithm_name:
                raise ValueError(
                    "algorithm_name is required when you want to persist the data. "
                    "Please add it to the function call of execute_algorithm()"
                )

            algorithms = self.get_setting("project.algorithms")
            if algorithm_name not in algorithms.keys():
                self.initialize_algorithm(algorithm_name=algorithm_name, file_path=path_to_file)

        job = self._submit_job(
            file_path=path_to_file,
            algorithm_name=algorithm_name,
            backend_type_id=backend_type_id,
            num_shots=num_shots,
            store_raw_data=store_raw_data,
            persist=persist,
        )

        if not persist:
            print("Successfully executed algorithm with job id:", job.job_id)
        return job

    @_refresh_auth_tokens
    def initialize_project(self, project_name: str, project_description: str = "", path: Optional[str] = None) -> None:
        """Initialize a remote project and store its settings locally.

        Does nothing if a project is already initialized.

        Args:
            project_name: Name of the project to initialize.
            project_description: Description of the project.
            path: Local path where the project settings should be stored. Uses the current directory if not provided.
        """

        init_dir = Path(path) if path is not None else Path.cwd()
        self._config_manager.initialize(init_dir)

        try:
            project_id = self._check_project_id()
            remote_project = self._job_manager.read_project(project_id)
            if remote_project is None:
                remote_project = self.initialize_remote_project(project_name, project_description)
            else:
                remote_project = self._job_manager.update_project(project_id, project_name, project_description)
        except RuntimeError:
            remote_project = self.initialize_remote_project(project_name, project_description)

        assert isinstance(remote_project, Project)
        self.set_setting("project.id", remote_project.id)
        self.set_setting("project.name", remote_project.name)
        self.set_setting("project.description", remote_project.description)

    @_refresh_auth_tokens
    def initialize_algorithm(
        self,
        algorithm_name: str,
        file_path: Path,
        backend_type_id: Optional[int] = None,
        num_shots: Optional[int] = None,
        store_raw_data: Optional[bool] = False,
    ) -> None:
        """Initialize a remote algorithm and store its settings locally.

        Args:
            algorithm_name: Name of the algorithm to initialize.
            file_path: Path to the algorithm file.
            backend_type_id: ID of the backend type to use.
            num_shots: Number of shots for the algorithm.
            store_raw_data: Whether to store raw data from executions.
        """
        project_id = self._check_project_id()
        algorithm_name = TypeAdapter(AlgorithmName).validate_python(algorithm_name)

        try:
            local_algorithm = self._get_local_algorithm(algorithm_name)

            if local_algorithm.id is None:
                remote_algorithm = None
            else:
                remote_algorithm = self._job_manager.read_algorithm(local_algorithm.id)

            if remote_algorithm is None:
                remote_algorithm = self._job_manager.create_algorithm(
                    project_id, algorithm_name, self._job_manager.get_algorithm_type(file_path)
                )
            else:
                assert isinstance(local_algorithm.id, int)
                remote_algorithm = self._job_manager.update_algorithm(
                    project_id, local_algorithm.id, algorithm_name, self._job_manager.get_algorithm_type(file_path)
                )
        except ValueError:
            remote_algorithm = self._job_manager.create_algorithm(
                project_id, algorithm_name, self._job_manager.get_algorithm_type(file_path)
            )

        local_algorithm = LocalAlgorithm(
            id=remote_algorithm.id,
            file_path=file_path,
            backend_type_id=backend_type_id,
            num_shots=num_shots,
            store_raw_data=store_raw_data,
        )
        self._add_algorithm_to_settings(algorithm_name, local_algorithm)

    @_refresh_auth_tokens
    def get_status_by_algorithm_name(self, algorithm_name: str, wait: bool = False, timeout: float = 60) -> JobStatus:
        """Get the status of the most recent job for the given algorithm.

        Args:
            algorithm_name: Name of the algorithm to get the status for.
            wait: Whether to wait for the job to complete before returning.
            timeout: Maximum time in seconds to wait for job completion.

        Returns:
            The current job status.
        """
        job_id = self.get_algorithm_setting(algorithm_name, "job_id")
        return self.get_status_by_job_id(job_id, wait=wait, timeout=timeout)

    @_refresh_auth_tokens
    def get_status_by_job_id(self, job_id: int, wait: bool = False, timeout: float = 60) -> JobStatus:
        """Get the status of the job with the given ID.

        Args:
            job_id: The ID of the job to get the status for.
            wait: Whether to wait for the job to complete before returning.
            timeout: Maximum time in seconds to wait for job completion.

        Returns:
            The current job status.
        """
        if wait:
            try:
                return self._job_manager.wait_for_job_completion(job_id, timeout=timeout).status
            except TimeoutError:
                print("Timeout while waiting for job completion. Returning current status.")

        return self.get_job(job_id).status

    def _check_project_id(self) -> int:
        """Verify that a project is initialized in the current settings.

        Raises:
            RuntimeError: If no project is found in the current settings.
        """
        try:
            project_id = self.get_setting("project.id")
            if project_id is None:
                raise RuntimeError("No project found. Please create a project by calling initialize_project()")
        except ValueError:
            raise RuntimeError("No project found. Please create a project by calling initialize_project()")

        assert isinstance(project_id, int)
        return project_id

    @_refresh_auth_tokens
    def _submit_job(
        self,
        file_path: Path,
        algorithm_name: Optional[str],
        num_shots: Optional[int] = None,
        store_raw_data: Optional[bool] = None,
        backend_type_id: Optional[int] = None,
        persist: bool = False,
    ) -> JobOptions:
        """Submit a job to the Quantum Inspire platform.

        Args:
            file_path: Path to the algorithm file to submit.
            algorithm_name: Name of the algorithm. Required when persist is True.
            num_shots: Number of shots to run.
            store_raw_data: Whether to store raw data from the execution.
            backend_type_id: ID of the backend type to use. Required when persist is False.
            persist: Whether to persist the project and algorithm settings locally.

        Returns:
            A JobOptions object containing details about the submitted job.
        """

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

        host = self._config_manager.get("default_host")
        owner_id = self._config_manager.user_settings.auths[host].owner_id
        job_options = self._job_manager.run_flow(JobOptions(**(options | {"file_path": file_path})), owner_id)

        if persist:
            local_algorithm = LocalAlgorithm(
                id=job_options.algorithm_id,
                file_path=job_options.file_path,
                num_shots=job_options.number_of_shots,
                store_raw_data=job_options.raw_data_enabled,
                job_id=job_options.job_id,
                backend_type_id=backend_type_id,
            )
            self._add_algorithm_to_settings(job_options.algorithm_name, local_algorithm)
            self.set_setting("project.id", job_options.project_id)
            self.set_setting("project.name", job_options.project_name)
            self.set_setting("project.description", job_options.project_description)

        return job_options

    @_refresh_auth_tokens
    def get_backend_types(self) -> List[BackendType]:
        """Retrieve all available backend types.

        Returns:
            A list of all available backend types.
        """
        return self._job_manager.get_backend_types()

    @_refresh_auth_tokens
    def get_job(self, job_id: int) -> Job:
        """Retrieve job details by job ID.

        Args:
            job_id: The ID of the job to retrieve.

        Returns:
            The Job object for the given job ID.
        """
        return self._job_manager.get_job(job_id)

    def get_latest_job_of_algorithm(self, algorithm_name: str) -> Job:
        """Retrieve the latest job of algorithm by name.

        Args:
            algorithm_name: Name of the algorithm.

        Returns:
            The Job object for the latest job of the given algorithm.
        """
        job_id = self.get_algorithm_setting(algorithm_name, "job_id")
        return self.get_job(job_id)

    def get_final_result_by_algorithm_name(self, algorithm_name: str) -> FinalResult | None:
        """Get the final result of the most recent job for the given algorithm.

        Args:
            algorithm_name: Name of the algorithm to get the result for.

        Returns:
            The final result of the job, or None if not yet available.
        """
        job_id = self.get_algorithm_setting(algorithm_name, "job_id")
        return self.get_final_result_by_job_id(job_id)

    @_refresh_auth_tokens
    def get_final_result_by_job_id(self, job_id: int) -> FinalResult | None:
        """Get the final result of the job with the given ID.

        Args:
            job_id: The ID of the job to get the result for.

        Returns:
            The final result of the job, or None if not yet available.
        """
        return self._job_manager.get_final_result(job_id)

    def get_results_by_algorithm_name(self, algorithm_name: str) -> list[Result] | None:
        """Get the result of the most recent job for the given algorithm.

        Args:
            algorithm_name: Name of the algorithm to get the result for.

        Returns:
            The result of the job, or None if not yet available.
        """
        job_id = self.get_algorithm_setting(algorithm_name, "job_id")
        return self.get_results_by_job_id(job_id)

    @_refresh_auth_tokens
    def get_results_by_job_id(self, job_id: int) -> list[Result] | None:
        """Get the result of the job with the given ID.

        Args:
            job_id: The ID of the job to get the result for.

        Returns:
            The result of the job, or None if not yet available.
        """
        return self._job_manager.get_results(job_id)

    def _get_local_algorithm(self, algorithm_name: str) -> LocalAlgorithm:
        """Retrieve the local algorithm settings for the given algorithm name.

        Args:
            algorithm_name: Name of the algorithm to retrieve.

        Returns:
            The LocalAlgorithm object for the given algorithm name.
        """
        algorithms = self.get_setting("project.algorithms")
        try:
            local_algorithm: LocalAlgorithm = algorithms[algorithm_name]
            return local_algorithm
        except KeyError:
            raise ValueError(f"Algorithm '{algorithm_name}' not found in settings.")

    def _add_algorithm_to_settings(self, algorithm_name: str, local_algorithm: LocalAlgorithm) -> None:
        """Add or update an algorithm entry in the local settings.

        Args:
            algorithm_name: Name of the algorithm to add or update.
            local_algorithm: The LocalAlgorithm object to store.
        """
        algorithms = self.get_setting("project.algorithms")
        algorithms[algorithm_name] = local_algorithm
        self.set_setting("project.algorithms", algorithms, is_user=False)

    @_refresh_auth_tokens
    def initialize_remote_project(self, project_name: str, project_description: Optional[str] = "") -> Project:
        """Create a new remote project on the Quantum Inspire platform.

        Args:
            project_name: Name of the project to create.
            project_description: Description of the project.

        Returns:
            The created Project object.
        """
        host = self.get_setting("default_host")
        owner_id = self._config_manager.user_settings.auths[host].owner_id
        return self._job_manager.create_project(owner_id, project_name, cast(str, project_description))

    def view_settings(self) -> Dict[str, Any]:
        """Retrieve the current configuration settings.

        Returns:
            A dictionary containing all current configuration settings.
        """
        return self._config_manager.inspect()

    def get_setting(self, key: str) -> Any:
        """Get a configuration setting by key.

        Args:
            key: The dot-separated key of the setting to retrieve.

        Returns:
            The value of the requested setting.
        """
        return self._config_manager.get(key)

    def get_algorithm_setting(self, algorithm_name: str, setting_name: str) -> Any:
        """Get a specific setting for a named algorithm.

        Args:
            algorithm_name: Name of the algorithm.
            setting_name: Name of the setting to retrieve.

        Returns:
            The value of the requested algorithm setting.
        """
        local_algorithm = self._get_local_algorithm(algorithm_name)
        return getattr(local_algorithm, setting_name)

    def set_setting(self, key: str, value: Any, is_user: bool = False) -> None:
        """Set a configuration setting.

        Args:
            key: The dot-separated key of the setting to update.
            value: The value to set.
            is_user: Whether to store the setting at the user level.
        """
        return self._config_manager.set(key, value, is_user)

    def set_algorithm_setting(self, algorithm_name: str, setting_name: str, value: Any) -> None:
        """Set a specific setting for a named algorithm.

        Args:
            algorithm_name: Name of the algorithm.
            setting_name: Name of the setting to update.
            value: The value to set.
        """
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
        """Build job options from algorithm settings and any provided overrides.

        Args:
            algorithm_name: Name of the algorithm to build options for.
            num_shots: Number of shots. Overrides the algorithm's stored value if provided.
            store_raw_data: Whether to store raw data. Overrides the algorithm's stored value if provided.
            backend_type_id: ID of the backend type. Overrides the algorithm's stored value if provided.

        Returns:
            A dictionary of job options ready to be passed to the job manager.
        """
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
        """Resolve an algorithm setting using an override value or the stored algorithm value.

        Args:
            override: The override value. Used if not None.
            setting_name: The name of the setting to retrieve from the stored algorithm.
            algorithm_name: Name of the algorithm.

        Returns:
            The override value if provided, otherwise the stored algorithm setting value.
        """
        local_algorithm = self._get_local_algorithm(algorithm_name)
        return override if override is not None else getattr(local_algorithm, setting_name)

    def _resolve(self, override: Optional[Any], key: str) -> Any:
        """Resolve a value using an override or a configuration setting.

        Args:
            override: The override value. Used if not None.
            key: The configuration key to fall back to.

        Returns:
            The override value if provided, otherwise the configuration setting value.
        """
        return override if override is not None else self._config_manager.get(key)

    @staticmethod
    def _resolve_protocol(url: str) -> str:
        """Add 'https://' protocol to the URL if not already present.

        Args:
            url: The URL to resolve.

        Returns:
            The URL prefixed with 'https://' if the host is reachable via HTTPS, otherwise prefixed with 'http://'.
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
