import datetime
import logging
import os
from typing import Dict, List, Optional, Sequence

from haystack import component
from letta_client import ChildToolRule, ContinueToolRule, CreateAgentRequestToolRulesItem, CreateBlock, Letta, LlmConfig, McpTool, TerminalToolRule

logger = logging.getLogger("letta_setup")



@component
class LettaCreateAgent:
    """
    A Haystack component that creates or retrieves a Letta agent by name,
    attaching specified tools during creation if the agent doesn't exist.
    """

    MCP_SERVER_NAME = os.getenv("MCP_SERVER_NAME", "hayhooks")
    DEFAULT_RETURN_CHAR_LIMIT = 50000

    def __init__(self, letta: Letta):
        """
        Initializes the setup class with Letta connection details.
        """
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
        requested_tools: List[str],
        mcp_server_name: str = MCP_SERVER_NAME,
    ) -> Dict[str, any]:
        """
        Finds an existing Letta agent by name or creates a new one with specified tools.

        If the agent doesn't exist, it's created with the provided configuration
        and the requested tools are discovered from the MCP server and attached.

        Args:
        -------
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
            A list of tool names to discover and attach to the agent upon creation.
        mcp_server_name:
            The name of the MCP server to discover tools from. Defaults to env var or 'hayhooks'.

        Returns:
        --------
        dict:
            A dictionary containing the agent_id and a list of attached_tool_ids
            (the IDs of the Letta tools corresponding to the requested MCP tools).

        Raises:
        ----------
        RuntimeError:
            If an unexpected error occurs during the setup process.
        """
        prepared_tool_ids: List[str] = []
        # Even Claude Sonnet 3.7 will occasional return heartbeat_status=false on
        # core_memory_replace or core_memory_append -- the continue tool rules are
        # already in place on archival memory tools but not on core memory tools.
        prepared_tool_rules: List[CreateAgentRequestToolRulesItem] = [
            #ContinueToolRule("core_memory_replace"),
            #ContinueToolRule("core_memory_append")
        ]
        try:
            logger.info(f"Starting setup for agent '{agent_name}'...")

            # --- Tool Preparation ---
            # This happens regardless of whether the agent exists,
            # so we know which tools *should* be attached.
            # Actual attachment only happens during creation.
            if requested_tools:
                logger.info(
                    f"Preparing tools {requested_tools} from MCP server: {mcp_server_name}"
                )
                try:
                    mcp_tools = self.client.tools.list_mcp_tools_by_server(
                        mcp_server_name=mcp_server_name
                    )
                    logger.info(
                        f"Found {len(mcp_tools)} tools on MCP server '{mcp_server_name}'."
                    )

                    for mcp_tool in mcp_tools:
                        if mcp_tool.name in requested_tools:
                            tool_id = self._prepare_single_mcp_tool(
                                mcp_server_name=mcp_server_name, mcp_tool=mcp_tool
                            )
                            if tool_id:
                                prepared_tool_ids.append(tool_id)
                                # XXX For now, hardcode requested rules to always call archival memory insert
                                tool_rule = ChildToolRule(tool_name=mcp_tool.name, children=["archival_memory_insert"])
                                prepared_tool_rules.append(tool_rule)
                            else:
                                logger.warning(
                                    f"Could not prepare tool '{mcp_tool.name}', it will not be attached during creation."
                                )
                except Exception as tool_prep_error:
                    logger.error(
                        f"Failed during MCP tool preparation for server '{mcp_server_name}': {tool_prep_error}",
                        exc_info=True,
                    )
                    # Decide if this is fatal? For now, log and continue without tools.
                    prepared_tool_ids = []
                    prepared_tool_rules = []

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
                agent_id = self._create_agent(
                    agent_name=agent_name,
                    human_block_content=human_block,
                    persona_block_content=persona_block,
                    letta_embedding=embedding_model,
                    letta_model=chat_model,
                    tool_ids=prepared_tool_ids,
                    tool_rules=prepared_tool_rules
                )
                logger.info(f"Created new agent '{agent_name}' with ID: {agent_id}")
            else:
                agent_id = found_agent_id
                # If agent exists, we return the prepared_tool_ids list based on requested_tools,
                # even though they weren't necessarily attached in *this* run.
                # Callers should be aware of this distinction.

            logger.info(f"Letta Agent setup complete. Agent ID: {agent_id}")
            return {"agent_id": agent_id, "attached_tool_ids": prepared_tool_ids}

        except Exception as e:
            logger.error(f"An unexpected error occurred during Letta agent setup for '{agent_name}': {e}", exc_info=True)
            # Return agent_id if found, otherwise re-raise or return error structure?
            # For now, re-raise to indicate failure.
            raise RuntimeError(
                f"Failed Letta agent setup for '{agent_name}'"
            ) from e

    def _create_agent(
        self,
        agent_name: str,
        human_block_content: str,
        persona_block_content: str,
        letta_model: str,
        letta_embedding: str,
        tool_ids: List[str],
        tool_rules: Optional[Sequence[CreateAgentRequestToolRulesItem]] = None
    ) -> str:
        """
        Creates a new Letta agent with the specified configuration and tools.

        Args:
        ----------
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
        tool_ids:
            A list of Letta tool IDs to attach to the agent during creation.
        tool_rules:
            An optional list of tool rules to attach to the agent during creation.
            
        Returns:
        --------
        str:
            The ID of the newly created agent.

        Raises:
        --------
        ValueError:
            If the specified chat model is not available.
        RuntimeError:
            If agent creation fails for other reasons.
        """
        try:
            memory_blocks = [
                CreateBlock(value=human_block_content, label="human"),
                CreateBlock(value=persona_block_content, label="persona"),
            ]

            available_llms: List[LlmConfig] = self.client.models.list_llms()
            available_model_names = {llm.handle for llm in available_llms}

            if letta_model in available_model_names:
                selected_model = letta_model
                logger.info(f"Using configured LETTA_MODEL: {selected_model}")
            else:
                raise ValueError(
                    f"Model {letta_model} not found in available models: {available_model_names}"
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
                tool_ids=tool_ids,
                tool_rules=tool_rules
            )
            logger.info(
                f"Successfully created agent '{agent_name}' (ID: {agent.id}) with {len(tool_ids)} tools."
            )
            # Add a note so we can see when it was created
            self.client.agents.passages.create(
                agent_id=agent.id,
                text=f"Created at {datetime.datetime.now()}Z",
            )
            return agent.id
        except Exception as e:
            raise RuntimeError(f"Failed to create agent '{agent_name}'") from e

    def _prepare_single_mcp_tool(
        self, mcp_server_name: str, mcp_tool: McpTool
    ) -> Optional[str]:
        """
        Ensures a Letta tool exists for the given MCP tool and configures it.

        Checks if a Letta tool corresponding to the MCP tool name exists.
        If not, it creates one using `add_mcp_tool`.
        It then modifies the tool's return character limit.

        Args:
            mcp_server_name: The name of the MCP server the tool belongs to.
            mcp_tool: The MCP tool object (containing name, etc.).

        Returns:
            The Letta tool ID if preparation is successful, otherwise None.
        """
        try:
            tool_name = mcp_tool.name
            # Check if the Letta tool already exists
            existing_tools = self.client.tools.list(name=tool_name)
            if len(existing_tools) > 0:
                tool_id = existing_tools[0].id
                logger.info(f"Found existing Letta tool '{tool_name}' (ID: {tool_id})")
            else:
                # Create a Letta tool from the MCP tool if it doesn't exist
                tool = self.client.tools.add_mcp_tool(
                    mcp_server_name=mcp_server_name,
                    mcp_tool_name=tool_name,
                )
                tool_id = tool.id
                logger.info(f"Created Letta tool '{tool_name}' (ID: {tool_id}) from MCP.")

            # Modify the return character limit (do this even for existing tools)
            # 6000 is a pokey function output size, we can do better
            self.client.tools.modify(
                tool_id=tool_id,
                return_char_limit=self.DEFAULT_RETURN_CHAR_LIMIT,
            )
            logger.info(f"Set return char limit for tool '{tool_name}' (ID: {tool_id})")
            return tool_id

        except Exception as e:
            logger.error(
                f"Failed to prepare Letta tool for MCP tool '{mcp_tool.name}' from server '{mcp_server_name}': {e}",
                exc_info=True,
            )
            return None
