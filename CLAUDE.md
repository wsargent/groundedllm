# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build Commands
- Run application: `docker compose up` or `docker compose up -d` (daemon mode)
- Rebuild container: `docker compose up --build 'hayhooks'`
- Complete reset: `docker compose down -v --remove-orphans && docker compose up --build`

## Test Commands
- Run all tests: `pytest tests/`
- Run specific test: `pytest tests/components/test_content_extraction.py`

## Development Environment
- Python: 3.12 required
- Package management: `uv venv && source .venv/bin/activate && uv sync`
- Node.js tools: `npm run build`, `npm run start`, `npm run dev`

## Code Style
- Type annotations for all function signatures
- Descriptive function and variable names
- Follow existing import organization patterns
- Clear error handling with appropriate logging
- Document public APIs with docstrings
- Validate input parameters, especially URLs and file paths
- Organize code in logical directories (components/, pipelines/, resources/)
- Maintain strict type checking where applicable