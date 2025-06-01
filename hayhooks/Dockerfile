FROM python:3.12-slim-bullseye

# Install uv.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Copy the application into the container.
# Copy the hayhooks application files into /app in the image.
# The build context is the project root, so 'hayhooks/' refers to the subfolder.
COPY hayhooks/ /app/

# Install the application dependencies.
WORKDIR /app
RUN uv sync --frozen --no-cache

# Copy Caddy's self-signed certificate
# The build context is the project root (.), so caddy/ refers to the project's caddy directory
COPY caddy/ca.pem /usr/local/share/ca-certificates/mkcert-ca.crt

# Install CA certificates package and update the system's trust store
RUN apt-get update && \
    apt-get install -y --no-install-recommends ca-certificates curl && \
    update-ca-certificates && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Run the application.
CMD ["/app/.venv/bin/python", "/app/app.py"]
