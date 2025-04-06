import importlib.resources as pkg_resources  # Added import
import logging
import os
import re

import yaml
from hayhooks.server.utils.base_pipeline_wrapper import BasePipelineWrapper
from haystack import Pipeline
from haystack.utils import Secret
from letta_client import Letta

from letta_setup import LettaAttachTools, LettaCreateAgent
from openwebui_setup import CreateFunction

logger = logging.getLogger("provision_search_agent")


# Provision Search Agent
class PipelineWrapper(BasePipelineWrapper):
    """
    A Haystack pipeline wrapper that orchestrates the creation and configuration
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
        """
        Initializes and configures the Haystack pipeline components.

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
        pipe = Pipeline()

        letta_base_url = os.getenv("LETTA_BASE_URL")
        if letta_base_url is None:
            raise ValueError("LETTA_BASE_URL is not defined!")

        logger.info(f"Using {letta_base_url}")

        letta = Letta(base_url=letta_base_url)
        create_agent = LettaCreateAgent(letta=letta)
        attach_tools = LettaAttachTools(letta=letta)

        # Setup for CreateFunction (OpenWebUI pipe)
        openwebui_base_url = os.getenv("OPENWEBUI_BASE_URL")
        if openwebui_base_url is None:
            raise ValueError("OPENWEBUI_BASE_URL is not defined!")

        # Should break this out for credentials.
        openwebui_email = "admin@localhost"
        openwebui_password = Secret.from_token("password")

        create_open_webui_function = CreateFunction(
            base_url=openwebui_base_url,
            email=openwebui_email,
            password=openwebui_password,
        )

        pipe.add_component("create_agent", create_agent)
        pipe.add_component("attach_tools", attach_tools)
        pipe.add_component("create_function", create_open_webui_function)

        # Connect agent_id to both attach_tools and create_function
        pipe.connect(sender="create_agent.agent_id", receiver="attach_tools.agent_id")
        pipe.connect(
            sender="create_agent.agent_id", receiver="create_function.agent_id"
        )

        self.pipeline = pipe

    def run_api(
        self,
        agent_name: str,
        chat_model: str,
        embedding_model: str,
    ) -> dict:
        """
        Runs the configured Haystack pipeline to create a Letta agent, attach tools,
        and provision the corresponding OpenWebUI pipe function.

        Args:
        -------------
        agent_name: str
            The name for the new Letta agent. This will also be used to generate the function ID and name in OpenWebUI.
        chat_model: (str, optional)
            The chat model identifier for the Letta agent.
        embedding_model: (str, optional)
            The embedding model identifier for the Letta agent.

        Returns:
        -----------
        dict:
            A dictionary containing the 'agent_id' of the newly created Letta agent
            and the 'create_function_result' dictionary from the OpenWebUI
            function creation component.
        """

        # Run the pipeline providing inputs for components that need them at runtime
        # agent_id is passed internally via connections
        create_agent_args = {
            "agent_name": agent_name,
            "chat_model": chat_model,
            "embedding_model": embedding_model,
            "human_block": "",
            "persona_block": self._read_persona_block_content(),
        }

        # only these tools go into search agent
        attach_tool_args = {"requested_tools": ["search", "extract"]}

        create_open_webui_function_args = {
            "function_id": self._snake_case(agent_name),
            "function_name": f"{agent_name}",
            "function_description": f"A pipe function for {agent_name}",
            "function_content": self._get_letta_pipe_script(),
            "function_manifest": self._get_function_manifest(),
        }

        # Run the actual pipeline
        result = self.pipeline.run(
            {
                "create_agent": create_agent_args,
                "attach_tools": attach_tool_args,
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

    def _read_resource_file(self, relative_path: str) -> str:
        """
        Reads content from a resource file located within the 'resources' package.

        Uses importlib.resources for reliable access to package data files,
        making it suitable for use even when the application is packaged.

        Args:
            relative_path (str): The path to the resource file relative to the 'resources' package.

        Returns:
            str: The content of the resource file as a string.

        Raises:
            RuntimeError: If the file cannot be found or read.
        """
        try:
            # Use importlib.resources to access package data files reliably
            package_resources = pkg_resources.files("resources")
            resource_path = package_resources.joinpath(relative_path)
            return resource_path.read_text(encoding="utf-8")
        except FileNotFoundError as e:
            raise RuntimeError(
                f"Could not find resource file '{package_resources}/{relative_path}'"
            ) from e
        except Exception as e:
            raise RuntimeError(
                f"An error occurred while reading '{package_resources}/{relative_path}'"
            ) from e

    def _read_persona_block_content(self):
        """Reads the persona content from the file."""
        return self._read_resource_file("persona_memory.md")

    def _get_letta_pipe_script(self) -> str:
        """Reads the Letta pipe script content from the file."""
        return self._read_resource_file("letta_pipe.py")

    def _get_function_manifest(self) -> dict:
        """Loads the manifest dictionary from the YAML file."""
        manifest_content = self._read_resource_file("function_manifest.yaml")
        try:
            manifest_data = yaml.safe_load(manifest_content)
            if not isinstance(manifest_data, dict):
                raise ValueError("Manifest file content is not a valid dictionary.")
            return manifest_data
        except yaml.YAMLError as e:
            logger.error(f"Error parsing manifest YAML: {e}")
            raise RuntimeError(f"Error parsing manifest YAML: {e}") from e
