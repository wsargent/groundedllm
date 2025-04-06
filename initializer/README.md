# Initializer

This is a docker container that initializes Letta and Open WebUI.

## Running

This project uses [uv](https://docs.astral.sh/uv/).

To run this outside the container (assuming you have Letta/Open WebUI up):

```
export LETTA_BASE_URL=http://localhost:8283
export OPEN_WEBUI_URL=http://localhost:3000

uv sync
uv run main.py
```
