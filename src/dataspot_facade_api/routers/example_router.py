import asyncio
from typing import Annotated

from dcc_backend_common.logger import get_logger
from dcc_backend_common.usage_tracking import UsageTrackingService
from fastapi import APIRouter, Request

from dataspot_facade_api.models.person import Person

logger = get_logger("convert_router")

def create_router(
) -> APIRouter:
    logger.debug("Creating example router")
    router: APIRouter = APIRouter(prefix="/example", tags=["example"])

    @router.get("/hello_world", description="Hello world route")
    def hello_world(name:str):
        return Person(name=name)

    @router.post("/ping", summary="Ping")
    async def convert(
        request: Request,
    ) -> str:
        return "Pong"

    logger.debug("Example router configured")
    return router
