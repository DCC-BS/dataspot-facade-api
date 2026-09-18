from uuid import UUID

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, HTTPException, status

from dataspot_facade_api.container import Container
from dataspot_facade_api.dependencies import get_jwt_payload
from dataspot_facade_api.logging_config import get_logger
from dataspot_facade_api.models.dataset import UpdateLastUpdateRequest, UpdateLastUpdateResponse
from dataspot_facade_api.services.authorization_service import DatasetAuthorizationService, NotAuthorizedError
from dataspot_facade_api.services.dataset_service import (
    DatasetNotFoundError,
    DatasetService,
    DatasetUpdateError,
)
from dataspot_facade_api.services.utils.jwt_utils import JwtPayload

logger = get_logger("dataset_router")

_jwt_payload_dependency = Depends(get_jwt_payload)


@inject
def create_router(
    dataset_service: DatasetService = Provide[Container.dataset_service],
    authorization_service: DatasetAuthorizationService = Provide[Container.dataset_authorization_service],
) -> APIRouter:
    logger.debug("Creating dataset router")
    router = APIRouter(prefix="/datasets", tags=["datasets"])

    @router.patch(
        "/{dataset_id}/last-update",
        summary="Update dataset lastUpdate",
        description=(
            "Updates the Dataspot dataset customProperties.lastUpdate field. "
            "Requires a valid facade JWT (Bearer token). The caller must hold the "
            "'Feld eines Assets als Data Steward aktualisieren' facade-API permission "
            "and be a Data Steward Datenrelease of the target dataset. Dataspot writes use the configured service user."
        ),
        response_model=UpdateLastUpdateResponse,
        responses={
            200: {"description": "Dataset lastUpdate successfully updated"},
            401: {"description": "Missing or invalid JWT"},
            403: {"description": "Caller is not authorized (permission/Data Steward Datenrelease)"},
            404: {"description": "Dataset not found"},
            502: {"description": "Dataspot write failed"},
        },
    )
    async def update_last_update(
        dataset_id: UUID,
        request: UpdateLastUpdateRequest,
        payload: JwtPayload = _jwt_payload_dependency,
    ) -> UpdateLastUpdateResponse:
        logger.info("Updating dataset lastUpdate", user=payload.email, dataset_id=str(dataset_id))
        try:
            await authorization_service.ensure_can_update_last_update(dataset_id, payload)
        except NotAuthorizedError as exc:
            logger.warning(
                "Dataset lastUpdate denied",
                user=payload.email,
                dataset_id=str(dataset_id),
                reason=str(exc),
            )
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

        try:
            return await dataset_service.update_last_update(dataset_id, request.last_update)
        except DatasetNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except DatasetUpdateError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=str(exc),
            ) from exc

    logger.debug("Dataset router configured")
    return router
