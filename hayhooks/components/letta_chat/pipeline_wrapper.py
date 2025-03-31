import os
from typing import Generator, List, Union
from haystack import Pipeline
from hayhooks.server.pipelines.utils import streaming_generator, get_last_user_message
from hayhooks.server.utils.base_pipeline_wrapper import BasePipelineWrapper
from hayhooks.server.logger import log

from haystack.utils import Secret
from letta_client import Letta

from components.letta_chat.letta_chat_generator import LettaChatGenerator

class PipelineWrapper(BasePipelineWrapper):
    AGENT_NAME = "letta-agent"

    def setup(self) -> None:
        base_url = os.getenv("LETTA_BASE_URL")
        if base_url is None:
            raise ValueError("No LETTA_BASE_URL environment variable found!")

        pipe = Pipeline()
        llm = LettaChatGenerator(base_url=base_url)
        pipe.add_component("llm", llm)

        self.pipeline = pipe

    def create_client(self):
        base_url = os.getenv("LETTA_BASE_URL")
        token = Secret.from_env_var("LETTA_API_KEY", strict=False)
        client = Letta(base_url=base_url, token=token.resolve_value())
        return client

    def run_api(self, messages: List[dict]) -> str:
        log.trace(f"Running pipeline with messages: {messages}")
        client = self.create_client()
        agents = client.agents.list(name=self.AGENT_NAME)
        if len(agents) == 0:
            raise ValueError("No Letta agent found with name 'letta-agent'")
        agent_id = agents[0].id

        user_message = get_last_user_message(messages)
        result = self.pipeline.run({"llm": {"user_message": user_message, "agent_id": agent_id}})
        return result["llm"]["replies"][0]

    def run_chat_completion(self, model: str, messages: List[dict], body: dict) -> Union[str, Generator]:
        log.trace(f"Running pipeline with model: {model}, messages: {messages}, body: {body}")
        client = self.create_client()
        agents = client.agents.list(name=self.AGENT_NAME)
        if len(agents) == 0:
            raise ValueError("No Letta agent found with name 'letta-agent'")

        user_message = get_last_user_message(messages)
        agent_id = agents[0].id
        return streaming_generator(
            pipeline=self.pipeline,
            pipeline_run_args={"llm": {"user_message": user_message, "agent_id": agent_id}}
        )
