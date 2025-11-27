import os
from datetime import datetime
from typing import Any, Callable, Dict, Generator, Iterator, List, Optional, Union

from hayhooks import BasePipelineWrapper, get_last_user_message, streaming_generator
from hayhooks import log as logger
from haystack import Pipeline, component
from haystack.dataclasses.chat_message import ChatMessage
from haystack.dataclasses.streaming_chunk import StreamingChunk, select_streaming_callback
from haystack.utils.auth import Secret
from letta_client import Letta
from letta_client.types import MessageCreateParam
from letta_client.types.agents import AssistantMessage, LettaResponse, LettaStreamingResponse, Message, ReasoningMessage, ToolCallMessage
from letta_client.types.agents.letta_streaming_response import LettaUsageStatistics
from letta_client.types.agents.text_content_param import TextContentParam
from letta_client.types.tool_return_message import ToolReturnMessage


@component
class LettaChatGenerator:
    """
    Generates chat responses using Letta.
    """

    def __init__(
        self,
        base_url: Optional[str] = os.getenv("LETTA_BASE_URL"),
        api_key: Optional[Secret] = Secret.from_env_var(["LETTA_API_TOKEN"], strict=False),
        generation_kwargs: Optional[Dict[str, Any]] = None,
        streaming_callback: Optional[Callable[[StreamingChunk], None]] = None,
    ):
        """
        Initialize the component with a Letta client.

        :param agent_id: The ID of the Letta agent to use for text generation.
        :param base_url: The base URL of the Letta instance.
        :param api_key: The API key to use as HTTP bearer authorization for Letta.
        :param generation_kwargs: A dictionary with keyword arguments to customize text generation.
        :param streaming_callback: An optional callable for handling streaming responses.
        """

        logger.info(f"Using Letta base URL: {base_url}")
        self.base_url = base_url
        self.api_key = api_key
        # Don't allow any OpenAI generation kwargs for now.
        self.generation_kwargs: Dict[str, Any] = {}
        self.streaming_callback = streaming_callback
        self.timeout = 300.0
        self.max_retries = 3

    @component.output_types(replies=List[str], meta=List[Dict[str, Any]])
    def run(self, prompt: str, agent_id: str, streaming_callback: Optional[Callable[[StreamingChunk], None]] = None, **kwargs):
        """
        Send a query to Letta and return the response.

        :param prompt: The string prompt to use for text generation.
        :param agent_id: The id of the Letta agent to use for text generation.
        :param streaming_callback: An optional callable for handling streaming responses.
        :param kwargs: Additional keyword arguments (filtered for OpenAI compatibility).
        :returns:
            A list of strings containing the generated responses and a list of dictionaries containing the metadata for each response.
        """

        if kwargs:
            logger.warning(f"Received unexpected kwargs: {kwargs}")

        try:
            api_key_value = None if self.api_key is None else self.api_key.resolve_value()
            logger.info(f"Connecting to Letta at {self.base_url} with agent {agent_id}")
            # Only pass api_key if it's set, otherwise use placeholder
            if api_key_value:
                client = Letta(base_url=self.base_url, api_key=api_key_value, timeout=self.timeout, max_retries=self.max_retries, environment="local")
            else:
                # Letta client requires an api_key even for local development without auth
                client = Letta(base_url=self.base_url, timeout=self.timeout, max_retries=self.max_retries, environment="local")
        except Exception as e:
            logger.exception(f"Failed to create Letta client: {str(e)}", e)
            raise ValueError(f"Failed to create Letta client: {str(e)}")

        if not agent_id:
            raise ValueError(f"No Letta agent ID available for {agent_id}!")

        try:
            message = self._message_from_user(prompt)
            messages = [message]
            logger.debug(f"Created message: {message}")
        except Exception as e:
            logger.exception(f"Failed to create message from prompt: {str(e)}", e)
            raise ValueError(f"Failed to create message: {str(e)}")
        streaming_callback = select_streaming_callback(self.streaming_callback, streaming_callback, requires_async=False)  # type: ignore[assignment]

        completions: List[ChatMessage] = []
        if streaming_callback is not None:
            try:
                logger.info(f"Creating stream for agent_id: {agent_id}")
                logger.debug(f"Messages: {messages}")
                stream_completion: Iterator[LettaStreamingResponse] = client.agents.messages.create(agent_id=agent_id, messages=messages, streaming=True)

                chunks = []
                last_chunk = None
                # Sometimes the response will time out while streaming, so we need a try / catch
                try:
                    for chunk in stream_completion:
                        last_chunk = chunk

                        chunk_delta: Optional[StreamingChunk] = self._process_streaming_chunk(chunk)
                        if chunk_delta:
                            chunks.append(chunk_delta)
                            streaming_callback(chunk_delta)

                    assert last_chunk is not None
                    completions = [self._create_message_from_chunks(agent_id, last_chunk, chunks)]
                except Exception as e:
                    logger.exception(f"An error occurred while processing a streaming response: {str(e)}", e)
                    completions = [ChatMessage.from_assistant(f"An error occurred while streaming response: {str(e)}")]
            except Exception as e:
                logger.exception(f"Failed to create Letta stream for agent {agent_id}: {str(e)}", e)
                completions = [ChatMessage.from_assistant(f"Failed to create stream: {str(e)}")]

        else:
            try:
                completion: LettaResponse = client.agents.messages.create(agent_id=agent_id, messages=messages, streaming=False)
                completions = [self._build_message(agent_id, completion)]
            except Exception as e:
                logger.exception(f"An error occurred while processing a response: {str(e)}", e)
                completions = [ChatMessage.from_assistant(f"An error occurred while waiting for response: {str(e)}")]

        logger.debug(f"run: completions={completions}")

        return {"replies": completions}

    @staticmethod
    def _message_from_user(prompt: str) -> MessageCreateParam:
        return MessageCreateParam(role="user", content=[TextContentParam(text=prompt, type="text")])

    def _create_message_from_chunks(self, agent_id, completion_chunk, streamed_chunks: List[StreamingChunk]) -> ChatMessage:
        """
        Creates a single ChatMessage from the streamed chunks. Some data is retrieved from the completion chunk.
        """
        logger.debug(f"_create_message_from_chunks: completion_chunk={completion_chunk}, streamed_chunks={streamed_chunks}")

        # "".join([chunk.content for chunk in streamed_chunks])
        complete_response = ChatMessage.from_assistant("")
        finish_reason = "stop"  # streamed_chunks[-1].meta["finish_reason"]

        usage_dict = {}
        if isinstance(completion_chunk, LettaUsageStatistics):
            usage_dict = {"completion_tokens": completion_chunk.completion_tokens, "prompt_tokens": completion_chunk.prompt_tokens, "total_tokens": completion_chunk.total_tokens}

        complete_response.meta.update(
            {
                "model": agent_id,
                "index": 0,
                "finish_reason": finish_reason,
                "completion_start_time": streamed_chunks[0].meta.get("received_at"),  # first chunk received
                "usage": usage_dict,
            }
        )
        return complete_response

    def _debug_tool_statements(self) -> bool:
        """
        Returns True if the environment variable DEBUG_TOOL_STATEMENTS is set to True.
        """
        return os.getenv("LETTA_CHAT_DEBUG_TOOL_STATEMENTS", "False").lower() == "true"

    def _process_streaming_chunk(self, chunk: LettaStreamingResponse) -> Optional[StreamingChunk]:
        """
        Process a streaming chunk based on its type and invoke the streaming callback.
        """
        logger.debug(f"Processing streaming chunk: {chunk}")

        if isinstance(chunk, ReasoningMessage):
            reasoning_chunk: ReasoningMessage = chunk
            now = datetime.now()
            meta_dict = {"type": "reasoning", "received_at": now.isoformat()}
            display_time = now.astimezone().time().isoformat("seconds")
            reasoning = reasoning_chunk.reasoning.strip().removeprefix('"').removesuffix('"')
            content = f"\n- {display_time} {reasoning}"
            return StreamingChunk(content=content, meta=meta_dict)
        elif isinstance(chunk, ToolCallMessage):
            tool_call_message: ToolCallMessage = chunk
            now = datetime.now()
            display_time = now.astimezone().time().isoformat("seconds")
            meta_dict = {"type": "tool_call", "received_at": now.isoformat()}
            tool_name = tool_call_message.tool_call.name
            call_statement = f"Calling tool {tool_name}"
            arguments: str = tool_call_message.tool_call.arguments if tool_call_message.tool_call.arguments else ""

            # DEBUG: Log raw arguments to investigate HTML entity issue
            logger.debug(f"RAW tool call arguments from Letta: {repr(arguments)}")
            logger.debug(f"Arguments contain &quot;: {'&quot;' in arguments}")
            logger.debug(f"Arguments contain &amp;: {'&amp;' in arguments}")

            no_heartbeat_requested = """"request_heartbeat": false""" in arguments
            if no_heartbeat_requested:
                call_statement = call_statement + " *without heartbeat*"

            if self._debug_tool_statements():
                call_statement = call_statement + " with arguments: " + arguments

            content = f"\n- {display_time} {call_statement}..."
            return StreamingChunk(content=content, meta=meta_dict)
        elif isinstance(chunk, ToolReturnMessage):
            tool_return_message: ToolReturnMessage = chunk
            now = datetime.now()
            meta_dict = {"type": "tool_return", "received_at": now.isoformat()}
            content = f" {tool_return_message.status}, returned {len(tool_return_message.tool_return)} characters."
            return StreamingChunk(content=content, meta=meta_dict)
        elif isinstance(chunk, AssistantMessage):
            now = datetime.now()
            meta_dict = {"type": "assistant", "received_at": now.isoformat()}

            logger.debug(f"Found assistant message: {chunk}")

            # chunk.content can be a string or a list of content objects
            if isinstance(chunk.content, str):
                content = chunk.content
            elif isinstance(chunk.content, list):
                # Extract text from content list
                text_parts = [c.text for c in chunk.content if hasattr(c, "text")]
                content = "".join(text_parts)
            else:
                content = ""

            logger.debug(f"Returning assistant content: {content}")

            return StreamingChunk(content=content, meta=meta_dict)
        elif isinstance(chunk, LettaUsageStatistics):
            logger.debug(f"Ignoring usage statistics: {chunk}")
            return None
        else:
            logger.debug(f"Ignoring unknown streaming chunk type: {type(chunk)}")
            return None

    def _build_message(self, agent_id: str, response: LettaResponse):
        """
        Converts the response from Letta to a ChatMessage.

        :param response:
            The response returned by Letta.
        :returns:
            The ChatMessage.
        """
        logger.debug(f"_build_message: response={response}")

        messages: List[Message] = response.messages
        usage = response.usage
        usage_dict = {"completion_tokens": usage.completion_tokens if usage.completion_tokens else 0, "prompt_tokens": usage.prompt_tokens if usage.prompt_tokens else 0, "total_tokens": usage.total_tokens if usage.total_tokens else 0}

        chat_message = None
        for message in messages:
            if isinstance(message, AssistantMessage):
                # Handle content that can be string or list
                if isinstance(message.content, str):
                    chat_message = ChatMessage.from_assistant(message.content)
                elif isinstance(message.content, list):
                    # Extract text from content list
                    text_parts = [c.text for c in message.content if hasattr(c, "text")]
                    chat_message = ChatMessage.from_assistant("".join(text_parts))
                break

        if not chat_message:
            chat_message = ChatMessage.from_assistant("No message found")

        chat_message.meta.update(
            {
                "model": agent_id,
                "index": 0,
                "finish_reason": "stop",
                "usage": usage_dict,
            }
        )
        return chat_message


class PipelineWrapper(BasePipelineWrapper):
    skip_mcp = True

    def setup(self) -> None:
        self.pipeline = Pipeline()

        letta_chat_generator = LettaChatGenerator()
        self.pipeline.add_component("llm", letta_chat_generator)

    def run_api(self, prompt: str, agent_id: str) -> str:
        result = self.pipeline.run({"llm": {"prompt": prompt, "agent_id": agent_id}})
        return result["llm"]["replies"][0]

    def run_chat_completion(self, model: str, messages: List[dict], body: dict) -> Union[str, Generator]:
        # The body argument contains the full request body, which may be used to extract more
        # information like the temperature or the max_tokens (see the OpenAI API reference for more information).
        logger.debug(f"Running pipeline with model: {model}, messages: {messages}, body keys: {list(body.keys())}")

        # Filter out OpenAI-specific parameters that might conflict with Letta
        filtered_body = {}
        for key, value in body.items():
            if key not in ["stream", "temperature", "max_tokens", "top_p", "frequency_penalty", "presence_penalty", "logit_bias", "user", "n", "stop"]:
                filtered_body[key] = value

        # Check if agent_id is in the nested body structure
        if "body" in filtered_body and isinstance(filtered_body["body"], dict) and "agent_id" in filtered_body["body"]:
            agent_id = filtered_body["body"]["agent_id"]
        else:
            agent_id = filtered_body.get("agent_id")
            if not agent_id:
                raise ValueError("No agent_id provided in the request body")
        prompt = get_last_user_message(messages)

        # streaming_generator yields StreamingChunk objects, but hayhooks expects strings
        # We need to extract the content from each chunk and add headers
        def content_generator() -> Generator[str, None, None]:
            current_section = None
            for chunk in streaming_generator(
                pipeline=self.pipeline,
                pipeline_run_args={
                    "llm": {
                        "prompt": prompt,
                        "agent_id": agent_id,
                    }
                },
            ):
                # Extract content from StreamingChunk objects
                if isinstance(chunk, StreamingChunk):
                    chunk_type = chunk.meta.get("type", "unknown")

                    # Add section header when switching to a new type
                    if chunk_type != current_section:
                        if chunk_type == "reasoning":
                            yield "\n\n**Agent Thoughts:**\n"
                        elif chunk_type == "tool_call":
                            yield "\n\n**Tool Calls:**\n"
                        elif chunk_type == "tool_return":
                            # Don't add header for tool returns, they're part of tool calls
                            pass
                        elif chunk_type == "assistant":
                            yield "\n\n**Assistant Response:**\n"
                        current_section = chunk_type

                    yield chunk.content
                else:
                    # Fallback for any other type (shouldn't happen, but be safe)
                    yield str(chunk)

        return content_generator()
