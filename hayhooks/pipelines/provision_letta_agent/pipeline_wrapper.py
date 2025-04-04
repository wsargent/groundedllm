import os

from haystack import Pipeline

from hayhooks.server.logger import log
from hayhooks.server.utils.base_pipeline_wrapper import BasePipelineWrapper
from letta_setup import LettaCreateAgent, LettaAttachTools
from letta_client import Letta

class PipelineWrapper(BasePipelineWrapper):
    """
    A Haystack pipeline wrapper that creates and configures a new letta agent.

    Input:
      agent_name (str): The name of the letta agent to create.

    Output:
      str: the id of the newly created agent.
    """

    def setup(self) -> None:
        pipe = Pipeline()

        letta_base_url = os.getenv("LETTA_BASE_URL", "http://letta:8283")    
        letta = Letta(base_url=letta_base_url)
        create_agent = LettaCreateAgent(letta=letta)
        attach_tools = LettaAttachTools(letta=letta)
      
        pipe.add_component("create_agent", create_agent)
        pipe.add_component("attach_tools", attach_tools)
        
        pipe.connect(sender="create_agent.agent_id", receiver="attach_tools.agent_id")
        self.pipeline = pipe

    def run_api(self, agent_name: str) -> str:
        result = self.pipeline.run({"create_agent": {"agent_name": agent_name}})
        
        log.debug(f"run_api: called with {agent_name} -- result = {result}")
        return result["attach_tools"]["agent_id"]
    