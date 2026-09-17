from dcc_backend_common.logger import get_logger
from fastapi import APIRouter, Depends, Request

from dataspot_facade_api.dependencies import get_jwt_payload
from dataspot_facade_api.models.person import Person
from dataspot_facade_api.utils.jwt_utils import JwtPayload

logger = get_logger("convert_router")

_jwt_payload_dependency = Depends(get_jwt_payload)


def create_router() -> APIRouter:
    logger.debug("Creating example router")
    router: APIRouter = APIRouter(prefix="/example", tags=["example"])

    @router.get("/hello_world", description="Hello world route")
    def hello_world(name: str):
        return Person(name=name)

    @router.post("/ping", summary="Ping")
    async def convert(
        request: Request,
    ) -> str:
        return "Pong"

    @router.get("/me", description="Returns the authenticated user from the JWT token")
    def me(payload: JwtPayload = _jwt_payload_dependency):
        return payload

    logger.debug("Example router configured")
    return router
