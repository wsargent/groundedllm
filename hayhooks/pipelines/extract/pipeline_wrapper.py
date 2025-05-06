import os
from typing import List

import haystack
from hayhooks.server.logger import log
from hayhooks.server.utils.base_pipeline_wrapper import BasePipelineWrapper
from haystack import Pipeline
from haystack.components.generators import OpenAIGenerator
from haystack.utils import Secret

from components.content_extraction import build_content_extraction_component


class PipelineWrapper(BasePipelineWrapper):
    """This pipeline extracts content from a URL and sends it to a model that can
    summarize or answer questions on the content.

    Input: A list of URLs.
    Output: The documents
    """

    def setup(self) -> None:
        self.pipeline = self.create_pipeline()

    def create_pipeline(self) -> Pipeline:
        default_user_agent = os.getenv(
            "EXTRACT_USER_AGENT",
            "SearchAgent.extract @ https://github.com/wsargent/groundedllm",
        )
        use_http2 = bool(os.getenv("EXTRACT_HTTP2", "true"))
        retry_attempts = int(os.getenv("EXTRACT_RETRY_ATTEMPTS", "3"))
        timeout = int(os.getenv("EXTRACT_TIMEOUT", "3"))
        raise_on_failure = bool(os.getenv("EXTRACT_RAISE_ON_FAILURE", "False"))
        content_extractor = build_content_extraction_component(
            raise_on_failure=raise_on_failure,
            user_agents=[default_user_agent],
            retry_attempts=retry_attempts,
            timeout=timeout,
            http2=use_http2,
        )

        pipe = Pipeline()
        pipe.add_component("content_extractor", content_extractor)
        return pipe

    def get_extract_generator(self, model) -> OpenAIGenerator:
        return OpenAIGenerator(
            api_key=Secret.from_env_var("OPENAI_API_KEY"),
            api_base_url=os.getenv("OPENAI_API_BASE"),
            model=model,
        )

    def run_api(self, url: str) -> str:
        """Extract pages from URL.

        This tool will fetch HTML, Markdown, PDF, or plain text web pages from URLs.
        and returns the content as JSON. It cannot handle audio, video, or binary content.

        Parameters
        ----------
        url: str
            The URL of the page to extract

        Returns
        -------
        str
            The content of the page, or null if the page could not be processed.

        """
        log.info(f"Running Extract pipeline with URL: {url}")

        result = self.pipeline.run({"content_extractor": {"urls": [url]}})

        documents: List[haystack.Document] = result["content_extractor"]["documents"]
        content = None
        if documents:
            content = documents[0].content or None

        return content
