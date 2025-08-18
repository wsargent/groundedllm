import os
from typing import Any, Dict, List, Optional

from hayhooks import log as logger
from haystack import Document, Pipeline, SuperComponent, component
from haystack.components.converters import (
    CSVToDocument,
    HTMLToDocument,
    MarkdownToDocument,
    PyPDFToDocument,
    TextFileToDocument,
)
from haystack.components.joiners import DocumentJoiner
from haystack.components.preprocessors import DocumentCleaner
from haystack.components.routers import FileTypeRouter
from haystack.dataclasses import ByteStream
from haystack.utils import Secret

from components.fetchers import ContentFetcherResolver
from components.github import GithubIssueContentResolver, GithubPRContentResolver, GithubRepoContentResolver
from components.google.google_oauth import GoogleOAuth
from components.notion import NotionContentResolver
from components.stackoverflow import StackOverflowContentResolver
from components.youtube_transcript import YouTubeTranscriptResolver
from components.zotero import ZoteroContentResolver


@component
class URLContentRouter:
    """A component that routes URLs to the appropriate resolver."""

    def __init__(self, resolvers: List[Any]):
        """Initialize the URL router.

        Args:
            resolvers (List[Any]): A list of URL content resolvers.
        """
        self.resolvers = resolvers
        # The last resolver should be the generic one that can handle any URL
        self.generic_resolver = resolvers[-1]

    @component.output_types(streams=List[ByteStream])
    def run(self, urls: List[str]):
        """Route URLs to the appropriate resolver and fetch their content.

        Args:
            urls (List[str]): A list of URLs to fetch content from.

        Returns:
            Dict[str, List[ByteStream]]: A dictionary with a "streams" key containing a list of ByteStream objects.
        """
        # Group URLs by resolver
        resolver_urls: Dict[Any, List[str]] = {}

        for url in urls:
            resolver = self._find_resolver(url)
            if resolver not in resolver_urls:
                resolver_urls[resolver] = []
            resolver_urls[resolver].append(url)

        # Fetch content using each resolver
        all_streams = []

        for resolver, urls in resolver_urls.items():
            try:
                result = resolver.run(urls)
                if "streams" in result:
                    streams = result["streams"]
                    all_streams.extend(streams)
                else:
                    logger.debug(f"No streams found for {resolver}")
            except Exception:
                logger.exception(f"Exception in {resolver} run with {urls}")

        return {"streams": all_streams}

    def _find_resolver(self, url: str) -> Any:
        """Find the appropriate resolver for the given URL.

        Args:
            url (str): The URL to find a resolver for.

        Returns:
            Any: The resolver that can handle the URL.
        """
        for resolver in self.resolvers:
            if resolver.can_handle(url):
                return resolver

        # This should never happen since the generic resolver can handle any URL
        return self.generic_resolver


@component
class ExtractUrls:
    @component.output_types(urls=list[str])
    def run(self, documents: list[Document]):
        urls = []
        for doc in documents:
            # Check for both "url" and "link" keys in the document meta
            if "url" in doc.meta:
                urls.append(doc.meta["url"])
            elif "link" in doc.meta:
                urls.append(doc.meta["link"])
        return {"urls": urls}


@component
class JoinWithContent:
    @component.output_types(documents=list[Document])
    def run(self, scored_documents: list[Document], content_documents: list[Document]):
        joined_documents = []
        extracted_content: dict[str, str] = {}

        # Helper function to get URL from document meta
        def get_url(doc):
            if "url" in doc.meta:
                return doc.meta["url"]
            elif "link" in doc.meta:
                return doc.meta["link"]
            return None

        # If the content extraction produced invalid documents, skip them and
        # use the original scored ones.
        for content_doc in content_documents:
            content = content_doc.content
            if content is None:
                logger.warning(f"No content found in {content_doc}, skipping")
                continue

            if len(content.strip()) == 0:
                logger.warning(f"Empty content found in {content_doc}, skipping")
                continue

            url = get_url(content_doc)
            if url is None:
                logger.warning(f"No url found in {content_doc}, skipping")
                continue

            extracted_content[url] = content

        for scored_document in scored_documents:
            url = get_url(scored_document)
            if not url:
                continue  # Skip documents without URL or link

            score = scored_document.score
            logger.debug(f"run: processing document {url} with score {score}")

            if url in extracted_content:
                content = extracted_content[url]
            else:
                content = scored_document.content

            doc = Document.from_dict(
                {
                    "title": scored_document.meta.get("title", "Untitled"),
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

    # Create resolvers
    stackoverflow_resolver = StackOverflowContentResolver(
        raise_on_failure=raise_on_failure,
        timeout=timeout,
    )

    zotero_resolver = ZoteroContentResolver(
        raise_on_failure=raise_on_failure,
        timeout=timeout,
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

    github_token = None
    if os.getenv("GITHUB_API_KEY"):
        github_token = Secret.from_env_var("GITHUB_API_KEY")
    github_issue_resolver = GithubIssueContentResolver(
        github_token=github_token,  # use api key to get private content and avoid rate limits
        raise_on_failure=raise_on_failure,
    )

    github_repo_resolver = GithubRepoContentResolver(
        github_token=github_token,  # use api key to get private content and avoid rate limits
        raise_on_failure=raise_on_failure,
    )

    github_pr_resolver = GithubPRContentResolver(
        github_token=github_token,  # use api key to get private content and avoid rate limits
        raise_on_failure=raise_on_failure,
    )

    # Content fetcher resolver as fallback, this just handles generic URLs
    content_fetcher_resolver = ContentFetcherResolver(raise_on_failure=raise_on_failure)

    # Create router with all resolvers (generic resolver must be last)
    url_router = URLContentRouter(
        resolvers=[
            stackoverflow_resolver,
            zotero_resolver,
            youtube_resolver,
            notion_resolver,
            github_issue_resolver,
            github_pr_resolver,
            github_repo_resolver,
            content_fetcher_resolver,  # Must be last
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

    # This should use MultiFileConverter
    file_type_router = FileTypeRouter(mime_types=mime_types, additional_mimetypes=additional_mimetypes)
    text_file_converter = TextFileToDocument()
    html_converter = HTMLToDocument()
    markdown_converter = MarkdownToDocument()
    mdx_converter = MarkdownToDocument()  # Treat mdx as markdown
    pdf_converter = PyPDFToDocument()
    csv_converter = CSVToDocument()
    # docx_converter = DOCXToDocument() # If needed later
    document_joiner = DocumentJoiner()

    # Should add warnings to this so it doesn't just fall through
    unclassified_file_converter = TextFileToDocument()

    # Add components to the internal pipeline
    preprocessing_pipeline.add_component(instance=url_router, name="url_router")
    preprocessing_pipeline.add_component(instance=file_type_router, name="file_type_router")
    preprocessing_pipeline.add_component(instance=unclassified_file_converter, name="unclassified_file_converter")
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
    preprocessing_pipeline.connect("file_type_router.unclassified", "unclassified_file_converter.sources")  # Route unclassified to text converter as fallback
    # preprocessing_pipeline.connect("file_type_router.application/vnd.openxmlformats-officedocument.wordprocessingml.document", "docx_converter.sources") # If needed later

    preprocessing_pipeline.connect("unclassified_file_converter", "document_joiner")
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
        input_mapping={"urls": ["url_router.urls"]},
        output_mapping={"document_cleaner.documents": "documents"},
    )
    return extraction_component
