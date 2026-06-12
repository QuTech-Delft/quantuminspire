from collections.abc import Callable
from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import Any, Concatenate, Dict, List, Optional, ParamSpec, TypeVar, cast
from urllib.parse import urlparse

import requests
from compute_api_client import (
    BackendType,
    CompileStage,
    FinalResult,
    Job,
    JobStatus,
    Project,
    Queue,
    Result,
)
from pydantic import TypeAdapter
from qi2_shared.settings import Url

from quantuminspire.managers.auth_manager import AuthManager
from quantuminspire.managers.config_manager import ConfigManager
from quantuminspire.managers.resource_manager import CompileOptions, JobOptions, ResourceManager
from quantuminspire.settings.models import AlgorithmName, LocalAlgorithm

P = ParamSpec("P")
R = TypeVar("R")

__all__ = ["CompileStage", "Api"]


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
        resource_manager: Optional[ResourceManager] = None,
        host: Optional[str] = None,
    ) -> None:
        """Initialize the Api instance.

        Args:
            config_manager: Manager for configuration settings. Uses default if not provided.
            auth_manager: Manager for authentication. Uses default if not provided.
            resource_manager: Manager for job operations. Uses default if not provided.
            host: The host URL to connect to. Overrides the configured default host if provided.
        """
        self._config_manager = config_manager or ConfigManager()

        if host is not None:
            host_url = TypeAdapter(Url).validate_python(self._resolve_protocol(host))
            self._config_manager.set("default_host", host_url, is_user=True)

        self._auth_manager = auth_manager or AuthManager(user_settings=self._config_manager.user_settings)
        self._resource_manager = resource_manager or ResourceManager()

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

    def logout(self, hostname: Optional[str] = None) -> None:
        """Log out of the Quantum Inspire platform by clearing stored tokens.

        Args:
            hostname: The host URL to log out from. Uses the configured default if not provided.
        """
        host_url: Optional[Url] = None
        if hostname is not None:
            host_url = TypeAdapter(Url).validate_python(self._resolve_protocol(hostname))

        resolved_host = self._resolve(host_url, "default_host")
        self._auth_manager.logout(resolved_host)
        print(f"Successfully logged out from {resolved_host}")

    @_refresh_auth_tokens
    def execute_algorithm(
        self,
        file_path: Optional[Path] = None,
        backend_type_id: Optional[int] = None,
        num_shots: Optional[int] = None,
        store_raw_data: Optional[bool] = False,
        algorithm_name: Optional[str] = None,
        persist: bool = False,
    ) -> JobOptions:
        """Execute the algorithm located at the specified path.

        Args:
            file_path: Path to the algorithm file to execute.
            backend_type_id: ID of the backend type to use. Required when persist is False.
            num_shots: Number of shots to run. If not provided, the backend type's default number of shots will be used.
            store_raw_data: Whether to store raw data from the execution.
            algorithm_name: Name of the algorithm. Required when persist is True.
            persist: Whether to persist the algorithm settings locally.

        Returns:
            A JobOptions object containing details about the submitted job.
        """
        if algorithm_name is None:
            if file_path is None:
                raise ValueError(
                    "file_path not provided. "
                    "Please provide a file_path or "
                    "the algorithm_name of a previously initialized algorithm."
                )
            if backend_type_id is None:
                raise ValueError(
                    "backend_type_id not provided. "
                    "Please provide a backend_type_id or "
                    "the algorithm_name of a previously initialized algorithm."
                )

        if persist:
            self._check_project_id()

            if not algorithm_name:
                raise ValueError(
                    "algorithm_name is required when you want to persist the data. "
                    "Please add it to the function call of execute_algorithm()"
                )

            algorithms = self.get_setting("project.algorithms")
            if algorithm_name not in algorithms.keys():
                if file_path is None:
                    raise ValueError("algorithm_name not found, please provide a file_path")
                if backend_type_id is None:
                    raise ValueError("algorithm_name not found, please provide a backend_type_id")
                self.initialize_algorithm(
                    algorithm_name=algorithm_name, file_path=file_path, backend_type_id=backend_type_id
                )

        job = self._submit_job(
            file_path=file_path,
            algorithm_name=algorithm_name,
            backend_type_id=backend_type_id,
            num_shots=num_shots,
            store_raw_data=store_raw_data,
            persist=persist,
        )

        print("Submitted algorithm with job id:", job.job_id)
        return job

    @_refresh_auth_tokens
    def compile_file(
        self,
        file_path: Optional[Path] = None,
        algorithm_name: Optional[str] = None,
        backend_type_id: Optional[int] = None,
        compile_stage: Optional[CompileStage] = None,
    ) -> None:
        """Compile the algorithm file up to the specified compilation stage.

        Args:
            file_path: Path to the algorithm file to compile.
            algorithm_name: Name of a previously initialized algorithm whose settings will be used.
                            Required if ``backend_type_id`` is not provided.
            backend_type_id: ID of the backend type to target. Required if ``algorithm_name`` is not provided.
            compile_stage: The stage up to which the algorithm should be compiled.
        """
        if algorithm_name is None:
            if file_path is None:
                raise ValueError(
                    "file_path not provided. "
                    "Please provide a file_path or "
                    "the algorithm_name of a previously initialized algorithm."
                )

            if backend_type_id is None:
                raise ValueError(
                    "backend_type_id not provided. "
                    "Please provide a backend_type_id or "
                    "the algorithm_name of a previously initialized algorithm."
                )

            options: Dict[str, Any] = self._create_default_options()
            options["compile_stage"] = compile_stage
            options["backend_type_id"] = backend_type_id
            options["file_path"] = file_path
        else:
            options = self._get_compile_options(algorithm_name, compile_stage, backend_type_id, file_path)

        host = self._config_manager.get("default_host")
        owner_id = self._config_manager.user_settings.auths[host].owner_id
        self._resource_manager.run_compile_file_flow(CompileOptions(**options), owner_id)

    @_refresh_auth_tokens
    def initialize_project(self, project_name: str, project_description: str = "") -> None:
        """Initialize a remote project and store its settings locally.

        If a project is already initialized, its name and description are updated on the remote.

        Args:
            project_name: Name of the project to initialize.
            project_description: Description of the project.
            path: Local path where the project settings should be stored. Uses the current directory if not provided.
        """

        init_dir = Path.cwd()
        self._config_manager.initialize(init_dir)

        try:
            project_id = self._check_project_id()
            remote_project = self._resource_manager.read_project(project_id)
            if remote_project is None:
                remote_project = self._initialize_remote_project(project_name, project_description)
            else:
                remote_project = self._resource_manager.update_project(project_id, project_name, project_description)
        except RuntimeError:
            remote_project = self._initialize_remote_project(project_name, project_description)

        assert isinstance(remote_project, Project)
        self.set_setting("project.id", remote_project.id)
        self.set_setting("project.name", remote_project.name)
        self.set_setting("project.description", remote_project.description)

    @_refresh_auth_tokens
    def get_projects(self, name: Optional[str] = None, exact: bool = False) -> list[Project]:
        """Retrieve all remote projects for the current user.

        Returns:
            A list of Project objects.
        """
        return self._resource_manager.read_projects(name, exact)

    def delete_projects(
        self,
        project_ids: Optional[List[int]] = None,
        name: Optional[str] = None,
        exact: bool = False,
    ) -> None:
        """Delete remote projects."""
        if project_ids:
            ids = project_ids
        else:
            ids = [project.id for project in self.get_projects(name, exact)]
            if name and not ids:
                raise ValueError(f"No projects match the name or description '{name}'.")

        self._resource_manager.delete_projects(ids)
        for project_id in ids:
            print(project_id)
        print(f"{len(ids)} projects deleted successfully.")

    @_refresh_auth_tokens
    def initialize_algorithm(
        self,
        algorithm_name: str,
        file_path: Path,
        backend_type_id: int,
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
                remote_algorithm = self._resource_manager.read_algorithm(local_algorithm.id)

            if remote_algorithm is None:
                remote_algorithm = self._resource_manager.create_algorithm(
                    project_id, algorithm_name, self._resource_manager.get_algorithm_type(file_path)
                )
            else:
                assert isinstance(local_algorithm.id, int)
                remote_algorithm = self._resource_manager.update_algorithm(
                    project_id, local_algorithm.id, algorithm_name, self._resource_manager.get_algorithm_type(file_path)
                )
        except ValueError:
            remote_algorithm = self._resource_manager.create_algorithm(
                project_id, algorithm_name, self._resource_manager.get_algorithm_type(file_path)
            )

        local_algorithm = LocalAlgorithm(
            id=remote_algorithm.id,
            file_path=file_path,
            backend_type_id=backend_type_id,
            num_shots=num_shots,
            store_raw_data=store_raw_data,
        )
        self._add_algorithm_to_settings(algorithm_name, local_algorithm)

    def _check_project_id(self) -> int:
        """Verify that a project is initialized in the current settings.

        Returns:
            The project ID stored in the current settings.

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

    def _submit_job(
        self,
        file_path: Optional[Path],
        algorithm_name: Optional[str],
        num_shots: Optional[int],
        store_raw_data: Optional[bool],
        backend_type_id: Optional[int],
        persist: bool,
    ) -> JobOptions:
        """Submit a job to the Quantum Inspire platform.

        Args:
            file_path: Path to the algorithm file to submit.
            algorithm_name: Name of the algorithm. Required when persist is True.
            num_shots: Number of shots to run.
            store_raw_data: Whether to store raw data from the execution.
            backend_type_id: ID of the backend type to use. Required when persist is False.
            persist: Whether to persist the algorithm settings locally.

        Returns:
            A JobOptions object containing details about the submitted job.
        """

        if not persist and algorithm_name is None:
            if backend_type_id is None:
                raise ValueError("backend_type_id not provided")

            options: Dict[str, Any] = self._create_default_options()
            options["backend_type_id"] = backend_type_id
            options["number_of_shots"] = num_shots
            options["raw_data_enabled"] = store_raw_data
            options["file_path"] = file_path

        elif persist and algorithm_name is None:
            raise ValueError("algorithm_name must be provided when persist is True")
        else:
            options = self._get_job_options(
                cast(str, algorithm_name), num_shots, store_raw_data, backend_type_id, file_path
            )

        host = self._config_manager.get("default_host")
        owner_id = self._config_manager.user_settings.auths[host].owner_id
        job_options = self._resource_manager.run_job_submission_flow(JobOptions(**options), owner_id)

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
        return self._resource_manager.get_backend_types()

    @_refresh_auth_tokens
    def get_backend_type(self, backend_type_id: int) -> BackendType:
        """Retrieve a backend type by ID.

        Args:
            backend_type_id: ID of the backend type.

        Returns:
            The backend type.
        """
        return self._resource_manager.get_backend_type(backend_type_id)

    @_refresh_auth_tokens
    def get_queue(self, backend_type_id: int, user_only: bool = False) -> Queue:
        """Retrieve the current size of the queue.

        Args:
            backend_type_id: The ID of the backend to check the queue size for.
            user_only: Whether to consider only the user's jobs in the queue.

        Returns:
            The current queue size of the backend, or None if the backend is not available.
        """
        return self._resource_manager.get_queue(backend_type_id, user_only=user_only)

    @_refresh_auth_tokens
    def get_job(self, job_id: Optional[int] = None, algorithm_name: Optional[str] = None) -> Job:
        """Retrieve job details by job ID or by algorithm name.

        Args:
            job_id: The ID of the job to retrieve.
            algorithm_name: Name of the algorithm whose latest job to retrieve.

        Returns:
            The Job object for the given job ID or the latest job of the given algorithm.
        """
        job_id = self._get_job_id(job_id, algorithm_name)
        return self._resource_manager.get_job(job_id)

    @_refresh_auth_tokens
    def get_job_logs(
        self, job_id: int, n_logs: Optional[int] = None, poll_interval: float = 5.0, timeout: float = 30.0
    ) -> list[str]:
        """Poll job logs until the job has finished.

        Args:
            job_id: The ID of the finished job to get logs for.
            n_logs: Number of expected logs.
            poll_interval: Interval time of polling.
            timeout: Maximum number of seconds to wait.

        Returns:
            A list of the job logs.
        """
        return self._resource_manager.get_job_logs(job_id, n_logs, poll_interval, timeout)

    @_refresh_auth_tokens
    def get_job_status(
        self,
        algorithm_name: Optional[str] = None,
        job_id: Optional[int] = None,
        wait: bool = False,
        timeout: float = 60,
    ) -> JobStatus:
        """Get the status of the job with the given ID or the most recent job for the given algorithm.

        Args:
            algorithm_name: Name of the algorithm to get the status for.
            job_id: The ID of the job to get the status for.
            wait: Whether to wait for the job to complete before returning.
            timeout: Maximum time in seconds to wait for job completion.

        Returns:
            The current job status.
        """
        job_id = self._get_job_id(job_id, algorithm_name)
        if wait:
            try:
                return self._resource_manager.wait_for_job_completion(job_id, timeout=timeout).status
            except TimeoutError:
                print("Timeout while waiting for job completion. Returning current status.")

        return self.get_job(job_id).status

    @_refresh_auth_tokens
    def get_final_result(
        self, algorithm_name: Optional[str] = None, job_id: Optional[int] = None
    ) -> FinalResult | None:
        """Get the final result of the job with the given ID or the most recent job for the given algorithm.

        Args:
            algorithm_name: Name of the algorithm to get the result for.
            job_id: The ID of the job to get the result for.

        Returns:
            The final result of the job, or None if not yet available.
        """
        job_id = self._get_job_id(job_id, algorithm_name)
        return self._resource_manager.get_final_result(job_id)

    @_refresh_auth_tokens
    def get_results(self, algorithm_name: Optional[str] = None, job_id: Optional[int] = None) -> list[Result]:
        """Get the results of the job with the given ID or the most recent job for the given algorithm.

        Args:
            algorithm_name: Name of the algorithm to get the result for.
            job_id: The ID of the job to get the result for.

        Returns:
            The results of the job, or an empty list if not yet available.
        """
        job_id = self._get_job_id(job_id, algorithm_name)
        return self._resource_manager.get_results(job_id)

    def _get_job_id(self, job_id: Optional[int], algorithm_name: Optional[str]) -> int:
        """Resolve a job ID from an explicit value or an algorithm name.

        If neither is provided and there is exactly one algorithm in the settings,
        the job ID from that algorithm is used implicitly.

        Args:
            job_id: The explicit job ID to use, if provided.
            algorithm_name: Name of the algorithm whose latest job ID to look up.

        Returns:
            The resolved job ID.

        Raises:
            ValueError: If neither job_id nor algorithm_name is provided and there is not
                exactly one algorithm in the settings.
        """
        resolved = job_id or (
            self.get_algorithm_setting(algorithm_name, "job_id") if algorithm_name is not None else None
        )
        if resolved is None:
            algorithms = self.get_setting("project.algorithms")
            if algorithms and len(algorithms) == 1:
                only_algorithm_name = next(iter(algorithms))
                resolved = self.get_algorithm_setting(only_algorithm_name, "job_id")
            if resolved is None:
                raise ValueError("Please provide a job_id or algorithm_name")
        return resolved

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

    def _initialize_remote_project(self, project_name: str, project_description: Optional[str]) -> Project:
        """Create a new remote project on the Quantum Inspire platform.

        Args:
            project_name: Name of the project to create.
            project_description: Description of the project.

        Returns:
            The created Project object.
        """
        host = self.get_setting("default_host")
        owner_id = self._config_manager.user_settings.auths[host].owner_id
        return self._resource_manager.create_project(owner_id, project_name, cast(str, project_description))

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

    @staticmethod
    def _create_default_options() -> Dict[str, Any]:
        """Create a dictionary of default options for job or compile submission with non-persistent data.

        Returns:
            A dictionary containing default options
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        options: Dict[str, Any] = {
            "project_name": f"Project created on {timestamp}",
            "project_description": "Project created for non-persistent algorithm",
            "algorithm_name": f"Algorithm created on {timestamp}",
        }
        return options

    def _get_resource_options(
        self, algorithm_name: str, file_path: Optional[Path], backend_type_id: Optional[int]
    ) -> Dict[str, Any]:
        """Retrieve the resource options for a specific algorithm.

        Args:
            algorithm_name: Name of the algorithm.
            file_path: Path to the algorithm file. Overrides the algorithm's stored value if provided.
            backend_type_id: ID of the backend type. Overrides the algorithm's stored value if provided.

        Returns:
            A dictionary containing resource options
        """

        options: Dict[str, Any] = {
            "project_id": self._config_manager.get("project.id"),
            "project_name": self._config_manager.get("project.name"),
            "project_description": self._config_manager.get("project.description"),
            "algorithm_id": self._resolve_algorithm_setting(None, "id", algorithm_name),
            "algorithm_name": algorithm_name,
            "file_path": self._resolve_algorithm_setting(file_path, "file_path", algorithm_name),
            "backend_type_id": self._resolve_algorithm_setting(backend_type_id, "backend_type_id", algorithm_name),
        }

        return options

    def _get_job_options(
        self,
        algorithm_name: str,
        num_shots: Optional[int],
        store_raw_data: Optional[bool],
        backend_type_id: Optional[int],
        file_path: Optional[Path],
    ) -> Dict[str, Any]:
        """Build job options from algorithm settings and any provided overrides.

        Args:
            algorithm_name: Name of the algorithm to build options for.
            num_shots: Number of shots. Overrides the algorithm's stored value if provided.
            store_raw_data: Whether to store raw data. Overrides the algorithm's stored value if provided.
            backend_type_id: ID of the backend type. Overrides the algorithm's stored value if provided.
            file_path: Path to the algorithm file. Overrides the algorithm's stored value if provided.

        Returns:
            A dictionary of job options ready to be passed to the job manager.
        """

        options: Dict[str, Any] = self._get_resource_options(algorithm_name, file_path, backend_type_id)

        options["number_of_shots"] = self._resolve_algorithm_setting(num_shots, "num_shots", algorithm_name)
        options["raw_data_enabled"] = self._resolve_algorithm_setting(store_raw_data, "store_raw_data", algorithm_name)

        return options

    def _get_compile_options(
        self,
        algorithm_name: str,
        compile_stage: Optional[CompileStage],
        backend_type_id: Optional[int],
        file_path: Optional[Path],
    ) -> Dict[str, Any]:
        """Build compile options from algorithm settings and any provided overrides.

        Args:
            algorithm_name: Name of the algorithm to build options for.
            compile_stage: Compile stage to build options for.
            backend_type_id: ID of the backend type. Overrides the algorithm's stored value if provided.
            file_path: Path to the algorithm file. Overrides the algorithm's stored value if provided.

        Returns:
            A dictionary of compile options.
        """
        options: Dict[str, Any] = self._get_resource_options(algorithm_name, file_path, backend_type_id)
        options["compile_stage"] = compile_stage
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
            _ = requests.head(f"https://{url}", timeout=3, allow_redirects=True)
            return f"https://{url}"
        except requests.RequestException:
            pass

        return f"http://{url}"
