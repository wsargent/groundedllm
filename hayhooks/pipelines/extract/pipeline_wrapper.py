import json
import os
from typing import List, Optional

import haystack
from hayhooks.server.utils.base_pipeline_wrapper import BasePipelineWrapper
from haystack import Pipeline
from haystack.components.generators import OpenAIGenerator
from haystack.utils import Secret
from loguru import logger as log

from components.content_extraction import build_content_extraction_component


class PipelineWrapper(BasePipelineWrapper):
    """This pipeline extracts content from a URL and sends it to a model that can
    summarize or answer questions on the content.

    Input: a URL
    Output: The documents
    """

    def setup(self) -> None:
        self.pipeline = self.create_pipeline()

    def create_pipeline(self) -> Pipeline:
        default_user_agent = os.getenv(
            "HAYHOOKS_EXTRACT_USER_AGENT",
            "SearchAgent.extract @ https://github.com/wsargent/groundedllm",
        )
        use_http2 = bool(os.getenv("HAYHOOKS_EXTRACT_HTTP2", "true"))
        retry_attempts = int(os.getenv("HAYHOOKS_EXTRACT_RETRY_ATTEMPTS", "3"))
        timeout = int(os.getenv("HAYHOOKS_EXTRACT_TIMEOUT", "3"))
        raise_on_failure = bool(os.getenv("HAYHOOKS_EXTRACT_RAISE_ON_FAILURE", "true").lower() == "true")
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
        and returns the content, using Markdown if possible.

        If given a youtube URL, it will return the transcript.

        Parameters
        ----------
        url: str
            The URL of the page to extract

        Returns
        -------
        str
            The JSON serialization of documents associated with the page, or a problem JSON.
        """
        log.info(f"Running Extract pipeline with URL: {url}")

        try:
            result = self.pipeline.run({"content_extractor": {"urls": [url]}})

            documents: Optional[List[haystack.Document]] = None
            if "content_extractor" in result:
                content_extractor = result["content_extractor"]
                documents: List[haystack.Document] = content_extractor["documents"]
            else:
                log.error(f"No contents found for url: {url} ", result)

            contents = None
            if documents:
                contents = [doc.content for doc in documents]

            if contents is None:
                problem = {"type": "urn:hayhooks:extract:error", "title": "No content extracted", "status": "404", "detail": f"There is no good way to extract the contents of url {url}, i.e. it may be a video that has no available transcript."}
                return json.dumps(problem)

            return json.dumps(contents)
        except Exception as e:
            log.exception(f"Error extracting content from {url}", e)
            problem = {"type": "urn:hayhooks:extract:error", "title": "Exception", "status": "500", "detail": f"Error extracting content from {url}: {str(e)}"}
            return json.dumps(problem)
