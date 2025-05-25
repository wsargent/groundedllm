from typing import Generator, List, Union

from hayhooks import BasePipelineWrapper, get_last_user_message, streaming_generator
from hayhooks import log as logger
from haystack import Pipeline

from components.letta_chat import LettaChatGenerator


class PipelineWrapper(BasePipelineWrapper):
    def setup(self) -> None:
        self.pipeline = Pipeline()

        letta_streaming_component = LettaChatGenerator(agent_name="search-agent")
        self.pipeline.add_component("llm", letta_streaming_component)

    def run_api(self, prompt: str) -> str:
        result = self.pipeline.run({"llm": {"prompt": prompt}})
        return result["llm"]["replies"][0]

    def run_chat_completion(self, model: str, messages: List[dict], body: dict) -> Union[str, Generator]:
        logger.trace(f"Running pipeline with model: {model}, messages: {messages}, body: {body}")

        prompt = get_last_user_message(messages)
        return streaming_generator(pipeline=self.pipeline, pipeline_run_args={"llm": {"prompt": prompt}})
