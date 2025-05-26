import os
import time
import uuid  # Added for chat completion IDs
from typing import Generator, List, Union

import uvicorn
from fastapi import HTTPException, Request  # Added HTTPException
from fastapi.concurrency import run_in_threadpool  # Added for running pipeline
from fastapi.responses import Response, StreamingResponse  # Added StreamingResponse
from fastapi.routing import APIRoute
from hayhooks import BasePipelineWrapper, create_app, log  # Added BasePipelineWrapper
from hayhooks.server.pipelines import registry  # Added for getting pipeline wrapper
from hayhooks.server.routers import openai as openai_module_to_patch
from hayhooks.server.routers.openai import ChatCompletion, ChatRequest, Choice, Message, ModelObject, ModelsResponse  # Added chat models
from hayhooks.server.utils.mcp_utils import (
    list_pipelines_as_tools,
    run_pipeline_as_tool,
)
from hayhooks.settings import settings
from haystack import tracing
from haystack.lazy_imports import LazyImport
from haystack.tracing.logging_tracer import LoggingTracer
from letta_client import Letta

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
        log.info(f"fetch_letta_models: LETTA_API_TOKEN from env is '{LETTA_API_TOKEN}'. Effective token for client: '{str(effective_token)[:5]}...' (showing first 5 chars if not None)")
        # Initialize the Letta client
        client = Letta(base_url=LETTA_BASE_URL, token=effective_token)

        # Get the list of agents
        agents = client.agents.list()

        # Filter out agents with names ending in "sleeptime"
        return [{"id": agent.id, "name": agent.name} for agent in agents if not agent.name.endswith("sleeptime")]
    except Exception as e:
        log.error(f"Unexpected error when fetching agents from Letta: {e}", exc_info=True)
        return []


# Override the get_models method in the OpenAI router
# The decorators were removed; get_models_override will be monkey-patched onto the openai module.
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

# https://github.com/deepset-ai/hayhooks/tree/main?tab=readme-ov-file#run-hayhooks-programmatically
# hayhooks = create_app() # Moved after chat_completions_override is defined and patched

# --- Chat Completions Override ---


async def chat_completions_override(chat_req: ChatRequest) -> Union[ChatCompletion, StreamingResponse]:
    log.info(f"--- CHAT_COMPLETIONS_OVERRIDE CALLED for model: {chat_req.model} ---")

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

    # The letta_proxy pipeline's run_chat_completion expects agent_id in the body.
    # The chat_req.model from OpenAI request should be the agent_id.
    # We need to ensure the body passed to run_chat_completion contains this.
    # The original chat_endpoint in Hayhooks passes chat_req.model_dump() as the body.
    # The letta_proxy wrapper already tries to get agent_id from body.get("agent_id")
    # or body["body"]["agent_id"]. If chat_req.model is the agent_id, we need to make sure
    # it's accessible via one of these paths in the `body` dict passed to run_chat_completion.
    # The simplest is to ensure body["agent_id"] = chat_req.model.
    # However, the letta_proxy wrapper's run_chat_completion already uses chat_req.model as `model` parameter,
    # and then tries to extract agent_id from the body. This seems a bit redundant if chat_req.model *is* the agent_id.
    # Let's rely on the letta_proxy's existing logic for now, assuming it can pick up chat_req.model correctly
    # or that the client (e.g. Open WebUI) sends agent_id in the body if needed.
    # The key is that `pipeline_wrapper.run_chat_completion` needs the `agent_id`.
    # The `model` parameter to `run_chat_completion` in the wrapper is `chat_req.model`.
    # The wrapper then tries to get `agent_id` from `body.get("agent_id")`.
    # So, if Open WebUI sends the selected model ID (which is our agent_id) as `model` in ChatRequest,
    # and the `letta_proxy` wrapper uses this `model` parameter as the `agent_id`, it should work.
    # Let's re-check the letta_proxy wrapper:
    # def run_chat_completion(self, model: str, messages: List[dict], body: dict)
    #   agent_id = body.get("agent_id") (or body["body"]["agent_id"])
    #   IF NOT agent_id: raise ValueError
    # This means the `model` parameter (chat_req.model) is NOT directly used as agent_id by the wrapper.
    # The agent_id MUST come from the `body`.
    # So, we need to inject chat_req.model into the body as 'agent_id'.

    request_body_dump = chat_req.model_dump()
    if "agent_id" not in request_body_dump:
        request_body_dump["agent_id"] = chat_req.model
        log.info(f"Injected agent_id='{chat_req.model}' into request_body_dump for letta_proxy.")

    # Call the pipeline's run_chat_completion method
    # This method is expected to return a generator for streaming
    try:
        result_generator = await run_in_threadpool(
            pipeline_wrapper.run_chat_completion,
            model=chat_req.model,  # This is the Letta Agent ID
            messages=chat_req.messages,
            body=request_body_dump,  # Pass the full request body
        )
    except ValueError as ve:
        log.error(f"ValueError in letta_proxy.run_chat_completion: {ve}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        log.error(f"Exception calling letta_proxy.run_chat_completion: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error processing chat request with letta_proxy.")

    resp_id = f"chatcmpl-{uuid.uuid4()}"  # OpenAI compatible ID

    # Handle streaming response
    # This logic is adapted from Hayhooks' original openai.py chat_endpoint
    def stream_chunks() -> Generator[str, None, None]:
        try:
            for chunk_content in result_generator:
                if not isinstance(chunk_content, str):
                    # If the pipeline returns non-string chunks, convert or log error
                    log.warning(f"letta_proxy returned non-string chunk: {type(chunk_content)}. Converting to str.")
                    chunk_content = str(chunk_content)

                chunk_resp = ChatCompletion(
                    id=resp_id,
                    object="chat.completion.chunk",
                    created=int(time.time()),
                    model=chat_req.model,  # Letta Agent ID
                    choices=[Choice(index=0, delta=Message(role="assistant", content=chunk_content))],
                )
                yield f"data: {chunk_resp.model_dump_json()}\n\n"

            # Send the final chunk with finish_reason
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
            # How to signal error in SSE? For now, just stop streaming.
            # A more robust solution might involve sending an error event.
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


# Now, apply the patches to the router
log.info("Attempting to modify FastAPI router endpoints directly for /models and /v1/models...")
for route_idx, route in enumerate(openai_module_to_patch.router.routes):
    if isinstance(route, APIRoute):
        if route.path in ["/models", "/v1/models"]:
            log.info(f"  Route {route_idx}: Path='{route.path}', Original Endpoint='{getattr(route.endpoint, '__name__', route.endpoint)}'. Overriding for get_models.")
            route.endpoint = get_models_override
            log.info(f"  Route {route_idx}: Path='{route.path}', New Endpoint='{getattr(route.endpoint, '__name__', route.endpoint)}'.")
        elif route.path in ["/chat/completions", "/v1/chat/completions"] or route.operation_id == "chat_completions":  # covers /{pipeline_name}/chat
            log.info(f"  Route {route_idx}: Path='{route.path}', OperationID='{route.operation_id}', Original Endpoint='{getattr(route.endpoint, '__name__', route.endpoint)}'. Overriding for chat_completions.")
            route.endpoint = chat_completions_override
            log.info(f"  Route {route_idx}: Path='{route.path}', New Endpoint='{getattr(route.endpoint, '__name__', route.endpoint)}'.")
log.info("Finished attempting to modify FastAPI router endpoints.")


hayhooks = create_app()  # Moved after chat_completions_override is defined and patched

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

if __name__ == "__main__":
    # Run the combined Hayhooks + MCP server
    uvicorn.run("app:hayhooks", host=settings.host, port=settings.port)
