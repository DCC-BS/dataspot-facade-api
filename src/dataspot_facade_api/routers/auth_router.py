from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, HTTPException

from dataspot_facade_api.app_config import Configuration
from dataspot_facade_api.container import Container
from dataspot_facade_api.logging_config import get_logger
from dataspot_facade_api.models.auth import AuthRequest, AuthResponse
from dataspot_facade_api.services.auth_service import AuthService

logger = get_logger("auth_router")


@inject
def create_router(
    auth_service: AuthService = Provide[Container.auth_service],
    config: Configuration = Provide[Container.config],
) -> APIRouter:
    logger.debug("Creating auth router")
    router: APIRouter = APIRouter(prefix="/auth", tags=["auth"])

    @router.post(
        "",
        summary="Authenticate with access key",
        description=(
            "Exchanges a raw Dataspot access key for a short-lived facade JWT. "
            "The access key is validated and used to look up the associated user; "
            "on success a signed JWT is returned that must be sent as a Bearer token "
            "to all protected endpoints."
        ),
        response_model=AuthResponse,
        responses={
            401: {"description": "Invalid access key"},
        },
    )
    def authenticate(request: AuthRequest) -> AuthResponse:
        logger.debug("Validating access key")
        user_info = auth_service.validate_and_identify(request.access_key)
        if user_info is None:
            logger.warning("Authentication failed: invalid access key")
            raise HTTPException(status_code=401, detail="Invalid access key")

        token = AuthService.create_jwt(
            user_id=user_info.user_id,
            email=user_info.email,
            person_id=user_info.person_id,
            secret=config.jwt_secret,
            algorithm=config.jwt_algorithm,
            expires_in_seconds=config.jwt_expires_in_seconds,
        )
        logger.info("User authenticated", user=user_info.email)
        return AuthResponse(access_token=token)

    logger.debug("Auth router configured")
    return router
