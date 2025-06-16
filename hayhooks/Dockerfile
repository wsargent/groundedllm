FROM python:3.12-slim-bullseye

# curl is needed for docker compose healthcheck
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Install uv.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Copy the application into the container.
# Copy the hayhooks application files into /app in the image.
# The build context is the project root, so 'hayhooks/' refers to the subfolder.
COPY . /app

# Install the application dependencies.
WORKDIR /app
RUN uv sync --frozen --no-cache

# Install the browser dependencies for stealthy fetch
#RUN uv run scrapling install

# Run the application.
CMD ["/app/.venv/bin/python", "/app/app.py"]
