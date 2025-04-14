# GroundedLLM

This is a pre-built, turnkey implementation of an AI agent grounded with search and extract tools to reduce hallucination.

If you have the API keys and Docker Compose, you should be able to go to http://localhost:3000 and have it Just Work.  It runs fine on a Macbook Pro with 8 GB memory.

It does require accounts with Tavily and Google's Gemini API, but these are free for individuals (as of 4/13/2025) and I've only hit the tier limit for Gemini once.

* [Tavily Pricing](https://tavily.com/#pricing)
* [Gemini Pricing](https://ai.google.dev/gemini-api/docs/pricing)

Even if you use a paid model from Anthropic or OpenAI, it's more cost effective to use the API directly compared to the $20 a month for Claude Pro or ChatGPT Plus that you would need for longer context windows. 

## Who's Interested?

This project may be of interest to you if:

* **You don't want to mess around.**  You want a search engine that knows what you want and gets smarter over time with very little effort on your part, and if that means you wait for 30 seconds to get the right answer, you're okay with that.
* **You are interested in AI agents.** This project is a low effort way to play with [Letta](https://docs.letta.com/letta-platform), and see a [stateful agent](https://docs.letta.com/stateful-agents) that can remember and learn.
* **You are interested in RAG pipelines.**  [Haystack](https://haystack.deepset.ai/) toolkit has several options to deal with document conversion, cleaning, and extraction.  The search and extract tools plug into these.
* **You're interested in [Open WebUI](https://github.com/open-webui/open-webui).** Unlike [Perplexity](https://www.perplexity.ai) and [Perplexica](https://github.com/ItzCrazyKns/Perplexica), this project doesn't give you a new front end UI to deal with when you want to find things. Open WebUI is powerful and popular, so let's use that.
* **You are interested in adding MCP servers.**  In addition to the search and extract tools, this project comes with [Wikipedia MCP server](https://github.com/scotthelm/wikipedia-mcp-server), [AWS documentation MCP server](https://awslabs.github.io/mcp/servers/aws-documentation-mcp-server/) and [Letta MCP Server](https://github.com/oculairmedia/Letta-MCP-server) and can be set up with more tools to help the agent with search.

## Description

This project helps ground your LLM from hallucination by providing it with search and page extraction tools and the ability to remember things through [Letta](https://docs.letta.com/letta-platform), an agent framework with memory and tool capabilities.  Every time it searches or extracts a web page, it will save a summary of the search and the results into archival memory, and can refer back to them.

Because a Letta agent is a stateful agent, it doesn't matter if you bring up a new chat.  The agent will continue the conversation from where you left off and remembers details (like your name and location) so that it can answer new questions.

![Sunset](./images/sunset.png)

Because a Letta agent has memory, it is teachable.  If you tell it your location, it will not only sort out timezone and locale for all subsequent queries, but it can also learn your preferences, websites to avoid, and even pick up new strategies for searching.  

The main advantage of an agent is that it's capable of recognizing and acting when a tool has not returned the correct results.  Letta will dig down into search results if it thinks it's not detailed enough.  For example, it performed three searches in response to the question "Please give me history and background about the increased traffic to sites from AI bots scraping, and the countermeasures involved.  When did this start, why is it a problem, and why is it happening?"

* "History and background of increased web traffic from AI bots scraping websites, when it started becoming a major issue, why it's a problem, and why it's happening. Include information about countermeasures websites use against AI scraping."
* "When did AI bots scraping websites first become a significant issue? What specific countermeasures have websites implemented against AI scraping bots? Include historical timeline and details about robots.txt, legal cases, and technical measures."
* "What are the major legal cases about AI web scraping from 2020-2025? When did companies like OpenAI and Anthropic start large-scale web scraping for training AI models?"

And produced this:

![AI Spam](./images/aispam.png)

If you want more details on what it's thinking, you can dig into the reasoning using [Letta Desktop](https://docs.letta.com/quickstart/desktop).  Here's an example of what goes on behind the scenes when I ask "What are the differences between [Roo Code](https://docs.roocode.com) and [Cline](https://github.com/cline/cline)?"

![Letta Grounding with Search](./images/grounding.png)

In addition to search, Letta can also extract content from specific URLs.  For example:

![Extract](./images/extract.png)

This is useful when the search engine hasn't picked up information on the pages.

## Getting Started

You will need the following:

* [Docker Compose](https://docs.docker.com/compose/install/).
* [Tavily API key](https://app.tavily.com/home) -- free up to 1000 searches, pay as you go (PAYG) is 8 cents per 1000 searches.
* [Gemini API key](https://ai.google.dev/gemini-api/docs/api-key).  The docker-compose.yml file is set up for `Gemini 2.5 Pro Experimental` and `Gemini Embedding Experimental 03-07`, which are on the free tier, but has [lower rate limits](https://ai.google.dev/gemini-api/docs/rate-limits#current-rate-limits).

Optional:

* [Anthropic or OpenAI API Key](https://console.anthropic.com/settings/keys) for Letta (Claude Sonnet 3.7, gpt4, etc).  Commented out in LiteLLM and the docker compose file.

If you do not have these accounts or API keys, it is *very* simple to set them up if you have a Google or Github account.  Gemini will ask you to sign in with your Google account, then give you a free key.  If you want to upgrade, you can set up a  [billing account](https://ai.google.dev/gemini-api/docs/billing) for PAYG.  Tavily is the same way; there's no [credit card required](https://docs.tavily.com/documentation/api-credits) and PAYG is opt in.

To configure the API keys, start by creating an `.env` file from the `env.example` file:

```
cp env.example .env
# edit .env file with your own API keys
```

To start the services, run the following:

```bash
docker compose up
```

You will see a bunch of text in the logs, but the important bit is this line:

```
initializer  | 2025-04-06 14:29:00,484 - INFO - Initialization complete!
```

(If you don't see this, it's probably a bug.  [File an issue](https://github.com/wsargent/groundedllm/issues/new) and copy and paste the logs into the issue.)

When you see that, you should be good to go.  Open a browser at http://localhost:3000 and type in "hello."

![Hello](./images/hello.png)

## Working with Letta

The first thing you'll want to do is tell Letta your name and location -- this will help it understand where and when you are.

After that, you will want to give it preferences, using the phrase "store this in your core memory" so that it can remember it for later.

Some example preferences:

* I like mermaid diagrams for visualizing technical concepts and relationships.
* I am using Haystack 2.12, please specify 2.x when searching for Haystack docs.
* Only give me sample code examples when I explicitly ask you to.
* Show me inline images when you provide results from Wikipedia pages.

Because Letta doesn't always store conversations in archival memory, you also want to ask it to explicitly summarize and store the conversation when you're changing topics.  This lets you take notes and store bookmarks when you want to bring up an old topic for later.

Grounding with search can reduce hallucinations, but *will not eliminate them*.  You will still need to check the sources and validate that what Letta is telling you is accurate, especially if you are doing anything critical.  Also, do your own searches!  Search engines are free for humans, and Letta will be happy to give you its reference material.

## Management

When you want it to run in the background, you can run it as a daemon:

```bash
docker compose up -d
```

To rebuild a container (probably Hayhooks or a new MCP container you're adding):

```
docker compose up --build 'hayhooks'
```

To completely destroy all resources (including all your data!) and rebuild from scratch:

```bash
docker compose down -v --remove-orphans && docker compose up --build
```

If you want to modify functionality, see the Hayhooks [README](./hayhooks/README.md).

## Composition

The docker compose file integrates several key components:

* **Open WebUI:** A user-friendly front-end interface 
* **Letta:** An agent framework with built-in memory and tooling capabilities.
* **Hayhooks:** A tool server for use by Letta.
* **LiteLLM Proxy Server:**  Makes all providers "OpenAI style" for Hayhooks.
* **MCP Servers:** Various MCP servers in docker containers.

Note that if you delete or rename the Letta agent or the Open WebUI pipe, the initializer will provision a new one with the same name automatically.

### Open WebUI

[Open WebUI](https://docs.openwebui.com) is the standard for front end interfaces to LLMs and AIs in general.

There are a number of tweaks to [improve performance](https://docs.openwebui.com/tutorials/tips/improve-performance-local) and minimize the time to get started.

For example, this instance is configured to use Gemini embedding so that it doesn't download 900MB of embedding model for its local RAG.

It is not possible to upload files into Letta through the Open WebUI interface right now.  The functionality does exist in Letta through the [data sources](https://docs.letta.com/guides/agents/sources) feature, but it might be easier to use a OWUI plugin to send it to Hayhooks and keep it in a document store.

### Letta

[Letta](https://docs.letta.com) is an agent framework that has built-in self editing memory and built-in tooling for editing the behavior of the agent, including adding new tools.

The search technique is pulled from this academic paper on [DeepRAG](https://arxiv.org/abs/2502.01142), although [query decomposition](https://haystack.deepset.ai/blog/query-decomposition) is a well known technique in general.  If you want a classic deep learning style agent, you can import one from Letta's [agent-file git repository](https://github.com/letta-ai/agent-file/tree/main/deep_research_agent).

#### Picking a Model Provider

The model is set up with Claude Sonnet 3.7 as it is much more proactive about calling tools until it gets a good answer.  You can use OpenAI for the same effect.  Gemini 2.0 models have been inconsistent and less proactive than Claude Sonnet, although Gemini 2.5 Pro is *very* smart at interpreting existing data.

If you are going to use Ollama with Letta you will need a powerful model, at least 13B and preferably 70B.

Some reasoning models have difficulty interacting with Letta's reasoning step.  Deepseek and Gemini 2.5 Pro will attempt to reply in the reasoning step, although that may be fixed in the latest version.

#### Letta Desktop

You may want Letta Desktop, which will allow you to see what the agent is doing under the hood, and directly edit the functionality. You can download it [here](https://docs.letta.com/quickstart/desktop).  Pick the PostgreSQL option when it comes up.

Start the docker compose app *first* and *then* open up Letta Desktop, as it is connecting to the Letta agent running inside the container.

### Hayhooks

[Hayhooks](https://github.com/deepset-ai/hayhooks/) is a FastAPI-based server that exposes [Haystack Pipelines](https://docs.haystack.deepset.ai/docs/intro) through REST APIs. It's primarily used for RAG, but it's also a great way to make tools available in general as it has MCP and OpenAPI support.

To cut down on Anthropic's brutally low rate limits and higher costs, the search and extract tools use Google Flash 2.0 to process the output from Tavily and create an answer for Letta.  Google Flash 2.0 also recommends possible follow up queries and [query expansion](https://haystack.deepset.ai/blog/query-expansion) along with the search results.

The extract tool converts HTML to Markdown and does some document cleanup before sending it to Google Flash 2.0.  Only HTML is processed for now, although there are [many converters](https://docs.haystack.deepset.ai/docs/converters) available, and PDF support through [docling-haystack](https://haystack.deepset.ai/integrations/docling) or [docling-serve](https://github.com/docling-project/docling-serve) should be easy.

There is no vector/embeddings/database RAG involved in this project, although you have the option to use your own by plugging it into Hayhooks.  In addition, Letta's archival memory is technically a RAG implementation based on pgvector.

See the [README](./hayhooks/README.md) for details of the tools provided by Hayhooks.

### LiteLLM Proxy Server

The [LiteLLM proxy server](https://docs.litellm.ai/docs/proxy/deploy) that provides an OpenAI compatible layer on top of several different providers. It is provided to Open WebUI (commented out) and to Hayhooks.

LiteLLM is mostly commented out here to focus attention on Letta.  However, it is very useful in general, especially as you scale up in complexity, and I think it's easier if you start using it from the beginning.

* It provides a way to point to a conceptual model rather than a concrete one (you can point to "claude-sonnet" and change the model from 3.5 to 3.7).  
* It insulates Open WebUI from the underlying providers.  You don't have to worry about changing your API key or other configuration settings when switching providers.  You also don't have to worry about Open WebUI timing out for 30 seconds while it tries to reach an unreachable provider.
* It lets you specify the same model with different parameters, so you can use `extra-headers` to experiment with [token-efficient tool use](https://docs.anthropic.com/en/docs/build-with-claude/tool-use/token-efficient-tool-use), for example.

### MCP Servers

The search agent is configured with tools through Letta's MCP support with some MCP servers.  There are a couple of good reasons for putting MCP servers in Docker containers.  The first is that Letta will not work with stdio MCP servers, and so SSE is required.  The second is that many MCP servers benefit from the isolation provided by containers -- they can have exactly the required environment and version they need without impacting other MCP servers or the OS itself.  It also makes it much easier to add and remove servers.

* Hayhooks itself provides the `search` and `extract` tools for fine-grained control over Tavily.
* Wikipedia search is provided by [wikipedia-mcp-server](https://github.com/scotthelm/wikipedia-mcp-server).
* AWS documentation is provided by [aws-documentation-mcp-server](https://awslabs.github.io/mcp/servers/aws-documentation-mcp-server/).
* Letta MCP Server is from [letta-mcp-server](https://github.com/oculairmedia/Letta-MCP-server) is configured but not attached to the search agent (you'll have to do that yourself through Letta Desktop).

The search will use these as appropriate, but you can prompt it by asking, i.e. "Use the recommend tool to recommend documentation for <sample AWS doc url>" and it will use the `recommend` tool.

The search will use these as appropriate, but you can prompt it to use a specific tool by asking, i.e. "Use the recommend tool to recommend documentation for <sample AWS doc url>" and it will use the `recommend` tool.

You can add your own MCP servers.  To do this is a four step process:

1. Find the MCP server you want, and create an `mcp/my-mcp-server` directory, then set up the `Dockerfile` to encapsulate it with a proxy that exposes it over SSE.
2. Add the MCP docker container to `docker-compose.yml`.
3. Add the URL to the docker container's endpoint in `letta_mcp_config.json`.
4. Add the MCP tools that you want the search agent provisioned with in the `hayhooks/provision_search_agent/pipeline_wrapper.py` file.

MCP is a pain in the butt [security wise](https://blog.sshh.io/p/everything-wrong-with-mcp) so wrapping them in docker containers at least limits the blast radius a bit.

It can be some work to set up credentials and work out how to set up the proxy for any given MCP server, so you should be technically comfortable with some futzing here.  You can ask Cline to use the existing instances as templates.

## Privacy Concerns

Since you're using this for search, you may want to know how your queries are processed.

There are three different services involved in search, each with their own privacy policy.

You do have options for customization.  Since the tools go through Hayhooks, you can write a [ConditionalRouter](https://docs.haystack.deepset.ai/docs/conditionalrouter) that will send different queries to different services or evaluate them before they are processed.

### Anthropic

Anthropic's [privacy policy](https://www.anthropic.com/legal/privacy) is clear: they do not use personal data for model training [without explicit consent](https://privacy.anthropic.com/en/articles/10023580-is-my-data-used-for-model-training).

### Tavily

Tavily's [privacy policy](https://tavily.com/privacy) is that they do store queries, and they will use queries to improve the quality of their services.  You can opt out through the [account settings](https://app.tavily.com/account/settings).

### Google

Google's [privacy policy](https://support.google.com/gemini/answer/13594961) states that your conversations with Gemini may be used to improve and develop their products and services, including machine learning technologies.  The [Gemini Pricing](https://ai.google.dev/gemini-api/docs/pricing) page says the free tier does your conversations to train their models. They do use human reviewers and there is a note saying **Please don’t enter confidential information in your conversations or any data you wouldn’t want a reviewer to see or Google to use to improve our products, services, and machine-learning technologies.**

