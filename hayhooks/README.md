# Hayhooks

[Hayhooks](https://docs.haystack.deepset.ai/docs/hayhooks#overview) is the tool server for Letta (or Open WebUI, or anything else you want for tool use).

It implements Haystack Pipelines as REST APIs, it's a FastAPI application and an MCP server, and it lets you deploy and undeploy tools very quickly.

Also see [hayhooks-open-webui-docker-compose](https://github.com/deepset-ai/hayhooks-open-webui-docker-compose).

## Running in Development

In addition to running as part of the docker compose stack, you can run hayhooks out of the box for development purposes.

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

### Search By Error

The Analyze trace pipeline takes a stacktrace (or fragment) and sends it to Stack Overflow.

```bash
hayhooks pipeline run search_by_error \
    --param 'error_message=error:0308010C:digital envelope routines::unsupported'
```

### Provision Search Agent Pipeline

This pipeline provisions a search agent in Letta, and sets it up with tools.

This pipeline is called by an initializer docker container that runs after Letta is healthy.

```bash
hayhooks pipeline run provision_search_agent \
    --param 'agent_name=letta-agent' \
    --param 'chat_model=anthropic/claude-3-7-sonnet-20250219" \
    --param 'embedding_model=letta/letta-free'
```

## Google OAuth2 Integration

Hayhooks includes a Google OAuth2 integration that allows your AI agents to access Google services like Gmail and Calendar on behalf of users. This follows the standard OAuth2 authorization flow:

1. The AI agent detects a need for Google API access
2. The agent directs the user to authorize access via a Google consent screen
3. After authorization, the agent can access the requested Google services

### Setup

1. Create a Google Cloud Project and OAuth 2.0 credentials:
   - Go to the [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select an existing one
   - Navigate to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth client ID"
   - Select "Web application" as the application type
   - Add your Hayhooks server URL to the "Authorized JavaScript origins"
   - Add `http://your-hayhooks-server.com/google-auth-callback` to the "Authorized redirect URIs"
   - Download the client secrets JSON file

2. Configure environment variables in your `.env` file:
   ```
   GOOGLE_CLIENT_SECRETS_FILE=/path/to/your/client_secret.json
   HAYHOOKS_BASE_URL=http://your-hayhooks-server.com
   GOOGLE_TOKEN_STORAGE_PATH=/path/to/store/tokens
   ```

### API Endpoints

The Google OAuth2 integration provides the following endpoints:

- **GET /google-auth-initiate**: Initiates the OAuth2 flow and returns the authorization URL
  - Query parameter: `user_id` (optional, defaults to "default_user")
  - Response: JSON with `authorization_url` and `state`

- **GET /google-auth-callback**: Handles the callback from Google after user authorization
  - This endpoint is called by Google after the user grants or denies consent
  - It stores the access and refresh tokens for the user

- **GET /check-google-auth**: Checks if a user is authenticated
  - Query parameter: `user_id` (optional, defaults to "default_user")
  - Response: JSON with `authenticated` (boolean) and `user_id`

### Usage in AI Agents

When your AI agent needs to access Google services, it should:

1. Check if the user is authenticated using the `/check-google-auth` endpoint
2. If not authenticated, get the authorization URL from `/google-auth-initiate` and present it to the user
3. After the user completes authorization, the agent can proceed with the original request

Example flow in an AI agent:
```
User: "Check my calendar for tomorrow"
Agent: [Checks authentication status]
Agent: "I need access to your Google Calendar to check your schedule. Please click this link to authorize access: [authorization URL]"
User: [Clicks link, grants permission, and returns to chat]
Agent: "Thanks! Now I can access your calendar. Let me check your schedule for tomorrow..."
```
