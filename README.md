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

## Running the dev server

```sh
mise run dev
```

This runs `uv run fastapi dev`, which starts the API with auto-reload and
serves the interactive docs at <http://127.0.0.1:8000/docs>.
