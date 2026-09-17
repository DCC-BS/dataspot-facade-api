from pydantic import Field
from pydantic.main import BaseModel


class AuthRequest(BaseModel):
    access_key: str = Field(
        description="Dataspot access key to authenticate. "
        "Obtained from the Dataspot platform; used once to obtain a facade JWT."
    )


class AuthResponse(BaseModel):
    access_token: str = Field(
        description="JWT token for authenticated requests. "
        "Send as the Authorization header value: 'Bearer <access_token>'."
    )
    token_type: str = Field(default="bearer", description="Token type; always 'bearer'.")
