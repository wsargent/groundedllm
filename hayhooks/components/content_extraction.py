from haystack import Pipeline, SuperComponent
from haystack.components.converters import (
    MarkdownToDocument,
    PyPDFToDocument,
    TextFileToDocument,
    HTMLToDocument,
    CSVToDocument,
)
from haystack.components.fetchers import LinkContentFetcher
from haystack.components.preprocessors import DocumentCleaner
from haystack.components.joiners import DocumentJoiner
from haystack.components.routers import FileTypeRouter
from haystack import AsyncPipeline

def build_content_extraction_component() -> SuperComponent:
    """
    Builds a Haystack SuperComponent responsible for fetching content from URLs,
    determining file types, converting them to Documents, joining them,
    and cleaning them.

    Returns:
        A SuperComponent ready to be added to a pipeline.
        Input: urls (List[str])
        Output: documents (List[Document])
    """

    # https://docs.haystack.deepset.ai/reference/pipeline-api#asyncpipeline
    preprocessing_pipeline = AsyncPipeline()

    # There is a note in the 2.12 highlights
    # "Introduced asynchronous functionality and HTTP/2 support in the LinkContentFetcher component,
    # thus improving content fetching in several aspects."
    # Not clear if this needs some config options to use async functionality.
    fetcher = LinkContentFetcher(http2=True)
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
    additional_mimetypes = {
        "text/mdx": ".mdx"
    }

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
    preprocessing_pipeline.connect("file_type_router.text/mdx", "mdx_converter.sources") # Route mdx to markdown converter
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
        output_mapping={"document_cleaner.documents": "documents"}
    )
    return extraction_component
