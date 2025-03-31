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

## Letta Agent

From https://github.com/letta-ai/letta/blob/main/examples/docs/example.py

Technically we could use MCP here, but that's more complicated than just adding it from function.

The prompt is taken from [DeepRAG](https://arxiv.org/abs/2502.01142).

## Create the Letta agent pipe function

The Letta pipe is a [function](https://docs.openwebui.com/features/plugin/functions/), more precisely a [pipe function](https://docs.openwebui.com/features/plugin/functions/pipe).  It lets Open WebUI talk to Letta.

It'd be really nice if there was a clean way to just pull the code from the website at https://openwebui.com/f/haervwe/letta_agent but I've already tweaked it several times, so we'll just upload it directly.

https://medium.com/@kenji-onisuka/my-experience-with-openwebui-api-access-overcoming-common-integration-challenges-3026aba44378

https://github.com/open-webui/open-webui/discussions/351

https://docs.openwebui.com/getting-started/api-endpoints/

http://localhost:3000/docs

```
curl -X 'GET' \
  'http://localhost:3000/api/v1/auths/' \
  -H 'accept: application/json' | jq ".token"
```

```
curl -X POST \
  http://localhost:3000/api/v1/functions/create \
  -H 'Content-Type: application/json' \
  -d '{
    "id": "string",
    "name": "letta_agent",
    "content": "content",
    "meta": {
      "description": "description"  
    }
  }'
```  

echo "Letta agent pipe function has been set up!"