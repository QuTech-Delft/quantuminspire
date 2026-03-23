from pathlib import Path
from typing import Annotated, Optional

from pydantic import AfterValidator, BaseModel, BeforeValidator, Field, HttpUrl

Url = Annotated[str, BeforeValidator(lambda value: str(HttpUrl(value)).rstrip("/"))]


def _validate_algorithm_name(value: str) -> str:
    if not value or not value.strip():
        raise ValueError("Algorithm name cannot be empty")
    if any(char in value for char in ['"', "\\"]):
        raise ValueError("Algorithm name cannot contain double quotes or backslashes")
    if any(ord(char) < 32 for char in value):
        raise ValueError("Algorithm name cannot contain control characters")
    return value


AlgorithmName = Annotated[str, BeforeValidator(lambda value: str(value)), AfterValidator(_validate_algorithm_name)]


class LocalAlgorithm(BaseModel):
    file_path: Path = Field(Path(""))
    id: Optional[int] = Field(None)
    backend_type_id: Optional[int] = Field(None)
    job_id: Optional[int] = Field(None)
    num_shots: Optional[int] = Field(None)
    store_raw_data: Optional[bool] = Field(False)


class Project(BaseModel):
    id: Optional[int] = Field(None)
    name: str = Field("")
    description: str = Field("")
    algorithms: dict[str, LocalAlgorithm] = Field(default_factory=dict)
