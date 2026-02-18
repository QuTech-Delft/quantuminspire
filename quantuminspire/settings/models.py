from typing import Annotated, Optional

from pydantic import BaseModel, BeforeValidator, Field, HttpUrl

Url = Annotated[str, BeforeValidator(lambda value: str(HttpUrl(value)).rstrip("/"))]


class LocalAlgorithm(BaseModel):
    id: int = Field(1)
    file_path: str = Field("")
    backend_type_id: Optional[int] = Field(None)
    job_id: Optional[int] = Field(None)
    num_shots: Optional[int] = Field(None)
    store_raw_data: Optional[bool] = Field(False)


class Project(BaseModel):
    id: Optional[int] = Field(None)
    name: str = Field("")
    description: str = Field("")
    algorithms: dict[str, LocalAlgorithm] = Field(default_factory=dict)
