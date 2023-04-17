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
import uuid

from compute_api_client import (
    Algorithm,
    AlgorithmIn,
    AlgorithmsApi,
    AlgorithmType,
    ApiClient,
    BatchRun,
    BatchRunIn,
    BatchRunsApi,
    Commit,
    CommitIn,
    CommitsApi,
    CompileStage,
    Configuration,
    File,
    FileIn,
    FilesApi,
    Project,
    ProjectIn,
    ProjectsApi,
    Run,
    RunIn,
    RunsApi,
    RunStatus,
    ShareType,
)

from quantuminspire.sdk.circuit import Circuit
from quantuminspire.util.api.base_runtime import BaseRuntime
from quantuminspire.util.configuration import Settings


class RemoteRuntime(BaseRuntime):
    """Connection to remote runtime.

    Create a connection with the remote runtime for Quantum Inspire. This connection creates the appropriate projects,
    algorithms, files etc. The algorithm/circuit will also be run.
    """

    def __init__(self) -> None:
        super().__init__()
        settings = Settings()
        host = "https://staging.qi2.quantum-inspire.com"
        self._configuration = Configuration(host=host, api_key={"user": str(settings.auths[host]["user_id"])})

    def run(self, circuit: Circuit) -> None:
        """Execute provided algorithm/circuit."""
        asyncio.run(self._create_flow(circuit))

    def get_results(self) -> None:
        """Get results for algorithm/circuit."""

    async def _create_flow(self, circuit: Circuit) -> None:
        """Call the necessary methods in the correct order, with the correct parameters."""
        async with ApiClient(self._configuration) as api_client:
            project = await self._create_project(api_client, circuit)
            algorithm = await self._create_algorithm(api_client, project)
            commit = await self._create_commit(api_client, algorithm)
            file = await self._create_file(api_client, commit, circuit)
            batch_run = await self._create_batch_run(api_client)
            await self._create_run(api_client, file, batch_run)
            await self._enqueue_batch_run(api_client, batch_run)

    @staticmethod
    async def _create_project(api_client: ApiClient, circuit: Circuit) -> Project:
        api_instance = ProjectsApi(api_client)
        obj = ProjectIn(
            owner_id=1,
            name=circuit.program_name,
            description="Quantum Circuit created by SDK",
            starred=False,
        )
        return await api_instance.create_project_projects_post(obj)

    @staticmethod
    async def _create_algorithm(api_client: ApiClient, project: Project) -> Algorithm:
        api_instance = AlgorithmsApi(api_client)
        obj = AlgorithmIn(
            project_id=project.id,
            type=AlgorithmType.QUANTUM,
            shared=ShareType.PRIVATE,
        )
        return await api_instance.create_algorithm_algorithms_post(obj)

    @staticmethod
    async def _create_commit(api_client: ApiClient, algorithm: Algorithm) -> Commit:
        commit_hash = uuid.uuid4().hex[0:8]
        api_instance = CommitsApi(api_client)
        obj = CommitIn(
            hash=commit_hash,
            description="Quantum Circuit created by SDK",
            algorithm_id=algorithm.id,
        )
        return await api_instance.create_commit_commits_post(obj)

    @staticmethod
    async def _create_file(api_client: ApiClient, commit: Commit, circuit: Circuit) -> File:
        api_instance = FilesApi(api_client)
        obj = FileIn(
            commit_id=commit.id,
            content=circuit.qasm,
            language_id=1,
            compile_stage=CompileStage.NONE,
            compile_properties={},
        )
        return await api_instance.create_file_files_post(obj)

    @staticmethod
    async def _create_batch_run(api_client: ApiClient) -> BatchRun:
        api_instance = BatchRunsApi(api_client)
        obj = BatchRunIn(runtime_type_id=3, user_id=1)
        return await api_instance.create_batch_run_batch_runs_post(obj)

    @staticmethod
    async def _create_run(api_client: ApiClient, file: File, batch_run: BatchRun) -> Run:
        api_instance = RunsApi(api_client)
        obj = RunIn(
            file_id=file.id,
            status=RunStatus.PLANNED,
            batch_run_id=batch_run.id,
        )
        return await api_instance.create_run_runs_post(obj)

    @staticmethod
    async def _enqueue_batch_run(api_client: ApiClient, batch_run: BatchRun) -> BatchRun:
        api_instance = BatchRunsApi(api_client)
        return await api_instance.enqueue_batch_run_batch_runs_id_enqueue_patch(batch_run.id)
