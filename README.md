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

### Production

For production, `compose.prod.yml` also builds and runs this API (with
`IS_PROD=true`) alongside Rustrak:

```sh
cp .env.example .env   # fill in values
docker compose -f compose.yml -f compose.prod.yml up -d --build
```

The API is built from the local `Dockerfile` and served on
`http://localhost:8000` (override with `APP_PORT`). The API port can be
overridden with `APP_PORT`, e.g. `APP_PORT=9000 docker compose -f compose.yml
-f compose.prod.yml up -d`.

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

## Running behind a reverse proxy with base paths

### The facade API under a sub-path

Set `BASE_PATH` (e.g. `/fade-api`) in `.env` and the API serves its routes,
docs and OpenAPI schema under that prefix:

```nginx
# nginx: forward the prefix untouched — no extra config needed
location /fade-api/ {
    proxy_pass http://app:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

If your proxy strips the prefix instead (e.g. `proxy_pass
http://app:8000/v1/`), either start uvicorn with `--root-path /fade-api` or
set `ROOT_PATH=/fade-api` so generated doc URLs still carry the prefix.

### Rustrak cannot run under a sub-path

The Rustrak dashboard is a SPA served from the root of its origin (`base: '/'`
in its Vite build, `/` router basepath) and the server has no base-path
setting. Give it its own hostname at the root:

```nginx
server {
    server_name rustrak.example.com;
    location / {
        proxy_pass http://rustrak:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Set `RUSTRAK_PUBLIC_URL=https://rustrak.example.com` (and
`DASHBOARD_URL=https://rustrak.example.com` for alert links) and
`SSL_PROXY=true` behind HTTPS. The facade API and Rustrak can then share one
host: this API on `/fade-api`, the Rustrak dashboard at `/`.

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
| `BASE_PATH` | no | Base path the API is served under, e.g. `/fade-api` behind a reverse proxy. Defaults to empty (served at the root) |
| `ROOT_PATH` | no | ASGI `root_path` for when the proxy strips the prefix and uvicorn is not started with `--root-path`. Defaults to `BASE_PATH` |
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
