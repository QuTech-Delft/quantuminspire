"""Quantum Inspire SDK.

Copyright 2022 QuTech Delft

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the
License. You may obtain a copy of the License at

https://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an
"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific
language governing permissions and limitations under the License.
"""

import asyncio
from typing import Any, List

from compute_api_client import (
    Algorithm,
    AlgorithmIn,
    AlgorithmsApi,
    ApiClient,
    BatchJob,
    BatchJobIn,
    BatchJobsApi,
    Commit,
    CommitIn,
    CommitsApi,
    Configuration,
    File,
    FileIn,
    FilesApi,
    Job,
    JobIn,
    JobsApi,
    JobStatus,
    Project,
    ProjectIn,
    ProjectsApi,
    Result,
    ResultsApi,
    ShareType,
)

from quantuminspire.sdk.models.base_algorithm import BaseAlgorithm
from quantuminspire.util.api.base_backend import BaseBackend
from quantuminspire.util.configuration import Settings


class RemoteBackend(BaseBackend):
    """Connection to remote backend.

    Create a connection with the remote backend for Quantum Inspire. This connection creates the appropriate projects,
    algorithms, files etc. The algorithm/circuit will also be run.
    """

    def __init__(self) -> None:
        super().__init__()
        settings = Settings()
        host = "https://staging.qi2.quantum-inspire.com"
        self._configuration = Configuration(host=host, api_key={"user": str(settings.auths[host]["user_id"])})

    def run(self, program: BaseAlgorithm, backend_type_id: int) -> int:
        """Execute provided algorithm/circuit."""
        return asyncio.run(self._create_flow(program, backend_type_id))

    async def _get_results(self, job_id: int) -> Any:
        async with ApiClient(self._configuration) as api_client:
            job = await self._read_job(api_client, job_id)
            if job.status != JobStatus.COMPLETED:
                return None

            return await self._read_results_for_job(api_client, job)

    def get_results(self, job_id: int) -> Any:
        """Get results for algorithm/circuit."""
        return asyncio.run(self._get_results(job_id))

    async def _create_flow(self, program: BaseAlgorithm, backend_type_id: int) -> int:
        """Call the necessary methods in the correct order, with the correct parameters."""
        async with ApiClient(self._configuration) as api_client:
            project = await self._create_project(api_client, program)
            algorithm = await self._create_algorithm(api_client, program, project)
            commit = await self._create_commit(api_client, algorithm)
            file = await self._create_file(api_client, program, commit)
            batch_job = await self._create_batch_job(api_client, backend_type_id=backend_type_id)
            job: Job = await self._create_job(api_client, file, batch_job)
            await self._enqueue_batch_job(api_client, batch_job)
            return job.id  # type: ignore

    @staticmethod
    async def _create_project(api_client: ApiClient, program: BaseAlgorithm) -> Project:
        api_instance = ProjectsApi(api_client)
        obj = ProjectIn(
            owner_id=1,
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
    async def _create_file(api_client: ApiClient, program: BaseAlgorithm, commit: Commit) -> File:
        api_instance = FilesApi(api_client)
        obj = FileIn(
            commit_id=commit.id,
            content=program.content,
            language_id=1,
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
    async def _create_job(api_client: ApiClient, file: File, batch_job: BatchJob) -> Job:
        api_instance = JobsApi(api_client)
        obj = JobIn(
            file_id=file.id,
            batch_job_id=batch_job.id,
        )
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
