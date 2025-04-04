from typing import Dict, List, Optional

import datetime
import logging
import os

from haystack import component

from letta_client import Letta, LlmConfig
from letta_client import CreateBlock

logger = logging.getLogger("letta_setup")


@component
class LettaCreateAgent:
    """Handles the setup and configuration of the Letta agent."""

    DEFAULT_MODEL = "letta/letta-free"
    LETTA_MODEL = os.getenv("LETTA_MODEL", DEFAULT_MODEL)
    LETTA_EMBEDDING = os.getenv("LETTA_EMBEDDING", DEFAULT_MODEL)

    PERSONA_FILE_PATH = "letta-agent/persona_memory.md"

    def __init__(self, letta: Letta):
        """
        Initializes the setup class with Letta connection details.

        Args:
            letta (str): The base URL of the Letta instance.
        """
        if not letta:
            raise ValueError("letta must be provided and non-empty.")

        self.client = letta

    @component.output_types(agent_id=str)
    def run(self, agent_name: str) -> str:
        """
        Checks if the Letta agent exists, creates it if not, and returns its ID.

        Returns:
            str: The ID of the Letta agent.
        """
        try:
            logger.info(f"Starting setup for agent '{agent_name}'...")
            agents = self.client.agents.list(name=agent_name)

            found_agent_id: Optional[str] = None
            if len(agents) == 1:
                logger.info(f"Found existing agent '{agent_name}'")
                found_agent_id = agents[0].id

            if found_agent_id is None:
                logger.info(f"{agent_name} not found, creating agent...")
                persona_block_content = self._read_persona_block_content()
                letta_model = self.LETTA_MODEL
                letta_embedding = self.LETTA_EMBEDDING
                agent_id = self._create_agent(
                    agent_name=agent_name,
                    persona_block_content=persona_block_content,
                    letta_embedding=letta_embedding,
                    letta_model=letta_model,
                )
                logger.info(f"Created new agent '{agent_name}'")
            else:
                agent_id = found_agent_id

            logger.info(f"Letta Agent setup complete. Agent ID: {agent_id}")
            return {"agent_id": agent_id}
        except Exception as e:
            raise RuntimeError(
                f"An unexpected error occurred during Letta agent setup for '{agent_name}'"
            ) from e

    def _read_persona_block_content(self):
        try:
            with open(self.PERSONA_FILE_PATH, "r") as f:
                return f.read()
        except FileNotFoundError as e:
            raise RuntimeError(
                f"Could not find persona file at {self.PERSONA_FILE_PATH}"
            ) from e

    def _create_agent(
        self,
        agent_name: str,
        persona_block_content: str,
        letta_model: str,
        letta_embedding: str,
    ) -> str:    
        try:
            memory_blocks = [
                CreateBlock(value="", label="human"),
                CreateBlock(value=persona_block_content, label="persona"),
            ]

            available_llms: List[LlmConfig] = self.client.models.list_llms()
            available_model_names = {
                llm.handle for llm in available_llms
            }

            if letta_model in available_model_names:
                selected_model = letta_model
                logger.info(f"Using configured LETTA_MODEL: {selected_model}")
            else:
                selected_model = self.DEFAULT_MODEL
                logger.warning(
                    f"'{letta_model}' not found in {available_model_names}. Defaulting to {selected_model}"
                )

            # Use reasoning model if we got it (gemini 2.5 pro does not support)
            enable_reasoner = None
            max_reasoning_tokens = None
            max_tokens = None

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
            )
            logger.info(
                f"Successfully created agent '{agent_name}' with ID: {agent.id}"
            )
            # Add a note so we can see when it was created
            self.client.agents.passages.create(
                agent_id=agent.id,
                text=f"Created at {datetime.datetime.now()}Z",
            )
            return agent.id
        except Exception as e:
            raise RuntimeError(f"Failed to create agent '{agent_name}'") from e



@component
class LettaAttachTools:
    MCP_SERVER_NAME = os.getenv("MCP_SERVER_NAME", "hayhooks")
    DEFAULT_RETURN_CHAR_LIMIT = 50000

    def __init__(self, letta: Letta):
        """
        Initializes the setup class with Letta connection details.

        Args:
            letta: The Letta instance to use
        """
        if not letta:
            raise ValueError("letta must be provided and non-empty.")
        self.client = letta


    @component.output_types(agent_id=str, attached_tools=Dict[str, str])
    def run(
        self, agent_id: str, mcp_server_name: str = MCP_SERVER_NAME
    ) -> Dict[str, str]:
        """Discovers and attaches all tools from the configured MCP server."""

        logger.info(
            f"Discovering and attaching tools from MCP server: {mcp_server_name}"
        )

        try:
            # List all tools from the MCP server
            mcp_tools = self.client.tools.list_mcp_tools_by_server(
                mcp_server_name=mcp_server_name
            )
            logger.info(
                f"Found {len(mcp_tools)} tools on MCP server '{mcp_server_name}'."
            )

            # Create Letta tools from MCP tools and attach them
            attached_tools: Dict[str, str] = {}
            for mcp_tool in mcp_tools:
                tool_id = self._attach_single_mcp_tool(
                    agent_id=agent_id,
                    mcp_server_name=mcp_server_name,
                    mcp_tool=mcp_tool,
                )
                if tool_id:
                    attached_tools[mcp_tool.name] = tool_id

            return {"agent_id": agent_id, "attached_tools": attached_tools}

        except Exception as e:
            # Log error for the overall process but don't necessarily halt agent creation
            logger.error(
                f"Failed during MCP tool discovery/attachment for server '{mcp_server_name}': {e}",
                exc_info=True,
            )
            return {"agent_id": agent_id}

    def _attach_single_mcp_tool(
        self, agent_id: str, mcp_server_name: str, mcp_tool
    ) -> Optional[str]:
        """Creates a Letta tool from an MCP tool and attaches it to the agent."""
        try:
            # Create a Letta tool from the MCP tool
            # This will create if not exists, or return existing if names match
            tool = self.client.tools.add_mcp_tool(
                mcp_server_name=mcp_server_name,
                mcp_tool_name=mcp_tool.name,
            )
            # 6000 is a pokey function output size, we can do better
            self.client.tools.modify(
                tool_id=tool.id,
                return_char_limit=self.DEFAULT_RETURN_CHAR_LIMIT,
            )

            # Attach the tool to the agent
            self.client.agents.tools.attach(agent_id=agent_id, tool_id=tool.id)
            logger.info(
                f"Attached MCP tool '{tool.name}' (ID: {tool.id}) to agent {agent_id}"
            )
            return tool.id
        except Exception as e:
            # Log error for individual tool attachment but continue with others
            logger.error(
                f"Failed to attach MCP tool '{mcp_tool.name}' from server '{mcp_server_name}': {e}",
                exc_info=True,
            )
            return None
