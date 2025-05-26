import datetime
from typing import Dict, List, Optional

from hayhooks import log as logger
from haystack import component
from letta_client import (
    CreateBlock,
    Letta,
    LlmConfig,
)
from letta_client.types import Tool

from resources.utils import read_resource_file


@component
class LettaCreateAgent:
    """A Haystack component that creates or retrieves a Letta agent by name,
    attaching specified tools during creation if the agent doesn't exist.
    """

    DEFAULT_RETURN_CHAR_LIMIT = 500000

    def __init__(self, letta: Letta):
        """Initializes the setup class with Letta connection details."""
        if not letta:
            raise ValueError("letta must be provided and non-empty.")
        self.client = letta

    @component.output_types(agent_id=str, attached_tool_ids=List[str])
    def run(
        self,
        agent_name: str,
        chat_model: str,
        embedding_model: str,
        human_block: str,
        persona_block: str,
        script_tools: List[str],
        mcp_tools: List[str],
    ) -> Dict[str, any]:
        """Finds an existing Letta agent by name or creates a new one with specified tools.

        If the agent doesn't exist, it's created with the provided configuration
        and the requested tools are discovered from the MCP server and attached.

        Args:
        ----
        agent_name:
            The name of the agent to find or create.
        chat_model:
            The identifier for the chat model (e.g., 'openai/gpt-4o').
        embedding_model:
            The identifier for the embedding model (e.g., 'openai/text-embedding-3-large').
        human_block:
            Content for the 'human' memory block.
        persona_block:
            Content for the 'persona' memory block.
        requested_tools:
            A list of tools to attach.

        Returns:
        -------
        dict:
            A dictionary containing the "agent_id".

        Raises:
        ------
        RuntimeError:
            If an unexpected error occurs during the setup process.

        """
        try:
            logger.info(f"Starting setup for agent '{agent_name}'...")

            # --- Agent Existence Check ---
            agents = self.client.agents.list(name=agent_name)
            found_agent_id: Optional[str] = None
            if len(agents) == 1:
                logger.info(f"Found existing agent '{agent_name}' with ID: {agents[0].id}")
                # Note: We don't currently verify if the existing agent has the requested tools.
                found_agent_id = agents[0].id

            # --- Agent Creation (if needed) ---
            if found_agent_id is None:
                logger.info(f"Agent '{agent_name}' not found, creating agent with prepared tools...")
                agent_id = self._create_agent(agent_name=agent_name, human_block_content=human_block, persona_block_content=persona_block, letta_embedding=embedding_model, letta_model=chat_model, script_tools=script_tools, mcp_tools=mcp_tools)
                logger.info(f"Created new agent '{agent_name}' with ID: {agent_id}")
            else:
                agent_id = found_agent_id

            logger.info(f"Letta Agent setup complete. Agent ID: {agent_id}")
            return {"agent_id": agent_id}

        except Exception as e:
            logger.error(
                f"An unexpected error occurred during Letta agent setup for '{agent_name}': {e}",
                exc_info=True,
            )
            # Return agent_id if found, otherwise re-raise or return error structure?
            # For now, re-raise to indicate failure.
            raise RuntimeError(f"Failed Letta agent setup for '{agent_name}'") from e

    def _create_agent(self, agent_name: str, human_block_content: str, persona_block_content: str, letta_model: str, letta_embedding: str, script_tools: List[str], mcp_tools: List[str]) -> str:
        """Creates a new Letta agent with the specified configuration and tools.

        Args:
        ----
        agent_name:
            The name for the new agent.
        human_block_content:
            Content for the 'human' memory block.
        persona_block_content:
            Content for the 'persona' memory block.
        letta_model:
            The identifier for the chat model.
        letta_embedding:
            The identifier for the embedding model.
        script_tools:
            The script tools to attach to the agent upon creation.
        mcp_tools:
            THe MCP tools to attach to the agent upon creation.

        Returns:
        -------
        str:
            The ID of the newly created agent.

        Raises:
        ------
        ValueError:
            If the specified chat model is not available.
        RuntimeError:
            If agent creation fails for other reasons.

        """
        try:
            memory_blocks = [
                CreateBlock(
                    value=human_block_content,
                    label="human",
                    limit=self._set_block_limit(human_block_content),
                ),
                CreateBlock(
                    value=persona_block_content,
                    label="persona",
                    limit=self._set_block_limit(persona_block_content),
                ),
            ]

            # hardcode the mcp server name for now
            mcp_server_name = "context7"

            script_tool_ids = self._find_tools_id(script_tools)
            mcp_tool_ids = self._add_mcp_tools(mcp_server_name=mcp_server_name, mcp_tool_names=mcp_tools)

            tool_ids: list[str] = [*script_tool_ids, *mcp_tool_ids]
            available_llms: List[LlmConfig] = self.client.models.list()
            available_model_names = {llm.handle for llm in available_llms}

            if letta_model in available_model_names:
                selected_model = letta_model
                logger.info(f"Using configured LETTA_MODEL: {selected_model}")
            else:
                raise ValueError(f"Model {letta_model} not found in available models: {available_model_names}")

            # Use reasoning model if we got it (gemini 2.5 pro does not support)
            enable_reasoner = None
            max_reasoning_tokens = None
            max_tokens = None
            enable_sleeptime = True

            # Still not sure if reasoning model is an advantage here
            # if "claude-3-7-sonnet" in selected_model:
            #     enable_reasoner = True
            #     max_reasoning_tokens = 1024
            #     max_tokens = 8192

            # Is there a way to set the context window size from here?
            # https://github.com/letta-ai/letta-python/blob/main/reference.md
            agent = self.client.agents.create(
                name=agent_name,
                memory_blocks=memory_blocks,
                model=selected_model,
                embedding=letta_embedding,
                enable_reasoner=enable_reasoner,
                max_reasoning_tokens=max_reasoning_tokens,
                max_tokens=max_tokens,
                tool_ids=tool_ids,
                enable_sleeptime=enable_sleeptime,
            )
            logger.info(f"Successfully created agent '{agent_name}' (ID: {agent.id}) with {len(tool_ids)} tools.")
            # Add a note so we can see when it was created
            self.client.agents.passages.create(
                agent_id=agent.id,
                text=f"Created at {datetime.datetime.now()}Z",
            )
            return agent.id
        except Exception as e:
            raise RuntimeError(f"Failed to create agent '{agent_name}'") from e

    def _set_block_limit(self, block_content: str) -> int:
        if block_content is None:
            return 5000
        if len(block_content) < 5000:
            return 5000
        return len(block_content) + 1000

    def _get_tool(self, name) -> Tool:
        """Returns the search tool from the Letta server."""
        tool = self._find_tool(name)
        if tool is None:
            tool = self._create_tool(f"{name}_tool.py")

        return tool

    def _create_tool(self, resource_file: str, return_char_limit: int = DEFAULT_RETURN_CHAR_LIMIT) -> Tool:
        """Creates a new Letta tool with the specified configuration."""
        tool_content = read_resource_file(resource_file)
        tool = self.client.tools.create(source_code=tool_content, return_char_limit=return_char_limit)
        return tool

    def _find_tool(self, name: str) -> Optional[Tool]:
        tool_list = self.client.tools.list(name=name, limit=1)
        return tool_list[0] if tool_list else None

    def _find_tools_id(self, script_tools: List[str]) -> List[str]:
        found_tools = []
        for tool_name in script_tools:
            tool = self._get_tool(tool_name)
            if tool is not None:
                found_tools.append(tool.id)
            else:
                logger.warning(f"Could not find tool '{tool_name}'")
        return found_tools

    def _add_mcp_tools(self, mcp_server_name: str, mcp_tool_names: list[str]) -> list[str]:
        found_tools = []
        existing_tools = self.client.tools.list()
        for tool_name in mcp_tool_names:
            tool = None
            for existing_tool in existing_tools:
                if existing_tool.name == tool_name:
                    logger.warning(f"Found exisiting tool '{tool_name}' with ID: {existing_tool.id} ")
                    tool = existing_tool
                    break

            if tool is None:
                tool = self._add_mcp_tool(mcp_server_name, tool_name)

            if tool is not None:
                found_tools.append(tool.id)
            else:
                logger.warning(f"Could not find or add tool '{tool_name}'")

        return found_tools

    def _add_mcp_tool(self, mcp_server_name: str, tool_name: str) -> Tool:
        mcp_tool = self.client.tools.add_mcp_tool(mcp_server_name=mcp_server_name, mcp_tool_name=tool_name)
        return mcp_tool
