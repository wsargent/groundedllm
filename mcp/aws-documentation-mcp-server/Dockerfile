# https://github.com/sparfenyuk/mcp-proxy
# Could also use the custom docker image
# https://github.com/sparfenyuk/mcp-proxy?tab=readme-ov-file#extending-the-container-image
FROM python:3.12-slim-bookworm

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Create a working directory
WORKDIR /app

# Copy the application files
COPY ./pyproject.toml ./uv.lock ./

# Install the dependencies
RUN uv sync --frozen --no-cache

# Expose the port mcp-proxy will listen on for SSE connections
EXPOSE 9712

ENV FASTMCP_LOG_LEVEL=ERROR

ENTRYPOINT ["/bin/uvx", "mcp-proxy", "--sse-port=9712", "--sse-host=0.0.0.0"]

# https://github.com/awslabs/mcp/tree/main/src/aws-documentation-mcp-server
CMD ["/bin/uvx", "awslabs.aws-documentation-mcp-server@latest"]
