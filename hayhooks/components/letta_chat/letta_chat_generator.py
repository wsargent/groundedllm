import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Iterator

from haystack import component, default_from_dict, default_to_dict, logging
from haystack.dataclasses import (
    ChatMessage,
    StreamingCallbackT,
    StreamingChunk,
    ToolCall,
    ChatRole,
    select_streaming_callback,
    SyncStreamingCallbackT,
)
from haystack.utils.auth import Secret, deserialize_secrets_inplace
from haystack.utils.callable_serialization import serialize_callable, deserialize_callable
from letta_client import Letta, TextContent, MessageRole, MessageCreate, LettaMessageUnion, UserMessage, \
    ToolCallMessage, SystemMessage, AssistantMessage, ReasoningMessage, LettaUsageStatistics, ToolReturnMessage, \
    LettaResponse
from letta_client.agents import LettaStreamingResponse

logger = logging.getLogger(__name__)

@component
class LettaChatGenerator:
    """
    Generates chat completions using the Letta API.

    This component interacts with the Letta API to generate responses based on a given list of messages.
    It supports both streaming and non-streaming modes.

    ### Usage example (Non-streaming)

    ```python
    from haystack.dataclasses import ChatMessage
    from haystack.utils import Secret
    from letta_chat_generator import LettaChatGenerator # Assuming the component is saved here

    # Ensure LETTA_API_TOKEN and LETTA_AGENT_ID are set as environment variables
    # or pass them directly:
    # token=Secret.from_token("your_token"), agent_id="your_agent_id"
    client = LettaChatGenerator(token=Secret.from_env_var("LETTA_API_TOKEN"),
                                agent_id=os.getenv("LETTA_AGENT_ID"))

    messages = [ChatMessage.from_user("Tell me about Berlin")]
    response = client.run(messages=messages)
    print(response["replies"][0].content)

    ### Usage example (Streaming)
    ```python
    import os
    from haystack.dataclasses import ChatMessage
    from haystack.utils import Secret
    from haystack.components.generators.utils import print_streaming_chunk
    from letta_chat_generator import LettaChatGenerator # Assuming the component is saved here

    # Ensure LETTA_API_TOKEN and LETTA_AGENT_ID are set as environment variables
    client = LettaChatGenerator(token=Secret.from_env_var("LETTA_API_TOKEN"),
                                agent_id=os.getenv("LETTA_AGENT_ID"),
                                streaming_callback=print_streaming_chunk)

    messages = [ChatMessage.from_user("Tell me about Paris")]
    response = client.run(messages=messages)
    # print_streaming_chunk will print the streamed chunks
    # The full response is also available in response["replies"]
    print("Full reply:")
    print(response["replies"][0].content)
    ```
    """

    def __init__(
        self,
        base_url: Optional[str] = os.getenv("LETTA_BASE_URL"),
        token: Secret = Secret.from_env_var("LETTA_API_TOKEN", strict=False),
        streaming_callback: Optional[StreamingCallbackT] = None,
        # generation_kwargs are typically set at the agent level in Letta
    ):
        """
        Initializes the LettaChatGenerator component.

        :base_url base_url: The base URL of the Letta server.
        :param token: The Letta API token. Can be provided as a Secret instance or read from the
                      LETTA_API_TOKEN environment variable.
        :param agent_id: The ID of the Letta agent to use for chat completions. Can be provided directly
                         or read from the LETTA_AGENT_ID environment variable.
        :param streaming_callback: An optional callback function that is invoked when a new chunk of data
                                   is received during streaming. The function should accept a single argument
                                   of type `StreamingChunk`.
        """

        self.token = token
        self.streaming_callback = streaming_callback
        # Initialize the sync client
        self.client = Letta(base_url = base_url, token=self.token.resolve_value())
        # Async client initialization (if needed later for run_async)
        # self.async_client = AsyncLetta(base_url = base_url, token=self.token.resolve_value())

    def to_dict(self) -> Dict[str, Any]:
        """
        Serializes the component to a dictionary.

        :returns:
            Dictionary with serialized data.
        """
        callback_name = serialize_callable(self.streaming_callback) if self.streaming_callback else None
        return default_to_dict(
            self,
            token=self.token.to_dict(),
            agent_id=self.agent_id,
            streaming_callback=callback_name,
        )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LettaChatGenerator":
        """
        Deserializes the component from a dictionary.

        :param data:
            Dictionary to deserialize from.
        :returns:
            Deserialized component.
        """
        deserialize_secrets_inplace(data["init_params"], keys=["token"])
        if (callback_name := data["init_params"].get("streaming_callback")) is not None:
            data["init_params"]["streaming_callback"] = deserialize_callable(callback_name)
        return default_from_dict(cls, data)

    @staticmethod
    def _convert_haystack_to_letta_message(message: ChatMessage) -> MessageCreate:
        """Converts a Haystack ChatMessage to a Letta MessageCreate object."""
        content = []
        if message.text:
            content.append(TextContent(text=message.text))
        # Note: Letta's MessageCreate primarily uses TextContent.
        # Handling ToolOutput (ChatMessage with role TOOL) might require formatting its content as text.
        if message.role == ChatRole.TOOL:
             # Format ToolOutput content as text for Letta
             # Need to access the tool name, which might be in meta for a TOOL role message
             tool_name = message.meta.get("name", "unknown_tool") # Get name from meta or use default
             tool_output_text = f"Tool {tool_name} output: {json.dumps(message.text)}"
             content.append(TextContent(text=tool_output_text))

        role_map = {
            "user": "user",
            "assistant": "assistant",
            "system": "system",
            "tool": "tool", # Letta uses 'tool' role
        }
        letta_role = role_map.get(message.role)
        if not letta_role:
            logger.warning(f"Unsupported Haystack ChatRole {message.role}, defaulting to 'user'.")
            letta_role = "user"

        # Handle tool calls specifically for assistant messages if needed by Letta's structure
        # Letta's MessageCreate doesn't seem to have a direct field for tool_calls like OpenAI.
        # Tool calls are typically part of the AssistantMessage response.
        # For sending tool results back, we use the 'tool' role.

        msg_data = {
            "role": letta_role,
            "content": content,
        }
        # Add tool_call_id if the message is from a Tool (role == TOOL)
        if message.role == ChatRole.TOOL and message.meta.get("tool_call_id"):
            msg_data["tool_call_id"] = message.meta["tool_call_id"]

        return MessageCreate(**msg_data)

    @staticmethod
    def _convert_letta_to_haystack_message(letta_message: LettaMessageUnion) -> ChatMessage:
        """Converts a Letta message object to a Haystack ChatMessage."""
        role_map = {
            "user": "user",
            "assistant": "assistant",
            "system": "system",
            "tool": "tool",
        }
        haystack_role = role_map.get(letta_message.role)
        if not haystack_role:
             logger.warning(f"Unsupported Letta role {letta_message.role}, skipping message.")
             return None # Or handle appropriately

        content = ""
        tool_calls = []
        meta = {"letta_message_type": type(letta_message).__name__} # Store message type

        if isinstance(letta_message, (UserMessage, SystemMessage, ToolCallMessage)): # Changed LettaToolMessage to ToolCallMessage
            # These usually have simple text content
            if letta_message.content and isinstance(letta_message.content, str):
                 content = letta_message.content
            elif letta_message.content and isinstance(letta_message.content, list) and letta_message.content:
                 # Assuming text content is the primary type
                 text_parts = [c.text for c in letta_message.content if isinstance(c, TextContent) and c.text]
                 content = "\n".join(text_parts)

        elif isinstance(letta_message, AssistantMessage):
            if letta_message.content and isinstance(letta_message.content, str):
                 content = letta_message.content
            elif letta_message.content and isinstance(letta_message.content, list) and letta_message.content:
                 text_parts = [c.text for c in letta_message.content if isinstance(c, TextContent) and c.text]
                 content = "\n".join(text_parts)

            # # Process tool calls from AssistantMessage
            # if letta_message.tool_calls:
            #     for tc in letta_message.tool_calls:
            #         if isinstance(tc, ToolCall) and tc.function:
            #             try:
            #                 arguments = json.loads(tc.function.arguments) if tc.function.arguments else {}
            #                 tool_calls.append(ToolCall(id=tc.id, tool_name=tc.function.name, arguments=arguments))
            #             except json.JSONDecodeError:
            #                 logger.warning(f"Failed to parse tool call arguments for tool {tc.function.name}: {tc.function.arguments}")
            # # Add other relevant metadata if available
            # meta["finish_reason"] = letta_message.finish_reason
            # meta["usage"] = letta_message.usage.to_dict() if letta_message.usage else {}


        if haystack_role == ChatRole.ASSISTANT:
             return ChatMessage.from_assistant(text=content or None, tool_calls=tool_calls or None, meta=meta)
        elif haystack_role == ChatRole.USER:
             return ChatMessage.from_user(text=content, meta=meta)
        elif haystack_role == ChatRole.SYSTEM:
             return ChatMessage.from_system(text=content, meta=meta)
        elif haystack_role == ChatRole.TOOL:
             # Need tool_call_id and name for ToolOutput
             tool_call_id = letta_message.tool_call_id if hasattr(letta_message, 'tool_call_id') else None
             # Letta ToolMessage doesn't inherently have a 'name', might need to infer or skip
             tool_call = ToolCall(id=tool_call_id, tool_name="unknown_tool", arguments={})
             return ChatMessage.from_tool(tool_result=content, origin=tool_call, meta=meta) # name is missing

        return None # Should not happen if roles are mapped correctly

    def _handle_stream_response(self, chat_completion: Iterator[LettaStreamingResponse], callback: SyncStreamingCallbackT) -> List[ChatMessage]:
        chunks: List[StreamingChunk] = []
        chunk = None
        chunk_delta: StreamingChunk

        for chunk in chat_completion:
            chunk_delta = self._convert_chat_completion_chunk_to_streaming_chunk(chunk)
            chunks.append(chunk_delta)
            callback(chunk_delta)
        return [self._convert_streaming_chunks_to_chat_message(chunk, chunks)]


    def _convert_streaming_chunks_to_chat_message(self, last_chunk: LettaStreamingResponse, chunks: List[LettaStreamingResponse]) -> ChatMessage:
        """
        Connects the streaming chunks into a single ChatMessage.

        :param last_chunk: The last chunk returned by Letta API.
        :param chunks: The list of all `LettaStreamingResponse` objects.

        :returns: The ChatMessage.
        """

        #FIXME need to get content through the streaming responses
        #text = "".join([chunk.content for chunk in chunks])
        tool_calls = []

        # Process tool calls if present in any chunk
        tool_call_data: Dict[str, Dict[str, str]] = {}  # Track tool calls by index

        meta = {
            "model": last_chunk.model,
            "index": 0,
            "completion_start_time": chunks[0].meta.get("received_at"),  # first chunk received
            "usage": dict(last_chunk.usage or {}),  # last chunk has the final usage data if available
        }
        return ChatMessage.from_assistant(text=text or None, tool_calls=tool_calls, meta=meta)


    def _convert_chat_completion_chunk_to_streaming_chunk(self, chunk: LettaStreamingResponse) -> StreamingChunk:
        """
        Converts the streaming response chunk from the Letta API to a StreamingChunk.

        :param chunk: The chunk returned by the Letta API.

        :returns:
            The StreamingChunk.
        """
        # if there are no choices, return an empty chunk
        if len(chunk.choices) == 0:
            return StreamingChunk(content="", meta={"model": chunk.model, "received_at": datetime.now().isoformat()})

        # we stream the content of the chunk if it's not a tool or function call
        content = ""
        if not isinstance(chunk, ToolCallMessage):
            content = chunk.content

        chunk_message = StreamingChunk(content)
        # but save the tool calls and function call in the meta if they are present
        # and then connect the chunks in the _convert_streaming_chunks_to_chat_message method
        chunk_message.meta.update(
            {
                "received_at": datetime.now().isoformat(),
            }
        )
        return chunk_message

    @component.output_types(replies=List[ChatMessage])
    def run(
        self,
        user_message: ChatMessage,
        agent_id: str,
        streaming_callback: Optional[StreamingCallbackT] = None
    ) -> Dict[str, List[ChatMessage]]:
        """
        Invokes the Letta agent to generate chat completions.

        :param user_message: The last user message.
        :param agent_id: The Agent ID to use.
        :param streaming_callback: An optional callback function invoked when streaming chunks are received.
                                   This overrides the callback provided during initialization.
        :returns: A dictionary containing:
          - `replies`: A list of `ChatMessage` instances representing the agent's responses.
        """

        # Select the appropriate streaming callback
        callback: Optional[StreamingCallbackT] = select_streaming_callback(self.streaming_callback, streaming_callback, requires_async=False)

        # Convert Haystack messages to Letta format
        letta_message: MessageCreate = self._convert_haystack_to_letta_message(user_message)
        if callback:
            # Streaming mode
            stream: Iterator[LettaStreamingResponse] = self.client.agents.messages.create_stream(
                agent_id=agent_id,
                messages=[letta_message],
                stream_tokens=True, # Request token streaming
            )
            completions = self._handle_stream_response(
                stream,  # type: ignore
                streaming_callback,  # type: ignore
            )

            return {"replies": completions}
        else:
            # Non-streaming mode
            try:
                response: LettaResponse = self.client.agents.messages.create(
                    agent_id=agent_id,
                    messages=[letta_message],
                )
                # Process the response messages
                replies = [self._convert_letta_to_haystack_message(msg) for msg in response.messages if msg]
                # Filter out None messages if conversion failed
                replies = [r for r in replies if r]
                # Typically, we want the last assistant message as the primary reply
                assistant_replies = [r for r in replies if r.role == ChatRole.ASSISTANT]
                return {"replies": assistant_replies }

            except Exception as e:
                logger.error(f"Letta API call failed: {e}")
                raise e