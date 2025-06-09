# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Hayhooks extends the basic Hayhooks tool server to create a comprehensive MCP (Model Context Protocol) server that bridges Haystack Pipelines with AI agents like Letta. The application serves as both a pipeline API server and an MCP server, providing tools for content extraction, web search, Google Workspace integration, and AI agent communication.

## Development Commands

```bash
# Setup development environment
cp env.example .env
uv venv
uv sync
source .venv/bin/activate

# Start dependencies (LiteLLM for model routing)
docker compose -f '../docker-compose.yml' up -d 'litellm'

# Run development server with debug logging
source ../.env
LOG=DEBUG python app.py

# Code quality
ruff check --fix .
mypy .

# Testing
pytest
pytest tests/components/test_specific_component.py  # Run single test file
pytest -v -s  # Verbose with output
```

## Architecture Overview

### Core Application (app.py)
The main FastAPI application extends basic Hayhooks with:
- **MCP Server** - Exposes pipelines as tools via Model Context Protocol
- **OpenAI-Compatible API** - Custom `/chat/completions` endpoint that proxies to Letta agents
- **Google OAuth2 Flow** - Authentication for Google Workspace services
- **Custom Model Endpoint** - Returns Letta agents as available "models"

### Component System (components/)
Modular Haystack components following a consistent pattern:
- **Content Extraction** - Unified content fetching with multiple resolvers (StackOverflow, Zotero, Notion, YouTube)
- **Google Integration** - OAuth2 + Calendar/Gmail/YouTube components with structured data models
- **Web Search** - Multi-provider search (Tavily, Exa, Linkup, Brave, SearXNG) with fallback strategy
- **Letta Integration** - Agent communication with streaming support

### Pipeline System (pipelines/)
Each pipeline directory contains a `pipeline_wrapper.py` extending `BasePipelineWrapper`:
- `setup()` method builds the Haystack pipeline
- `run_api()` method defines the public API interface
- Components connected using Haystack's declarative syntax

### Shared Resources (resources/)
- **Prompt templates** (`.md` files) - LLM instructions for different use cases
- **Tool definitions** (`.py` files) - MCP tool specifications with parameter schemas
- **Utility functions** - Resource loading and common operations

## Key Development Patterns

### Pipeline Development
1. Create new directory in `pipelines/`
2. Implement `pipeline_wrapper.py` extending `BasePipelineWrapper`
3. Define component connections in `setup()`
4. Expose API parameters in `run_api()`
5. Add corresponding tool definition in `resources/`

### Component Development
1. Follow Haystack component patterns with `@component` decorator
2. Use structured data models (Pydantic/dataclasses) for complex data
3. Implement proper error handling and logging
4. Add comprehensive docstrings for MCP tool generation

### Authentication Flow
- Google OAuth2 uses `/auth/google` endpoint with callback to `/auth/google/callback`
- Tokens stored in `google_tokens/` directory
- Components check for valid tokens before API calls

### Environment Configuration
Critical environment variables:
- `LETTA_SERVER_URL` and `LETTA_API_TOKEN` - Letta agent integration
- `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` - Google OAuth2
- Search provider API keys (TAVILY_API_KEY, EXA_API_KEY, etc.)
- `LOG=DEBUG` - Enable detailed logging for development

### Testing Strategy
- Unit tests for individual components in `tests/components/`
- Pipeline integration tests in `tests/pipelines/`
- Use async test patterns for FastAPI endpoints
- Mock external API calls for reliable testing

## Important Notes

- **Python 3.12 Required** - Strict version requirement in pyproject.toml
- **UV Package Manager** - Used for dependency management and virtual environments
- **Rate Limiting** - Search operations use separate models to avoid agent rate limits
- **Content Caching** - Zotero integration includes SQLite caching for performance
- **Streaming Support** - Full streaming chat completions via Letta integration
- **Multi-format Processing** - Supports PDF, CSV, HTML, Markdown content extraction