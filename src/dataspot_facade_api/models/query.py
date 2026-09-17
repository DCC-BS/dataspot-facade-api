from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    sql: str = Field(description="The SQL query to execute against the Dataspot Query API")
