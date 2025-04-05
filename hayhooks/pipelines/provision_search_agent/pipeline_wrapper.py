import os
import importlib.resources as pkg_resources # Added import

from haystack import Pipeline

from hayhooks.server.utils.base_pipeline_wrapper import BasePipelineWrapper
from letta_setup import LettaCreateAgent, LettaAttachTools
from letta_client import Letta
# Assuming CreateFunction is correctly imported from a local module
from openwebui_setup import CreateFunction
import yaml
from haystack.utils import Secret

import logging

logger = logging.getLogger("provision_letta_agent")


DEFAULT_MODEL = "letta/letta-free"
LETTA_MODEL = os.getenv("LETTA_MODEL", DEFAULT_MODEL)
LETTA_EMBEDDING = os.getenv("LETTA_EMBEDDING", DEFAULT_MODEL)


class PipelineWrapper(BasePipelineWrapper):
    """
    A Haystack pipeline wrapper that creates and configures a new letta agent
    and provisions the corresponding Letta Pipe function in OpenWebUI.

    Input:
      agent_name (str): The name of the letta agent to create.

    Output:
      dict: Contains the agent_id and the result from the CreateFunction component.
    """
    # Constants for the OpenWebUI function pipe
    _LETTA_PIPE_ID = "letta_pipe"
    _LETTA_PIPE_NAME = "Letta Pipe"
    _LETTA_PIPE_DESCRIPTION = "Pipe requests to Letta Agent"

    def setup(self) -> None:
        pipe = Pipeline()

        letta_base_url = os.getenv("LETTA_BASE_URL")
        if letta_base_url is None:
            raise ValueError("LETTA_BASE_URL is not defined!")

        logger.info(f"Using {letta_base_url}")

        letta = Letta(base_url=letta_base_url)
        persona_block_content = self._read_persona_block_content()
        create_agent = LettaCreateAgent(
            letta=letta,
            chat_model=LETTA_MODEL,
            embedding_model=LETTA_EMBEDDING,
            persona_block_content=persona_block_content,
        )
        attach_tools = LettaAttachTools(letta=letta)

        # Setup for CreateFunction (OpenWebUI pipe)
        openwebui_base_url = os.getenv("OPENWEBUI_BASE_URL")
        if openwebui_base_url is None:
            raise ValueError("OPENWEBUI_BASE_URL is not defined!")
        email = "admin@localhost" # Assuming default, consider making configurable if needed
        password = Secret.from_token("password") # Assuming default, consider making configurable if needed

        create_function = CreateFunction(
            base_url=openwebui_base_url, email=email, password=password
        )

        pipe.add_component("create_agent", create_agent)
        pipe.add_component("attach_tools", attach_tools)
        pipe.add_component("create_function", create_function)

        # Connect agent_id to both attach_tools and create_function
        pipe.connect(sender="create_agent.agent_id", receiver="attach_tools.agent_id")
        pipe.connect(sender="create_agent.agent_id", receiver="create_function.agent_id")

        self.pipeline = pipe

    def run_api(self, agent_name: str) -> dict:
        """
        Runs the pipeline to create an agent, attach tools, and provision the OpenWebUI pipe.
        """
        # Prepare static arguments for the create_function component
        create_function_args = {
            "function_id": self._LETTA_PIPE_ID,
            "function_name": self._LETTA_PIPE_NAME,
            "function_description": self._LETTA_PIPE_DESCRIPTION,
            "function_content": self._get_letta_pipe_script(),
            "function_manifest": self._get_function_manifest()
        }

        # Run the pipeline providing inputs for components that need them at runtime
        # agent_id is passed internally via connections
        result = self.pipeline.run({
            "create_agent": {"agent_name": agent_name},
            "create_function": create_function_args
        })

        logger.debug(f"run_api: called with {agent_name} -- result = {result}")

        # Return relevant results from both branches
        return {
            "agent_id": result.get("attach_tools", {}).get("agent_id"),
            "create_function_result": result.get("create_function", {})
        }

    def _read_resource_file(self, relative_path: str) -> str:
        """Reads content from a resource file relative to the script's directory."""
        try:
            # Use importlib.resources to access package data files reliably
            package_resources = pkg_resources.files('resources')
            resource_path = package_resources.joinpath(relative_path)
            return resource_path.read_text(encoding='utf-8')
        except FileNotFoundError as e:
            # Log the relative path as the absolute path might be confusing inside a package
            logger.error(f"Could not find resource file '{package_resources}/{relative_path}'")
            raise RuntimeError(
                f"Could not find resource file '{package_resources}/{relative_path}'"
            ) from e
        except Exception as e:
            logger.error(f"An error occurred while reading '{package_resources}/{relative_path}': {e}")
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
