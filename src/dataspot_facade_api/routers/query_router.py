import asyncio
import logging
from time import perf_counter

import sentry_sdk
from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, HTTPException, Request, status

from dataspot_facade_api.container import Container
from dataspot_facade_api.dependencies import get_jwt_payload
from dataspot_facade_api.models.query import QueryRequest
from dataspot_facade_api.services.authorization_service import NotAuthorizedError, QueryAuthorizationService
from dataspot_facade_api.services.query_service import QueryService
from dataspot_facade_api.services.utils.jwt_utils import JwtPayload

logger = logging.getLogger("dataspot_facade_api.query_router")

_jwt_payload_dependency = Depends(get_jwt_payload)


@inject
def create_router(
    query_service: QueryService = Provide[Container.query_service],
    authorization_service: QueryAuthorizationService = Provide[Container.query_authorization_service],
) -> APIRouter:
    logger.debug("Creating query router")
    router: APIRouter = APIRouter(prefix="/queries", tags=["queries"])

    @router.post(
        "/execute",
        summary="Execute a SQL query via the Dataspot Query API",
        description=(
            "Runs an arbitrary SQL statement against the configured Dataspot database "
            "and returns the result set as JSON. The query is executed via the Dataspot "
            "Query API running as the configured service user. "
            "Requires a valid facade JWT (Bearer token)."
            "Requires a valid facade JWT. The caller must hold the "
            "'Query-Befehle' facade-API permission."
        ),
        responses={
            200: {"description": "Query result set as JSON"},
            401: {"description": "Missing or invalid JWT"},
            502: {"description": "Dataspot Query API request failed"},
        },
    )
    async def execute_query(
        request: Request,
        query: QueryRequest,
        payload: JwtPayload = _jwt_payload_dependency,
    ):
        start = perf_counter()
        sentry_sdk.set_tag("user", payload.email)
        sentry_sdk.set_tag("endpoint", "POST /v1/queries/execute")
        logger.debug("Query execution started user=%s", payload.email)

        try:
            await authorization_service.ensure_can_execute_query(payload)
        except NotAuthorizedError as exc:
            logger.info("Query execution denied user=%s reason=%s", payload.email, exc)
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

        try:
            result = await asyncio.to_thread(query_service.execute_query, query.sql)
        except HTTPException:
            raise
        except Exception as e:
            sentry_sdk.capture_exception(e)
            logger.error("Query execution failed error=%s user=%s", e, payload.email)
            raise HTTPException(status_code=502, detail=f"Query API request failed: {e}") from e

        elapsed_ms = round((perf_counter() - start) * 1000, 2)
        sentry_sdk.set_tag("query_duration_ms", elapsed_ms)
        logger.info(
            "Query executed successfully duration_ms=%s user=%s",
            elapsed_ms,
            payload.email,
        )
        return result

    logger.debug("Query router configured")
    return router
