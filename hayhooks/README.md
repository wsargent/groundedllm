# Hayhooks

[Hayhooks](https://docs.haystack.deepset.ai/docs/hayhooks#overview) is the tool server for Letta (or Open WebUI, or anything else you want for tool use).

It implements Haystack Pipelines as REST APIs, it's a FastAPI application and an MCP server, and it lets you deploy and undeploy tools very quickly.

Also see [hayhooks-open-webui-docker-compose](https://github.com/deepset-ai/hayhooks-open-webui-docker-compose).

## Running in Development

In addition to running as part of the docker compose stack, you can run hayhooks out of the box for development purposes.

### Running FastAPI backend

This project uses [uv](https://docs.astral.sh/uv/).  It requires Python 3.12.

First, set up your uv environment with development dependencies (be aware that `uv sync` does not include dev tools):

```bash
cp env.example .env
uv venv
uv sync
source .venv/bin/activate
```

And then start up LiteLLM as Hayhooks will use it:

```bash
docker compose -f '../docker-compose.yml' up -d 'litellm'
```

Copy your `env.example` to `.env` in the root directory to set up the environment variables, and then start the hayhooks server:

```bash
source ../.env
LOG=DEBUG python app.py
```

You can see the OpenAPI routes at http://localhost:1416/docs to see what pipelines are available.

## Tracing

```

uv run opentelemetry-instrument \
    --traces_exporter console \
    --metrics_exporter console \
    --logs_exporter console \
    --service_name hayhooks \
    python app.py
```

## Pipelines

The pipelines here do not use RAG in the traditional sense of indexing / retrieving from a vector database.  They do retrieve content that assists in generation, but are set up to be as lightweight as possible.

**Make sure you have Hayhooks running in another terminal before calling `hayhooks pipeline run <foo>`.**

All pipelines start off in the undeployed directory, as Letta can easily get rate-limited by Anthropic for running too many queries in succession.  You can deploy it to a running container by running [deploy-files](https://github.com/deepset-ai/hayhooks/tree/main?tab=readme-ov-file#pipelinewrapper-development-with-overwrite-option) on it.

### Search Pipeline

Searches using Tavily, and uses a model to read the summary and return an answer.  Gemini 2.0 Flash is perfect for this, as it's cheap, fast, and has a large context window.

Using a distinct model for searches also protects the agent against itself; giving an agent a tool that can search and telling it to search until it knows what's going on can result in rate limiting errors in some models, especially Claude Sonnet 3.7.  

```bash
hayhooks pipeline run search \
    --param 'question="What does Haystack do?"' \
    --param 'search_depth="advanced"'
```

Note that the `time_range` does not take quotes:

```bash
hayhooks pipeline run search --param 'question="When was the last full moon?"' --param 'time_range=month'
```

### Excerpt Pipeline

This pipeline takes URLs, scrapes the contents, and feeds it to an LLM with a large context window.

```bash
hayhooks pipeline run excerpt \
    --param 'urls=["https://docs.letta.com/guides/server/providers/openai-proxy.mdx"]' \
    --param 'question="What are the contents of this URL?  Provide a detailed summary."'
```

CSV and PDF are also supported:

```bash
hayhooks pipeline run excerpt \
    --param 'urls=["https://arxiv.org/pdf/2410.11782"]' \
    --param 'question="Explain this paper to me like I am five years old."'
```

### Extract Pipeline

The Extract pipeline takes a URL, scrapes the contents, and feeds it to an LLM with a large context window.  It then extracts the text from the URL and returns it.

```bash
hayhooks pipeline run extract \
    --param 'url=https://docs.letta.com/guides/agents/sleep-time-agents'
```

There is a resolver system that can manage URLs that would otherwise be unavailable.  For example, if you have a StackOverflow URL:

```bash
hayhooks pipeline run extract \                                                                             
  --param 'url=https://stackoverflow.com/questions/69692842/error-message-error0308010cdigital-envelope-routinesunsupported'
```

Then the StackOverflow content resolver will make a query through the StackExchange API and return the content, using your API key if configured.

If you have Zotero, you can use the Zotero content extractor to match URLs that are in your library and pull the content. The Zotero content extractor now uses a local SQLite database to cache Zotero items for faster querying:

```bash
hayhooks pipeline run extract \                                                                             
  --param 'url=https://doi.org/10.1145/3459637.3482468'
```

You can configure the path to the SQLite database file by setting the `ZOTERO_DB_FILE` environment variable in your `.env` file. By default, it uses `zotero_json_cache.db` in the current directory.

If you have the Notion integration set up, you can extract Notion content directly from the URL:

```bash
hayhooks pipeline run extract \                                                                            
  --param 'url=https://www.notion.so/AI-Work-Log-1ff20f5b9bec8000a169e6a29bae0b42'
```

### Analyze Stack Trace

The Analyze trace pipeline takes a stacktrace (or fragment) and sends it to Stack Overflow.

```bash
hayhooks pipeline run analyze_trace \
    --param 'stack_trace=java.lang.NullPointerException' \
    --param 'language=java'
```

### Search Stackoverflow

The search_stackoverflow pipeline takes an error and sends it to Stack Overflow.

```bash
hayhooks pipeline run search_stackoverflow \
    --param 'error_message=error:0308010C:digital envelope routines::unsupported'
```

### Provision Search Agent Pipeline

This pipeline provisions a search agent in Letta, and sets it up with tools.

This pipeline is called by an initializer docker container that runs after Letta is healthy.

You'll need to set `LETTA_BASE_URL` and `LETTA_API_TOKEN` environment variables to run this pipeline to specify where you want the agent installed.

```bash
hayhooks pipeline run provision_search_agent \
    --param 'agent_name=letta-agent' \
    --param 'chat_model=anthropic/claude-sonnet-4-20250514' \
    --param 'embedding_model=letta/letta-free'
```

## Google Authentication Pipeline

Calling `google_auth` will either tell you if you're authenticated or kick off a new OAuth 2 flow.

```bash
hayhooks pipeline run google_auth
```

## Search calendars

Searches calendar events from Google Calendar.  You must be authenticated for this to work.

```bash
hayhooks pipeline run search_calendars --param 'user_id=me' 
```

## Search Email

Searches emails from Google Mail.  You must be authenticated for this to work.

```bash
hayhooks pipeline run search_emails --param 'user_id=me' 
```

## Google OAuth2 Integration

Hayhooks includes a Google OAuth2 integration that allows your AI agents to access Google services like Gmail and Calendar on behalf of users. This follows the standard OAuth2 authorization flow:

1. The AI agent detects a need for Google API access
2. The agent directs the user to authorize access via a Google consent screen
3. After authorization, the agent can access the requested Google services

This can be tricky to set up, but it's honestly not that bad using [a step by step guide](https://blog.futuresmart.ai/integrating-google-authentication-with-fastapi-a-step-by-step-guide).  There are also some [Youtube Videos](https://www.youtube.com/watch?v=A3838fq6j4U) that can help walk you through the process.

### Configure Cloud Project

- Go to the [Google Cloud Console](https://console.cloud.google.com/)
- Create a new project or select an existing one
- Navigate to "APIs & Services" > "Credentials"
- Click "Create Credentials" > "OAuth client ID"
- Select "Web application" as the application type
- Add `http://localhost:1416/google-auth-callback` to the "Authorized redirect URIs"
- Download the client secrets JSON file to your Hayhooks directory as `client_secret.json` so it matches the `GOOGLE_CLIENT_SECRETS_FILE` environment variable.

Once you have the `client_secret.json` file in the `hayhooks` directory, then you should do `docker compose up --build` so that the new container has the json file included.

### Enable Services

Download the [CLI](https://cloud.google.com/sdk/docs/install-sdk) and enable the google services using [gcloud](https://cloud.google.com/sdk/gcloud/reference/services/enable). 

```
gcloud services enable calendar-json.googleapis.com --project=1070070617610
gcloud services enable gmail.googleapis.com --project=1070070617610
gcloud services enable youtube.googleapis.com --project=1070070617610
```

If you do *not* have it configured, you will run into something like this:

```
Encountered 403 Forbidden with reason "accessNotConfigured"
```

If you want to reset or add any permissions, you should revoke access in [Google Third-party apps & services](ccount.google.com/connections?filters=3,4&hl=en) and then walk through the authorization flow again.

### Running Google Authentication

You can then go to http://localhost:1416/ and do the google authentication from there. 

Google authentication does not auto-renew -- the existing token will timeout every so often and you will have to click on the page again.  I'm actually fine with this, as I don't want to have the model have permanent access to email and calendar information anyway.