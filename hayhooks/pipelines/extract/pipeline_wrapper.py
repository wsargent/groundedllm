import logging
import os
from typing import List

from hayhooks.server.logger import log
from hayhooks.server.utils.base_pipeline_wrapper import BasePipelineWrapper
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
    This pipeline extracts HTML content from a URL and sends it to a model that can
    summarize or answer questions on the content.

    Input: A list of URLs.
    Output: The answer based on the contents of the URLs.
    """

    # TODO: Add support for PDF extraction using components like PyPDFToDocumentConverter
    # from haystack.components.converters import PyPDFToDocumentConverter

    def setup(self) -> None:
        self.template = read_resource_file("extract_prompt.md")
        self.pipeline = self.create_pipeline()

    def create_extractor_pipeline(self):
        extraction_sub_pipeline = Pipeline()
        fetcher = LinkContentFetcher()
        converter = HTMLToDocument()
        cleaner = DocumentCleaner()
        extraction_sub_pipeline.add_component("fetcher", fetcher)
        extraction_sub_pipeline.add_component("converter", converter)
        extraction_sub_pipeline.add_component("cleaner", cleaner)

        extraction_sub_pipeline.connect("fetcher.streams", "converter.sources")
        extraction_sub_pipeline.connect("converter.documents", "cleaner.documents")

        extraction_component = SuperComponent(
            pipeline=extraction_sub_pipeline,
            input_mapping={"urls": ["fetcher.urls"]},
            output_mapping={"cleaner.documents": "documents"}
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
        pipe.add_component("html_extractor", self.create_extractor_pipeline())
        pipe.add_component("prompt_builder", prompt_builder)
        pipe.add_component("llm", llm)

        pipe.connect("html_extractor.documents", "prompt_builder.documents")
        pipe.connect("prompt_builder", "llm")

        return pipe

    def get_extract_generator(self, model) -> OpenAIGenerator:
        return OpenAIGenerator(
            api_key=Secret.from_env_var("OPENAI_API_KEY"),
            api_base_url=os.getenv("OPENAI_API_BASE"),
            model=model
        )

    def run_api(self, urls: List[str], question: str) -> str:
        """
        This tool fetches HTML web page from URLs and sends them to an LLM model
        that can answer questions about the content of the web pages.

        It cannot handle video or PDF.

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


        result = self.pipeline.run(
            {
                "html_extractor": {"urls": urls}, # extraction bit, this can be async
             "prompt_builder": {"query": question}
         }
        )
        if "llm" in result and "replies" in result["llm"] and result["llm"]["replies"]:
            reply = result["llm"]["replies"][0]
            logger.info(f"answer: reply is {reply}")
            return reply
        else:
            raise RuntimeError("Error: Could not retrieve answer from the pipeline.")
