import logging
import os

import sentry_sdk
from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration

from dataspot_facade_api.container import Container
from dataspot_facade_api.logging_config import setup_logging
from dataspot_facade_api.routers import auth_router, dataset_router, query_router

logger = logging.getLogger("dataspot_facade_api.app")


def create_app() -> FastAPI:
    # RUSTRAK_DEBUG=true turns on the app's debug log lines by raising LOG_LEVEL
    # to DEBUG before the logging pipeline is initialized below.
    if os.environ.get("RUSTRAK_DEBUG", "false").lower() == "true":
        os.environ.setdefault("LOG_LEVEL", "DEBUG")

    setup_logging()

    # Mount the app under a base path, e.g. /fade-api. Starlette strips the
    # root_path prefix from incoming requests before matching routes, so this
    # covers both proxy styles: one that strips /fade-api before forwarding
    # (with the prefix reaching the app via `uvicorn --root-path /fade-api` or
    # the proxy's forwarded scope) and one that forwards /fade-api/... as-is.
    base_path = os.environ.get("BASE_PATH", "").rstrip("/")
    root_path = os.environ.get("ROOT_PATH", base_path).rstrip("/")

    dsn = os.environ.get("RUSTRAK_DSN")
    if dsn:
        # Level at which app log records are forwarded to Rustrak's Logs.
        rustrak_log_level = os.environ.get("RUSTRAK_LOG_LEVEL", "INFO").upper()
        # Level at which records also become error events in the dashboard.
        rustrak_event_level = os.environ.get("RUSTRAK_EVENT_LEVEL", "ERROR").upper()
        rustrak_logging = LoggingIntegration(
            level=getattr(logging, rustrak_log_level, logging.INFO),
            event_level=getattr(logging, rustrak_event_level, logging.ERROR),
        )
        # traces_sample_rate / profiles_sample_rate power the Performance view:
        # every request becomes a transaction (FastAPI/Starlette), each outbound
        # call and handler becomes a span, and errors show their context.
        sentry_sdk.init(
            dsn=dsn,
            traces_sample_rate=1.0,
            profiles_sample_rate=1.0,
            integrations=[
                StarletteIntegration(transaction_style="endpoint"),
                FastApiIntegration(transaction_style="endpoint"),
                rustrak_logging,
            ],
            _experiments={"enable_logs": True},
        )
        logger.info(
            "Sentry/Rustrak initialized event_level=%s log_level=%s",
            rustrak_event_level,
            rustrak_log_level,
        )
    else:
        logger.warning("RUSTRAK_DSN not set; error tracking and performance disabled")

    logger.info("Starting Dataspot Facade API application")

    logger.debug("Reading environment configuration")
    debug_enabled = os.environ.get("RUSTRAK_DEBUG", "false").lower() == "true"
    logger.debug("Configuring dependency injection container")
    container = Container()
    container.wire(
        modules=[
            auth_router,
            query_router,
            dataset_router,
        ]
    )
    container.check_dependencies()
    logger.debug("Dependency injection configured container_ok=True")

    config = container.config()
    logger.info(
        "Running with configuration base_url=%s database_name=%s",
        config.dataspot_base_url,
        config.database_name,
    )

    app = FastAPI(
        title="Dataspot Facade API",
        description=(
            "FastAPI facade service for the Dataspot platform.\n\n"
            "The source code and additional documentation are available at "
            "https://github.com/DCC-BS/dataspot-facade-api; working examples "
            "for all endpoints can be found under "
            "https://github.com/DCC-BS/dataspot-facade-api/tree/main/examples.\n\n"
            "## Authentication\n"
            "This API is not addressed directly with Dataspot credentials. Instead, a "
            "Dataspot access key is exchanged for a short-lived JWT that is used for "
            "all subsequent calls:\n\n"
            "1. Obtain a Dataspot access key (a personal access key from the Dataspot "
            "platform).\n"
            "2. Send it to `POST /v1/auth` to validate the key and identify the "
            "associated user.\n"
            "3. On success, the endpoint returns a signed JWT (HS256 by default) that "
            "is **valid for 1 hour** (`jwt_expires_in_seconds=3600`).\n"
            "4. Send the JWT on every protected request as the `Authorization` header: "
            "`Bearer <access_token>`. When it expires, repeat the exchange with the "
            "access key to get a new JWT.\n\n"
            "All protected endpoints rely on the claims of this JWT (user id, email, "
            "person id) for authorization."
        ),
        version="v1",
        root_path=root_path,
    )

    api_prefix = "/v1"
    api_router = APIRouter(prefix=api_prefix)

    # app.include_router(health_probe_router(service_dependencies))

    logger.debug("Setting up CORS middleware")
    is_prod = os.environ.get("IS_PROD", "false").lower() == "true"
    origins = [config.dataspot_base_url]
    if not is_prod:
        origins.append("http://127.0.0.1:8090")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    logger.debug("Registering API routers")
    api_router.include_router(auth_router.create_router())
    api_router.include_router(query_router.create_router())
    api_router.include_router(dataset_router.create_router())
    logger.debug("All routers registered")
    app.include_router(api_router)

    logger.info("API setup complete debug_enabled=%s base_path=%s", debug_enabled, base_path or "/")
    return app


app = create_app()
