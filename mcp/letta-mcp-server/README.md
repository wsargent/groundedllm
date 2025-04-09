# Letta MCP Server with SSE Transport

This repository contains a Model Context Protocol (MCP) server implementation for the Letta platform with Server-Sent Events (SSE) transport support.

## Features

- Supports both SSE and stdio transports
- Provides access to Letta API functionality through MCP tools
- Secure by default with non-root user in Docker
- Environment variable configuration
- Health check endpoint

## Quick Start

### Environment Setup

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Edit the `.env` file with your Letta API credentials:
   ```
   LETTA_BASE_URL=https://your-letta-api-url.com
   LETTA_PASSWORD=your_password_here
   PORT=3001
   NODE_ENV=production
   ```

### Using Docker Compose

The easiest way to run the server is with Docker Compose:

```bash
docker-compose up -d
```

This will build the image if needed and start the server in detached mode.

### Using Docker Directly

You can also build and run the Docker image directly:

```bash
# Build the image
docker build -t oculair/letta-tools-mcp:v1.0.4 .

# Run the container
docker run -p 3001:3001 --env-file .env --rm -it oculair/letta-tools-mcp:v1.0.4
```

### Multi-Architecture Build

To build for multiple architectures (amd64 and arm64):

1. Enable Docker Buildx:
   ```bash
   docker buildx create --use --name multiarch-builder
   docker buildx inspect --bootstrap
   ```

2. Build and push:
   ```bash
   docker buildx build --platform linux/amd64,linux/arm64 \
     -t oculair/letta-tools-mcp:v1.0.4 \
     --push .
   ```

3. Verify the multi-architecture image:
   ```bash
   docker manifest inspect oculair/letta-tools-mcp:v1.0.4
   ```

## Development

### Project Structure

```
.
├── everything/
│   ├── src/
│   │   ├── core/       # Core server implementation
│   │   ├── tools/      # MCP tool implementations
│   │   ├── transports/ # Transport implementations (SSE, stdio)
│   │   └── index.js    # Main entry point
│   └── package.json    # Node.js dependencies
├── .env.example        # Example environment variables
├── .gitignore          # Git ignore file
├── compose.yaml        # Docker Compose configuration
├── Dockerfile          # Docker build configuration
└── README.md           # This file
```

### Debugging

To debug the container, you can run it with an interactive shell:

```bash
docker run -p 3001:3001 --env-file .env --rm -it --entrypoint bash oculair/letta-tools-mcp:v1.0.4