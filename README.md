# DerpyRAG

This is an "all in one" solution for a more useful agent than Claude Desktop.

It can remember things, customize itself, and if you give it search capabilities, it can hunt down documentation.

You may want the following for additional functionality, although it is not required:

* A Tavily API key (required for search)
* A Gemini API key (very useful for searching documentation)

## Docker

To start the services, run the following:

## Running

```
docker compose up --build
```

Open WebUI will take an ungodly amount of time to get started the first time, because it downloads many megabytes of embedding models for its local RAG and there's no way to disable it without breaking document uploads completely.

### Management

To see the running containers:

```
docker ps
```

To see the logs for one of the containers:

```
docker logs open-webui -f 
```

To delete a particular container:

```
docker rm -f litellm 
```

To remove all stopped containers (not just the docker compose ones!):

```
docker container prune   
```


## Letta

https://docs.letta.com

You may want Letta Desktop, which will allow you to see what the agent is doing under the hood, and directly edit the functionality.  You can download it [here](https://docs.letta.com/quickstart/desktop).

Start the docker compose app *first* and *then* open up Letta Desktop.  It will connect to the Letta agent inside the container.

## Open WebUI

https://docs.openwebui.com

https://medium.com/@kenji-onisuka/my-experience-with-openwebui-api-access-overcoming-common-integration-challenges-3026aba44378

## Hayhooks

https://github.com/deepset-ai/hayhooks/

TODO: Convert uploaded PDF to Markdown
TODO: Convert PDF URL to Markdown
TODO: Search using Tavily
TODO: Configure agent

https://medium.com/tr-labs-ml-engineering-blog/build-a-haystack-custom-component-step-by-step-structured-generation-with-outlines-11e8d660f381

## Tavily

https://docs.tavily.com/welcome

https://github.com/tavily-ai/tavily-python



# https://medium.com/@kenji-onisuka/my-experience-with-openwebui-api-access-overcoming-common-integration-challenges-3026aba44378
curl -X 'GET' \
  'http://localhost:3000/api/v1/auths/' \
  -H 'accept: application/json' | jq ".token"


# Create the Letta agent pipe function
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

echo "Letta agent pipe function has been set up!"