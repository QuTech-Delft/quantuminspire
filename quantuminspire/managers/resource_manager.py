import time
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
    CompilePayload,
    CompileStage,
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
    PageBackendType,
    PageResult,
    Project,
    ProjectIn,
    ProjectPatch,
    ProjectsApi,
    Result,
    ResultsApi,
    ShareType,
)
from compute_api_client.exceptions import ForbiddenException, NotFoundException
from pydantic import BaseModel, Field
from qi2_shared.client import config
from qi2_shared.pagination import ItemType, PageReader, PageType
from qi2_shared.utils import run_async


class ResourceOptions(BaseModel):
    algorithm_id: Optional[int] = Field(None)
    project_id: Optional[int] = Field(None)
    project_name: str
    project_description: str
    algorithm_name: str
    file_path: Path


class JobOptions(ResourceOptions):
    job_id: Optional[int] = Field(None)
    number_of_shots: Optional[int] = Field(None)
    raw_data_enabled: Optional[bool] = Field(None)
    backend_type_id: int


class CompileOptions(ResourceOptions):
    compile_stage: Optional[CompileStage] = Field(None)
    backend_type_id: int


class ResourceManager:
    @staticmethod
    def _invoke(
        api_class: Type[Any],
        method_name: str,
        *args: Any,
        page_reader: Optional[PageReader[PageType, ItemType]] = None,
        **kwargs: Any,
    ) -> Any:
        """Invoke an API method asynchronously using the given API class and method name.

        Opens an API client, instantiates the given API class, and calls the specified method.
        If a page_reader is provided, all paginated results are fetched and returned; otherwise
        the method is called directly and its result is returned.

        Args:
            api_class: The API class to instantiate with the API client.
            method_name: The name of the method to call on the API instance.
            page_reader: An optional PageReader used to fetch all pages of a paginated response.
                If None, the method is called directly.
            *args: Positional arguments to pass to the API method.
            **kwargs: Keyword arguments to pass to the API method.

        Returns:
            All items across pages if a page_reader is provided, otherwise the direct result
            returned by the API method.
        """

        async def _execute() -> Any:
            async with ApiClient(config()) as client:
                api_instance = api_class(client)
                method: Callable[..., Awaitable[Any]] = getattr(api_instance, method_name)

                if page_reader is None:
                    return await method(*args, **kwargs)
                else:
                    return await page_reader.get_all(method, **kwargs)

        return run_async(_execute())

    def _run_create_commit_flow(self, resource_options: ResourceOptions, owner_id: int) -> Commit:
        """Run the flow to create or update project and algorithm resources, and then create a commit.

        Args:
            resource_options: Options describing the project and algorithm, including names, descriptions, file path.
            owner_id: The ID of the owner under which remote resources are created.

        Returns:
            The created Commit object
        """
        if resource_options.project_id is None or self.read_project(resource_options.project_id) is None:
            project = self.create_project(
                owner_id=owner_id,
                project_name=resource_options.project_name,
                project_description=resource_options.project_description,
            )
            resource_options.project_id = project.id
        else:
            self.update_project(
                project_id=resource_options.project_id,
                project_name=resource_options.project_name,
                project_description=resource_options.project_description,
            )

        algorithm_type: AlgorithmType = self.get_algorithm_type(file_path=resource_options.file_path)

        if resource_options.algorithm_id is None or self.read_algorithm(resource_options.algorithm_id) is None:
            algorithm = self.create_algorithm(
                project_id=resource_options.project_id,
                algorithm_name=resource_options.algorithm_name,
                algorithm_type=algorithm_type,
            )
            resource_options.algorithm_id = algorithm.id
        else:
            algorithm = self.update_algorithm(
                project_id=resource_options.project_id,
                algorithm_id=resource_options.algorithm_id,
                algorithm_name=resource_options.algorithm_name,
                algorithm_type=algorithm_type,
            )

        return self._create_commit(algorithm_id=algorithm.id)

    def _run_create_file_flow(self, resource_options: ResourceOptions, commit_id: int) -> File:
        """Run the flow to create a file attached to a commit.

        Args:
            resource_options: Options describing the file to create, including the file path and algorithm type.
            commit_id: The ID of the commit to attach the file to.

        Returns:
            The created File object.
        """
        algorithm_type: AlgorithmType = self.get_algorithm_type(file_path=resource_options.file_path)
        language: Language = self._get_language_for_algorithm(algorithm_type=algorithm_type)

        return self._create_file(
            file_content=resource_options.file_path.read_text(), language_id=language.id, commit_id=commit_id
        )

    def run_job_submission_flow(self, job_options: JobOptions, owner_id: int) -> JobOptions:
        """Run the full job submission flow, creating or updating all required remote resources.

        Args:
            job_options: Options describing the job to submit, including project, algorithm, and execution settings.
            owner_id: The ID of the owner under which remote resources are created.

        Returns:
            The updated JobOptions with all remote resource IDs populated, including the submitted job ID.
        """
        commit = self._run_create_commit_flow(resource_options=job_options, owner_id=owner_id)
        file = self._run_create_file_flow(resource_options=job_options, commit_id=commit.id)

        batch_job: BatchJob = self._create_batch_job(backend_type_id=job_options.backend_type_id)

        job: Job = self._create_job(
            file_id=file.id,
            batch_job_id=batch_job.id,
            num_shots=job_options.number_of_shots,
            raw_data_enabled=job_options.raw_data_enabled,
        )

        self._enqueue_batch_job(batch_job_id=batch_job.id)

        job_options.job_id = job.id

        return job_options

    def run_compile_file_flow(self, compile_options: CompileOptions, owner_id: int) -> None:
        """Run the flow to compile a file attached to a commit, creating or updating all required remote resources.

        Args:
            compile_options: Options describing the file to compile,
                including project and algorithm details, file path, and compile settings.
            owner_id: The ID of the owner under which remote resources are created.

        Returns:
            None. The compiled file content is saved to disk with a modified name based on the original file path.
        """
        commit = self._run_create_commit_flow(resource_options=compile_options, owner_id=owner_id)
        self._run_create_file_flow(resource_options=compile_options, commit_id=commit.id)

        self._invoke(
            CommitsApi,
            "compile_commit_commits_id_compile_post",
            commit.id,
            CompilePayload(
                compile_stage=compile_options.compile_stage, backend_type_id=compile_options.backend_type_id
            ),
        )

        commit_files = self._invoke(FilesApi, "read_files_files_get", commit_id=commit.id, generated=True)

        if commit_files.items:
            compiled_file: File = commit_files.items[0]
            compiled_file_name = (
                f"{compile_options.file_path.with_suffix('')}{compiled_file.name}{compile_options.file_path.suffix}"
            )
            Path(compiled_file_name).write_text(compiled_file.content)
            print(f"Compiled file saved to {compiled_file_name}")
        else:
            raise RuntimeError("No compiled file was generated for the commit")

    def get_backend_types(self) -> List[BackendType]:
        """Retrieve all available backend types.

        Returns:
            A list of all available backend types.
        """
        backend_types_page: PageBackendType = self._invoke(BackendTypesApi, "read_backend_types_backend_types_get")
        items: List[BackendType] = backend_types_page.items
        return items

    def get_job(self, job_id: int) -> Job:
        """Retrieve a job by its ID.

        Args:
            job_id: The ID of the job to retrieve.

        Returns:
            The Job object for the given ID.
        """
        return self._invoke(JobsApi, "read_job_jobs_id_get", id=job_id)

    def wait_for_job_completion(self, job_id: int, timeout: float) -> Job:
        """Poll until the job has finished or the timeout is reached.

        Args:
            job_id: The ID of the job to wait for.
            timeout: Maximum number of seconds to wait before raising a TimeoutError.

        Returns:
            The completed Job object once it leaves the PLANNED or RUNNING state.
        """
        start_time = time.monotonic()

        print("Waiting for job to complete...")
        while True:
            job = self.get_job(job_id)

            if job.status not in [JobStatus.PLANNED, JobStatus.RUNNING]:
                return job

            if time.monotonic() - start_time >= timeout:
                raise TimeoutError(f"Job {job.id} did not complete within {timeout} seconds")

            time.sleep(1)

    def get_final_result(self, job_id: int) -> FinalResult | None:
        """Retrieve the final result of a job by its ID.

        Args:
            job_id: The ID of the job to retrieve the result for.

        Returns:
            The FinalResult object for the job, or None if no result is available yet.
        """
        return self._invoke(FinalResultsApi, "read_final_result_by_job_id_final_results_job_job_id_get", job_id)

    def get_results(self, job_id: int) -> list[Result]:
        """Retrieve the results of a job by its ID.

        Args:
            job_id: The ID of the job to retrieve the results for.

        Returns:
            The list of the Result object for the job, or None if no result is available yet.
        """
        page_reader = PageReader[PageResult, Result]()
        results: list[Result] = self._invoke(
            ResultsApi, "read_results_by_job_id_results_job_job_id_get", page_reader=page_reader, job_id=job_id
        )
        return results

    @staticmethod
    def get_algorithm_type(file_path: Path) -> AlgorithmType:
        """Determine the algorithm type from the file extension.

        Args:
            file_path: Path to the algorithm file.

        Returns:
            AlgorithmType.HYBRID for .py files, or AlgorithmType.QUANTUM for .cq files.
        """
        if file_path.suffix == ".py":
            return AlgorithmType.HYBRID
        elif file_path.suffix == ".cq":
            return AlgorithmType.QUANTUM
        raise ValueError("Incorrect file type. Supported types are .py and .cq")

    def create_project(self, owner_id: int, project_name: str, project_description: str) -> Project:
        """Create a new remote project.

        Args:
            owner_id: The ID of the owner of the project.
            project_name: Name of the project to create.
            project_description: Description of the project.

        Returns:
            The created Project object.
        """
        obj = ProjectIn(
            owner_id=owner_id,
            name=project_name,
            description=project_description,
            starred=False,
        )
        return self._invoke(ProjectsApi, "create_project_projects_post", obj)

    def read_project(self, project_id: int) -> Project | None:
        """Retrieve a remote project by its ID.

        Args:
            project_id: The ID of the project to retrieve.

        Returns:
            The Project object if found, or None if the project does not exist or access is forbidden.
        """
        try:
            return self._invoke(ProjectsApi, "read_project_projects_id_get", project_id)
        except (NotFoundException, ForbiddenException):
            return None

    def update_project(self, project_id: int, project_name: str, project_description: str) -> Project:
        """Update an existing remote project.

        Args:
            project_id: The ID of the project to update.
            project_name: New name for the project.
            project_description: New description for the project.

        Returns:
            The updated Project object.
        """
        obj = ProjectPatch(name=project_name, description=project_description)
        return self._invoke(ProjectsApi, "partial_update_project_projects_id_patch", project_id, obj)

    def create_algorithm(self, project_id: int, algorithm_name: str, algorithm_type: AlgorithmType) -> Algorithm:
        """Create a new remote algorithm within a project.

        Args:
            project_id: The ID of the project to create the algorithm in.
            algorithm_name: Name of the algorithm to create.
            algorithm_type: The type of the algorithm (HYBRID or QUANTUM).

        Returns:
            The created Algorithm object.
        """
        obj = AlgorithmIn(
            project_id=project_id,
            type=algorithm_type,
            shared=ShareType.PRIVATE,
            name=algorithm_name,
        )
        return self._invoke(AlgorithmsApi, "create_algorithm_algorithms_post", obj)

    def read_algorithm(self, algorithm_id: int) -> Algorithm | None:
        """Retrieve a remote algorithm by its ID.

        Args:
            algorithm_id: The ID of the algorithm to retrieve.

        Returns:
            The Algorithm object if found, or None if the algorithm does not exist or access is forbidden.
        """
        try:
            return self._invoke(AlgorithmsApi, "read_algorithm_algorithms_id_get", algorithm_id)
        except (NotFoundException, ForbiddenException):
            return None

    def update_algorithm(
        self, project_id: int, algorithm_id: int, algorithm_name: str, algorithm_type: AlgorithmType
    ) -> Algorithm:
        """Update an existing remote algorithm.

        Args:
            project_id: The ID of the project the algorithm belongs to.
            algorithm_id: The ID of the algorithm to update.
            algorithm_name: New name for the algorithm.
            algorithm_type: The type of the algorithm (HYBRID or QUANTUM).

        Returns:
            The updated Algorithm object.
        """
        obj = AlgorithmIn(
            project_id=project_id,
            type=algorithm_type,
            shared=ShareType.PRIVATE,
            name=algorithm_name,
        )
        return self._invoke(AlgorithmsApi, "update_algorithm_algorithms_id_put", algorithm_id, obj)

    def _create_commit(self, algorithm_id: int) -> Commit:
        """Create a new commit for the given algorithm.

        Args:
            algorithm_id: The ID of the algorithm to create a commit for.

        Returns:
            The created Commit object.
        """
        obj = CommitIn(
            description="Commit created by SDK",
            algorithm_id=algorithm_id,
        )
        return self._invoke(CommitsApi, "create_commit_commits_post", obj)

    def _get_language_for_algorithm(self, algorithm_type: AlgorithmType) -> Language:
        """Retrieve the language associated with the given algorithm type.

        Args:
            algorithm_type: The algorithm type to look up a language for.

        Returns:
            The Language object matching the algorithm type.
        """
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
        """Create a new file resource attached to a commit.

        Args:
            file_content: The source code content of the file.
            language_id: The ID of the language the file is written in.
            commit_id: The ID of the commit to attach the file to.

        Returns:
            The created File object.
        """
        obj = FileIn(
            commit_id=commit_id,
            content=file_content,
            language_id=language_id,
            compile_stage=CompileStage.NONE,
            compile_properties={},
        )

        return self._invoke(FilesApi, "create_file_files_post", obj)

    def _create_batch_job(self, backend_type_id: int) -> BatchJob:
        """Create a new batch job for the given backend type.

        Args:
            backend_type_id: The ID of the backend type to run the batch job on.

        Returns:
            The created BatchJob object.
        """
        obj = BatchJobIn(backend_type_id=backend_type_id)
        return self._invoke(BatchJobsApi, "create_batch_job_batch_jobs_post", obj)

    def _create_job(
        self, file_id: int, batch_job_id: int, num_shots: Optional[int], raw_data_enabled: Optional[bool]
    ) -> Job:
        """Create a new job within a batch job.

        Args:
            file_id: The ID of the file to execute.
            batch_job_id: The ID of the batch job to attach this job to.
            num_shots: Number of shots to run.
            raw_data_enabled: Whether to enable raw data collection for the job.

        Returns:
            The created Job object.
        """
        obj = JobIn(
            file_id=file_id, batch_job_id=batch_job_id, number_of_shots=num_shots, raw_data_enabled=raw_data_enabled
        )
        return self._invoke(JobsApi, "create_job_jobs_post", obj)

    def _enqueue_batch_job(self, batch_job_id: int) -> BatchJob:
        """Enqueue a batch job for execution.

        Args:
            batch_job_id: The ID of the batch job to enqueue.

        Returns:
            The updated BatchJob object after enqueuing.
        """
        return self._invoke(BatchJobsApi, "enqueue_batch_job_batch_jobs_id_enqueue_patch", batch_job_id)
