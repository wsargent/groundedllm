import re
from typing import Dict, List

from hayhooks import log as logger
from haystack import component
from haystack.dataclasses.byte_stream import ByteStream
from haystack.dataclasses.document import Document
from haystack.utils.auth import Secret
from notion_haystack import NotionExporter


@component
class NotionContentResolver:
    def __init__(self, api_key: Secret = Secret.from_env_var("NOTION_API_KEY"), raise_on_failure: bool = False):
        self.exporter = None
        self.raise_on_failure = raise_on_failure
        try:
            api_key_value = api_key.resolve_value()
            if api_key_value:
                self.exporter = NotionExporter(api_token=api_key_value)
        except Exception as e:
            logger.error(f"Error initializing NotionContentResolver: {e}")

        if self.exporter is None:
            logger.info("NOTION_API_KEY is not initialized. Notion integration is disabled.")

    def _extract_page_ids(self, urls: List[str]) -> List[str]:
        """Extract Notion page IDs from URLs.

        Notion page IDs are 32-character hexadecimal strings, sometimes with hyphens.
        They appear in URLs like https://www.notion.so/{workspace}/{page-id} or
        https://www.notion.so/{page-id}

        Args:
            urls (List[str]): List of Notion URLs

        Returns:
            List[str]: List of extracted page IDs
        """
        page_ids = []
        for url in urls:
            # Look for a 32-character hexadecimal string at the end of the URL path
            match = re.search(r"([a-f0-9]{32}|[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})", url, re.IGNORECASE)
            if match:
                page_id = match.group(1)
                # Remove hyphens if present
                page_id = page_id.replace("-", "")
                page_ids.append(page_id)
            else:
                logger.warning(f"Could not extract page ID from URL: {url}")

        return page_ids

    def _convert_to_streams(self, documents_result: Dict[str, List[Document]]) -> List[ByteStream]:
        """Convert Haystack Documents to ByteStream objects.

        Args:
            documents_result (Dict[str, List[Document]]): Dictionary containing a list of documents

        Returns:
            List[ByteStream]: List of ByteStream objects
        """
        documents = documents_result.get("documents", [])
        streams = []

        for doc in documents:
            if doc.content:
                # Create ByteStream from document content
                stream = ByteStream(data=doc.content.encode("utf-8"))
                # Add metadata from document
                stream.meta.update(doc.meta)
                stream.meta["content_type"] = "text/markdown"
                stream.mime_type = "text/markdown"
                streams.append(stream)

        return streams

    @component.output_types(streams=List[ByteStream])
    def run(self, urls: List[str]):
        if self.exporter is None:
            if self.raise_on_failure:
                raise ValueError("NotionExporter is not initialized. Check your NOTION_API_KEY.")
            logger.debug("NotionExporter is not initialized. Returning empty list of streams.")
            return {"streams": []}

        page_ids = self._extract_page_ids(urls)
        # logger.debug(f"Extracted page IDs: {page_ids}")
        documents = self.exporter.run(page_ids=page_ids)
        # logger.debug(f"Extracted documents: {documents}")
        successful_streams = self._convert_to_streams(documents)
        # logger.debug(f"Extracted successful_streams: {successful_streams}")

        return {"streams": successful_streams}

    def can_handle(self, url: str) -> bool:
        if self.exporter is None:
            return False

        if url.startswith("https://www.notion.so"):
            page_ids = self._extract_page_ids([url])
            return len(page_ids) == 1
        else:
            return False
