"""Quantum Inspire SDK.

Copyright 2022 QuTech Delft

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the
License. You may obtain a copy of the License at

https://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an
"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific
language governing permissions and limitations under the License.
"""

from typing import Any, List, cast

from compute_api_client import (
    Algorithm,
    AlgorithmIn,
    AlgorithmsApi,
    ApiClient,
    BackendTypesApi,
    BatchJob,
    BatchJobIn,
    BatchJobsApi,
    Commit,
    CommitIn,
    CommitsApi,
    File,
    FileIn,
    FilesApi,
    FinalResult,
    FinalResultsApi,
    Job,
    JobIn,
    JobsApi,
    JobStatus,
    Language,
    LanguagesApi,
    Project,
    ProjectIn,
    ProjectsApi,
    Result,
    ResultsApi,
    ShareType,
)
from qi2_shared.utils import run_async

from quantuminspire.sdk.models.base_algorithm import BaseAlgorithm
from quantuminspire.sdk.models.job_options import JobOptions
from quantuminspire.util.api.base_backend import BaseBackend
from quantuminspire.util.authentication import Configuration, OauthDeviceSession
from quantuminspire.util.configuration import Settings


class RemoteBackend(BaseBackend):
    """Connection to remote backend.

    Create a connection with the remote backend for Quantum Inspire. This connection creates the appropriate projects,
    algorithms, files etc. The algorithm/circuit will also be run.
    """

    def __init__(self) -> None:
        super().__init__()
        settings = Settings()
        self.auth_settings = settings.default_auth_settings

        oauth_session = OauthDeviceSession(self.auth_settings)
        tokens = oauth_session.refresh()
        settings.store_tokens(settings.default_host, tokens)

        self._configuration = Configuration(host=settings.default_host, oauth_session=oauth_session)

    def run(
        self,
        program: BaseAlgorithm,
        backend_type_id: int,
        options: JobOptions = JobOptions(),
    ) -> int:
        """Execute provided algorithm/circuit."""
        return cast(int, run_async(self._create_flow(program, backend_type_id, job_options=options)))

    async def _get_job(self, job_id: int) -> Any:
        async with ApiClient(self._configuration) as api_client:
            return await self._read_job(api_client, job_id)

    async def _get_results(self, job_id: int) -> Any:
        async with ApiClient(self._configuration) as api_client:
            job = await self._read_job(api_client, job_id)
            if job.status != JobStatus.COMPLETED:
                return None

            return await self._read_results_for_job(api_client, job)

    async def _get_final_results(self, job_id: int) -> Any:
        async with ApiClient(self._configuration) as api_client:
            job = await self._read_job(api_client, job_id)
            if job.status != JobStatus.COMPLETED:
                return None

            return await self._read_final_results_for_job(api_client, job)

    async def _get_backend_types(self) -> Any:
        async with ApiClient(self._configuration) as api_client:
            api_instance = BackendTypesApi(api_client)
            return await api_instance.read_backend_types_backend_types_get()

    def get_job(self, job_id: int) -> Any:
        """Get job for algorithm/circuit."""
        return run_async(self._get_job(job_id))

    def get_results(self, job_id: int) -> Any:
        """Get results for algorithm/circuit."""
        return run_async(self._get_results(job_id))

    def get_final_results(self, job_id: int) -> Any:
        """Get final results for algorithm/circuit."""
        return run_async(self._get_final_results(job_id))

    def get_backend_types(self) -> Any:
        """Get backend types."""
        return run_async(self._get_backend_types())

    async def _create_flow(
        self,
        program: BaseAlgorithm,
        backend_type_id: int,
        job_options: JobOptions,
    ) -> int:
        """Call the necessary methods in the correct order, with the correct parameters."""
        async with ApiClient(self._configuration) as api_client:
            project = await self._create_project(api_client, program)
            algorithm = await self._create_algorithm(api_client, program, project)
            commit = await self._create_commit(api_client, algorithm)
            file = await self._create_file(api_client, program, commit)
            batch_job = await self._create_batch_job(api_client, backend_type_id=backend_type_id)
            job: Job = await self._create_job(api_client, file, batch_job, job_options)
            await self._enqueue_batch_job(api_client, batch_job)
            return job.id  # type: ignore

    async def _create_project(self, api_client: ApiClient, program: BaseAlgorithm) -> Project:
        api_instance = ProjectsApi(api_client)
        obj = ProjectIn(
            owner_id=self.auth_settings.owner_id,
            name=program.program_name,
            description="Project created by SDK",
            starred=False,
        )
        return await api_instance.create_project_projects_post(obj)

    @staticmethod
    async def _create_algorithm(api_client: ApiClient, program: BaseAlgorithm, project: Project) -> Algorithm:
        api_instance = AlgorithmsApi(api_client)
        obj = AlgorithmIn(
            project_id=project.id,
            type=program.content_type,
            shared=ShareType.PRIVATE,
            name=program.program_name,
        )
        return await api_instance.create_algorithm_algorithms_post(obj)

    @staticmethod
    async def _create_commit(api_client: ApiClient, algorithm: Algorithm) -> Commit:
        api_instance = CommitsApi(api_client)
        obj = CommitIn(
            description="Commit created by SDK",
            algorithm_id=algorithm.id,
        )
        return await api_instance.create_commit_commits_post(obj)

    @staticmethod
    async def _get_language_for_algorithm(api_client: ApiClient, algorithm: BaseAlgorithm) -> Language:
        api_instance = LanguagesApi(api_client)
        page_languages = await api_instance.read_languages_languages_get()
        for language in page_languages.items:
            if language.name.lower() == algorithm.language_name.lower():
                return language

        raise ValueError(f"Language {algorithm.language_name} not found in API")

    @staticmethod
    async def _create_file(api_client: ApiClient, program: BaseAlgorithm, commit: Commit) -> File:
        api_instance = FilesApi(api_client)
        language = await RemoteBackend._get_language_for_algorithm(api_client, program)

        obj = FileIn(
            commit_id=commit.id,
            content=program.content,
            language_id=language.id,
            compile_stage=program.compile_stage,
            compile_properties={},
        )
        return await api_instance.create_file_files_post(obj)

    @staticmethod
    async def _create_batch_job(api_client: ApiClient, backend_type_id: int) -> BatchJob:
        api_instance = BatchJobsApi(api_client)
        obj = BatchJobIn(backend_type_id=backend_type_id)
        return await api_instance.create_batch_job_batch_jobs_post(obj)

    @staticmethod
    async def _create_job(api_client: ApiClient, file: File, batch_job: BatchJob, job_options: JobOptions) -> Job:
        api_instance = JobsApi(api_client)
        obj = JobIn(file_id=file.id, batch_job_id=batch_job.id, **job_options.model_dump())
        return await api_instance.create_job_jobs_post(obj)

    @staticmethod
    async def _enqueue_batch_job(api_client: ApiClient, batch_job: BatchJob) -> BatchJob:
        api_instance = BatchJobsApi(api_client)
        return await api_instance.enqueue_batch_job_batch_jobs_id_enqueue_patch(batch_job.id)

    @staticmethod
    async def _read_job(api_client: ApiClient, job_id: int) -> Job:
        api_instance = JobsApi(api_client)
        return await api_instance.read_job_jobs_id_get(job_id)

    @staticmethod
    async def _read_results_for_job(api_client: ApiClient, job: Job) -> List[Result]:
        api_instance = ResultsApi(api_client)
        return await api_instance.read_results_by_job_id_results_job_job_id_get(job.id)  # type: ignore

    @staticmethod
    async def _read_final_results_for_job(api_client: ApiClient, job: Job) -> List[FinalResult]:
        api_instance = FinalResultsApi(api_client)
        return await api_instance.read_final_result_by_job_id_final_results_job_job_id_get(job.id)  # type: ignore
