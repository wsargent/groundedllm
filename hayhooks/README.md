# Hayhooks

[Hayhooks](https://docs.haystack.deepset.ai/docs/hayhooks#overview) is the tool server for Letta (or Open WebUI, or anything else you want for tool use).

It implements Haystack Pipelines as REST APIs, it's a FastAPI application and an MCP server, and it lets you deploy and undeploy tools very quickly.

Also see [hayhooks-open-webui-docker-compose](https://github.com/deepset-ai/hayhooks-open-webui-docker-compose).

## Running in Development

In addition to running as part of the docker compose stack, you can run hayhooks out of the box for development purposes.

This project uses [uv](https://docs.astral.sh/uv/).  It requires Python 3.12.

First, set up your uv environment.

```bash
cp env.example .env
uv venv
source .venv/bin/activate
uv sync
```

And then start up Open WebUI and Letta:

```
docker compose -f '../docker-compose.yml' up -d 'open-webui'
docker compose -f '../docker-compose.yml' up -d 'letta'
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
hayhooks pipeline run search \
    --param 'query="What does Haystack do?"'
```

### Extract Pipeline

This pipeline takes URLs, scrapes the contents, and feeds it to an LLM with a large context window.

```bash
hayhooks pipeline run extract \
    --param 'urls=["https://docs.letta.com/guides/server/providers/openai-proxy.mdx"]' \
    --param 'question="What are the contents of this URL?  Provide a detailed summary."'
```

CSV and PDF are also supported:

```bash
hayhooks pipeline run extract \
    --param 'urls=["https://arxiv.org/pdf/2410.11782"]' \
    --param 'question="Explain this paper to me like I am five years old."'
```

### Provision Search Agent Pipeline

This pipeline provisions a search agent in Letta and creates a pipe function in Open WebUI to talk to it.  The search agent is configured with the search and extract tools by the pipeline.

This pipeline is called by an initializer docker container that runs after Letta and Open WebUI are both healthy.

```bash
hayhooks pipeline run provision_search_agent \
    --param 'agent_name=letta-agent' \
    --param 'chat_model=anthropic/claude-3-7-sonnet-20250219" \
    --param 'embedding_model=letta/letta-free'
```

