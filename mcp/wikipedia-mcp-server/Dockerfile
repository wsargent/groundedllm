FROM node:18-alpine

WORKDIR /app

# Install the necessary global npm packages during the build
# Using --no-update-notifier --no-fund to reduce noise and potential pauses
# Using --prefer-offline during build if possible after first download
RUN npm install -g --no-update-notifier --no-fund mcp-proxy @shelm/wikipedia-mcp-server

EXPOSE 9713

# Define the main command (the proxy)
# This will run when the container starts
ENTRYPOINT ["mcp-proxy", "--port", "9713", "--endpoint", "/sse"]

# Define the default command to be proxied
# This can be overridden when running the container if needed
CMD ["npx", "@shelm/wikipedia-mcp-server"]