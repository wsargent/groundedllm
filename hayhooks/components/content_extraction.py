import json
import mimetypes
import os
import re
import sqlite3
from typing import Any, Dict, List, Optional, Tuple

import httpx
from hayhooks import log as logger
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
from haystack.dataclasses import ByteStream
from haystack.utils import Secret
from pyzotero import zotero

from components.stackoverflow_search import DEFAULT_TIMEOUT, STACKOVERFLOW_API, StackOverflowBase


class URLContentResolver:
    """Base class for URL content resolvers."""

    def __init__(self, raise_on_failure: bool = False):
        """Initialize the URL content resolver.

        Args:
            raise_on_failure: Whether to raise an exception if fetching fails.
        """
        self.raise_on_failure = raise_on_failure

    @component.output_types(streams=List[ByteStream])
    def run(self, urls: List[str]):
        """Fetch content from URLs.

        Args:
            urls: A list of URLs to fetch content from.

        Returns:
            A dictionary with a "streams" key containing a list of ByteStream objects.
        """
        raise NotImplementedError("Subclasses must implement this method")

    def can_handle(self, url: str) -> bool:
        """Check if this resolver can handle the given URL.

        Args:
            url: The URL to check.

        Returns:
            True if this resolver can handle the URL, False otherwise.
        """
        raise NotImplementedError("Subclasses must implement this method")


@component
class GenericURLContentResolver:
    """A resolver that uses the existing FallbackLinkContentFetcher for generic URLs."""

    def __init__(
        self,
        raise_on_failure: bool = False,
        user_agents: Optional[List[str]] = None,
        retry_attempts: int = 2,
        timeout: int = 3,
        http2: bool = False,
        client_kwargs: Optional[Dict] = None,
        jina_timeout: int = 10,
        jina_retry_attempts: int = 2,
    ):
        self.raise_on_failure = raise_on_failure
        self.fetcher = FallbackLinkContentFetcher(
            raise_on_failure=raise_on_failure,
            user_agents=user_agents,
            retry_attempts=retry_attempts,
            timeout=timeout,
            http2=http2,
            client_kwargs=client_kwargs,
            jina_timeout=jina_timeout,
            jina_retry_attempts=jina_retry_attempts,
        )

    @component.output_types(streams=List[ByteStream])
    def run(self, urls: List[str]):
        return self.fetcher.run(urls)

    def can_handle(self, url: str) -> bool:
        # This is the fallback resolver, so it can handle any URL
        return True


@component
class StackOverflowContentResolver:
    """A resolver that uses the StackExchange API to fetch content from StackOverflow URLs."""

    def __init__(
        self,
        api_key: Secret = Secret.from_env_var("STACKOVERFLOW_API_KEY"),
        access_token: Optional[Secret] = None,
        timeout: int = DEFAULT_TIMEOUT,
        raise_on_failure: bool = False,
    ):
        self.raise_on_failure = raise_on_failure
        self.stackoverflow_client = StackOverflowBase(
            api_key=api_key,
            access_token=access_token,
            timeout=timeout,
        )

    @component.output_types(streams=List[ByteStream])
    def run(self, urls: List[str]):
        streams = []

        for url in urls:
            try:
                # Extract question ID from URL
                question_id = self._extract_question_id(url)
                if not question_id:
                    logger.warning(f"Could not extract question ID from {url}")
                    continue

                # Fetch question details
                params = self.stackoverflow_client._prepare_base_params(
                    filter="withbody",  # Include question body
                    site="stackoverflow",
                )
                api_url = f"{STACKOVERFLOW_API}/questions/{question_id}"

                response = httpx.get(api_url, params=params, timeout=self.stackoverflow_client.timeout)
                response.raise_for_status()
                data = response.json()

                if not data.get("items"):
                    logger.warning(f"No question found for ID {question_id}")
                    continue

                question = data["items"][0]

                # Fetch answers
                answers = self.stackoverflow_client.fetch_answers(question_id)

                # Combine question and answers into a single document
                result = {"question": question, "answers": answers}

                # Format the content as markdown
                content = self._format_as_markdown(result)

                # Create ByteStream
                stream = ByteStream(data=content.encode("utf-8"))
                stream.meta = {"url": url, "content_type": "text/markdown", "title": question.get("title", ""), "source": "stackoverflow"}
                stream.mime_type = "text/markdown"

                streams.append(stream)

            except Exception as e:
                logger.warning(f"Failed to fetch {url} using StackOverflow API: {str(e)}")
                if self.raise_on_failure:
                    raise e

        return {"streams": streams}

    def can_handle(self, url: str) -> bool:
        # Check if the URL is from StackOverflow
        return "stackoverflow.com/questions" in url

    def _extract_question_id(self, url: str) -> Optional[int]:
        """Extract the question ID from a StackOverflow URL."""
        import re

        # Match patterns like:
        # https://stackoverflow.com/questions/12345/title
        # https://stackoverflow.com/questions/12345
        match = re.search(r"stackoverflow\.com/questions/(\d+)", url)
        if match:
            return int(match.group(1))
        return None

    def _format_as_markdown(self, result: Dict) -> str:
        """Format the question and answers as markdown."""
        question = result["question"]
        answers = result["answers"]

        # Format question
        md = f"# {question.get('title', 'Untitled Question')}\n\n"
        md += f"**Score**: {question.get('score', 0)} | "
        md += f"**Asked by**: {question.get('owner', {}).get('display_name', 'Anonymous')} | "
        md += f"**Date**: {question.get('creation_date', '')}\n\n"
        md += question.get("body", "")
        md += "\n\n---\n\n"

        # Format answers
        md += f"## {len(answers)} Answers\n\n"

        # Sort answers by score (highest first)
        sorted_answers = sorted(answers, key=lambda x: x.get("score", 0), reverse=True)

        for i, answer in enumerate(sorted_answers):
            md += f"### Answer {i + 1} (Score: {answer.get('score', 0)})\n\n"
            md += f"**Answered by**: {answer.get('owner', {}).get('display_name', 'Anonymous')} | "
            md += f"**Date**: {answer.get('creation_date', '')}\n\n"
            md += answer.get("body", "")
            md += "\n\n---\n\n"

        return md


@component
class ZoteroContentResolver:
    """A resolver that uses the Zotero API to fetch academic papers by DOI.

    Uses a local SQLite database to cache Zotero items for faster querying.
    """

    # Default SQLite database file path
    DEFAULT_DB_FILE = "zotero_json_cache.db"

    def __init__(
        self,
        library_id: Secret = Secret.from_env_var("ZOTERO_LIBRARY_ID"),
        api_key: Secret = Secret.from_env_var("ZOTERO_API_KEY"),
        db_file: str = os.getenv("ZOTERO_DB_FILE"),
        library_type: str = "user",  # 'user' or 'group'
        timeout: int = 10,
        raise_on_failure: bool = False,
    ):
        """Initialize the Zotero content resolver.

        Args:
            library_id: The Zotero library ID.
            api_key: The Zotero API key.
            db_file: The path to the SQLite database file for caching Zotero items.
            library_type: The type of library ('user' or 'group').
            timeout: The timeout for API requests in seconds.
            raise_on_failure: Whether to raise an exception if fetching fails.
        """
        self.raise_on_failure = raise_on_failure
        self.timeout = timeout
        self.library_type = library_type

        # Resolve the database file path from the environment variable or use the default
        try:
            self.db_file = db_file if db_file else self.DEFAULT_DB_FILE
        except Exception:
            self.db_file = self.DEFAULT_DB_FILE
            logger.info(f"Using default Zotero SQLite database path: {self.db_file}")

        try:
            self.library_id = library_id.resolve_value()
            self.api_key = api_key.resolve_value()
            self.is_enabled = self.library_id is not None and self.api_key is not None

            if self.is_enabled:
                self.zotero_client = zotero.Zotero(self.library_id, library_type, self.api_key)
                # Initialize the SQLite database
                self._init_json_db()
                # Sync Zotero data to the local database
                self._sync_zotero_to_json_sqlite()
            else:
                logger.info("No ZOTERO_LIBRARY_ID or ZOTERO_API_KEY provided. ZoteroContentResolver is disabled.")
        except Exception as e:
            logger.error(f"Failed to initialize Zotero client: {str(e)}")
            self.is_enabled = False

    def _init_json_db(self):
        """Initialize the SQLite database for storing Zotero items."""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS zotero_items_json (
                item_key TEXT PRIMARY KEY,
                date_modified TEXT,
                item_data TEXT 
            );
            """)
            # Create indexes on JSON properties to speed up searches
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_json_doi ON zotero_items_json (json_extract(item_data, '$.data.DOI'));")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_json_url ON zotero_items_json (json_extract(item_data, '$.data.url'));")

            # Create a table to store the library version for incremental syncs
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS zotero_library_version (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                version INTEGER NOT NULL DEFAULT 0
            );
            """)
            # Insert a default version if it doesn't exist
            cursor.execute("""
            INSERT OR IGNORE INTO zotero_library_version (id, version) VALUES (1, 0);
            """)

            conn.commit()
            conn.close()
            logger.info(f"Initialized Zotero SQLite database at {self.db_file}")
        except Exception as e:
            logger.error(f"Failed to initialize Zotero SQLite database: {str(e)}")
            if self.raise_on_failure:
                raise e

    def _sync_zotero_to_json_sqlite(self):
        """Sync Zotero items to the local SQLite database using incremental sync."""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()

            # Get the last synced library version
            cursor.execute("SELECT version FROM zotero_library_version WHERE id = 1")
            result = cursor.fetchone()
            last_version = result[0] if result else 0

            # Fetch items from Zotero that have changed since the last sync
            if last_version > 0:
                logger.info(f"Performing incremental sync from version {last_version}")
                # Use items with since parameter for incremental sync
                items = self.zotero_client.everything(self.zotero_client.items(since=last_version))
            else:
                logger.info("Performing initial full sync")
                # For the first sync, get all items
                items = self.zotero_client.everything(self.zotero_client.top())

            for item in items:
                # INSERT OR REPLACE will update if item_key exists, or insert if new
                cursor.execute(
                    """
                INSERT OR REPLACE INTO zotero_items_json 
                (item_key, date_modified, item_data)
                VALUES (?, ?, ?)
                """,
                    (
                        item.get("key"),
                        item.get("data", {}).get("dateModified"),
                        json.dumps(item),  # Store the whole item as a JSON string
                    ),
                )

            # Get the current library version
            current_version = self.zotero_client.last_modified_version()

            # Update the stored library version
            cursor.execute("UPDATE zotero_library_version SET version = ? WHERE id = 1", (current_version,))

            conn.commit()
            conn.close()
            logger.info(f"Synced {len(items)} items from Zotero to SQLite database (version {current_version})")
        except Exception as e:
            logger.error(f"Failed to sync Zotero items to SQLite database: {str(e)}")
            if self.raise_on_failure:
                raise e

    def _search_json_by_doi_sqlite(self, target_doi: str) -> List[dict]:
        """Search the SQLite database for items with the given DOI.

        Args:
            target_doi: The DOI to search for.

        Returns:
            A list of matching Zotero items.
        """
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()

            # Querying JSON: json_extract(column_name, path_to_value)
            cursor.execute(
                """
            SELECT item_data FROM zotero_items_json
            WHERE json_extract(item_data, '$.data.DOI') = ? 
            OR json_extract(item_data, '$.DOI') = ?
            OR json_extract(item_data, '$.data.extra') LIKE ?
            """,
                (target_doi, target_doi, f"%DOI: {target_doi}%"),
            )

            results = [json.loads(row[0]) for row in cursor.fetchall()]
            conn.close()
            return results
        except Exception as e:
            logger.error(f"Failed to search SQLite database by DOI: {str(e)}")
            if self.raise_on_failure:
                raise e
            return []

    def _search_json_by_url_sqlite(self, target_url: str) -> List[dict]:
        """Search the SQLite database for items with the given URL.

        Args:
            target_url: The URL to search for.

        Returns:
            A list of matching Zotero items.
        """
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()

            cursor.execute(
                """
            SELECT item_data FROM zotero_items_json
            WHERE json_extract(item_data, '$.data.url') LIKE ?
            """,
                (f"%{target_url}%",),
            )

            results = [json.loads(row[0]) for row in cursor.fetchall()]
            conn.close()
            return results
        except Exception as e:
            logger.error(f"Failed to search SQLite database by URL: {str(e)}")
            if self.raise_on_failure:
                raise e
            return []

    def _find_matching_item(self, url: str) -> Optional[dict]:
        """Find a matching Zotero item for the given URL.

        Args:
            url: The URL to find a matching item for.

        Returns:
            The matching Zotero item, or None if no match is found.
        """
        matching_item = None

        # First, try to find the item by URL in the local database
        url_matches = self._search_json_by_url_sqlite(url)
        if url_matches:
            matching_item = url_matches[0]  # Take the first match

        # If no match by URL, try to find by DOI
        if not matching_item:
            doi = self._extract_doi(url)
            if doi:
                doi_matches = self._search_json_by_doi_sqlite(doi)
                if doi_matches:
                    matching_item = doi_matches[0]  # Take the first match

        return matching_item

    def _process_attachments(self, parent_item: dict, url: str, streams: List[ByteStream]) -> bool:
        """Process attachments for a Zotero item and add them to the streams list.

        Args:
            parent_item: The parent Zotero item.
            url: The original URL.
            streams: The list of ByteStream objects to append to.

        Returns:
            True if processing was successful, False otherwise.
        """
        parent_item_key = parent_item.get("data", {}).get("key", "")
        title = parent_item.get("data", {}).get("title", "")

        try:
            child_items = self.zotero_client.children(parent_item_key)

            # If no child items found, log and return
            if not child_items:
                logger.warning(f"No child items found for Zotero item with URL {url}, skipping")
                return False

            # Find attachment items
            attachment_found = False

            for child in child_items:
                # Check if the child is an attachment
                if child["data"]["itemType"] == "attachment":
                    filename = child["data"].get("filename")
                    child_item_key = child["key"]

                    # Skip if no filename
                    if not filename:
                        continue

                    # Check if the file is a PDF or HTML
                    is_pdf = filename.lower().endswith(".pdf")
                    is_html = filename.lower().endswith((".html", ".htm"))

                    if not (is_pdf or is_html):
                        continue

                    # We found a valid attachment
                    attachment_found = True

                    # Get the file contents using the child item key
                    file_contents = self.zotero_client.file(child_item_key)

                    # Determine MIME type from filename
                    mime_type = "application/pdf"  # Default fallback
                    if filename:
                        guessed_type, _ = mimetypes.guess_type(filename)
                        if guessed_type:
                            mime_type = guessed_type

                    # Create ByteStream
                    stream = ByteStream(data=file_contents)
                    stream.meta = {"url": url, "filename": filename, "title": title, "source": "zotero"}
                    stream.mime_type = mime_type

                    streams.append(stream)

            # If no valid attachments were found, log and return
            if not attachment_found:
                logger.warning(f"No valid PDF or HTML attachments found for Zotero item with URL {url}, skipping")
                return False

            return True

        except Exception as e:
            logger.warning(f"Failed to get child items for Zotero item with URL {url}: {str(e)}")
            if self.raise_on_failure:
                raise e
            return False

    @component.output_types(streams=List[ByteStream])
    def run(self, urls: List[str]):
        """Fetch content from Zotero for academic paper URLs.

        Args:
            urls: A list of URLs to fetch content from.

        Returns:
            A dictionary with a "streams" key containing a list of ByteStream objects.
        """
        streams = []

        if not self.is_enabled:
            logger.warning("ZoteroContentResolver is disabled. Skipping.")
            return {"streams": streams}

        for url in urls:
            try:
                # Find matching item
                matching_item = self._find_matching_item(url)

                # If no match, log and continue to next URL
                if not matching_item:
                    logger.warning(f"No matching item found in Zotero database for URL {url}")
                    continue

                # Process attachments
                self._process_attachments(matching_item, url, streams)

            except Exception as e:
                logger.warning(f"Failed to fetch {url} using Zotero: {str(e)}")
                if self.raise_on_failure:
                    raise e

        return {"streams": streams}

    def can_handle(self, url: str) -> bool:
        """Check if this resolver can handle the given URL.

        Args:
            url: The URL to check.

        Returns:
            True if this resolver can handle the URL, False otherwise.
        """
        # Check if the URL is a DOI link
        if "doi.org" in url:
            return True

        # Check if the URL is from an academic site and ends with .pdf
        academic_domains = ["researchgate.net", "academia.edu", "arxiv.org", "sciencedirect.com", "springer.com", "ieee.org", "acm.org", "jstor.org", "nature.com", "wiley.com", "tandfonline.com", "sagepub.com", "oup.com", "elsevier.com"]

        if any(domain in url for domain in academic_domains):
            return True

        return False

    def _extract_doi(self, url: str) -> Optional[str]:
        """Extract the DOI from a URL."""
        # Extract DOI from doi.org URLs
        doi_match = re.search(r"doi\.org/(.+?)(?:$|[?#])", url)
        if doi_match:
            return doi_match.group(1)

        # Extract DOI from PDF URLs with DOI in the filename
        pdf_doi_match = re.search(r"/(10\.\d{4,}[/.][\w.]+)\.pdf", url)
        if pdf_doi_match:
            return pdf_doi_match.group(1)

        return None


@component
class URLContentRouter:
    """A component that routes URLs to the appropriate resolver."""

    def __init__(self, resolvers: List[Any]):
        """Initialize the URL router.

        Args:
            resolvers: A list of URL content resolvers.
        """
        self.resolvers = resolvers
        # The last resolver should be the generic one that can handle any URL
        self.generic_resolver = resolvers[-1]

    @component.output_types(streams=List[ByteStream])
    def run(self, urls: List[str]):
        """Route URLs to the appropriate resolver and fetch their content.

        Args:
            urls: A list of URLs to fetch content from.

        Returns:
            A dictionary with a "streams" key containing a list of ByteStream objects.
        """
        # Group URLs by resolver
        resolver_urls = {}

        for url in urls:
            resolver = self._find_resolver(url)
            if resolver not in resolver_urls:
                resolver_urls[resolver] = []
            resolver_urls[resolver].append(url)

        # Fetch content using each resolver
        all_streams = []

        for resolver, urls in resolver_urls.items():
            result = resolver.run(urls)
            all_streams.extend(result["streams"])

        return {"streams": all_streams}

    def _find_resolver(self, url: str) -> Any:
        """Find the appropriate resolver for the given URL.

        Args:
            url: The URL to find a resolver for.

        Returns:
            The resolver that can handle the URL.
        """
        for resolver in self.resolvers:
            if resolver.can_handle(url):
                return resolver

        # This should never happen since the generic resolver can handle any URL
        return self.generic_resolver


@component
class FallbackLinkContentFetcher:
    """
    A component that tries to fetch content using LinkContentFetcher first,
    and falls back to JinaLinkContentFetcher if it fails.
    """

    def __init__(
        self,
        raise_on_failure: bool = False,
        user_agents: Optional[List[str]] = None,
        retry_attempts: int = 2,
        timeout: int = 3,
        http2: bool = False,
        client_kwargs: Optional[Dict] = None,
        jina_timeout: int = 10,
        jina_retry_attempts: int = 2,
    ):
        """
        Initialize the FallbackLinkContentFetcher.

        Args:
            raise_on_failure: Whether to raise an exception if both fetchers fail.
            user_agents: A list of user agents to use for the primary fetcher.
            retry_attempts: The number of retry attempts for the primary fetcher.
            timeout: The timeout for the primary fetcher in seconds.
            http2: Whether to use HTTP/2 for the primary fetcher.
            client_kwargs: Additional kwargs for the primary fetcher's HTTP client.
            jina_timeout: The timeout for the fallback fetcher in seconds.
            jina_retry_attempts: The number of retry attempts for the fallback fetcher.
        """
        self.primary_fetcher = LinkContentFetcher(
            raise_on_failure=False,  # We handle failures ourselves
            user_agents=user_agents,
            retry_attempts=retry_attempts,
            timeout=timeout,
            http2=http2,
            client_kwargs=client_kwargs,
        )
        self.fallback_fetcher = JinaLinkContentFetcher(
            timeout=jina_timeout,
            retry_attempts=jina_retry_attempts,
        )
        self.raise_on_failure = raise_on_failure

    @component.output_types(streams=List[ByteStream])
    def run(self, urls: List[str]):
        """
        Fetch content from URLs using the primary fetcher first,
        and fall back to the fallback fetcher if it fails.

        Args:
            urls: A list of URLs to fetch content from.

        Returns:
            A dictionary with a "streams" key containing a list of ByteStream objects.
        """
        primary_result = self.primary_fetcher.run(urls)
        streams = primary_result["streams"]

        # Check if any streams are empty (failed to fetch)
        failed_urls = []
        successful_streams = []

        for stream in streams:
            url = stream.meta.get("url", "")

            # Check if the stream is empty (failed to fetch)
            if stream.data == b"":
                failed_urls.append(url)
                logger.info(f"Primary fetcher failed to fetch {url}, trying fallback fetcher")
            else:
                successful_streams.append(stream)

        # If there are any failed URLs, try the fallback fetcher
        if failed_urls:
            try:
                fallback_result = self.fallback_fetcher.run(failed_urls)
                fallback_streams = fallback_result["streams"]

                # Process fallback streams to match LinkContentFetcher format
                for i, item in enumerate(fallback_streams):
                    if isinstance(item, dict) and "metadata" in item and "stream" in item:
                        # Extract metadata and stream from dictionary
                        metadata = item["metadata"]
                        stream = item["stream"]
                        # Update stream metadata
                        stream.meta.update(metadata)
                        stream.mime_type = stream.meta.get("content_type", None)
                        successful_streams.append(stream)
                        # Log successful fallbacks
                        url = metadata.get("url", "")
                        logger.info(f"Successfully fetched {url} using fallback fetcher")
                    else:
                        # If already in the right format, just add it
                        successful_streams.append(item)
                        # Log successful fallbacks
                        url = item.meta.get("url", "")
                        logger.info(f"Successfully fetched {url} using fallback fetcher")

            except Exception as e:
                logger.warning(f"Fallback fetcher failed: {str(e)}")
                if self.raise_on_failure:
                    raise e

        return {"streams": successful_streams}


@component
class JinaLinkContentFetcher:
    """
    A component that fetches content from URLs using the jina.ai service.
    This is used as a fallback when LinkContentFetcher fails.
    """

    def __init__(self, timeout: int = 10, retry_attempts: int = 2, api_key: Secret = Secret.from_env_var("JINA_API_KEY")):
        """
        Initialize the JinaLinkContentFetcher.

        Args:
            timeout: The timeout for the HTTP request in seconds.
            retry_attempts: The number of retry attempts for failed requests.
        """
        self.timeout = timeout
        self.retry_attempts = retry_attempts
        try:
            self.api_key = api_key.resolve_value()
        except Exception:
            self.api_key = None

        self.jina_url = "https://r.jina.ai/api/v1/fetch"

    @component.output_types(streams=List[ByteStream])
    def run(self, urls: List[str]):
        """
        Fetch content from URLs using jina.ai service.

        Args:
            urls: A list of URLs to fetch content from.

        Returns:
            A dictionary with a "streams" key containing a list of ByteStream objects.
        """
        streams = []

        for url in urls:
            metadata, stream = self._fetch_with_retries(url)
            if metadata and stream:
                # Update stream metadata
                stream.meta.update(metadata)
                stream.mime_type = stream.meta.get("content_type", None)
                streams.append(stream)

        return {"streams": streams}

    def _fetch_with_retries(self, url: str) -> Tuple[Optional[Dict[str, str]], Optional[ByteStream]]:
        """
        Fetch content from a URL with retry logic.

        Args:
            url: The URL to fetch content from.

        Returns:
            A tuple containing metadata and ByteStream.
        """
        attempt = 0

        while attempt <= self.retry_attempts:
            try:
                return self._fetch(url)
            except Exception as e:
                attempt += 1
                if attempt <= self.retry_attempts:
                    # Wait before retry using exponential backoff
                    import time

                    time.sleep(min(2 * 2 ** (attempt - 1), 10))
                else:
                    logger.warning(f"Failed to fetch {url} using jina.ai after {self.retry_attempts} attempts: {str(e)}")
                    break

        # If we've exhausted all retries, return None
        return None, None

    def _fetch(self, url: str) -> Tuple[Dict[str, str], ByteStream]:
        """
        Fetch content from a URL using jina.ai service.

        Args:
            url: The URL to fetch content from.

        Returns:
            A tuple containing metadata and ByteStream.
        """
        if self.api_key:
            headers = {"Authentication:": f"Bearer {self.api_key}"}
        else:
            headers = {}
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(self.jina_url, headers=headers, json={"url": url})
            response.raise_for_status()

            # Extract content from response
            content = response.json().get("content", "")
            content_type = response.json().get("content_type", "text/html")

            # Create ByteStream and metadata
            stream = ByteStream(data=content.encode("utf-8"))
            metadata = {"content_type": content_type, "url": url}

            return metadata, stream


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

    # Create router with all resolvers (generic resolver must be last)
    url_router = URLContentRouter(
        resolvers=[
            stackoverflow_resolver,
            zotero_resolver,
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

    extraction_component = SuperComponent(
        pipeline=preprocessing_pipeline,
        input_mapping={"urls": ["url_router.urls"]},
        output_mapping={"document_cleaner.documents": "documents"},
    )
    return extraction_component
