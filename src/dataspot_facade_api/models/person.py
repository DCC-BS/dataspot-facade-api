
from pydantic.fields import Field
from pydantic.main import BaseModel


class Person(BaseModel):
    name: str = Field(description="The name of the person")
