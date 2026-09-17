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
