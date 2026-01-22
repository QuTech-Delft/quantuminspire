from typing import Annotated, Optional

from pydantic import BaseModel, BeforeValidator, Field, HttpUrl

Url = Annotated[str, BeforeValidator(lambda value: str(HttpUrl(value)).rstrip("/"))]


class Algorithm(BaseModel):
    id: Optional[int] = Field(None)
    algorithm_type: str = Field("quantum")
    num_shots: int = Field(1024)
    store_raw_data: bool = Field(False)


class Project(BaseModel):
    id: Optional[int] = Field(None)
    name: str = Field("Example Project")
    description: str = Field("Example Project")


class Job(BaseModel):
    id: Optional[int] = Field(None)
