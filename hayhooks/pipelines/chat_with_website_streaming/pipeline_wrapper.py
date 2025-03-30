from typing import Generator, List, Union
from haystack import Pipeline
from hayhooks.server.pipelines.utils import get_last_user_message, streaming_generator
from hayhooks.server.utils.base_pipeline_wrapper import BasePipelineWrapper
from hayhooks.server.logger import log
import os

from haystack.utils import Secret
from haystack.components.fetchers import LinkContentFetcher
from haystack.components.converters import HTMLToDocument
from haystack.components.generators.openai import OpenAIGenerator
from haystack.components.builders.prompt_builder import PromptBuilder

URLS = ["https://haystack.deepset.ai", "https://www.redis.io", "https://ssi.inc"]

pipeline_dir = os.getenv("HAYHOOKS_PIPELINES_DIR")

# https://github.com/deepset-ai/hayhooks-open-webui-docker-compose/blob/main/pipelines/chat_with_website_streaming/pipeline_wrapper.py
class PipelineWrapper(BasePipelineWrapper):
    def create_pipeline(self) -> Pipeline:
        fetcher = LinkContentFetcher(
            raise_on_failure=True,
            retry_attempts=2,
            timeout=3,
            user_agents=["haystack/LinkContentFetcher/2.0.0b8"],
        )

        converter = HTMLToDocument()

        llm = OpenAIGenerator(
            model=os.getenv("CHAT_MODEL"),
            api_key=Secret.from_env_var("OPENAI_API_KEY"),
            api_base_url=os.getenv("OPENAI_API_BASE"),
        )

        prompt = PromptBuilder(
            template="""According to the contents of this website:
        {% for document in documents %}
          {{document.content}}
        {% endfor %}
        Answer the given question: {{query}}
        Answer:
        """
        )

        pipe = Pipeline()
        pipe.add_component("fetcher", fetcher)
        pipe.add_component("converter", converter)
        pipe.add_component("llm", llm)
        pipe.add_component("prompt", prompt)

        pipe.connect("fetcher.streams", "converter.sources")
        pipe.connect("converter.documents", "prompt.documents")
        pipe.connect("prompt.prompt", "llm.prompt")

        return pipe

    def create_pipeline_args(self, urls: List[str], question: str) -> dict:
        return {"fetcher": {"urls": urls}, "prompt": {"query": question}}

    def setup(self) -> None:
        self.pipeline = self.create_pipeline()
        
    def run_api(self, urls: List[str], question: str) -> str:
        log.trace(f"Running pipeline with urls: {urls} and question: {question}")
        result = self.pipeline.run(self.create_pipeline_args(urls, question))
        return result["llm"]["replies"][0]

    def run_chat_completion(self, model: str, messages: List[dict], body: dict) -> Union[str, Generator]:
        log.trace(f"Running pipeline with model: {model}, messages: {messages}, body: {body}")

        question = get_last_user_message(messages)
        log.trace(f"Question: {question}")

        # Streaming pipeline run, will return a generator
        return streaming_generator(
            pipeline=self.pipeline,
            pipeline_run_args=self.create_pipeline_args(URLS, question),
        )
