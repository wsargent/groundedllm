from typing import Optional

from haystack import Pipeline, SuperComponent
from haystack.components.converters import (
    CSVToDocument,
    HTMLToDocument,
    MarkdownToDocument,
    OutputAdapter,
    PyPDFToDocument,
    TextFileToDocument,
)
from haystack.components.fetchers import LinkContentFetcher
from haystack.components.joiners import DocumentJoiner
from haystack.components.preprocessors import DocumentCleaner
from haystack.components.routers import FileTypeRouter


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

    extract_urls_template = """[{% for doc in documents %}"{{ doc.meta.link }}"{% if not loop.last %},{% endif %}{% endfor %}]"""
    extract_content_template = """[{% for doc in documents %}"{{ doc.content }}"{% if not loop.last %},{% endif %}{% endfor %}]"""

    extract_urls_adapter = OutputAdapter(template=extract_urls_template, output_type=list[str])
    extract_content_adapter = OutputAdapter(
        template=extract_content_template,
        output_type=list[str],
    )

    pipe.add_component("extract_urls_adapter", extract_urls_adapter)
    pipe.add_component("content_extractor", content_extraction_component)
    pipe.add_component("extract_content_adapter", extract_content_adapter)

    # OutputAdapter always has dict with "output" as the key
    pipe.connect("extract_urls_adapter.output", "content_extractor.urls")
    pipe.connect("content_extractor.documents", "extract_content_adapter.documents")

    extraction_component = SuperComponent(
        pipeline=pipe,
        input_mapping={"documents": ["extract_urls_adapter.documents"]},
        output_mapping={"extract_content_adapter.output": "contents"},
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
        Input: urls (List[str]) or documents (List[documents])
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
