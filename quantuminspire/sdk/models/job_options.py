from pydantic import BaseModel, Field


class JobOptions(BaseModel):
    """Options for running a job.

    Subset of fields in the JobIn schema.
    """

    number_of_shots: int = Field(
        1024, ge=1, description="Number of shots for the job (only pure cQASM algorithms supported)."
    )
    raw_data_enabled: bool = Field(
        False, description="Whether to enable shot memory for the job (only pure cQASM algorithms supported)."
    )
