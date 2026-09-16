
from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from structlog.stdlib import BoundLogger

from dcc_backend_common.logger import get_logger
from dcc_backend_common.fastapi_health_probes import health_probe_router

from dataspot_facade_api.routers import example_router


def create_app() -> FastAPI:

    logger: BoundLogger = get_logger("app")
    logger.info("Starting Text Mate API application")

    app = FastAPI(
        title="Dataspot Facade API",
        description="TODO",
        version="v1",
    )

    api_prefix = "/v1"
    api_router = APIRouter(prefix=api_prefix)

    # app.include_router(health_probe_router(service_dependencies))

    logger.debug("Setting up CORS middleware")
    app.add_middleware(
        CORSMiddleware,
        # allow_origins=[config.client_url],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Binds a per-request request_id into the structlog context so every log line
    # emitted while handling a request carries the same id.
    # add_logging_middleware(app)

    logger.debug("Registering API routers")
    api_router.include_router(example_router.create_router())
    # api_router.include_router(quick_action.create_router())
    # api_router.include_router(word_synonym.create_router())
    # api_router.include_router(sentence_rewrite.create_router())
    # api_router.include_router(convert_route.create_router())
    # api_router.include_router(user_action_route.create_router())
    # api_router.include_router(text_analysis.create_router())
    # api_router.include_router(simplify.create_router())
    logger.debug("All routers registered")
    app.include_router(api_router)

    logger.info("API setup complete")
    return app


app = create_app()