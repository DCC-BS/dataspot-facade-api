import asyncio
from time import perf_counter

import sentry_sdk
from dcc_backend_common.logger import get_logger
from fastapi import APIRouter, Depends, HTTPException, Request, status

from dataspot_facade_api.app_config import Configuration
from dataspot_facade_api.dependencies import get_jwt_payload
from dataspot_facade_api.models.query import QueryRequest
from dataspot_facade_api.services.auth_service import DataspotAuthClient
from dataspot_facade_api.services.authorization_service import NotAuthorizedError, QueryAuthorizationService
from dataspot_facade_api.services.query_service import QueryService
from dataspot_facade_api.utils.jwt_utils import JwtPayload

logger = get_logger("query_router")

_jwt_payload_dependency = Depends(get_jwt_payload)


def create_router(config: Configuration, authorization_service: QueryAuthorizationService) -> APIRouter:
    logger.debug("Creating query router")
    router: APIRouter = APIRouter(prefix="/queries", tags=["queries"])

    @router.post(
        "/execute",
        summary="Execute a SQL query via the Dataspot Query API",
        description=(
            "Executes a SQL query against the Dataspot Query API. "
            "Requires a valid facade JWT. The caller must hold the "
            "'Query-Befehle' facade-API permission."
        ),
    )
    async def execute_query(
        request: Request,
        query: QueryRequest,
        payload: JwtPayload = _jwt_payload_dependency,
    ):
        start = perf_counter()
        sentry_sdk.set_tag("user", payload.email)
        sentry_sdk.set_tag("endpoint", "POST /v1/queries/execute")
        logger.debug("Query execution started", user=payload.email)

        try:
            await authorization_service.ensure_can_execute_query(payload)
        except NotAuthorizedError as exc:
            logger.info("Query execution denied", user=payload.email, reason=str(exc))
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

        dataspot_auth = DataspotAuthClient()
        query_service = QueryService(config=config, dataspot_auth=dataspot_auth)

        try:
            result = await asyncio.to_thread(query_service.execute_query, query.sql)
        except HTTPException:
            raise
        except Exception as e:
            sentry_sdk.capture_exception(e)
            logger.error("Query execution failed", error=str(e), user=payload.email)
            raise HTTPException(status_code=502, detail=f"Query API request failed: {e}") from e

        elapsed_ms = round((perf_counter() - start) * 1000, 2)
        sentry_sdk.set_tag("query_duration_ms", elapsed_ms)
        logger.info(
            "Query executed successfully",
            duration_ms=elapsed_ms,
            user=payload.email,
        )
        return result

    logger.debug("Query router configured")
    return router
