import os

from dcc_backend_common.logger import get_logger, init_logger
from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from structlog.stdlib import BoundLogger

from dataspot_facade_api.container import Container
from dataspot_facade_api.routers import auth_router, dataset_router, example_router, query_router


def create_app() -> FastAPI:

    init_logger(app_name="dataspot-facade-api")

    logger: BoundLogger = get_logger("app")
    logger.info("Starting Dataspot Facade API application")

    logger.debug("Configuring dependency injection container")
    container = Container()
    container.wire(modules=[example_router])
    container.check_dependencies()
    logger.debug("Dependency injection configured")

    config = container.config()
    logger.info(f"Running with configuration: {config}")

    app = FastAPI(
        title="Dataspot Facade API",
        description="TODO",
        version="v1",
    )

    api_prefix = "/v1"
    api_router = APIRouter(prefix=api_prefix)

    # app.include_router(health_probe_router(service_dependencies))

    logger.debug("Setting up CORS middleware")
    is_prod = os.environ.get("IS_PROD", "false").lower() == "true"
    origins = [config.base_url]
    if not is_prod:
        origins.append("http://127.0.0.1:8090")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Binds a per-request request_id into the structlog context so every log line
    # emitted while handling a request carries the same id.
    # add_logging_middleware(app)

    logger.debug("Registering API routers")
    api_router.include_router(example_router.create_router())
    api_router.include_router(auth_router.create_router(config))
    api_router.include_router(query_router.create_router(config))
    api_router.include_router(dataset_router.create_router(container.dataset_service()))
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
