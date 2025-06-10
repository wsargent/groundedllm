import os
from typing import Optional

from haystack import Pipeline, super_component
from haystack.components.converters import CSVToDocument, HTMLToDocument, MarkdownToDocument, PyPDFToDocument, TextFileToDocument
from haystack.components.joiners import DocumentJoiner
from haystack.components.preprocessors import DocumentCleaner
from haystack.components.routers import FileTypeRouter

from components.google.google_oauth import GoogleOAuth
from components.notion import NotionContentResolver
from components.resolver import GenericURLContentResolver, URLContentRouter
from components.stackoverflow import StackOverflowContentResolver
from components.youtube_transcript import YouTubeTranscriptResolver
from components.zotero import ZoteroContentResolver


@super_component
class ContentExtractionComponent:
    """Builds a Haystack SuperComponent responsible for fetching content from URLs,
    determining file types, converting them to Documents, joining them,
    and cleaning them.

    Input: urls (List[str])
    Output: documents (List[Document])
    """

    def __init__(
        self,
        raise_on_failure: bool = True,
        user_agents: Optional[list[str]] = None,
        retry_attempts: int = 2,
        timeout: int = 3,
        http2: bool = False,
    ):
        preprocessing_pipeline = Pipeline()

        # Create resolvers
        stackoverflow_resolver = StackOverflowContentResolver(
            raise_on_failure=raise_on_failure,
            timeout=timeout,
        )

        zotero_resolver = ZoteroContentResolver(
            raise_on_failure=raise_on_failure,
            timeout=timeout,
        )

        # Add more domain-specific resolvers here as needed
        # github_resolver = GitHubContentResolver(...)
        # medium_resolver = MediumContentResolver(...)

        # Generic resolver as fallback
        generic_resolver = GenericURLContentResolver(
            raise_on_failure=raise_on_failure,
            user_agents=user_agents,
            retry_attempts=retry_attempts,
            timeout=timeout,
            http2=http2,
            jina_timeout=10,
            jina_retry_attempts=2,
        )

        user_id = os.environ.get("HAYHOOKS_USER_ID", "me")
        google_oauth = GoogleOAuth()

        # Create YouTube transcript resolver
        youtube_resolver = YouTubeTranscriptResolver(
            oauth_provider=google_oauth,
            raise_on_failure=raise_on_failure,
            user_id=user_id,
        )

        notion_resolver = NotionContentResolver(raise_on_failure=raise_on_failure)

        # Create router with all resolvers (generic resolver must be last)
        url_router = URLContentRouter(
            resolvers=[
                stackoverflow_resolver,
                zotero_resolver,
                youtube_resolver,
                notion_resolver,
                generic_resolver,  # Must be last
            ]
        )

        document_cleaner = DocumentCleaner()

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
        preprocessing_pipeline.add_component(instance=url_router, name="url_router")
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
        preprocessing_pipeline.connect("url_router.streams", "file_type_router.sources")

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

        self.pipeline = preprocessing_pipeline

        # Input and output mapping for the supercomponent
        self.input_mapping = {"urls": ["url_router.urls"]}
        self.output_mapping = {"document_cleaner.documents": "documents"}


def build_content_extraction_component(
    raise_on_failure: bool = True,
    user_agents: Optional[list[str]] = None,
    retry_attempts: int = 2,
    timeout: int = 3,
    http2: bool = False,
) -> ContentExtractionComponent:
    """Builds a Haystack SuperComponent responsible for fetching content from URLs,
    determining file types, converting them to Documents, joining them,
    and cleaning them.

    This function is kept for backward compatibility.

    Returns:
        A ContentExtractionComponent ready to be added to a pipeline.
        Input: urls (List[str])
        Output: documents (List[Document])
    """
    return ContentExtractionComponent(
        raise_on_failure=raise_on_failure,
        user_agents=user_agents,
        retry_attempts=retry_attempts,
        timeout=timeout,
        http2=http2,
    )
