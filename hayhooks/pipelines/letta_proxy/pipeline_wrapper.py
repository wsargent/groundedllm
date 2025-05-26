from typing import Generator, List, Union

from hayhooks import BasePipelineWrapper, get_last_user_message, streaming_generator
from hayhooks.server.logger import log as logger
from haystack import Pipeline

from components.letta_chat import LettaChatGenerator


class PipelineWrapper(BasePipelineWrapper):
    def setup(self) -> None:
        self.pipeline = Pipeline()

        letta_chat_generator = LettaChatGenerator()
        self.pipeline.add_component("llm", letta_chat_generator)

    def run_api(self, prompt: str, agent_id: str) -> str:
        result = self.pipeline.run({"llm": {"prompt": prompt, "agent_id": agent_id}})
        return result["llm"]["replies"][0]

    def run_chat_completion(self, model: str, messages: List[dict], body: dict) -> Union[str, Generator]:
        # The body argument contains the full request body, which may be used to extract more
        # information like the temperature or the max_tokens (see the OpenAI API reference for more information).
        logger.debug(f"Running pipeline with model: {model}, messages: {messages}, body: {body}")
        # Check if agent_id is in the nested body structure
        if "body" in body and isinstance(body["body"], dict) and "agent_id" in body["body"]:
            agent_id = body["body"]["agent_id"]
        else:
            agent_id = body.get("agent_id")
            if not agent_id:
                raise ValueError("No agent_id provided in the request body")
        prompt = get_last_user_message(messages)
        return streaming_generator(
            pipeline=self.pipeline,
            pipeline_run_args={
                "llm": {
                    "prompt": prompt,
                    "agent_id": agent_id,
                }
            },
        )
