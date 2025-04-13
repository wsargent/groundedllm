import uvicorn
from typing import List
from hayhooks.settings import settings
from hayhooks import create_app
from hayhooks.server.utils.mcp_utils import (
    list_pipelines_as_tools,
    run_pipeline_as_tool,
)
from hayhooks.server.logger import log

from haystack import tracing
from haystack.tracing.logging_tracer import LoggingTracer
from haystack.lazy_imports import LazyImport

import logging

with LazyImport("Run 'pip install \"mcp\"' to install MCP.") as mcp_import:
    from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource
    from mcp.server import Server
    from mcp.server.sse import SseServerTransport

###########
# This class adds MCP support and logging beyond what running `hayhooks run` would get us.

# uvicorn_access = logging.getLogger("uvicorn.access")
# uvicorn_access.disabled = True

HAYSTACK_DETAILED_TRACING = False

if HAYSTACK_DETAILED_TRACING:
    logging.basicConfig(
        format="%(levelname)s - %(name)s -  %(message)s", level=logging.WARNING
    )
    logging.getLogger("haystack").setLevel(logging.DEBUG)

    # https://docs.haystack.deepset.ai/docs/logging
    tracing.tracer.is_content_tracing_enabled = (
        True  # to enable tracing/logging content (inputs/outputs)
    )
    tracing.enable_tracing(
        LoggingTracer(
            tags_color_strings={
                "haystack.component.input": "\x1b[1;31m",
                "haystack.component.name": "\x1b[1;34m",
            }
        )
    )

# https://github.com/deepset-ai/hayhooks/tree/main?tab=readme-ov-file#run-hayhooks-programmatically
hayhooks = create_app()

# --- MCP Server Integration ---
mcp_import.check()

# Setup the MCP server
mcp_server: Server = Server("hayhooks-mcp-server")

# Setup the SSE server transport for MCP
mcp_sse = SseServerTransport("/messages/")


@mcp_server.list_tools()
async def list_tools() -> List[Tool]:
    try:
        return await list_pipelines_as_tools()
    except Exception as e:
        log.error(f"Error listing MCP tools: {e}")
        return []


@mcp_server.call_tool()
async def call_tool(
    name: str, arguments: dict
) -> List[TextContent | ImageContent | EmbeddedResource]:
    try:
        return await run_pipeline_as_tool(name, arguments)
    except Exception as e:
        log.error(f"Error calling MCP tool '{name}': {e}")
        # Consider returning an error structure if MCP spec allows
        return []


async def handle_sse(request):
    async with mcp_sse.connect_sse(
        request.scope, request.receive, request._send
    ) as streams:
        await mcp_server.run(
            streams[0], streams[1], mcp_server.create_initialization_options()
        )


# Add MCP routes directly to the main Hayhooks app
hayhooks.add_route("/sse", handle_sse)
hayhooks.mount("/messages", mcp_sse.handle_post_message)
# --- End MCP Server Integration ---

if __name__ == "__main__":
    # Run the combined Hayhooks + MCP server
    uvicorn.run("app:hayhooks", host=settings.host, port=settings.port)
