import os

from hayhooks import log as logger
from hayhooks.server.utils.base_pipeline_wrapper import BasePipelineWrapper
from haystack import Pipeline
from letta_client import Letta

from components.letta_setup import LettaCreateAgent
from resources.utils import read_resource_file


# Provision Search Agent
class PipelineWrapper(BasePipelineWrapper):
    """A Haystack pipeline wrapper that orchestrates the creation and configuration
    of a new Letta agent and attaches tools.

    Input (via run_api):
      agent_name (str):
        The desired name for the new Letta agent.
      chat_model (str, optional):
        The chat model to use for the agent. Defaults to DEFAULT_MODEL.
      embedding_model (str, optional):
        The embedding model to use for the agent. Defaults to DEFAULT_MODEL.

    Output (from run_api):
      dict: A dictionary containing the created 'agent_id' and the 'create_function_result'
            which holds the response from the OpenWebUI function creation process.
    """

    def setup(self) -> None:
        """Initializes and configures the Haystack pipeline components."""
        # Removed settings instantiation
        pipe = Pipeline()

        # Revert to using os.getenv
        letta_base_url = os.getenv("LETTA_BASE_URL")
        letta_token = os.getenv("LETTA_API_TOKEN")
        if letta_base_url is None:
            raise ValueError("LETTA_BASE_URL is not defined!")
        logger.info(f"Using Letta base URL: {letta_base_url}")
        letta = Letta(base_url=letta_base_url, token=letta_token)
        create_agent = LettaCreateAgent(letta=letta)

        pipe.add_component("create_agent", create_agent)

        self.pipeline = pipe

    def run_api(
        self,
        agent_name: str,
        chat_model: str,
        embedding_model: str,
    ) -> dict:
        """Runs the configured Haystack pipeline to create a Letta agent, attach tools,
        and provision the corresponding OpenWebUI pipe function.

        Args:
        ----
        agent_name: str
            The name for the new Letta agent. This will also be used to generate the function ID and name in OpenWebUI.
        chat_model: (str, optional)
            The chat model identifier for the Letta agent.
        embedding_model: (str, optional)
            The embedding model identifier for the Letta agent.

        Returns:
        -------
        dict:
            A dictionary containing the 'agent_id' of the newly created Letta agent
            and the 'create_function_result' dictionary from the OpenWebUI
            function creation component.

        """
        # Run the pipeline providing inputs for components that need them at runtime
        # agent_id is passed internally via connections
        requested_tools = [
            "extract",  # extracts full text
            "excerpt",  # queries an LLM that was given the full text
            "google_auth",  # check google authentication
            "search",  # calls search engines
            "search_zotero",  # search zotero repository
            "search_stackoverflow",  # searches stack overflow
            "search_calendars",  # search calendars
            "search_emails",  # search emails
        ]
        tool_env_vars = {
            "HAYHOOKS_BASE_URL": self._get_hayhooks_base_url(),  # base url for tools
            "HAYHOOKS_USER_ID": self._get_hayhooks_user_id(),  # google user id
        }
        system_timezone = os.getenv("TZ", "America/Los_Angeles")
        create_agent_args = {
            "agent_name": agent_name,
            "chat_model": chat_model,
            "embedding_model": embedding_model,
            "human_block": "",
            "persona_block": self._read_persona_block_content(),
            "requested_tools": requested_tools,
            "tool_exec_environment_variables": tool_env_vars,
            "timezone": system_timezone,
        }

        # Run the actual pipeline
        result = self.pipeline.run({"create_agent": create_agent_args})

        logger.debug(f"run_api: called with {agent_name} -- result = {result}")

        # Return relevant results from both branches
        return {"agent_id": result.get("attach_tools", {}).get("agent_id")}

    # Restore internal helper methods (they now use the shared read_resource_file)
    def _read_persona_block_content(self):
        """Reads the persona content from the file."""
        return read_resource_file("persona_memory.md")

    def _get_hayhooks_base_url(self):
        return os.getenv("HAYHOOKS_BASE_URL")

    def _get_hayhooks_user_id(self):
        return os.getenv("HAYHOOKS_USER_ID")
