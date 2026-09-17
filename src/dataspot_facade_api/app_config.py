from typing import override

from dcc_backend_common.config import AbstractAppConfig, get_env_or_throw
from pydantic import Field


class Configuration(AbstractAppConfig):
    dataspot_base_url: str = Field(
        description="The base URL of the Dataspot instance", default="https://datenkatalog.bs.ch"
    )
    database_name: str = Field(description="The name of the database", default="wonderfull")
    jwt_secret: str = Field(description="Secret key for signing JWT tokens")
    jwt_algorithm: str = Field(description="Algorithm for signing JWT tokens", default="HS256")
    jwt_expires_in_seconds: int = Field(description="JWT token expiration time in seconds", default=3600)

    @classmethod
    @override
    def from_env(cls) -> "Configuration":
        return cls(
            dataspot_base_url=get_env_or_throw("BASE_URL"),
            database_name=get_env_or_throw("DATABASE_NAME"),
            jwt_secret=get_env_or_throw("JWT_SECRET"),
        )

    @override
    def __str__(self) -> str:
        return f"""
        Configuration(
            dataspot_base_url={self.dataspot_base_url},
            database_name={self.database_name}
        )
        """
