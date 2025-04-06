# Hayhooks

[Hayhooks](https://docs.haystack.deepset.ai/docs/hayhooks#overview) implements Haystack Pipelines as REST APIs.  It's also a FastAPI application, so this is where any custom Python tools go.

Also see [hayhooks-open-webui-docker-compose](https://github.com/deepset-ai/hayhooks-open-webui-docker-compose).

## Running

This project uses [uv](https://docs.astral.sh/uv/).  It requires Python 3.12.

This is primarily used in the docker compose, but you can run hayhooks out of the box for development purposes, which is useful for debugging pipelines.

First, set up your uv environment.

```bash
cp env.example .env # modify as needed
uv venv
source .venv/bin/activate
uv sync # needed for some reason?
```

And then start up Open WebUI and Letta:

```
docker compose -f '../docker-compose.yml' up -d --build 'open-webui'
docker compose -f '../docker-compose.yml' up -d --build 'letta'
```

And then start the hayhooks server:

```
export OPENWEBUI_BASE_URL=http://localhost:3000
export LETTA_BASE_URL=http://localhost:8382
python app.py
```

You can see the OpenAPI routes at http://localhost:1416/docs to see what pipelines are available.

## Pipelines

The pipelines here do not use RAG in the traditional sense of indexing / retrieving from a vector database.  They do retrieve content that assists in generation, but are set up to be as lightweight as possible.

**Make sure you have Hayhooks running in another terminal before calling `hayhooks pipeline run <foo>`.**

All pipelines start off in the undeployed directory, as Letta can easily get rate-limited by Anthropic for running too many queries in succession.  You can deploy it to a running container by running [deploy-files](https://github.com/deepset-ai/hayhooks/tree/main?tab=readme-ov-file#pipelinewrapper-development-with-overwrite-option) on it.

### Search Pipeline

Searches using Tavily, and uses a model to read the summary and return an answer.  Gemini 2.0 Flash is perfect for this, as it's cheap, fast, and has a large context window.

Using a distinct model for searches also protects the agent against itself; giving an agent a tool that can search and telling it to search unti it knows what's going on can result in rate limiting errors in some models, especially Claude Sonnet 3.7.  

```bash
hayhooks pipeline run search --param 'query="What does Haystack do?"'
```

### Extract Pipeline

This pipeline takes a URL, scrapes the contents, and converts it to Markdown.

```bash
hayhooks pipeline run extract --param 'url=https://gist.github.com/wsargent/fc99042002ce3d6067cfde3fa04ec6ca'
```

### Provision Search Agent Pipeline

This pipeline provisions a search agent in Letta and creates a pipe function in Open WebUI to talk to it.

```bash
hayhooks pipeline run provision_search_agent \
    --param 'agent_name=letta-agent' \
    --param 'chat_model=anthropic/" \
    --param 'embedding_model=letta/letta-free'
```

## Custom Components

There are a few Haystack [custom components](https://docs.haystack.deepset.ai/docs/custom-components) that are in root of the project.

### Tavily Component

This is a custom Tavily search component that is used for the search pipelines.  It uses the [tavily-python](https://github.com/tavily-ai/tavily-python) library.

### OpenWebUI Setup Component

This is an component used for provisioning the Letta pipeline function in Open WebUI.  It uses straight `requests`.

### Letta Setup Component

This component is used to provision the Letta agent and register tools

