from typing import Optional

from haystack import Document, Pipeline, SuperComponent, component
from haystack.components.converters import (
    CSVToDocument,
    HTMLToDocument,
    MarkdownToDocument,
    PyPDFToDocument,
    TextFileToDocument,
)
from haystack.components.fetchers import LinkContentFetcher
from haystack.components.joiners import DocumentJoiner
from haystack.components.preprocessors import DocumentCleaner
from haystack.components.routers import FileTypeRouter
from haystack.logging import getLogger

logger = getLogger("haystack.content_extraction")


@component
class ExtractUrls:
    @component.output_types(urls=list[str])
    def run(self, documents: list[Document]):
        return {"urls": [doc.meta["url"] for doc in documents]}


@component
class JoinWithContent:
    @component.output_types(documents=list[Document])
    def run(self, scored_documents: list[Document], content_documents: list[Document]):
        joined_documents = []
        extracted_content: dict[str, str] = {}
        for content_doc in content_documents:
            url = content_doc.meta["url"]
            extracted_content[url] = content_doc.content

        for scored_document in scored_documents:
            url = scored_document.meta["url"]
            score = scored_document.score
            logger.debug(f"run: processing document {url} with score {score}")
            if url in extracted_content:
                content = extracted_content[url]
            else:
                content = scored_document.content

            doc = Document.from_dict(
                {
                    "title": scored_document.meta["title"],
                    "content": content,
                    "url": url,
                    "score": score,
                }
            )
            joined_documents.append(doc)
        return {"documents": joined_documents}


def build_search_extraction_component(
    raise_on_failure: bool = True,
    user_agents: Optional[list[str]] = None,
    retry_attempts: int = 2,
    timeout: int = 3,
    http2: bool = False,
) -> SuperComponent:
    """Fetches URLs from a list of documents and extract the contents of the pages"""

    pipe = Pipeline()

    content_extraction_component = build_content_extraction_component(raise_on_failure=raise_on_failure, user_agents=user_agents, retry_attempts=retry_attempts, timeout=timeout, http2=http2)

    extract_urls_adapter = ExtractUrls()
    content_joiner = JoinWithContent()

    pipe.add_component("extract_urls_adapter", extract_urls_adapter)
    pipe.add_component("content_extractor", content_extraction_component)
    pipe.add_component("content_joiner", content_joiner)

    # OutputAdapter always has dict with "output" as the key
    pipe.connect("extract_urls_adapter.urls", "content_extractor.urls")
    pipe.connect("content_extractor.documents", "content_joiner.content_documents")

    extraction_component = SuperComponent(
        pipeline=pipe,
        input_mapping={"documents": ["extract_urls_adapter.documents", "content_joiner.scored_documents"]},
        output_mapping={"content_joiner.documents": "documents"},
    )
    return extraction_component


def build_content_extraction_component(
    raise_on_failure: bool = True,
    user_agents: Optional[list[str]] = None,
    retry_attempts: int = 2,
    timeout: int = 3,
    http2: bool = False,
) -> SuperComponent:
    """Builds a Haystack SuperComponent responsible for fetching content from URLs,
    determining file types, converting them to Documents, joining them,
    and cleaning them.

    Returns:
        A SuperComponent ready to be added to a pipeline.
        Input: urls (List[str])
        Output: documents (List[Document])

    """
    preprocessing_pipeline = Pipeline()

    # There is a note in the 2.12 highlights
    # "Introduced asynchronous functionality and HTTP/2 support in the LinkContentFetcher component,
    # thus improving content fetching in several aspects."
    # Not clear if this needs some config options to use async functionality.
    fetcher = LinkContentFetcher(
        raise_on_failure=raise_on_failure,
        user_agents=user_agents,
        retry_attempts=retry_attempts,
        timeout=timeout,
        http2=http2,
    )
    document_cleaner = DocumentCleaner()

    # Also see MultiFileConverter
    # https://haystack.deepset.ai/release-notes/2.12.0
    # https://github.com/deepset-ai/haystack-experimental/blob/main/haystack_experimental/super_components/converters/multi_file_converter.py
    # Define supported MIME types and any custom mappings
    mime_types = [
        "text/plain",
        "text/html",
        "text/csv",
        "text/markdown",
        "text/mdx",  # Letta uses this sometimes
        "application/pdf",
        # Add other types like docx if needed later
        # "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ]
    additional_mimetypes = {"text/mdx": ".mdx"}

    file_type_router = FileTypeRouter(mime_types=mime_types, additional_mimetypes=additional_mimetypes)
    text_file_converter = TextFileToDocument()
    html_converter = HTMLToDocument()
    markdown_converter = MarkdownToDocument()
    mdx_converter = MarkdownToDocument()  # Treat mdx as markdown
    pdf_converter = PyPDFToDocument()
    csv_converter = CSVToDocument()
    # docx_converter = DOCXToDocument() # If needed later
    document_joiner = DocumentJoiner()

    # Add components to the internal pipeline
    preprocessing_pipeline.add_component(instance=fetcher, name="fetcher")
    preprocessing_pipeline.add_component(instance=file_type_router, name="file_type_router")
    preprocessing_pipeline.add_component(instance=text_file_converter, name="text_file_converter")
    preprocessing_pipeline.add_component(instance=markdown_converter, name="markdown_converter")
    preprocessing_pipeline.add_component(instance=html_converter, name="html_converter")
    preprocessing_pipeline.add_component(instance=pdf_converter, name="pypdf_converter")
    preprocessing_pipeline.add_component(instance=csv_converter, name="csv_converter")
    # preprocessing_pipeline.add_component(instance=docx_converter, name="docx_converter") # If needed later
    preprocessing_pipeline.add_component(instance=mdx_converter, name="mdx_converter")
    preprocessing_pipeline.add_component(instance=document_joiner, name="document_joiner")
    preprocessing_pipeline.add_component(instance=document_cleaner, name="document_cleaner")

    # Connect the components
    preprocessing_pipeline.connect("fetcher.streams", "file_type_router.sources")

    preprocessing_pipeline.connect("file_type_router.text/plain", "text_file_converter.sources")
    preprocessing_pipeline.connect("file_type_router.text/html", "html_converter.sources")
    preprocessing_pipeline.connect("file_type_router.text/csv", "csv_converter.sources")
    preprocessing_pipeline.connect("file_type_router.application/pdf", "pypdf_converter.sources")
    preprocessing_pipeline.connect("file_type_router.text/markdown", "markdown_converter.sources")
    preprocessing_pipeline.connect("file_type_router.text/mdx", "mdx_converter.sources")  # Route mdx to markdown converter
    # preprocessing_pipeline.connect("file_type_router.application/vnd.openxmlformats-officedocument.wordprocessingml.document", "docx_converter.sources") # If needed later

    preprocessing_pipeline.connect("text_file_converter", "document_joiner")
    preprocessing_pipeline.connect("html_converter", "document_joiner")
    preprocessing_pipeline.connect("csv_converter", "document_joiner")
    preprocessing_pipeline.connect("pypdf_converter", "document_joiner")
    preprocessing_pipeline.connect("markdown_converter", "document_joiner")
    preprocessing_pipeline.connect("mdx_converter", "document_joiner")
    # preprocessing_pipeline.connect("docx_converter", "document_joiner") # If needed later

    preprocessing_pipeline.connect("document_joiner", "document_cleaner")

    extraction_component = SuperComponent(
        pipeline=preprocessing_pipeline,
        input_mapping={"urls": ["fetcher.urls"]},
        output_mapping={"document_cleaner.documents": "documents"},
    )
    return extraction_component
