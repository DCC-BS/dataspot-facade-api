from dcc_backend_common.logger import get_logger
from fastapi import APIRouter, Depends, HTTPException, Request

from dataspot_facade_api.app_config import Configuration
from dataspot_facade_api.dependencies import get_jwt_payload
from dataspot_facade_api.models.query import QueryRequest
from dataspot_facade_api.services.auth_service import DataspotAuthClient
from dataspot_facade_api.services.query_service import QueryService
from dataspot_facade_api.utils.jwt_utils import JwtPayload

logger = get_logger("query_router")

_jwt_payload_dependency = Depends(get_jwt_payload)


def create_router(config: Configuration) -> APIRouter:
    logger.debug("Creating query router")
    router: APIRouter = APIRouter(prefix="/queries", tags=["queries"])

    @router.post("/execute", summary="Execute a SQL query via the Dataspot Query API")
    def execute_query(
        request: Request,
        query: QueryRequest,
        payload: JwtPayload = _jwt_payload_dependency,
    ):
        dataspot_auth = DataspotAuthClient()
        query_service = QueryService(config=config, dataspot_auth=dataspot_auth)

        try:
            return query_service.execute_query(query.sql)
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Query execution failed: %s", e)
            raise HTTPException(status_code=502, detail=f"Query API request failed: {e}") from e

    logger.debug("Query router configured")
    return router
