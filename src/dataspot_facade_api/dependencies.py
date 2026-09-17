from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from dataspot_facade_api.app_config import Configuration
from dataspot_facade_api.container import Container
from dataspot_facade_api.services.utils.jwt_utils import JwtPayload, validate_jwt

_bearer_scheme = HTTPBearer()
_config_dependency = Depends(lambda: Container().config())
_credentials_dependency = Depends(_bearer_scheme)


def get_jwt_payload(
    credentials: HTTPAuthorizationCredentials = _credentials_dependency,
    config: Configuration = _config_dependency,
) -> JwtPayload:
    try:
        return validate_jwt(credentials.credentials, config)
    except ValueError as e:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from e
