# Letta MCP Server

This directory contains the reorganized Letta MCP server code with a more logical structure.

## Directory Structure

- `core/` - Core server functionality
  - `server.js` - Main server class with initialization and API communication

- `tools/` - Individual tool implementations
  - `list-agents.js` - Tool for listing agents
  - `prompt-agent.js` - Tool for sending messages to agents
  - `list-agent-tools.js` - Tool for listing tools available for a specific agent
  - `list-tools.js` - Tool for listing all available tools
  - `index.js` - Exports all tool definitions and handlers

- `transports/` - Server transport implementations
  - `stdio-transport.js` - StdioServerTransport implementation
  - `sse-transport.js` - SSEServerTransport implementation
  - `index.js` - Exports all transport handlers

- `index.js` - Main entry point that initializes and runs the server

## Running the Server

### Using JavaScript (Development)

```bash
# Run with stdio transport
npm run dev

# Run with SSE transport
npm run dev:sse
```

### Using TypeScript (Production)

```bash
# Build the TypeScript code
npm run build

# Run with stdio transport
npm run start

# Run with SSE transport
npm run start:sse