from uuid import UUID

from dcc_backend_common.logger import get_logger
from fastapi import APIRouter, Depends, HTTPException, status

from dataspot_facade_api.dependencies import get_jwt_payload
from dataspot_facade_api.models.dataset import UpdateLastUpdateRequest, UpdateLastUpdateResponse
from dataspot_facade_api.services.dataset_service import (
    DatasetNotFoundError,
    DatasetService,
    DatasetUpdateError,
)
from dataspot_facade_api.utils.jwt_utils import JwtPayload

logger = get_logger("dataset_router")

_jwt_payload_dependency = Depends(get_jwt_payload)


def create_router(dataset_service: DatasetService) -> APIRouter:
    logger.debug("Creating dataset router")
    router = APIRouter(prefix="/datasets", tags=["datasets"])

    @router.patch(
        "/{dataset_id}/last-update",
        summary="Update dataset lastUpdate",
        description=(
            "Updates the Dataspot dataset customProperties.lastUpdate field. "
            "Requires a valid facade JWT. Dataspot writes use the configured service user."
        ),
        response_model=UpdateLastUpdateResponse,
    )
    async def update_last_update(
        dataset_id: UUID,
        request: UpdateLastUpdateRequest,
        _payload: JwtPayload = _jwt_payload_dependency,
    ) -> UpdateLastUpdateResponse:
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
