import os
import re

import yaml
from hayhooks import log as logger
from hayhooks.server.utils.base_pipeline_wrapper import BasePipelineWrapper
from haystack import Pipeline
from haystack.utils import Secret
from letta_client import Letta

from components.letta_setup import LettaCreateAgent
from components.openwebui_setup import CreateFunction
from resources.utils import read_resource_file


# Provision Search Agent
class PipelineWrapper(BasePipelineWrapper):
    """A Haystack pipeline wrapper that orchestrates the creation and configuration
    of a new Letta agent, attaches necessary tools, and provisions a corresponding
    Letta Pipe function within OpenWebUI.

    This pipeline integrates Letta agent management with OpenWebUI function deployment.

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
        """Initializes and configures the Haystack pipeline components.

        This method sets up the necessary components:
        - LettaCreateAgent: To create the agent in Letta.
        - LettaAttachTools: To attach predefined tools to the created agent.
        - CreateFunction: To provision the corresponding pipe function in OpenWebUI.

        It reads configuration like base URLs from environment variables and
        connects the components appropriately within the pipeline.

        Raises:
            ValueError: If required environment variables (LETTA_BASE_URL, OPENWEBUI_BASE_URL)
                        are not set.

        """
        # Removed settings instantiation
        pipe = Pipeline()

        # Revert to using os.getenv
        letta_base_url = os.getenv("LETTA_BASE_URL")
        if letta_base_url is None:
            raise ValueError("LETTA_BASE_URL is not defined!")
        logger.info(f"Using Letta base URL: {letta_base_url}")
        letta = Letta(base_url=letta_base_url)
        create_agent = LettaCreateAgent(letta=letta)

        # Revert Setup for CreateFunction
        openwebui_base_url = os.getenv("OPENWEBUI_BASE_URL")
        if openwebui_base_url is None:
            raise ValueError("OPENWEBUI_BASE_URL is not defined!")
        logger.info(f"Using OpenWebUI base URL: {openwebui_base_url}")
        # Revert to hardcoded/Secret values
        openwebui_email = "admin@localhost"
        openwebui_password = Secret.from_token("password")

        create_open_webui_function = CreateFunction(
            base_url=openwebui_base_url,
            email=openwebui_email,
            password=openwebui_password,
        )

        pipe.add_component("create_agent", create_agent)
        pipe.add_component("create_function", create_open_webui_function)

        pipe.connect(sender="create_agent.agent_id", receiver="create_function.agent_id")

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
        requested_tools = ["search", "extract", "excerpt"]
        create_agent_args = {
            "agent_name": agent_name,
            "chat_model": chat_model,
            "embedding_model": embedding_model,
            "human_block": "",
            "persona_block": self._read_persona_block_content(),
            "requested_tools": requested_tools,
        }

        create_open_webui_function_args = {
            "function_id": self._snake_case(agent_name),
            "function_name": f"{agent_name}",
            "function_description": f"A pipe function for {agent_name}",
            # Revert to using internal helper method
            "function_content": self._get_letta_pipe_script(),
            # Revert to using internal helper method
            "function_manifest": self._get_function_manifest(),
        }

        # Run the actual pipeline
        result = self.pipeline.run(
            {
                "create_agent": create_agent_args,
                "create_function": create_open_webui_function_args,
            }
        )

        logger.debug(f"run_api: called with {agent_name} -- result = {result}")

        # Return relevant results from both branches
        return {
            "agent_id": result.get("attach_tools", {}).get("agent_id"),
            "create_function_result": result.get("create_function", {}),
        }

    def _snake_case(self, s: str) -> str:
        """Converts a string to snake_case."""
        # Replace hyphens with underscores
        s = s.replace("-", "_")
        # Insert underscore before uppercase letters preceded by a lowercase letter or digit
        s = re.sub(r"(?<=[a-z0-9])([A-Z])", r"_\1", s)
        # Insert underscore before uppercase letters preceded by another uppercase letter and followed by a lowercase letter
        s = re.sub(r"(?<=[A-Z])([A-Z][a-z])", r"_\1", s)
        # Convert to lowercase
        return s.lower()

    # Restore internal helper methods (they now use the shared read_resource_file)
    def _read_persona_block_content(self):
        """Reads the persona content from the file."""
        return read_resource_file("persona_memory.md")

    def _get_letta_pipe_script(self) -> str:
        """Reads the Letta pipe script content from the file."""
        return read_resource_file("letta_pipe.py")

    def _get_function_manifest(self) -> dict:
        """Loads the manifest dictionary from the YAML file."""
        manifest_content = read_resource_file("function_manifest.yaml")
        try:
            manifest_data = yaml.safe_load(manifest_content)
            if not isinstance(manifest_data, dict):
                raise ValueError("Manifest file content is not a valid dictionary.")
            return manifest_data
        except yaml.YAMLError as e:
            logger.error(f"Error parsing manifest YAML: {e}")
            raise RuntimeError(f"Error parsing manifest YAML: {e}") from e
