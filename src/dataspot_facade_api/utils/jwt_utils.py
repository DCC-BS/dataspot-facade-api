from dataclasses import dataclass
from datetime import datetime

import jwt
from jwt.exceptions import InvalidTokenError

from dataspot_facade_api.app_config import Configuration


@dataclass
class JwtPayload:
    user_id: str
    email: str
    issued_at: datetime | None
    expires_at: datetime | None


def validate_jwt(token: str, config: Configuration) -> JwtPayload:
    try:
        decoded = jwt.decode(token, config.jwt_secret, algorithms=[config.jwt_algorithm])
    except InvalidTokenError as e:
        raise ValueError(f"Invalid JWT token: {e}") from e

    user_id = decoded.get("sub")
    email = decoded.get("email")

    if user_id is None or email is None:
        raise ValueError("JWT token is missing required claims (sub, email)")

    issued_at = None
    if "iat" in decoded:
        issued_at = datetime.fromtimestamp(decoded["iat"])

    expires_at = None
    if "exp" in decoded:
        expires_at = datetime.fromtimestamp(decoded["exp"])

    return JwtPayload(
        user_id=user_id,
        email=email,
        issued_at=issued_at,
        expires_at=expires_at,
    )
