FROM python:3.12-slim-bookworm

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# https://github.com/awslabs/mcp/tree/main/src/aws-documentation-mcp-server
# https://github.com/sparfenyuk/mcp-proxy

# Create a working directory
WORKDIR /app

# Copy the application files
COPY ./pyproject.toml ./uv.lock ./

# Install the dependencies
RUN uv sync --frozen --no-cache

# Expose the port mcp-proxy will listen on for SSE connections
EXPOSE 9712

# Define the ENTRYPOINT as mcp-proxy with its arguments.
# The '--' separates mcp-proxy args from the command it will run.
ENTRYPOINT ["/bin/uvx", "mcp-proxy", "--sse-port=9712"]

# Define the default command (CMD) that mcp-proxy should execute.
# This executes the aws-documentation-mcp-server directly.
CMD ["/bin/uvx", "awslabs.aws-documentation-mcp-server@latest"]
