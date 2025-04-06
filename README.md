# GroundedLLM

You just want a search engine that doesn't hallucinate, that knows what you want and picks up more and more context over time with very little effort on your part.  If that means you wait for 30 seconds to get the right answer, you're okay with that.

This is a pre-built, turnkey implementation of that.  If you have the API keys and Docker Compose, you should be able to go to http://localhost:3000 and have it Just Work.

## Description

This project makes Claude or ChatGPT (large language models or LLM) dramatically more useful, by [grounding]https://techcommunity.microsoft.com/blog/fasttrackforazureblog/grounding-llms/3843857) your LLM through [Letta](https://docs.letta.com/letta-platform), an agent with memory and tooling capabilities.  

Grounding the LLM will reduce hallucination and make your LLM more robust and thoughtful.  Here's an example of what goes on behind the scenes when I ask "How do I delete a docker volume?"

![Letta Grounding with Search](./grounding.png)

In addition, because Letta has memory, it is teachable.  If you tell it your location, it will not only sort out timezone and locale for all subsequent queries, but it can also learn your preferences, websites to avoid, and will gather additional context  from previous searches.  It's like a better [Claude Projects](https://simonwillison.net/2024/Dec/19/one-shot-python-tools/).

There is no vector/embeddings/database RAG involved in this package, although you have the option to use your own by plugging it into Hayhooks.  In addition, Letta's archival memory is a RAG implementation based on pgvector.

## Who's Interested?

* If you are interested in AI agents, this project is a low effort way to play with [Letta](https://docs.letta.com/letta-platform), and see a [stateful agent](https://docs.letta.com/stateful-agents) that can learn from its own interactions.
* If you are interested in RAG problems (document conversion / cleaning / extraction), the [Hayhooks](https://docs.haystack.deepset.ai/docs/hayhooks) and [Haystack](https://haystack.deepset.ai/) toolkit is used to implement pipelines, including several custom components.
* If you're interested in [Open WebUI](https://github.com/open-webui/open-webui), this project goes to some lengths to work through OWUI's environment variables and REST API to provision Letta.
* If you are interested in tooling like MCP and OpenAPI, Hayhooks exposes an MCP server, and has [OpenAPIServiceToFunctions](https://docs.haystack.deepset.ai/docs/openapiservicetofunctions), [OpenAPIConnector](https://docs.haystack.deepset.ai/docs/openapiconnector) [MCPTool](https://docs.haystack.deepset.ai/docs/mcptool), and more.

## Description

The docker compose file integrates several key components:

* **Open WebUI:** A user-friendly front-end interface 
* **Letta:** An agent framework with built-in memory and tooling capabilities.
* **Hayhooks:** A tool server for use by Letta.
* **LiteLLM Proxy Server:**  Makes all providers "OpenAI style" for Hayhooks.

## Minimum Requirements

You will need the following:

* [Tavily API key](https://app.tavily.com/home) (required for search) -- this is free up to a certain level.
* [Gemini API key](https://ai.google.dev/gemini-api/docs/api-key) (very useful for searching documentation) -- also has a free tier
* [Anthropic or OpenAI API Key](https://console.anthropic.com/settings/keys) for Letta (Claude Sonnet 3.7, gpt4, etc) -- not free but often cheaper than the monthly subscription.  The docker-compose.yml file is set up for Claude Sonnet 3.7.

## Docker

You will need to have Docker Compose installed. The easiest way to do this is by using Docker Desktop:

https://docs.openwebui.com/tutorials/docker-install#for-windows-and-mac-users

### Running

First, configure your keys by creating an `.env` file:

```
cp env.example .env
# edit .env file with your own keys
```

To start the services, run the following:

```bash
docker compose up
```

When you want it to run in the background, you can run it as a daemon:

```bash
docker compose up -d
```

To stop it:

```bash
docker compose down
```

To completely destroy all resources and rebuild from scratch:

```bash
docker compose down -v --remove-orphans && docker compose up --build
```

## Open WebUI

[Open WebUI](https://docs.openwebui.com) is the standard for front end interfaces to LLMs and AIs in general.

There are a number of tweaks to [improve performance](https://docs.openwebui.com/tutorials/tips/improve-performance-local) and minimize the time to get started.

For example, this instance is configured to use Gemini embedding so that it doesn't download 900MB of embedding model for its local RAG.

## Letta

[Letta](https://docs.letta.com) is an agent framework that has built-in self editing memory and built-in tooling for editing the behavior of the agent, including adding new tools.

### Picking a Model Provider

The model is set up with Claude Sonnet 3.7 as it is much more proactive about calling tools until it gets a good answer.  You can use OpenAI for the same effect.  Gemini 2.0 models have been inconsistent and less proactive than Claude Sonnet.

If you are going to use Ollama with Letta you will need a powerful model, at least 13B and preferably 70B.

Some reasoning models have difficulty interacting with Letta's reasoning step.  Deepseek and Gemini 2.5 Pro will attempt to reply in the reasoning step, so avoid using them in Letta.

### Letta Desktop

You may want Letta Desktop, which will allow you to see what the agent is doing under the hood, and directly edit the functionality. You can download it [here](https://docs.letta.com/quickstart/desktop).

Start the docker compose app *first* and *then* open up Letta Desktop, as it is connecting to the Letta agent running inside the container.

## Hayhooks

[Hayhooks](https://github.com/deepset-ai/hayhooks/) is a FastAPI-based server that exposes [Haystack Pipelines](https://docs.haystack.deepset.ai/docs/intro) through REST APIs. It's primarily used for RAG, but it's also a great way to make tools available in general as it has MCP and OpenAPI support.

See the [README](./hayhooks/README.md) for details of the tools provided by Hayhooks.

## LiteLLM

The [LiteLLM proxy server](https://docs.litellm.ai/docs/proxy/deploy) that provides an OpenAI compatible layer on top of several different providers. It is provided to Open WebUI (commented out) and to Hayhooks.

See [README](./litellm/README.md)
