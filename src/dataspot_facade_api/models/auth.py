from pydantic import Field
from pydantic.main import BaseModel


class AuthRequest(BaseModel):
    access_key: str = Field(description="Dataspot access key to authenticate")


class AuthResponse(BaseModel):
    access_token: str = Field(description="JWT token for authenticated requests")
    token_type: str = Field(default="bearer", description="Token type")
