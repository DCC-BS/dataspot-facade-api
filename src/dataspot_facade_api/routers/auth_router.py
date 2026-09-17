from dcc_backend_common.logger import get_logger
from fastapi import APIRouter, HTTPException

from dataspot_facade_api.app_config import Configuration
from dataspot_facade_api.models.auth import AuthRequest, AuthResponse
from dataspot_facade_api.services.auth_service import AuthService, DataspotAuthClient

logger = get_logger("auth_router")


def create_router(config: Configuration) -> APIRouter:
    logger.debug("Creating auth router")
    router: APIRouter = APIRouter(prefix="/auth", tags=["auth"])

    @router.post("", summary="Authenticate with access key", response_model=AuthResponse)
    def authenticate(request: AuthRequest) -> AuthResponse:
        dataspot_auth = DataspotAuthClient()
        auth_service = AuthService(config=config, dataspot_auth=dataspot_auth)

        user_info = auth_service.validate_and_identify(request.access_key)
        if user_info is None:
            raise HTTPException(status_code=401, detail="Invalid access key")

        token = AuthService.create_jwt(
            user_id=user_info.user_id,
            email=user_info.email,
            person_id=user_info.person_id,
            secret=config.jwt_secret,
            algorithm=config.jwt_algorithm,
            expires_in_seconds=config.jwt_expires_in_seconds,
        )

        return AuthResponse(access_token=token)

    logger.debug("Auth router configured")
    return router
