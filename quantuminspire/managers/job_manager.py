from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from compute_api_client import (
    AlgorithmType,
    BackendStatus,
    BackendType,
    FinalResult,
    Job,
    JobStatus,
)
from pydantic import BaseModel, Field

from quantuminspire.managers.auth_manager import AuthManager


class JobOptions(BaseModel):
    project_id: Optional[int] = Field(None)
    job_id: Optional[int] = Field(None)
    project_name: str
    project_description: str
    backend_type: int
    number_of_shots: int
    raw_data_enabled: bool
    algorithm_name: str
    file_path: Path


class JobManager:

    def __init__(self, auth_manager: AuthManager) -> None:
        self._auth_manager = auth_manager

    def run_flow(self, job_options: JobOptions) -> JobOptions:
        options: Dict[str, Any] = {
            "file_path": Path.cwd(),
            "project_id": 1,
            "job_id": 1,
            "project_name": "some-project",
            "project_description": "some-project",
            "backend_type": 1,
            "number_of_shots": 1,
            "raw_data_enabled": False,
            "algorithm_name": "some-name",
        }
        return JobOptions(**options)

    def get_backend_types(self) -> List[BackendType]:
        options: Dict[str, Any] = {
            "id": 1,
            "name": "Spin 2",
            "infrastructure": "Hetzner",
            "description": "some-text",
            "image_id": "abcd1234",
            "is_hardware": True,
            "supports_raw_data": True,
            "features": ["multiple_measurements"],
            "default_compiler_config": {},
            "gateset": ["X", "Y", "Z"],
            "topology": [[0, 1], [1, 2], [2, 0], [3, 2]],
            "nqubits": 2,
            "status": BackendStatus.IDLE,
            "default_number_of_shots": 1,
            "max_number_of_shots": 1,
            "enabled": True,
            "identifier": "some-name",
            "protocol_version": 3,
        }
        return [BackendType(**options)]

    def get_job(self, job_id: int) -> Job:

        options: Dict[str, Any] = {
            "id": job_id,
            "created_on": datetime(2022, 11, 3, 17, 20, 56, 36676, tzinfo=timezone.utc),
            "file_id": 1,
            "algorithm_type": AlgorithmType.QUANTUM,
            "status": JobStatus.PLANNED,
            "batch_job_id": 1,
            "queued_at": datetime(2022, 11, 3, 17, 20, 56, 36676, tzinfo=timezone.utc),
            "finished_at": datetime(2022, 11, 3, 17, 20, 56, 36676, tzinfo=timezone.utc),
            "number_of_shots": 1,
            "raw_data_enabled": False,
            "session_id": "8e7e2b6c-2b3c-4d9f-8b12-6a4d9b1e3f5a",
            "trace_id": "8e7e2b6c-2b3c-4d9f-8b12-6a4d9b1e3f5a",
            "message": "",
            "source": "",
        }
        return Job(**options)

    def get_final_result(self, job_id: int) -> FinalResult | None:
        return None


# from pathlib import Path
# from typing import Any, Awaitable, Callable, List, Optional, Type


# from compute_api_client import (
#     Algorithm,
#     AlgorithmIn,
#     AlgorithmType,
#     AlgorithmsApi,
#     ApiClient,
#     BackendTypesApi,
#     BackendType,
#     BatchJob,
#     BatchJobIn,
#     BatchJobsApi,
#     Commit,
#     CommitIn,
#     CommitsApi,
#     CompileStage,
#     File,
#     FileIn,
#     FilesApi,
#     FinalResult,
#     Job,
#     JobIn,
#     JobsApi,
#     FinalResultsApi,
#     Language,
#     LanguagesApi,
#     Project,
#     ProjectIn,
#     ProjectPatch,
#     ProjectsApi,
#     ShareType,
#     PageBackendType,
# )


# from pydantic import BaseModel, Field
# from qi2_shared.client import config
# from qi2_shared.utils import run_async

# from quantuminspire.auth_manager.auth_manager import AuthManager


# class JobManager:

#     def __init__(self, auth_manager: AuthManager) -> None:
#         self._auth_manager = auth_manager

#     @staticmethod
#     def _invoke(
#         api_class: Type[Any],
#         method_name: str,
#         *args: Any,
#         **kwargs: Any,
#     ) -> Any:
#         async def _execute() -> Any:
#             async with ApiClient(config()) as client:
#                 api_instance = api_class(client)
#                 method: Callable[..., Awaitable[Any]] = getattr(api_instance, method_name)
#                 return await method(*args, **kwargs)

#         return run_async(_execute())

#     def run_flow(self, job_options: JobOptions) -> JobOptions:

#         if job_options.project_id is None:
#             project = self._create_project(
#                 owner_id=self._auth_manager.get_team_member_id(),
#                 project_name=job_options.project_name,
#                 project_description=job_options.project_description,
#             )
#             job_options.project_id = project.id
#         else:
#             self._update_project(project_id=job_options.project_id, project_name=job_options.project_name,
# project_description=job_options.project_description)

#         algorithm_type: AlgorithmType = self._get_algorithm_type(file_path=job_options.file_path)

#         algorithm = self._create_algorithm(
#             project_id=job_options.project_id, algorithm_name=job_options.algorithm_name,
# algorithm_type=algorithm_type
#         )
#         commit = self._create_commit(algorithm_id=algorithm.id)
#         language: Language = self._get_language_for_algorithm(algorithm_type=algorithm_type)
#         file_ = self._create_file(
#             file_content=job_options.file_path.read_text(), language_id=language.id, commit_id=commit.id
#         )
#         batch_job: BatchJob = self._create_batch_job(backend_type_id=job_options.backend_type)
#         job: Job = self._create_job(
#             file_id=file_.id,
#             batch_job_id=batch_job.id,
#             num_shots=job_options.number_of_shots,
#             raw_data_enabled=job_options.raw_data_enabled,
#         )
#         self._enqueue_batch_job(batch_job_id=batch_job.id)

#         job_options.job_id = job.id

#         return job_options

#     def get_backend_types(self) -> List[BackendType]:
#         backend_types_page: PageBackendType = self._invoke(BackendTypesApi, "read_backend_types_backend_types_get")
#         return backend_types_page.items

#     def get_job(self, job_id: int) -> Job:
#         return self._invoke(JobsApi, "read_job_jobs_id_get", id=job_id)

#     def get_final_result(self, job_id: int) -> FinalResult | None:
#         return self._invoke(FinalResultsApi, "read_final_result_by_job_id_final_results_job_job_id_get", job_id)

#     def _get_algorithm_type(self, file_path: Path) -> AlgorithmType:

#         is_python_file = self._looks_like_python(file_path.read_text())
#         if is_python_file:
#             return AlgorithmType.HYBRID
#         return AlgorithmType.QUANTUM

#     @staticmethod
#     def _looks_like_python(text: str) -> bool:
#         lines = text.splitlines()
#         for line in lines:
#             stripped = line.strip()
#             if stripped.startswith("def ") or stripped.startswith("class "):
#                 return True
#             if stripped.startswith("import ") or stripped.startswith("from "):
#                 return True
#         return False

#     def _create_project(self, owner_id: int, project_name: str, project_description: str) -> Project:
#         obj = ProjectIn(
#             owner_id=owner_id,
#             name=project_name,
#             description=project_description,
#             starred=False,
#         )
#         return self._invoke(ProjectsApi, "create_project_projects_post", obj)

#     def _update_project(self, project_id: int, project_name: str, project_description: str) -> Project:
#         obj = ProjectPatch(name=project_name, description=project_description)
#         return self._invoke(ProjectsApi, "partial_update_project_projects_id_patch", project_id, obj)

#     def _create_algorithm(self, project_id: int, algorithm_name: str, algorithm_type: AlgorithmType) -> Algorithm:
#         obj = AlgorithmIn(
#             project_id=project_id,
#             type=algorithm_type,
#             shared=ShareType.PRIVATE,
#             name=algorithm_name,
#         )
#         return self._invoke(AlgorithmsApi, "create_algorithm_algorithms_post", obj)

#     def _create_commit(self, algorithm_id: int) -> Commit:
#         obj = CommitIn(
#             description="Commit created by SDK",
#             algorithm_id=algorithm_id,
#         )
#         return self._invoke(CommitsApi, "create_commit_commits_post", obj)

#     def _get_language_for_algorithm(self, algorithm_type: AlgorithmType) -> Language:
#         type_to_lang = {
#             AlgorithmType.HYBRID: "python",
#             AlgorithmType.QUANTUM: "cqasm",
#         }

#         target_name = type_to_lang.get(algorithm_type)

#         page_languages = self._invoke(LanguagesApi, "read_languages_languages_get")

#         for language in page_languages.items:
#             if language.name.lower() == target_name:
#                 return language

#         raise ValueError(f"Language '{target_name}' not found in API")

#     def _create_file(self, file_content: str, language_id: int, commit_id: int) -> File:

#         obj = FileIn(
#             commit_id=commit_id,
#             content=file_content,
#             language_id=language_id,
#             compile_stage=CompileStage.NONE,
#             compile_properties={},
#         )

#         return self._invoke(FilesApi, "create_file_files_post", obj)

#     def _create_batch_job(self, backend_type_id: int) -> BatchJob:
#         obj = BatchJobIn(backend_type_id=backend_type_id)
#         return self._invoke(BatchJobsApi, "create_batch_job_batch_jobs_post", obj)

#     def _create_job(self, file_id: int, batch_job_id: int, num_shots: int, raw_data_enabled: bool) -> Job:
#         obj = JobIn(
#             file_id=file_id, batch_job_id=batch_job_id, number_of_shots=num_shots, raw_data_enabled=raw_data_enabled
#         )
#         return self._invoke(JobsApi, "create_job_jobs_post", obj)

#     def _enqueue_batch_job(self, batch_job_id: int) -> BatchJob:
#         return self._invoke(BatchJobsApi, "enqueue_batch_job_batch_jobs_id_enqueue_patch", batch_job_id)
