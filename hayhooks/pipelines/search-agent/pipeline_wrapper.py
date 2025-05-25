from typing import Generator, List, Union

from hayhooks import BasePipelineWrapper, get_last_user_message, streaming_generator
from haystack import Pipeline

from components.letta_chat import LettaChatGenerator


class PipelineWrapper(BasePipelineWrapper):
    def setup(self) -> None:
        self.pipeline = Pipeline()

        agent_name = "search-agent"
        letta_chat_generator = LettaChatGenerator(agent_name=agent_name)
        self.pipeline.add_component("llm", letta_chat_generator)

    def run_api(self, prompt: str) -> str:
        result = self.pipeline.run({"llm": {"prompt": prompt}})
        return result["llm"]["replies"][0]

    def run_chat_completion(self, model: str, messages: List[dict], body: dict) -> Union[str, Generator]:
        # The body argument contains the full request body, which may be used to extract more
        # information like the temperature or the max_tokens (see the OpenAI API reference for more information).
        # logger.trace(f"Running pipeline with model: {model}, messages: {messages}, body: {body}")
        prompt = get_last_user_message(messages)
        return streaming_generator(pipeline=self.pipeline, pipeline_run_args={"llm": {"prompt": prompt}})
