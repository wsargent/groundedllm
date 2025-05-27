import json
import os
from typing import Any, List
from urllib.parse import urlparse

from hayhooks import log as logger
from hayhooks.server.utils.base_pipeline_wrapper import BasePipelineWrapper
from haystack import Pipeline
from haystack.components.builders.prompt_builder import PromptBuilder
from haystack.components.generators import OpenAIGenerator
from haystack.utils import Secret

from components.content_extraction import build_content_extraction_component
from resources.utils import read_resource_file


class PipelineWrapper(BasePipelineWrapper):
    """This pipeline extracts content from a URL and sends it to a model that can
    summarize or answer questions on the content.

    Input: A list of URLs.
    Output: The answer based on the contents of the URLs.
    """

    def __init__(self):
        super().__init__()
        self.template = read_resource_file("excerpt_prompt.md")

    def setup(self) -> None:
        self.pipeline = self.create_pipeline()

    def create_pipeline(self) -> Pipeline:
        prompt_builder = PromptBuilder(template=self.template, required_variables=["query", "documents"])

        # Ideally I'd like to get the model at pipeline execution but
        # that's not an option here
        model = os.getenv("HAYHOOKS_EXCERPT_MODEL")
        if model is None or model == "":
            raise ValueError("No model found in HAYHOOKS_EXCERPT_MODEL environment variable!")
        llm = self.get_extract_generator(model)

        logger.info(f"Using excerpt model: {model}")

        default_user_agent = os.getenv(
            "EXCERPT_USER_AGENT",
            "SearchAgent.excerpt @ https://github.com/wsargent/groundedllm",
        )
        use_http2 = bool(os.getenv("EXCERPT_HTTP2", "true"))
        retry_attempts = int(os.getenv("EXCERPT_RETRY_ATTEMPTS", "3"))
        timeout = int(os.getenv("EXCERPT_TIMEOUT", "3"))
        raise_on_failure = bool(os.getenv("EXCERPT_RAISE_ON_FAILURE", "False"))
        content_extractor = build_content_extraction_component(
            raise_on_failure=raise_on_failure,
            user_agents=[default_user_agent],
            retry_attempts=retry_attempts,
            timeout=timeout,
            http2=use_http2,
        )

        pipe = Pipeline()
        pipe.add_component("content_extractor", content_extractor)
        pipe.add_component("prompt_builder", prompt_builder)
        pipe.add_component("llm", llm)

        pipe.connect("content_extractor.documents", "prompt_builder.documents")
        pipe.connect("prompt_builder", "llm")

        return pipe

    def get_extract_generator(self, model) -> OpenAIGenerator:
        return OpenAIGenerator(
            api_key=Secret.from_env_var("OPENAI_API_KEY"),
            api_base_url=os.getenv("OPENAI_API_BASE"),
            model=model,
        )

    def _clean_urls(self, urls: Any) -> List[str]:
        """Cleans the input URLs. Handles cases where input might be a single string,
        a JSON string representation of a list, or a list containing non-URL strings.

        Args:
            urls: The input, which could be a list of strings, a single URL string,
                  or a JSON string representing a list of URLs.

        Returns:
            A list of validated URL strings.

        """
        cleaned_urls: List[str] = []
        potential_urls: List[Any] = []

        if isinstance(urls, str):
            try:
                # Attempt to parse as JSON list first
                parsed_urls = json.loads(urls)
                if isinstance(parsed_urls, list):
                    potential_urls = parsed_urls
                else:
                    # If JSON parsed but not a list, treat original string as single URL
                    logger.warning(f"Input string parsed as JSON but is not a list: {urls}. Treating as single URL.")
                    potential_urls = [urls]
            except json.JSONDecodeError:
                # If not valid JSON, treat as a single URL string
                potential_urls = [urls]
        elif isinstance(urls, list):
            potential_urls = urls
        else:
            # If it's neither a string nor a list, return empty
            logger.warning(f"Invalid input type for URLs: {type(urls)}. Expected str or list. Input: {urls}")
            return []

        for item in potential_urls:
            if not isinstance(item, str):
                logger.warning(f"Skipping non-string item in URL list: {item}")
                continue
            try:
                # Basic check for empty strings or whitespace
                if not item or item.isspace():
                    logger.warning(f"Skipping empty or whitespace string: '{item}'")
                    continue

                parsed = urlparse(item)
                # Check for scheme (http, https) and netloc (domain name)
                if parsed.scheme in ["http", "https"] and parsed.netloc:
                    cleaned_urls.append(item)
                else:
                    logger.warning(f"Skipping invalid or non-HTTP/S URL: {item}")
            except Exception as e:  # Catch potential errors during parsing
                logger.warning(f"Error parsing potential URL '{item}': {e}")

        if not cleaned_urls and potential_urls:
            logger.warning(f"No valid URLs found after cleaning. Original input: {urls}")
        elif not cleaned_urls and not potential_urls:
            logger.warning(f"No URLs provided or input was invalid type: {urls}")

        return cleaned_urls

    def run_api(self, urls: List[str], question: str) -> str:
        """Extract pages from URLs and answers questions about the pages.

        This tool will fetch HTML, Markdown, PDF, or plain text web pages from URLs.
        and sends them to an LLM model that can answer questions about the content of the
        web pages. If given a URL to a youtube video, it will use the transcript as input
        to the LLM.

        Parameters
        ----------
        urls: List[str]
            The URLs of the pages to extract.
        question: str
            The instructions to give and questions to ask about the web pages.

        Returns
        -------
        str
            The answer from the LLM model.

        """

        try:
            logger.debug(f"Running EXCERPT pipeline with URLs: {urls}")
            if not hasattr(self, "pipeline") or not self.pipeline:
                raise RuntimeError("Pipeline not initialized during setup.")

            clean_urls = self._clean_urls(urls)

            result = self.pipeline.run(
                {
                    "content_extractor": {"urls": clean_urls},
                    "prompt_builder": {"query": question},
                }
            )

            if "llm" in result and "replies" in result["llm"] and result["llm"]["replies"]:
                reply = result["llm"]["replies"][0]
                logger.info(f"answer: reply is {reply}")
                return reply
            else:
                raise RuntimeError("Error: Could not retrieve answer from the pipeline.")
        except Exception as e:
            return f"Error: {e}"
