from typing import Optional

from haystack import Document, Pipeline, component, super_component
from loguru import logger as logger

from components.content_extraction import ContentExtractionComponent


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

        for content_doc in content_documents:
            url = get_url(content_doc)
            if url:
                extracted_content[url] = content_doc.content

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


@super_component
class DocumentContentExtractor:
    """Fetches URLs from a list of documents and extract the contents of the pages"""

    # if TYPE_CHECKING:
    #     def run(self, *, documents: List[Document]) -> dict[str, list[Document]]:
    #         ...

    def __init__(
        self,
        raise_on_failure: bool = True,
        user_agents: Optional[list[str]] = None,
        retry_attempts: int = 2,
        timeout: int = 3,
        http2: bool = False,
    ):
        pipe = Pipeline()

        content_extraction_component = ContentExtractionComponent(raise_on_failure=raise_on_failure, user_agents=user_agents, retry_attempts=retry_attempts, timeout=timeout, http2=http2)

        extract_urls_adapter = ExtractUrls()
        content_joiner = JoinWithContent()

        pipe.add_component("extract_urls_adapter", extract_urls_adapter)
        pipe.add_component("content_extractor", content_extraction_component)
        pipe.add_component("content_joiner", content_joiner)

        # OutputAdapter always has dict with "output" as the key
        pipe.connect("extract_urls_adapter.urls", "content_extractor.urls")
        pipe.connect("content_extractor.documents", "content_joiner.content_documents")

        self.pipeline = pipe

        # Input and output mapping for the supercomponent
        self.input_mapping = {"documents": ["extract_urls_adapter.documents", "content_joiner.scored_documents"]}
        self.output_mapping = {"content_joiner.documents": "documents"}
