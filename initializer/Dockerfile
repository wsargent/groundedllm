FROM python:3.12-slim-bullseye

# Install uv.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Install git so we can get openwebui-python
# RUN apt-get update && \
#     apt-get install -y --no-install-recommends git && \
#     rm -rf /var/lib/apt/lists/*

# Copy the application into the container.
COPY . /app

# Install the application dependencies.
WORKDIR /app
RUN uv sync --frozen --no-cache

CMD ["/app/.venv/bin/python", "/app/main.py"]