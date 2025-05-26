FROM node:18-alpine
WORKDIR /app
# Install the latest version globally within the container
RUN npm install -g supergateway @upstash/context7-mcp

CMD ["npx", "-y", "supergateway", "--stdio", "npx -y @upstash/context7-mcp", "--port", "8002"]