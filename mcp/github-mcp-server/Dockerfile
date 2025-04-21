FROM ghcr.io/sparfenyuk/mcp-proxy:latest

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY . /app

WORKDIR /app

# Expose the port mcp-proxy will listen on for SSE connections
EXPOSE 9720

ENV FASTMCP_LOG_LEVEL=ERROR

ENTRYPOINT ["/bin/uvx", "mcp-proxy", "--sse-port=9720", "--sse-host=0.0.0.0", "--pass-environment"]

# This is done by extracting directly from the go project:
#
# git clone https://github.com/github/github-mcp-server
# cd cmd/github-mcp-server
# env GOOS=linux GOARCH=amd64 go build -o github-mcp-server_linux_amd64
# env GOOS=linux GOARCH=arm64 go build -o github-mcp-server_linux_arm64
# env GOOS=darwin GOARCH=arm64 go build -o github-mcp-server_macos_arm64
# env GOOS=darwin GOARCH=amd64 go build -o github-mcp-server_macos_amd64

CMD ["/app/github-mcp-server_linux_amd64", "stdio"]
