# Hayhooks

[Hayhooks](https://docs.haystack.deepset.ai/docs/hayhooks#overview) implements Haystack Pipelines as REST APIs.  It's also a FastAPI application, so this is where any custom Python tools go.

Also see [hayhooks-open-webui-docker-compose](https://github.com/deepset-ai/hayhooks-open-webui-docker-compose).

## Running

This project uses [uv](https://docs.astral.sh/uv/).  It requires Python 3.12.

This is primarily used in the docker compose, but you can run hayhooks out of the box for development purposes, which is useful for debugging pipelines:

```bash
$ cp env.example .env # modify as needed
$ uv venv
$ source .venv/bin/activate
$ uv sync # needed for some reason?
$ hayhooks run --additional-python-path "." --pipelines-dir "./pipelines"
```

You can see the OpenAPI routes at http://localhost:1416/docs

## Pipelines

The pipelines here do not use RAG in the traditional sense of indexing / retrieving from a vector database.  They do retrieve content that assists in generation, but are set up to be as lightweight as possible.

Make sure you have Hayhooks running in another terminal before calling `hayhooks pipeline run <foo>`.

All pipelines start off in the undeployed directory, as Letta can easily get rate-limited by Anthropic for running too many queries in succession.  You can deploy it to a running container by running [deploy-files](https://github.com/deepset-ai/hayhooks/tree/main?tab=readme-ov-file#pipelinewrapper-development-with-overwrite-option) on it.

### Search Pipeline

Searches using Tavily, and uses a model with a large context window to read the summary and return an answer.

This is the default, because using direct_search on Claude Sonnet 3.7 with Letta will result in an agent that can run its own queries to drill down on search results.  This can often result in a rate limit error.

```bash
hayhooks pipeline run search --param 'query="What does Haystack do?"'
```

### Extract Pipeline

This pipeline takes a URL, scrapes the contents, and converts it to Markdown.

```bash
hayhooks pipeline run extract --param 'url=https://gist.github.com/wsargent/fc99042002ce3d6067cfde3fa04ec6ca'
```

### Direct Search Pipeline

This pipeline queries with Tavily and returns a Markdown representation of the results, containing scores and snippets.

```bash
hayhooks pipeline run direct_search --param 'query="What does Haystack do?"'
```

## Custom Components

There are a few Haystack [custom components](https://docs.haystack.deepset.ai/docs/custom-components) that are in root of the project.

### Tavily Component

This is a custom Tavily search component that is used for the search pipelines.  It uses the [tavily-python](https://github.com/tavily-ai/tavily-python) library.

### OpenWebUI Setup Component

This is an component used for provisioning the Letta pipeline function in Open WebUI.  It uses straight `requests`.

### Letta Setup Component

This component is used to provision the Letta agent and register tools

