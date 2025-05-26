"""title: Hayhooks Letta Proxy
author: wsargent
version: 0.0.1
description: A pipe to connect to Letta agents through Hayhooks.
"""

import json
import logging
from typing import AsyncGenerator, Dict, List, Optional

import aiohttp
from open_webui.constants import TASKS
from pydantic import BaseModel, Field

function_name = "letta_pipe"


def setup_logger():
    logger = logging.getLogger(function_name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        handler.set_name(function_name)
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.propagate = False
    return logger


logger = setup_logger()


class Pipe:
    class Valves(BaseModel):
        HAYHOOKS_BASE_URL: str = Field(
            default="http://hayhooks:1416",
            description="Base URL for your Hayhooks server",
        )
        LETTA_BASE_URL: str = Field(
            default="http://letta:8283",
            description="Base URL for your Letta server",
        )

    def __init__(self):
        self.type = "manifold"
        self.valves = self.Valves()

    # https://docs.openwebui.com/features/plugin/functions/pipe/#creating-multiple-models-with-pipes
    async def pipes(self) -> List[Dict[str, str]]:
        """Return available models/pipelines"""

        target_url = f"{self.valves.LETTA_BASE_URL}/v1/agents/"
        try:
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get(
                        target_url,
                        headers={"Content-Type": "application/json"},
                    ) as resp:
                        if resp.status == 200:
                            agents = await resp.json()
                            return [self.parse_agent(agent) for agent in agents]
                        else:
                            error_content = await resp.text()
                            logger.error(f"Error fetching agents from Letta: {resp.status} - {error_content}")
                            return []
                except aiohttp.ClientError as e:
                    logger.error(f"HTTP client error when fetching agents: {e}")
                    return []
        except Exception as e:
            logger.error(f"Unexpected error when fetching agents: {e}", exc_info=True)
            return []

    @staticmethod
    def parse_agent(agent):
        logger.debug(f"Parsing agent: {json.dumps(agent, indent=2)}")
        agent_id = agent["id"]
        agent_name = agent["name"]
        return {"id": agent_id, "name": agent_name}

    async def emit_message(self, message: str):
        await self.__current_event_emitter__({"type": "message", "data": {"content": message}})

    async def emit_status(self, level: str, message: str, done: bool):
        await self.__current_event_emitter__(
            {
                "type": "status",
                "data": {
                    "status": "complete" if done else "in_progress",
                    "level": level,
                    "description": message,
                    "done": done,
                },
            }
        )

    async def pipe(self, body: dict, __user__: dict, __event_emitter__=None, __task__=None, __model__=None, __task_body__: Optional[dict] = None) -> AsyncGenerator[str, None]:
        """Proxy requests to Hayhooks run_chat_completion endpoint"""
        # Store event_emitter in instance variable for future use
        if __event_emitter__:
            self.__current_event_emitter__ = __event_emitter__

        # If the user has title or tags called on this model by accident (it's the default model)
        # then give up without passing it through hayhooks
        if __task__ == TASKS.FUNCTION_CALLING:
            return
        if __task__ == TASKS.TITLE_GENERATION:
            yield f"{__task_body__['model']}"  # type: ignore
            return
        if __task__ in [TASKS.AUTOCOMPLETE_GENERATION, TASKS.TAGS_GENERATION]:
            # TODO: prompt and tags autogeneration
            return

        messages = body.get("messages", [])

        # For some reason the agent_id is prefixed with the function name
        model = body.get("model", "invalid-agent-id").removeprefix(f"{function_name}.")
        stream = body.get("stream", False)

        # Prepare the payload for Hayhooks
        hayhooks_payload = {
            "model": "letta_proxy",
            "body": {
                "agent_id": model,
            },
            "messages": messages,
            "stream": stream,
        }

        target_url = f"{self.valves.HAYHOOKS_BASE_URL}/letta_proxy/chat"

        logger.info(f"Proxying request for model '{model}' to {target_url}")
        logger.debug(f"Payload: {json.dumps(hayhooks_payload)}")

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    target_url,
                    json=hayhooks_payload,
                    headers={"Content-Type": "application/json"},
                ) as resp:
                    if resp.status == 200:
                        if stream:
                            logger.debug("Streaming response from Hayhooks")
                            async for line in resp.content:
                                if line.strip():
                                    line_str = line.decode("utf-8").strip()
                                    if line_str.startswith("data: "):
                                        data_json_str = line_str[len("data: ") :]
                                        if data_json_str == "[DONE]":
                                            logger.info("Stream [DONE]")
                                            yield "data: [DONE]\n\n"
                                            break
                                        try:
                                            yield f"data: {data_json_str}\n\n"
                                        except Exception as e_inner:
                                            logger.error(f"Error processing/yielding Hayhooks stream chunk: {data_json_str}, Error: {e_inner}")

                            logger.debug("Finished streaming response.")
                        else:
                            logger.debug("Non-streaming response from Hayhooks")
                            response_data = await resp.json()
                            content = response_data.get("choices", [{}])[0].get("message", {}).get("content")
                            if content:
                                yield content
                            logger.debug(f"Non-streaming response data: {json.dumps(response_data)}")
                    else:
                        error_content = await resp.text()
                        logger.error(f"Error from Hayhooks: {resp.status} - {error_content}")
                        if hasattr(self, "__current_event_emitter__") and self.__current_event_emitter__:
                            await self.emit_status("error", f"Error from Hayhooks: {resp.status} - {error_content[:200]}", True)
                        yield f"Error: Could not connect to Hayhooks. Status: {resp.status}. Response: {error_content[:200]}"

        except aiohttp.ClientConnectorError as e:
            logger.error(f"Connection error to Hayhooks at {target_url}: {e}")
            if hasattr(self, "__current_event_emitter__") and self.__current_event_emitter__:
                await self.emit_status("error", f"Connection error to Hayhooks: {e}", True)
            yield f"Error: Could not connect to Hayhooks. Details: {e}"
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}", exc_info=True)
            if hasattr(self, "__current_event_emitter__") and self.__current_event_emitter__:
                await self.emit_status("error", f"An unexpected error occurred: {e}", True)
            yield f"Error: An unexpected error occurred. Details: {e}"

        logger.info("Hayhooks proxy pipe processing complete.")
