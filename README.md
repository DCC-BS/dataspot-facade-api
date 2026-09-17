# Dataspot Facade API

FastAPI facade service for the Dataspot platform.

## Requirements

- [mise](https://mise.jdx.dev/) (manages the toolchain, incl. `uv` and Python)

## Setup

Install the toolchain and dependencies:

```sh
mise install
uv sync
```

## Running with Docker Compose (incl. Rustrak)

[Rustrak](https://rustrak.github.io/rustrak/) is a self-hosted, Sentry-compatible
error tracker. `compose.yml` runs both Rustrak and this API:

```sh
cp .env.example .env   # fill in values
docker compose up -d
```

This starts:

- **Rustrak** on `http://localhost:8080` — the dashboard and its `/api`, with
  data persisted in a Docker volume.
- **dataspot-facade-api** on `http://localhost:8000`.

On first start Rustrak creates the admin user from `RUSTRAK_SUPERUSER` (format
`email:password`). `SESSION_SECRET_KEY` must be set — generate one with:

```sh
openssl rand -hex 32
```

### Enable error tracking, logging and performance monitoring

1. Log in to the Rustrak dashboard (`http://localhost:8080`).
2. Create a project and copy its DSN, e.g. `http://<key>@localhost:8080/1`.
3. Set `RUSTRAK_DSN=<that-dsn>` in `.env`.
4. Restart:
   - Compose: `docker compose up -d --force-recreate app`
   - Dev server (picks up the change on reload): just keep `mise run dev` running

The API is wired with `sentry-sdk` (`src/dataspot_facade_api/app.py`) and
reports four things to the Rustrak dashboard:

- **Errors / issues** — unhandled exceptions and any record at or above
  `RUSTRAK_EVENT_LEVEL` (default `ERROR`) become dashboard issues.
- **Logs** — every log record at or above `RUSTRAK_LOG_LEVEL` (default `INFO`)
  is forwarded to Rustrak's **Logs** view. Both structlog (`get_logger(...)`)
  and the Python `logging` stdlib logger are captured.
- **Performance / transactions** — every HTTP request becomes a transaction
  with its own timing, and handler/outbound calls are spans (driven by the
  bundled FastAPI/Starlette integrations, `traces_sample_rate` and
  `profiles_sample_rate`). Handlers also attach context via `sentry_sdk.set_tag`
  (e.g. `user`, `query_duration_ms`).
- **Request timing** — a middleware logs each incoming request and a
  `Request finished` line including `duration_ms`, `method`, `path` and
  `client_host`.

> In production set `RUSTRAK_PUBLIC_URL` to your public host so SDKs get a
> reachable DSN.

## Environment variables

Copy the example env file and fill in the values:

```sh
cp .env.example .env
```

| Variable | Required | Description |
|---|---|---|
| `MY_DATASPOT_TOKEN` | yes | Access key used to authenticate via `/v1/auth` and receive a JWT |
| `JWT_SECRET` | yes | Secret key for signing JWT tokens |
| `BASE_URL` | yes | Base URL of the Dataspot instance |
| `DATABASE_NAME` | yes | Database name in Dataspot |
| `IS_PROD` | no | Set to `"true"` to enable production mode (disables local CORS origins). Defaults to `"false"` |
| `DATASPOT_SERVICE_USER_ACCESS_KEY` | no | Backend service-user access key |
| `DATASPOT_TENANT_ID` | no | Azure AD / Entra ID tenant ID |
| `DATASPOT_CLIENT_ID` | no | Azure AD / Entra ID client ID |
| `DATASPOT_CLIENT_SECRET` | no | Azure AD / Entra ID client secret |
| `DATASPOT_EXPOSED_CLIENT_ID` | no | Azure AD / Entra ID exposed client ID |

### Rustrak observability

| Variable | Default | Description |
|---|---|---|
| `RUSTRAK_DSN` | — | Sentry-compatible DSN. When set, enables error tracking, logging and performance monitoring |
| `RUSTRAK_LOG_LEVEL` | `INFO` | Minimum level forwarded to Rustrak **Logs** (`DEBUG` / `INFO` / `WARNING` / `ERROR`) |
| `RUSTRAK_EVENT_LEVEL` | `ERROR` | Records at or above this level also become dashboard **issues** |
| `RUSTRAK_DEBUG` | `false` | Set `"true"` to enable the app's `logger.debug(...)` lines (raises `LOG_LEVEL` to `DEBUG`) |

To see debug records forwarded to Rustrak, set `RUSTRAK_DEBUG=true` (or
`RUSTRAK_LOG_LEVEL=DEBUG`).

## Running the dev server

```sh
mise run dev
```

This runs `uv run fastapi dev`, which starts the API with auto-reload and
serves the interactive docs at <http://127.0.0.1:8000/docs>.

## Authenticating and opening the docs

```sh
mise run auth
```

This task:

1. Calls `/v1/auth` with `MY_DATASPOT_TOKEN` to obtain a JWT
2. Copies the JWT to your clipboard
3. Opens a local docs page (port 8090) with the token pre-authorized in Swagger UI

The local docs server keeps running until you press `Ctrl+C`. Make sure the dev
server is already running (`mise run dev`) before using this task.
