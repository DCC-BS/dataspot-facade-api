import logging
import os
from time import perf_counter

import sentry_sdk
from dcc_backend_common.logger import get_logger, init_logger
from fastapi import APIRouter, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration
from structlog.stdlib import BoundLogger

from dataspot_facade_api.container import Container
from dataspot_facade_api.routers import auth_router, example_router, query_router


def _build_trace_context(request: Request) -> dict:
    """Gather a slice of request metadata for debug/trace log lines."""
    return {
        "method": request.method,
        "path": request.url.path,
        "client_host": request.client.host if request.client else None,
    }


def create_app() -> FastAPI:

    # RUSTRAK_DEBUG=true turns on the app's debug log lines by raising LOG_LEVEL
    # to DEBUG before the logging pipeline is initialized below.
    if os.environ.get("RUSTRAK_DEBUG", "false").lower() == "true":
        os.environ.setdefault("LOG_LEVEL", "DEBUG")

    init_logger(app_name="dataspot-facade-api")

    logger: BoundLogger = get_logger("app")

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
            "Sentry/Rustrak initialized",
            event_level=rustrak_event_level,
            log_level=rustrak_log_level,
        )
    else:
        logger.warning("RUSTRAK_DSN not set; error tracking and performance disabled")

    logger.info("Starting Dataspot Facade API application")

    logger.debug("Reading environment configuration")
    debug_enabled = os.environ.get("RUSTRAK_DEBUG", "false").lower() == "true"
    logger.debug("Configuring dependency injection container")
    container = Container()
    container.wire(modules=[example_router])
    container.check_dependencies()
    logger.debug("Dependency injection configured", container_ok=True)

    config = container.config()
    logger.info(
        "Running with configuration",
        base_url=config.base_url,
        database_name=config.database_name,
    )

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

    @app.middleware("http")
    async def trace_requests(request: Request, call_next):
        ctx = _build_trace_context(request)
        start = perf_counter()
        logger.debug("Incoming request", **ctx)
        response = await call_next(request)
        elapsed_ms = round((perf_counter() - start) * 1000, 2)
        logger.info(
            "Request finished",
            status_code=response.status_code,
            duration_ms=elapsed_ms,
            **ctx,
        )
        return response

    logger.debug("Registering API routers")
    api_router.include_router(example_router.create_router())
    api_router.include_router(auth_router.create_router(config))
    api_router.include_router(query_router.create_router(config))
    logger.debug("All routers registered")
    app.include_router(api_router)

    logger.info("API setup complete", debug_enabled=debug_enabled)
    return app


app = create_app()
