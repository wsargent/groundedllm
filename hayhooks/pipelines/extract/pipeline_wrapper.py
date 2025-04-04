from hayhooks.server.logger import log
from hayhooks.server.utils.base_pipeline_wrapper import BasePipelineWrapper
from typing import Generator, List, Union, Dict, Any

from haystack import Pipeline, Document
from haystack.components.fetchers import LinkContentFetcher
from haystack.components.converters import HTMLToDocument
from haystack.components.preprocessors import DocumentCleaner


class PipelineWrapper(BasePipelineWrapper):
    """
    A Haystack pipeline wrapper that fetches content from URLs, converts HTML to Documents,
    and extracts the text content.

    Input: A single URL string.
    Output: The extracted text content of the webpage as a string.
    """

    # TODO: Add support for PDF extraction using components like PyPDFToDocumentConverter
    # from haystack.components.converters import PyPDFToDocumentConverter

    def create_pipeline(self) -> Pipeline:
        fetcher = LinkContentFetcher()
        converter = HTMLToDocument()
        cleaner = DocumentCleaner()

        pipe = Pipeline()
        pipe.add_component("fetcher", fetcher)
        pipe.add_component("converter", converter)
        pipe.add_component("cleaner", cleaner)
        pipe.connect("fetcher.streams", "converter.sources")
        pipe.connect("converter.documents", "cleaner.documents")

        return pipe

    def create_pipeline_args(self, urls: List[str]) -> Dict[str, Dict[str, Any]]:
        return {"fetcher": {"urls": urls}}

    def setup(self) -> None:
        self.pipeline = self.create_pipeline()
        
    def run_api(self, url: str) -> str:
        """
        This tool takes a URL and returns the markdown of the page.

        Parameters
        ----------
        url: str
            The URL of the page to extract.

        Returns
        -------
        str
            The markdown content of the page, or an error message.
        """
        log.debug(f"Running Extract pipeline with URL: {url}")
        if not hasattr(self, 'pipeline') or not self.pipeline:
             raise RuntimeError("Pipeline not initialized during setup.")

        pipeline_args = self.create_pipeline_args([url])
        result = self.pipeline.run(pipeline_args)

        documents: List[Document] = result["cleaner"]["documents"]
        content = documents[0].content
        return content
