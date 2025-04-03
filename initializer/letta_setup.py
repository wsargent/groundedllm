import datetime
import logging
from typing import List, Optional
import os

from letta_client import Letta, LlmConfig
from letta_client import CreateBlock

logger = logging.getLogger("letta_setup")


class LettaSetup:
    """Handles the setup and configuration of the Letta agent."""

    DEFAULT_MODEL = "letta/letta-free"
    LETTA_MODEL = os.getenv("LETTA_MODEL", DEFAULT_MODEL)
    LETTA_EMBEDDING = os.getenv("LETTA_EMBEDDING", DEFAULT_MODEL)
    LETTA_AGENT_NAME = os.getenv("LETTA_AGENT_NAME", "letta-agent")
    MCP_SERVER_NAME = os.getenv("MCP_SERVER_NAME", "hayhooks")
    DEFAULT_RETURN_CHAR_LIMIT = 50000

    PERSONA_FILE_PATH = "letta-agent/persona_memory.md"

    def __init__(self, base_url: str):
        """
        Initializes the setup class with Letta connection details.

        Args:
            base_url (str): The base URL of the Letta instance.
        """
        if not base_url:
            raise ValueError("base_url must be provided and non-empty.")

        self.base_url = base_url
        self.client = Letta(base_url=self.base_url)
        logger.info(f"Letta client initialized for base URL: {self.base_url}")

    def _attach_mcp_tools(self, agent_id: str):
        """Discovers and attaches all tools from the configured MCP server."""
        logger.info(
            f"Discovering and attaching tools from MCP server: {self.MCP_SERVER_NAME}"
        )

        if not self.MCP_SERVER_NAME:
            logger.warning(
                "MCP_SERVER_NAME is not configured. Skipping MCP tool attachment."
            )
            return

        try:
            # List all tools from the MCP server
            mcp_tools = self.client.tools.list_mcp_tools_by_server(
                mcp_server_name=self.MCP_SERVER_NAME
            )
            logger.info(
                f"Found {len(mcp_tools)} tools on MCP server '{self.MCP_SERVER_NAME}'."
            )

            # Create Letta tools from MCP tools and attach them
            attached_tools_count = 0
            for mcp_tool in mcp_tools:
                try:
                    # Create a Letta tool from the MCP tool
                    # This will create if not exists, or return existing if names match
                    tool = self.client.tools.add_mcp_tool(
                        mcp_server_name=self.MCP_SERVER_NAME,
                        mcp_tool_name=mcp_tool.name,
                    )
                    # 6000 is a pokey function output size, we can do better
                    self.client.tools.modify(
                        tool_id=tool.id,
                        return_char_limit=self.DEFAULT_RETURN_CHAR_LIMIT,
                    )

                    # Attach the tool to the agent
                    self.client.agents.tools.attach(agent_id=agent_id, tool_id=tool.id)
                    attached_tools_count += 1
                    logger.info(
                        f"Attached MCP tool '{tool.name}' (ID: {tool.id}) to agent {agent_id}"
                    )
                except Exception as e:
                    # Log error for individual tool attachment but continue with others
                    logger.error(
                        f"Failed to attach MCP tool '{mcp_tool.name}' from server '{self.MCP_SERVER_NAME}': {e}",
                        exc_info=True,
                    )

            logger.info(
                f"Successfully attached {attached_tools_count} MCP tools from server '{self.MCP_SERVER_NAME}' to agent {agent_id}"
            )

        except Exception as e:
            # Log error for the overall process but don't necessarily halt agent creation
            logger.error(
                f"Failed during MCP tool discovery/attachment for server '{self.MCP_SERVER_NAME}': {e}",
                exc_info=True,
            )
            # Depending on requirements, you might want to raise RuntimeError here

    def _create_agent(self) -> str:
        """Creates the letta-agent and attaches tools from the configured MCP server."""
        logger.info(f"{self.LETTA_AGENT_NAME} not found, creating agent...")

        # --- Read Persona ---
        try:
            with open(self.PERSONA_FILE_PATH, "r") as f:
                persona_block_content = f.read()
            logger.info(f"Successfully read persona from {self.PERSONA_FILE_PATH}")
        except FileNotFoundError as e:
            raise RuntimeError(
                f"Could not find persona file at {self.PERSONA_FILE_PATH}"
            ) from e
        # --- End Read Persona ---

        # --- Create Agent ---
        try:
            memory_blocks = [
                CreateBlock(value="", label="human"),
                CreateBlock(value=persona_block_content, label="persona"),
            ]

            available_llms: List[LlmConfig] = self.client.models.list_llms()
            available_model_names = {
                llm.handle for llm in available_llms
            }  # Use model attribute as per LlmConfig

            if self.LETTA_MODEL in available_model_names:
                selected_model = self.LETTA_MODEL
                logger.info(f"Using configured LETTA_MODEL: {selected_model}")
            else:
                selected_model = self.DEFAULT_MODEL
                logger.warning(
                    f"Configured LETTA_MODEL '{self.LETTA_MODEL}' not found in available models: {available_model_names}. Defaulting to {selected_model}"
                )

            # Use reasoning model if we got it (gemini 2.5 pro does not support)
            enable_reasoner = None
            max_reasoning_tokens = None
            max_tokens = None
            if selected_model == "anthropic/claude-3.7-sonnet-20250219":
                enable_reasoner = True
                max_reasoning_tokens = 1024
                max_tokens = 8192

            # Is there a way to set the context window size from here?
            # https://github.com/letta-ai/letta-python/blob/main/reference.md
            agent = self.client.agents.create(
                name=self.LETTA_AGENT_NAME,
                memory_blocks=memory_blocks,
                model=selected_model,
                embedding=self.LETTA_EMBEDDING,
                enable_reasoner=enable_reasoner,
                max_reasoning_tokens=max_reasoning_tokens,
                max_tokens=max_tokens
            )
            logger.info(
                f"Successfully created agent '{self.LETTA_AGENT_NAME}' with ID: {agent.id}"
            )
            # Add a note so we can compare this.
            self.client.agents.passages.create(
                agent_id=agent.id,
                text=f"Created at {datetime.datetime.now()}",
            )
        except Exception as e:
            raise RuntimeError(
                f"Failed to create agent '{self.LETTA_AGENT_NAME}'"
            ) from e
        # --- End Create Agent ---

        # Attach tools from Hayhook (this attaches ALL tools)
        self._attach_mcp_tools(agent_id=agent.id)

        return agent.id

    def setup_agent(self) -> str:
        """
        Checks if the Letta agent exists, creates it if not, and returns its ID.

        Returns:
            str: The ID of the Letta agent.
        """
        try:
            logger.info(f"Starting setup for agent '{self.LETTA_AGENT_NAME}'...")
            agents = self.client.agents.list(name=self.LETTA_AGENT_NAME)

            found_agent_id: Optional[str] = None
            if len(agents) == 1:
                logger.info(f"Found existing agent '{self.LETTA_AGENT_NAME}'")
                found_agent_id = agents[0].id

            if found_agent_id is None:
                agent_id = self._create_agent()
                logger.info(f"Created new agent '{self.LETTA_AGENT_NAME}'")
            else:
                agent_id = found_agent_id

            logger.info(f"Letta Agent setup complete. Agent ID: {agent_id}")
            return agent_id
        except Exception as e:
            raise RuntimeError(
                f"An unexpected error occurred during Letta agent setup for '{self.LETTA_AGENT_NAME}'"
            ) from e
