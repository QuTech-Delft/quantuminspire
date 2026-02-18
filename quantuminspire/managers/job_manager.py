from pathlib import Path
from typing import Any, Awaitable, Callable, List, Optional, Type

from compute_api_client import (
    Algorithm,
    AlgorithmIn,
    AlgorithmsApi,
    AlgorithmType,
    ApiClient,
    BackendType,
    BackendTypesApi,
    BatchJob,
    BatchJobIn,
    BatchJobsApi,
    Commit,
    CommitIn,
    CommitsApi,
    CompileStage,
    File,
    FileIn,
    FilesApi,
    FinalResult,
    FinalResultsApi,
    Job,
    JobIn,
    JobsApi,
    Language,
    LanguagesApi,
    PageBackendType,
    Project,
    ProjectIn,
    ProjectPatch,
    ProjectsApi,
    ShareType,
)
from pydantic import BaseModel, Field
from qi2_shared.client import config
from qi2_shared.utils import run_async

from quantuminspire.managers.config_manager import ConfigManager


class JobOptions(BaseModel):
    project_id: Optional[int] = Field(None)
    job_id: Optional[int] = Field(None)
    algorithm_id: Optional[int] = Field(None)
    project_name: str
    project_description: str
    backend_type_id: int
    number_of_shots: Optional[int] = Field(None)
    raw_data_enabled: Optional[bool] = Field(None)
    algorithm_name: str
    file_path: Path


class JobManager:

    def __init__(self, config_manager: ConfigManager) -> None:
        self._config_manager = config_manager

    @staticmethod
    def _invoke(
        api_class: Type[Any],
        method_name: str,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        async def _execute() -> Any:
            async with ApiClient(config()) as client:
                api_instance = api_class(client)
                method: Callable[..., Awaitable[Any]] = getattr(api_instance, method_name)
                return await method(*args, **kwargs)

        return run_async(_execute())

    def run_flow(self, job_options: JobOptions) -> JobOptions:

        host = self._config_manager.get("default_host")
        owner_id = self._config_manager.user_settings.auths[host].owner_id
        if job_options.project_id is None:
            project = self.create_project(
                owner_id=owner_id,
                project_name=job_options.project_name,
                project_description=job_options.project_description,
            )
            job_options.project_id = project.id
        else:
            self._update_project(
                project_id=job_options.project_id,
                project_name=job_options.project_name,
                project_description=job_options.project_description,
            )

        algorithm_type: AlgorithmType = self.get_algorithm_type(file_path=job_options.file_path)

        if job_options.algorithm_id is None:
            algorithm = self.create_algorithm(
                project_id=job_options.project_id,
                algorithm_name=job_options.algorithm_name,
                algorithm_type=algorithm_type,
            )
            job_options.algorithm_id = algorithm.id
        else:
            algorithm = self._read_algorithm(algorithm_id=job_options.algorithm_id)

        commit = self._create_commit(algorithm_id=algorithm.id)
        language: Language = self._get_language_for_algorithm(algorithm_type=algorithm_type)
        file_ = self._create_file(
            file_content=job_options.file_path.read_text(), language_id=language.id, commit_id=commit.id
        )
        batch_job: BatchJob = self._create_batch_job(backend_type_id=job_options.backend_type_id)
        job: Job = self._create_job(
            file_id=file_.id,
            batch_job_id=batch_job.id,
            num_shots=job_options.number_of_shots,
            raw_data_enabled=job_options.raw_data_enabled,
        )

        self._enqueue_batch_job(batch_job_id=batch_job.id)

        job_options.job_id = job.id

        return job_options

    def get_backend_types(self) -> List[BackendType]:
        backend_types_page: PageBackendType = self._invoke(BackendTypesApi, "read_backend_types_backend_types_get")
        items: List[BackendType] = backend_types_page.items
        return items

    def get_job(self, job_id: int) -> Job:
        return self._invoke(JobsApi, "read_job_jobs_id_get", id=job_id)

    def get_final_result(self, job_id: int) -> FinalResult | None:
        return self._invoke(FinalResultsApi, "read_final_result_by_job_id_final_results_job_job_id_get", job_id)

    @staticmethod
    def get_algorithm_type(file_path: Path) -> AlgorithmType:
        if file_path.suffix == ".py":
            return AlgorithmType.HYBRID
        elif file_path.suffix == ".cq":
            return AlgorithmType.QUANTUM
        raise ValueError("Incorrect file type. Supported types are .py and .cq")

    def create_project(self, owner_id: int, project_name: str, project_description: str) -> Project:
        obj = ProjectIn(
            owner_id=owner_id,
            name=project_name,
            description=project_description,
            starred=False,
        )
        return self._invoke(ProjectsApi, "create_project_projects_post", obj)

    def _update_project(self, project_id: int, project_name: str, project_description: str) -> Project:
        obj = ProjectPatch(name=project_name, description=project_description)
        return self._invoke(ProjectsApi, "partial_update_project_projects_id_patch", project_id, obj)

    def create_algorithm(self, project_id: int, algorithm_name: str, algorithm_type: AlgorithmType) -> Algorithm:
        obj = AlgorithmIn(
            project_id=project_id,
            type=algorithm_type,
            shared=ShareType.PRIVATE,
            name=algorithm_name,
        )
        return self._invoke(AlgorithmsApi, "create_algorithm_algorithms_post", obj)

    def _read_algorithm(self, algorithm_id: int) -> Algorithm:
        return self._invoke(AlgorithmsApi, "read_algorithm_algorithms_id_get", algorithm_id)

    def _create_commit(self, algorithm_id: int) -> Commit:
        obj = CommitIn(
            description="Commit created by SDK",
            algorithm_id=algorithm_id,
        )
        return self._invoke(CommitsApi, "create_commit_commits_post", obj)

    def _get_language_for_algorithm(self, algorithm_type: AlgorithmType) -> Language:
        type_to_lang = {
            AlgorithmType.HYBRID: "python",
            AlgorithmType.QUANTUM: "cqasm",
        }

        target_name = type_to_lang.get(algorithm_type)

        page_languages = self._invoke(LanguagesApi, "read_languages_languages_get")

        for language in page_languages.items:
            if language.name.lower() == target_name:
                return language

        raise ValueError(f"Language '{target_name}' not found in API")

    def _create_file(self, file_content: str, language_id: int, commit_id: int) -> File:

        obj = FileIn(
            commit_id=commit_id,
            content=file_content,
            language_id=language_id,
            compile_stage=CompileStage.NONE,
            compile_properties={},
        )

        return self._invoke(FilesApi, "create_file_files_post", obj)

    def _create_batch_job(self, backend_type_id: int) -> BatchJob:
        obj = BatchJobIn(backend_type_id=backend_type_id)
        return self._invoke(BatchJobsApi, "create_batch_job_batch_jobs_post", obj)

    def _create_job(
        self, file_id: int, batch_job_id: int, num_shots: Optional[int], raw_data_enabled: Optional[bool]
    ) -> Job:
        obj = JobIn(
            file_id=file_id, batch_job_id=batch_job_id, number_of_shots=num_shots, raw_data_enabled=raw_data_enabled
        )
        return self._invoke(JobsApi, "create_job_jobs_post", obj)

    def _enqueue_batch_job(self, batch_job_id: int) -> BatchJob:
        return self._invoke(BatchJobsApi, "enqueue_batch_job_batch_jobs_id_enqueue_patch", batch_job_id)
