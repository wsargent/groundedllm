import os
import time
import uuid
from typing import Generator, List, Union

import uvicorn
from fastapi import HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, HTMLResponse, Response, StreamingResponse
from fastapi.routing import APIRoute
from fastapi.staticfiles import StaticFiles
from hayhooks import BasePipelineWrapper, create_app
from hayhooks.server.pipelines import registry
from hayhooks.server.routers import openai as openai_module_to_patch
from hayhooks.server.routers.openai import ChatCompletion, ChatRequest, Choice, Message, ModelObject, ModelsResponse
from hayhooks.server.utils.mcp_utils import (
    list_pipelines_as_tools,
    run_pipeline_as_tool,
)
from hayhooks.settings import settings
from haystack import tracing
from haystack.lazy_imports import LazyImport
from haystack.tracing.logging_tracer import LoggingTracer
from letta_client import Letta
from loguru import logger as log
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from components.google.google_oauth import GoogleOAuth

with LazyImport("Run 'pip install \"mcp\"' to install MCP.") as mcp_import:
    from mcp.server import Server
    from mcp.server.sse import SseServerTransport
    from mcp.types import EmbeddedResource, ImageContent, TextContent, Tool

###########
# This class adds MCP support and logging beyond what running `hayhooks run` would get us.

# uvicorn_access = logging.getLogger("uvicorn.access")
# uvicorn_access.disabled = True

HAYSTACK_DETAILED_TRACING = False

if HAYSTACK_DETAILED_TRACING:
    # https://docs.haystack.deepset.ai/docs/logging
    tracing.tracer.is_content_tracing_enabled = True  # to enable tracing/logging content (inputs/outputs)
    tracing.enable_tracing(
        LoggingTracer(
            tags_color_strings={
                "haystack.component.input": "\x1b[1;31m",
                "haystack.component.name": "\x1b[1;34m",
            }
        )
    )

# Define the Letta server URL and token
LETTA_BASE_URL = os.getenv("LETTA_BASE_URL", "http://letta:8283")
LETTA_API_TOKEN = os.getenv("LETTA_API_TOKEN", "")


def fetch_letta_models():
    """Fetch available models from Letta server using the Letta client directly"""
    try:
        effective_token = LETTA_API_TOKEN if LETTA_API_TOKEN else None
        # Initialize the Letta client
        client = Letta(base_url=LETTA_BASE_URL, token=effective_token)

        # Get the list of agents
        agents = client.agents.list()

        # Filter out agents with names ending in "sleeptime"
        return [{"id": agent.id, "name": agent.name} for agent in agents if not agent.name.endswith("sleeptime")]
    except Exception as e:
        log.error(f"Unexpected error when fetching agents from Letta: {e}", exc_info=True)
        return []


async def get_models_override():
    """
    Override of the OpenAI /models endpoint to return Letta models.

    This returns a list of available Letta agents as OpenAI-compatible models.
    """
    letta_models = fetch_letta_models()

    return ModelsResponse(
        data=[
            ModelObject(
                id=model["id"],
                name=model["name"],
                object="model",
                created=int(time.time()),
                owned_by="letta",
            )
            for model in letta_models
        ],
        object="list",
    )


openai_module_to_patch.get_models = get_models_override

for route_idx, route in enumerate(openai_module_to_patch.router.routes):
    if isinstance(route, APIRoute) and route.path in ["/models", "/v1/models"]:
        route.endpoint = get_models_override


async def chat_completions_override(chat_req: ChatRequest) -> Union[ChatCompletion, StreamingResponse]:
    # Get the letta_proxy pipeline wrapper
    # Assuming 'letta_proxy' is the registered name of your pipeline
    pipeline_wrapper = registry.get("letta_proxy")

    if not pipeline_wrapper:
        log.error("Pipeline 'letta_proxy' not found in registry.")
        raise HTTPException(status_code=500, detail="Chat backend pipeline 'letta_proxy' not found.")

    if not isinstance(pipeline_wrapper, BasePipelineWrapper):
        log.error(f"Retrieved 'letta_proxy' is not a BasePipelineWrapper instance. Type: {type(pipeline_wrapper)}")
        raise HTTPException(status_code=500, detail="Chat backend pipeline 'letta_proxy' is of an unexpected type.")

    if not pipeline_wrapper._is_run_chat_completion_implemented:  # Now Pylance should be happier after isinstance
        log.error(f"Pipeline 'letta_proxy' (type: {type(pipeline_wrapper)}) does not implement run_chat_completion.")
        raise HTTPException(status_code=501, detail="Chat completions endpoint not implemented for 'letta_proxy' model.")

    request_body_dump = chat_req.model_dump()
    if "agent_id" not in request_body_dump:
        request_body_dump["agent_id"] = chat_req.model
        log.info(f"Injected agent_id='{chat_req.model}' into request_body_dump for letta_proxy.")

    try:
        result_generator = await run_in_threadpool(
            pipeline_wrapper.run_chat_completion,
            model=chat_req.model,
            messages=chat_req.messages,
            body=request_body_dump,
        )
    except ValueError as ve:
        log.error(f"ValueError in letta_proxy.run_chat_completion: {ve}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        log.error(f"Exception calling letta_proxy.run_chat_completion: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error processing chat request with letta_proxy.")

    resp_id = f"chatcmpl-{uuid.uuid4()}"  # OpenAI compatible ID

    def stream_chunks() -> Generator[str, None, None]:
        try:
            for chunk_content in result_generator:
                if not isinstance(chunk_content, str):
                    log.warning(f"letta_proxy returned non-string chunk: {type(chunk_content)}. Converting to str.")
                    chunk_content = str(chunk_content)

                chunk_resp = ChatCompletion(
                    id=resp_id,
                    object="chat.completion.chunk",
                    created=int(time.time()),
                    model=chat_req.model,
                    choices=[Choice(index=0, delta=Message(role="assistant", content=chunk_content))],
                )
                yield f"data: {chunk_resp.model_dump_json()}\n\n"

            final_chunk = ChatCompletion(
                id=resp_id,
                object="chat.completion.chunk",
                created=int(time.time()),
                model=chat_req.model,
                choices=[Choice(index=0, delta=Message(role="assistant", content=""), finish_reason="stop")],
            )
            yield f"data: {final_chunk.model_dump_json()}\n\n"
        except Exception as e:
            log.error(f"Error during streaming from letta_proxy: {e}", exc_info=True)
            error_chunk_content = f"Error processing stream: {e}"
            error_resp = ChatCompletion(
                id=resp_id,
                object="chat.completion.chunk",
                created=int(time.time()),
                model=chat_req.model,
                choices=[Choice(index=0, delta=Message(role="assistant", content=error_chunk_content), finish_reason="stop")],
            )
            yield f"data: {error_resp.model_dump_json()}\n\n"

    if chat_req.stream:
        log.info(f"Returning StreamingResponse for model {chat_req.model}")
        return StreamingResponse(stream_chunks(), media_type="text/event-stream")
    else:
        # Non-streaming: collect all chunks and return a single ChatCompletion
        log.info(f"Returning non-streaming ChatCompletion for model {chat_req.model}")
        full_response_content = ""
        try:
            for chunk_content in result_generator:
                if not isinstance(chunk_content, str):
                    log.warning(f"letta_proxy returned non-string chunk (non-streaming): {type(chunk_content)}. Converting to str.")
                    chunk_content = str(chunk_content)
                full_response_content += chunk_content

            final_resp = ChatCompletion(
                id=resp_id,
                object="chat.completion",
                created=int(time.time()),
                model=chat_req.model,
                choices=[Choice(index=0, message=Message(role="assistant", content=full_response_content), finish_reason="stop")],
            )
            return final_resp
        except Exception as e:
            log.error(f"Error during non-streaming from letta_proxy: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Error collecting stream from letta_proxy: {e}")


for route_idx, route in enumerate(openai_module_to_patch.router.routes):
    if isinstance(route, APIRoute):
        if route.path in ["/models", "/v1/models"]:
            route.endpoint = get_models_override
        elif route.path in ["/chat/completions", "/v1/chat/completions"] or route.operation_id == "chat_completions":  # covers /{pipeline_name}/chat
            route.endpoint = chat_completions_override

hayhooks = create_app()

# Add ProxyHeadersMiddleware to handle X-Forwarded-* headers
# This is crucial for the app to know it's behind an HTTPS proxy
# https://github.com/encode/uvicorn/blob/master/uvicorn/middleware/proxy_headers.py
# This doesn't seem to work in Hayhooks?
hayhooks.add_middleware(ProxyHeadersMiddleware, trusted_hosts=["localhost", "127.0.0.1"])

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
async def call_tool(name: str, arguments: dict) -> List[TextContent | ImageContent | EmbeddedResource]:
    try:
        return await run_pipeline_as_tool(name, arguments)
    except Exception as e:
        log.error(f"Error calling MCP tool '{name}': {e}")
        # Consider returning an error structure if MCP spec allows
        return []


async def handle_sse(request: Request) -> Response:
    async with mcp_sse.connect_sse(request.scope, request.receive, request._send) as streams:
        await mcp_server.run(streams[0], streams[1], mcp_server.create_initialization_options())
    return Response(status_code=200, media_type="text/event-stream")


# Add MCP routes directly to the main Hayhooks app
hayhooks.add_route("/sse", handle_sse)
hayhooks.mount("/messages", mcp_sse.handle_post_message)
# --- End MCP Server Integration ---

# --- Google OAuth2 Integration ---
# Initialize the Google OAuth handler
google_oauth = GoogleOAuth()

hayhooks.mount("/static", StaticFiles(directory="static"), name="static")


@hayhooks.get("/", response_class=HTMLResponse)
async def test_page():
    return FileResponse("static/index.html")


@hayhooks.get("/google-auth-initiate")
async def google_auth_initiate(user_id: str):
    """
    Initiates the Google OAuth2 flow.
    Returns the authorization URL that the user should visit to grant permissions.
    """
    try:
        authorization_url, state = google_oauth.create_authorization_url(user_id)
        return {"authorization_url": authorization_url, "state": state}
    except Exception as e:
        log.error(f"Error initiating Google OAuth: {e}")
        raise HTTPException(status_code=500, detail=f"Error initiating Google OAuth: {e}")


@hayhooks.get("/google-auth-callback")
async def google_auth_callback(request: Request):
    """
    Handles the callback from Google after user authorization.
    """
    log.debug(f"Callback received: {request.url}")
    log.debug(f"Query params: {dict(request.query_params)}")
    log.debug(f"Headers: {dict(request.headers)}")

    try:
        # Get the full URL including query parameters
        authorization_response = str(request.url)
        state = request.query_params.get("state")

        if not state:
            raise HTTPException(status_code=400, detail="Missing state parameter")

        google_oauth.handle_callback(authorization_response, state)

        log.info("Successful callback!")

        # Return a success HTML page
        return HTMLResponse(
            content="""
            <html>
                <body>
                    <h1>Google Authorization Successful!</h1>
                    <p>You can now close this window and return to your chat.</p>
                    <script>
                        // Close the window after 5 seconds
                        setTimeout(function() {
                            window.close();
                        }, 5000);
                    </script>
                </body>
            </html>
        """
        )
    except HTTPException as he:
        log.error(f"HTTPError in Google OAuth callback: {he}")
        # Re-raise HTTP exceptions
        raise he
    except Exception as e:
        log.error(f"Error in Google OAuth callback: {e}")
        return HTMLResponse(
            content=f"""
            <html>
                <body>
                    <h1>Google Authorization Failed!</h1>
                    <p>An error occurred: {e}</p>
                    <p>Please close this window and try again.</p>
                </body>
            </html>
        """,
            status_code=500,
        )


@hayhooks.get("/check-google-auth")
async def check_google_auth(user_id: str):
    """
    Checks if a user is authenticated with Google.
    """
    try:
        is_authenticated = google_oauth.check_auth_status(user_id)
        return {"authenticated": is_authenticated, "user_id": user_id}
    except Exception as e:
        log.error(f"Error checking Google auth status: {e}")
        raise HTTPException(status_code=500, detail=f"Error checking Google auth status: {e}")


# --- End Google OAuth2 Integration ---

if __name__ == "__main__":
    # Run the combined Hayhooks + MCP server
    uvicorn.run("app:hayhooks", host=settings.host, port=settings.port)
