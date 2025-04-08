import asyncio
import datetime
import logging
import sys
from contextlib import asynccontextmanager
from typing import List

import uvicorn
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from hayhooks.server.app import (
    lifespan as hayhooks_lifespan
)
from hayhooks.server.logger import log
from hayhooks.server.routers import (
    deploy_router,
    draw_router,
    openai_router,
    status_router,
    undeploy_router,
)
from hayhooks.server.utils.mcp_utils import (
    list_pipelines_as_tools,
    run_pipeline_as_tool,
)
from hayhooks.settings import check_cors_settings, settings
from haystack import tracing
from haystack.lazy_imports import LazyImport
from haystack.tracing.logging_tracer import LoggingTracer

# MCP Imports
with LazyImport("Run 'pip install \"mcp\"' to install MCP.") as mcp_import:
    from mcp.server import Server
    from mcp.server.sse import SseServerTransport
    from mcp.types import EmbeddedResource, ImageContent, TextContent, Tool

###########
# Configuration
###########

# uvicorn_access = logging.getLogger("uvicorn.access")
# uvicorn_access.disabled = True

HAYSTACK_DETAILED_TRACING = True

if HAYSTACK_DETAILED_TRACING:
    logging.basicConfig(
        format="%(levelname)s - %(name)s -  %(message)s", level=logging.WARNING
    )
    logging.getLogger("haystack").setLevel(logging.DEBUG)

    logging.getLogger('apscheduler').setLevel(logging.DEBUG)

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

###########
# Custom Scheduler Logic
###########

scheduler = AsyncIOScheduler(timezone="UTC")  # Choose your timezone


async def my_periodic_task():
    """
    This is the function that will be executed every 10 seconds.
    """
    logger = logging.getLogger("app")
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logger.info(f"Periodic task executed at: {current_time}")
    # --- Add your actual code here ---
    await asyncio.sleep(1)  # Simulate some async work if needed
    logger.info("Periodic task finished.")


@asynccontextmanager
async def scheduler_lifespan(app: FastAPI):
    """Manages the scheduler lifecycle."""
    log.info("Starting scheduler...")
    # Add the job to the scheduler
    scheduler.add_job(
        my_periodic_task,
        trigger=IntervalTrigger(seconds=10),
        id="my_periodic_task_job",  # Give the job a unique ID
        name="Run my task every 10 seconds",
        replace_existing=True,
    )
    # Start the scheduler
    scheduler.start()
    log.info("Scheduler started.")
    try:
        yield  # Application runs
    finally:
        log.info("Shutting down scheduler...")
        scheduler.shutdown()
        log.info("Scheduler shut down.")


###########
# Combined Lifespan
###########


@asynccontextmanager
async def combined_lifespan(app: FastAPI):
    """Combines custom scheduler lifespan with hayhooks lifespan."""
    async with scheduler_lifespan(app):
        async with hayhooks_lifespan(app):
            yield  # Application runs here


###########
# FastAPI App Creation (Replicating hayhooks.create_app but with combined lifespan)
###########


def create_my_app() -> FastAPI:
    """
    Create and configure a FastAPI application with combined lifespan.
    """
    if additional_path := settings.additional_python_path:
        sys.path.append(additional_path)
        log.trace(f"Added {additional_path} to sys.path")

    # Instantiate FastAPI with the *combined* lifespan
    if root_path := settings.root_path:
        app = FastAPI(root_path=root_path, lifespan=combined_lifespan)
    else:
        app = FastAPI(lifespan=combined_lifespan)

    # Add CORS middleware (copied from hayhooks)
    check_cors_settings()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_methods=settings.cors_allow_methods,
        allow_headers=settings.cors_allow_headers,
        allow_credentials=settings.cors_allow_credentials,
        allow_origin_regex=settings.cors_allow_origin_regex,
        expose_headers=settings.cors_expose_headers,
        max_age=settings.cors_max_age,
    )

    # Include hayhooks routers (copied from hayhooks)
    app.include_router(status_router)
    app.include_router(draw_router)
    app.include_router(deploy_router)
    app.include_router(undeploy_router)
    app.include_router(openai_router)

    # Include your own routers if any
    # from .my_routers import custom_router
    # app.include_router(custom_router)

    return app


# Create the app instance using your factory function
app = create_my_app()

###########
# MCP Server Integration (Attached to the new 'app' instance)
###########
mcp_import.check()

# Setup the MCP server
mcp_server: Server = Server("hayhooks-mcp-server")

# Setup the SSE server transport for MCP
mcp_sse = SseServerTransport("/messages/")


@mcp_server.list_tools()
async def list_tools() -> List[Tool]:
    try:
        # Pass the app instance if needed by the underlying function, otherwise remove
        return await list_pipelines_as_tools(app)
    except Exception as e:
        log.error(f"Error listing MCP tools: {e}")
        return []


@mcp_server.call_tool()
async def call_tool(
    name: str, arguments: dict
) -> List[TextContent | ImageContent | EmbeddedResource]:
    try:
        # Pass the app instance if needed by the underlying function, otherwise remove
        return await run_pipeline_as_tool(app, name, arguments)
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


# Add MCP routes directly to the *new* app instance
app.add_route("/sse", handle_sse)
app.mount("/messages", mcp_sse.handle_post_message)

###########
# Run with Uvicorn
###########

if __name__ == "__main__":
    # Run the application using the 'app' instance created by create_my_app()
    uvicorn.run(
        "app:app", host=settings.host, port=settings.port, reload=True
    )  # Added reload for convenience
