import os
from datetime import datetime
from typing import Any, Callable, Dict, Iterator, List, Optional

from hayhooks import log as logger
from haystack import component
from haystack.dataclasses import ChatMessage, StreamingChunk, select_streaming_callback
from haystack.utils import Secret
from letta_client import Letta, MessageCreate, TextContent
from letta_client.agents.messages.types.letta_streaming_response import LettaStreamingResponse
from letta_client.types.assistant_message import AssistantMessage
from letta_client.types.letta_message_union import LettaMessageUnion
from letta_client.types.letta_response import LettaResponse
from letta_client.types.letta_usage_statistics import LettaUsageStatistics
from letta_client.types.reasoning_message import ReasoningMessage
from letta_client.types.tool_call_message import ToolCallMessage
from letta_client.types.tool_return_message import ToolReturnMessage


@component
class LettaChatGenerator:
    """
    Generates chat responses using Letta.
    """

    def __init__(
        self,
        agent_id: Optional[str] = None,
        base_url: Optional[str] = os.getenv("LETTA_BASE_URL"),
        token: Optional[Secret] = Secret.from_env_var(["LETTA_API_TOKEN"], strict=False),
        generation_kwargs: Optional[Dict[str, Any]] = None,
        streaming_callback: Optional[Callable[[StreamingChunk], None]] = None,
    ):
        """
        Initialize the component with a Letta client.

        :param agent_id: The ID of the Letta agent to use for text generation.
        :param base_url: The base URL of the Letta instance.
        :param token: The token to use as HTTP bearer authorization for Letta.
        :param generation_kwargs: A dictionary with keyword arguments to customize text generation.
        :param streaming_callback: An optional callable for handling streaming responses.
        """

        logger.info(f"Using Letta base URL: {base_url} with agent_id = {agent_id}")
        self.agent_id = agent_id
        self.base_url = base_url
        self.token = token
        self.send_end_think = False
        self.generation_kwargs = generation_kwargs
        self.streaming_callback = streaming_callback

    @component.output_types(replies=List[str], meta=List[Dict[str, Any]])
    def run(self, prompt: str, agent_id: str, streaming_callback: Optional[Callable[[StreamingChunk], None]] = None):
        """
        Send a query to Letta and return the response.

        :param prompt: The string prompt to use for text generation.
        :param agent_id: The id of the Letta agent to use for text generation.
        :param streaming_callback: An optional callable for handling streaming responses.
        :returns:
            A list of strings containing the generated responses and a list of dictionaries containing the metadata for each response.
        """

        client = Letta(base_url=self.base_url, token=self.token.resolve_value())
        agent_id = agent_id or self.agent_id
        if not agent_id:
            raise ValueError(f"No Letta agent ID available for {agent_id}!")

        message = self._message_from_user(prompt)
        messages = [message]
        streaming_callback = select_streaming_callback(self.streaming_callback, streaming_callback, requires_async=False)

        completions: List[ChatMessage] = []
        if streaming_callback is not None:
            stream_completion: Iterator[LettaStreamingResponse] = client.agents.messages.create_stream(agent_id=agent_id, messages=messages)

            meta_dict = {"type": "assistant", "received_at": datetime.now().isoformat()}
            think_chunk = StreamingChunk(content="<think>", meta=meta_dict)
            chunks = [think_chunk]
            streaming_callback(think_chunk)
            last_chunk = None
            for chunk in stream_completion:
                last_chunk = chunk

                chunk_delta: Optional[StreamingChunk] = self._process_streaming_chunk(chunk)
                if chunk_delta:
                    chunks.append(chunk_delta)
                    streaming_callback(chunk_delta)

            assert last_chunk is not None
            completions = [self._create_message_from_chunks(last_chunk, chunks)]
        else:
            completion: LettaResponse = client.agents.messages.create(agent_id=agent_id, messages=messages)
            completions = [self._build_message(completion)]

        logger.debug(f"run: completions={completions}")

        return {"replies": completions}

    @staticmethod
    def _message_from_user(prompt: str) -> MessageCreate:
        return MessageCreate(role="user", content=[TextContent(text=prompt)])

    def _create_message_from_chunks(self, completion_chunk, streamed_chunks: List[StreamingChunk]) -> ChatMessage:
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
                "model": self.agent_id,
                "index": 0,
                "finish_reason": finish_reason,
                "completion_start_time": streamed_chunks[0].meta.get("received_at"),  # first chunk received
                "usage": usage_dict,
            }
        )
        return complete_response

    def _debug_tooL_statements(self) -> bool:
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
            self.send_end_think = True
            reasoning_chunk: ReasoningMessage = chunk
            now = datetime.now()
            meta_dict = {"type": "assistant", "received_at": now.isoformat()}
            display_time = now.astimezone().time().isoformat("seconds")
            reasoning = reasoning_chunk.reasoning.strip().removeprefix('"').removesuffix('"')
            content = f"\n- {display_time} {reasoning}"
            return StreamingChunk(content=content, meta=meta_dict)
        if isinstance(chunk, ToolCallMessage):
            self.send_end_think = False
            tool_call_message: ToolCallMessage = chunk
            now = datetime.now()
            display_time = now.astimezone().time().isoformat("seconds")
            meta_dict = {"type": "assistant", "received_at": now.isoformat()}
            tool_name = tool_call_message.tool_call.name
            call_statement = f"Calling tool {tool_name}"
            arguments: str = tool_call_message.tool_call.arguments
            no_heartbeat_requested = """"request_heartbeat": false""" in arguments
            if no_heartbeat_requested:
                self.send_end_think = True
                call_statement = call_statement + " *without heartbeat*"

            if self._debug_tooL_statements():
                call_statement = call_statement + " with arguments: " + arguments

            content = f"\n- {display_time} {call_statement}..."
            return StreamingChunk(content=content, meta=meta_dict)
        if isinstance(chunk, ToolReturnMessage):
            tool_return_message: ToolReturnMessage = chunk
            now = datetime.now()
            meta_dict = {"type": "assistant", "received_at": now.isoformat()}
            content = f" {tool_return_message.status}, returned {len(tool_return_message.tool_return)} characters."
            if self.send_end_think:
                content = content + "</think>[No request heartbeat, you must prompt the agent to reply.]"
                self.send_end_think = False

            return StreamingChunk(content=content, meta=meta_dict)
        if isinstance(chunk, AssistantMessage):
            now = datetime.now()
            meta_dict = {"type": "assistant", "received_at": now.isoformat()}
            content = ""
            if self.send_end_think:
                content = "</think>"

            self.send_end_think = False  # always set this after think

            content = content + chunk.content

            # Assistant message is the last chunk so we need to close the <think> tag
            return StreamingChunk(content=content, meta=meta_dict)
        else:
            logger.debug(f"Ignoring streaming chunk type: {type(chunk)}")
            return None

    def _build_message(self, response: LettaResponse):
        """
        Converts the response from Letta to a ChatMessage.

        :param response:
            The response returned by Letta.
        :returns:
            The ChatMessage.
        """
        logger.debug(f"_build_message: response={response}")

        messages: List[LettaMessageUnion] = response.messages
        usage: LettaUsageStatistics = response.usage
        usage_dict = {"completion_tokens": usage.completion_tokens, "prompt_tokens": usage.prompt_tokens, "total_tokens": usage.total_tokens}

        chat_message = None
        for message in messages:
            if isinstance(message, AssistantMessage):
                chat_message = ChatMessage.from_assistant(message.content)
                break

        if not chat_message:
            chat_message = ChatMessage.from_assistant("No message found")

        chat_message.meta.update(
            {
                "model": self.agent_id,
                "index": 0,
                "finish_reason": "stop",
                "usage": usage_dict,
            }
        )
        return chat_message
