import logging
import os
from typing import List, Any  # Added Any
import json
from urllib.parse import urlparse

from haystack.components.converters import MarkdownToDocument, PyPDFToDocument, TextFileToDocument
from haystack.components.converters.csv import CSVToDocument

from hayhooks.server.logger import log
from hayhooks.server.utils.base_pipeline_wrapper import BasePipelineWrapper
from haystack.components.joiners import DocumentJoiner
from haystack.components.routers import FileTypeRouter

from haystack import Pipeline, SuperComponent
from haystack.components.builders.prompt_builder import PromptBuilder
from haystack.components.converters import HTMLToDocument
from haystack.components.fetchers import LinkContentFetcher
from haystack.components.generators import OpenAIGenerator
from haystack.components.preprocessors import DocumentCleaner
from haystack.utils import Secret

from resources.utils import read_resource_file

logger = logging.getLogger("extract")

class PipelineWrapper(BasePipelineWrapper):
    """
    This pipeline extracts content from a URL and sends it to a model that can
    summarize or answer questions on the content.

    Input: A list of URLs.
    Output: The answer based on the contents of the URLs.
    """

    def setup(self) -> None:
        self.template = read_resource_file("extract_prompt.md")
        self.pipeline = self.create_pipeline()

    def create_extractor_pipeline(self):
        preprocessing_pipeline = Pipeline()
        fetcher = LinkContentFetcher()
        document_cleaner = DocumentCleaner()

        # Letta has text/mdx for some reason :-/
        mime_types = [
          "text/plain",
          "text/html",
          "text/csv",
          "text/markdown",
          "text/mdx",
          "application/pdf"
        ]
        additional_mimetypes = {
          "text/mdx": ".mdx"
        }
        file_type_router = FileTypeRouter(mime_types=mime_types,
                                          additional_mimetypes=additional_mimetypes)
        text_file_converter = TextFileToDocument()
        html_converter = HTMLToDocument()
        markdown_converter = MarkdownToDocument()
        mdx_converter = MarkdownToDocument()
        pdf_converter = PyPDFToDocument()
        csv_converter = CSVToDocument()
        #docx_converter = DOCXToDocument(table_format=DOCXTableFormat.CSV)
        document_joiner = DocumentJoiner()

        preprocessing_pipeline.add_component(instance=fetcher, name="fetcher")
        preprocessing_pipeline.add_component(instance=file_type_router, name="file_type_router")

        preprocessing_pipeline.add_component(instance=text_file_converter, name="text_file_converter")
        preprocessing_pipeline.add_component(instance=markdown_converter, name="markdown_converter")
        preprocessing_pipeline.add_component(instance=html_converter, name="html_converter")
        preprocessing_pipeline.add_component(instance=pdf_converter, name="pypdf_converter")
        preprocessing_pipeline.add_component(instance=csv_converter, name="csv_converter")
        #preprocessing_pipeline.add_component(instance=docx_converter, name="docx_converter")
        preprocessing_pipeline.add_component(instance=mdx_converter, name="mdx_converter")

        preprocessing_pipeline.add_component(instance=document_joiner, name="document_joiner")
        preprocessing_pipeline.add_component(instance=document_cleaner, name="document_cleaner")

        # Could this be an async pipeline?
        preprocessing_pipeline.connect("fetcher.streams", "file_type_router.sources")

        preprocessing_pipeline.connect("file_type_router.text/plain", "text_file_converter.sources")
        preprocessing_pipeline.connect("file_type_router.text/html", "html_converter.sources")
        preprocessing_pipeline.connect("file_type_router.text/csv", "csv_converter.sources")
        preprocessing_pipeline.connect("file_type_router.application/pdf", "pypdf_converter.sources")
        preprocessing_pipeline.connect("file_type_router.text/markdown", "markdown_converter.sources")
        preprocessing_pipeline.connect("file_type_router.text/mdx", "mdx_converter.sources")

        preprocessing_pipeline.connect("text_file_converter", "document_joiner")
        preprocessing_pipeline.connect("html_converter", "document_joiner")
        preprocessing_pipeline.connect("csv_converter", "document_joiner")
        preprocessing_pipeline.connect("pypdf_converter", "document_joiner")
        preprocessing_pipeline.connect("markdown_converter", "document_joiner")
        preprocessing_pipeline.connect("mdx_converter", "document_joiner")

        preprocessing_pipeline.connect("document_joiner", "document_cleaner")

        extraction_component = SuperComponent(
            pipeline=preprocessing_pipeline,
            input_mapping={"urls": ["fetcher.urls"]},
            output_mapping={"document_cleaner.documents": "documents"},
        )
        return extraction_component

    def create_pipeline(self) -> Pipeline:
        prompt_builder = PromptBuilder(
            template=self.template, required_variables=["query"]
        )

        # Ideally I'd like to get the model at pipeline execution but
        # that's not an option here
        model = os.getenv("EXTRACT_MODEL")
        if model is None:
            raise ValueError("No model found in EXTRACT_MODEL environment variable!")
        llm = self.get_extract_generator(model)

        pipe = Pipeline()
        pipe.add_component("content_extractor", self.create_extractor_pipeline())
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
        """
        Cleans the input URLs. Handles cases where input might be a single string,
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
                    logger.warning(
                        f"Input string parsed as JSON but is not a list: {urls}. Treating as single URL."
                    )
                    potential_urls = [urls]
            except json.JSONDecodeError:
                # If not valid JSON, treat as a single URL string
                potential_urls = [urls]
        elif isinstance(urls, list):
            potential_urls = urls
        else:
            # If it's neither a string nor a list, return empty
            logger.warning(
                f"Invalid input type for URLs: {type(urls)}. Expected str or list. Input: {urls}"
            )
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
            logger.warning(
                f"No valid URLs found after cleaning. Original input: {urls}"
            )
        elif not cleaned_urls and not potential_urls:
            logger.warning(f"No URLs provided or input was invalid type: {urls}")

        return cleaned_urls

    def run_api(self, urls: List[str], question: str) -> str:
        """
        This tool fetches HTML, Markdown, PDF, or plain text web pages from URLs and sends them to an LLM model
        that can answer questions about the content of the web pages.

        It cannot handle audio, video, or binary content.

        Parameters
        ----------
        urls: List[str]
            The URLs of the pages to extract.
        question: str
            The instructions to give and questions to ask about the content of the web pages.

        Returns
        -------
        str
            The answer from the LLM model.
        """
        log.debug(f"Running Extract pipeline with URLs: {urls}")
        if not hasattr(self, "pipeline") or not self.pipeline:
            raise RuntimeError("Pipeline not initialized during setup.")

        clean_urls = self._clean_urls(urls)

        result = self.pipeline.run(
            {
                "content_extractor": {
                    "urls": clean_urls
                },
                "prompt_builder": {"query": question},
            }
        )
        if "llm" in result and "replies" in result["llm"] and result["llm"]["replies"]:
            reply = result["llm"]["replies"][0]
            logger.info(f"answer: reply is {reply}")
            return reply
        else:
            raise RuntimeError("Error: Could not retrieve answer from the pipeline.")
