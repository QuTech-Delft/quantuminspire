from pathlib import Path
from typing import Any, Dict, List, Optional

from compute_api_client import (
    BackendType,
    FinalResult,
    Job,
)
from pydantic import TypeAdapter

from quantuminspire.auth_manager.auth_manager import AuthManager
from quantuminspire.config_manager.config_manager import ConfigManager
from quantuminspire.job_manager.job_manager import JobManager, JobOptions
from quantuminspire.settings.models import Url


class QIApi:

    def __init__(
        self,
        config_manager: Optional[ConfigManager] = None,
        auth_manager: Optional[AuthManager] = None,
        job_manager: Optional[JobManager] = None,
    ) -> None:
        self._config_manager = config_manager or ConfigManager()
        self._auth_manager = auth_manager or AuthManager()
        self._job_manager = job_manager or JobManager(self._auth_manager)

    def login(self, hostname: Optional[str] = None) -> None:
        host_url: Optional[Url] = TypeAdapter(Url).validate_python(hostname) if hostname is not None else None
        self._auth_manager.login(self._resolve(host_url, "default_host"))

    def submit_job(
        self,
        file_path: str,
        file_name: Optional[str] = None,
        num_shots: Optional[int] = None,
        store_raw_data: Optional[bool] = None,
        backend_type_id: Optional[int] = None,
        persist: bool = True,
    ) -> JobOptions:

        options: Dict[str, Any] = self._get_job_options(file_name, num_shots, store_raw_data, backend_type_id)

        job_options = self._job_manager.run_flow(JobOptions(**(options | {"file_path": Path(file_path)})))

        self._config_manager.set("project.id", job_options.project_id, is_user=False)

        if persist:
            self._config_manager.set("job.id", job_options.job_id, is_user=False)
            self._config_manager.set("algorithm.name", job_options.algorithm_name, is_user=False)

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

    def initialize(self, path: Optional[Path] = None) -> None:
        init_dir = path or Path.cwd()
        self._config_manager.initialize(init_dir)

    def inspect(self) -> Dict[str, Any]:
        return self._config_manager.inspect()

    def get(self, key: str) -> Any:
        return self._config_manager.get(key)

    def set(self, key: str, value: Any, is_user: bool = False) -> None:
        return self._config_manager.set(key, value, is_user)

    def _get_job_options(
        self,
        file_name: Optional[str] = None,
        num_shots: Optional[int] = None,
        store_raw_data: Optional[bool] = None,
        backend_type_id: Optional[int] = None,
    ) -> Dict[str, Any]:

        options: Dict[str, Any] = {
            "project_id": self._config_manager.get("project.id"),
            "project_name": self._config_manager.get("project.name"),
            "project_description": self._config_manager.get("project.description"),
            "backend_type": self._resolve(backend_type_id, "backend_type"),
            "number_of_shots": self._resolve(num_shots, "algorithm.num_shots"),
            "raw_data_enabled": self._resolve(store_raw_data, "algorithm.store_raw_data"),
            "algorithm_name": self._resolve(file_name, "algorithm.name"),
        }

        return options

    def _resolve(self, override: Optional[Any], key: str) -> Any:
        return override if override is not None else self._config_manager.get(key)
