import time
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
from quantuminspire.settings.models import LocalAlgorithm, Url


class Api:

    def __init__(
        self,
        config_manager: Optional[ConfigManager] = None,
        auth_manager: Optional[AuthManager] = None,
        job_manager: Optional[JobManager] = None,
    ) -> None:
        self._config_manager = config_manager or ConfigManager()
        self._auth_manager = auth_manager or AuthManager(user_settings=self._config_manager.user_settings)
        self._job_manager = job_manager or JobManager(self._config_manager)

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
            self.add_algorithm_to_settings(job_options.algorithm_name, local_algorithm)

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

    def wait_for_job_completion(self, job_id: Optional[int] = None, timeout: Optional[int] = 60) -> Job:
        start_time = time.time()

        print("Waiting for job to complete...")
        while True:
            job = self.get_job(job_id)

            if job.status not in [JobStatus.PLANNED, JobStatus.RUNNING]:
                return job

            if timeout is not None and time.time() - start_time >= timeout:
                raise TimeoutError(f"Job {job.id} did not complete within {timeout} seconds")

            time.sleep(1)

    def _get_local_algorithm(self, algorithm_name: str) -> LocalAlgorithm:
        algorithms = self._config_manager.get("project.algorithms")
        try:
            local_algorithm: LocalAlgorithm = algorithms[algorithm_name]
            return local_algorithm
        except KeyError:
            raise ValueError(f"Algorithm '{algorithm_name}' not found in settings.")

    def add_algorithm_to_settings(self, algorithm_name: str, local_algorithm: LocalAlgorithm) -> None:
        algorithms = self._config_manager.get("project.algorithms")
        algorithms[algorithm_name] = local_algorithm
        self._config_manager.set("project.algorithms", algorithms, is_user=False)

    @staticmethod
    def initialize_project(path: Optional[Path] = None) -> None:
        init_dir = path or Path.cwd()
        ConfigManager.initialize(init_dir)

    def initialize_remote_project(self, project_name: str, project_description: Optional[str] = "") -> Project:
        host = self._config_manager.get("default_host")
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
        self.add_algorithm_to_settings(algorithm_name, local_algorithm)

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
