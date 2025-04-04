import os
from typing import Generator, List, Union

from haystack import Pipeline

from hayhooks.server.logger import log
from hayhooks.server.utils.base_pipeline_wrapper import BasePipelineWrapper

class PipelineWrapper(BasePipelineWrapper):
    """
    A Haystack pipeline wrapper that sets up a new letta agent.

    Input:
      agent_name (str): The name of the letta agent to create.

    Output:
      str: "not implemented"
    """

    def setup(self) -> None:
        pipe = Pipeline()
        
        
        return pipe

    def run_api(self, agent_name: str) -> str:
        return "not implemented"
    