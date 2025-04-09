FROM docker.io/node:23-slim

# Set working directory
WORKDIR /app

# Add metadata labels
LABEL maintainer="Letta Team"
LABEL description="Letta MCP Server with SSE transport"
LABEL version="1.0.4"

# Copy package files and install dependencies
COPY everything/package*.json ./
RUN npm install
RUN npm install dotenv

# Copy source code
COPY everything/src ./src
COPY everything/index.js ./

# Create a non-root user and switch to it
RUN groupadd -r letta && useradd -r -g letta letta
RUN chown -R letta:letta /app
USER letta

# Expose the port
EXPOSE 3001

# Default environment variables (can be overridden at build or runtime)
ARG PORT=3001
ARG NODE_ENV=production
ENV PORT=${PORT}
ENV NODE_ENV=${NODE_ENV}

# Add healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:${PORT}/health || exit 1

# Run the server
CMD ["node", "./src/index.js", "--sse"]
