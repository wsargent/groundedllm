# Hayhooks

[Hayhooks](https://docs.haystack.deepset.ai/docs/hayhooks#overview) implements Haystack Pipelines as REST APIs.  It's also a FastAPI application, so this is where any custom Python tools go.

Tavily Search is implemented as a custom Haystack component, and is used in pipelines.

Also see [hayhooks-open-webui-docker-compose](https://github.com/deepset-ai/hayhooks-open-webui-docker-compose).

## Running

This project uses [uv](https://docs.astral.sh/uv/).

You should set up the environment variables in `.env`:

```commandline
cp env.example .env
```

You can run hayhooks out of the box:

```
$ uv venv
$ source .venv/bin/activate
$ hayhooks run --additional-python-path "."
```

There's an `app.py` that is used in docker compose and has additional functionality like healthchecks and MCP support:

```
uv run app.py
```

You can see the OpenAPI routes at http://localhost:1416/docs

## Pipelines

The pipelines here do not use RAG in the traditional sense of indexing / retrieving from a vector database.  They do retrieve content that assists in generation, but are set up to be as lightweight as possible.

Make sure you have Hayhooks running in another terminal before calling `hayhooks pipeline run <foo>`.

### Answer Pipeline

TODO

### Search Pipeline

This pipeline queries with Tavily and returns a Markdown representation of the results, containing scores and snippets.

```
hayhooks pipeline run search --param 'query="What does Haystack do?"'
```

### Extract Pipeline

This pipeline takes a URL, scrapes the contents, and converts it to Markdown.

```
hayhooks pipeline run extract --param 'url=https://gist.github.com/wsargent/fc99042002ce3d6067cfde3fa04ec6ca'
```

## Tavily

There is a custom Tavily component that is used for the answer and search pipelines.

https://docs.tavily.com/welcome

https://github.com/tavily-ai/tavily-python

