import json
import mimetypes
import os
import re
import sqlite3
from typing import List, Optional

from hayhooks import log as logger
from haystack import component
from haystack.dataclasses import ByteStream
from haystack.utils import Secret
from pyzotero import zotero

# Check if the URL is from an academic site
ACADEMIC_DOMAINS = ["researchgate.net", "academia.edu", "arxiv.org", "sciencedirect.com", "springer.com", "ieee.org", "acm.org", "jstor.org", "nature.com", "wiley.com", "tandfonline.com", "sagepub.com", "oup.com", "elsevier.com"]


class ZoteroDatabase:
    """A class to handle Zotero database operations.

    This class manages the SQLite database used to cache Zotero items for faster querying.

    A zotero item looks like this:

    {u'data': {u'ISBN': u'0810116820',
           u'abstractNote': u'',
           u'accessDate': u'',
           u'archive': u'',
           u'archiveLocation': u'',
           u'callNumber': u'HIB 828.912 BEC:3g N9',
           u'collections': [u'2UNGXMU9'],
           u'creators': [{u'creatorType': u'author',
                          u'firstName': u'Daniel',
                          u'lastName': u'Katz'}],
           u'date': u'1999',
           u'dateAdded': u'2010-01-04T14:50:40Z',
           u'dateModified': u'2014-08-06T11:28:41Z',
           u'edition': u'',
           u'extra': u'',
           u'itemType': u'book',
           u'key': u'VDNIEAPH',
           u'language': u'',
           u'libraryCatalog': u'library.catalogue.tcd.ie Library Catalog',
           u'numPages': u'',
           u'numberOfVolumes': u'',
           u'place': u'Evanston, Ill',
           u'publisher': u'Northwestern University Press',
           u'relations': {u'dc:replaces': u'http://zotero.org/users/436/items/9TXN8QUD'},
           u'rights': u'',
           u'series': u'',
           u'seriesNumber': u'',
           u'shortTitle': u'Saying I No More',
           u'tags': [{u'tag': u'Beckett, Samuel', u'type': 1},
                     {u'tag': u'Consciousness in literature', u'type': 1},
                     {u'tag': u'English prose literature', u'type': 1},
                     {u'tag': u'Ireland', u'type': 1},
                     {u'tag': u'Irish authors', u'type': 1},
                     {u'tag': u'Modernism (Literature)', u'type': 1},
                     {u'tag': u'Prose', u'type': 1},
                     {u'tag': u'Self in literature', u'type': 1},
                     {u'tag': u'Subjectivity in literature', u'type': 1}],
           u'title': u'Saying I No More: Subjectivity and Consciousness in The Prose of Samuel Beckett',
           u'url': u'',
           u'version': 792,
           u'volume': u''},
           u'key': u'VDNIEAPH',
           u'library': {u'id': 436,
                        u'links': {u'alternate': {u'href': u'https://www.zotero.org/urschrei',
                                                    u'type': u'text/html'}},
                        u'name': u'urschrei',
                        u'type': u'user'},
           u'links': {u'alternate': {u'href': u'https://www.zotero.org/urschrei/items/VDNIEAPH',
                                    u'type': u'text/html'},
                        u'self': {u'href': u'https://api.zotero.org/users/436/items/VDNIEAPH',
                                u'type': u'application/json'}},
           u'meta': {u'creatorSummary': u'Katz',
                    u'numChildren': 0,
                    u'parsedDate': u'1999-00-00'},
           u'version': 792}

    """

    # Default SQLite database file path
    DEFAULT_DB_FILE = "zotero_json_cache.db"

    def __init__(
        self,
        db_file: str = DEFAULT_DB_FILE,
        raise_on_failure: bool = False,
    ):
        """Initialize the Zotero database.

        Args:
            db_file: The path to the SQLite database file for caching Zotero items.
            raise_on_failure: Whether to raise an exception if database operations fail.
        """
        self.raise_on_failure = raise_on_failure

        # Resolve the database file path or use the default
        try:
            self.db_file = db_file if db_file else self.DEFAULT_DB_FILE
        except Exception:
            self.db_file = self.DEFAULT_DB_FILE

        logger.info(f"Using Zotero SQLite database path: {self.db_file}")

        # Initialize the database
        self.init_json_db()

    def init_json_db(self) -> None:
        """Initialize the SQLite database for storing Zotero items."""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            cursor.execute("""
                           CREATE TABLE IF NOT EXISTS zotero_items_json
                           (
                               item_key      TEXT PRIMARY KEY,
                               date_modified TEXT,
                               item_data     TEXT
                           );
                           """)
            # Create indexes on JSON properties to speed up searches
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_json_doi ON zotero_items_json (json_extract(item_data, '$.data.DOI'));")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_json_url ON zotero_items_json (json_extract(item_data, '$.data.url'));")

            # Create a table to store the library version for incremental syncs
            version_table = "CREATE TABLE IF NOT EXISTS zotero_library_version(id INTEGER PRIMARY KEY CHECK(id =1),version INTEGER NOT NULL DEFAULT 0);"
            cursor.execute(version_table)
            # Insert a default version if it doesn't exist
            cursor.execute("INSERT OR IGNORE INTO zotero_library_version (id, version) VALUES (1, 0);")

            conn.commit()
            conn.close()
            logger.info(f"Initialized Zotero SQLite database at {self.db_file}")
        except Exception as e:
            logger.error(f"Failed to initialize Zotero SQLite database: {str(e)}")
            if self.raise_on_failure:
                raise e

    def sync_zotero_to_json_sqlite(self, zotero_client):
        """Sync Zotero items to the local SQLite database using incremental sync.

        Args:
            zotero_client: The Zotero client to use for fetching items.

        Returns:
            The number of items synced.
        """
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
                items = zotero_client.everything(zotero_client.items(since=last_version))
            else:
                logger.info("Performing initial full sync")
                # For the first sync, get all items
                items = zotero_client.everything(zotero_client.top())

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
            current_version = zotero_client.last_modified_version()

            # Update the stored library version
            cursor.execute("UPDATE zotero_library_version SET version = ? WHERE id = 1", (current_version,))

            conn.commit()
            conn.close()
            logger.info(f"Synced {len(items)} items from Zotero to SQLite database (version {current_version})")
            return len(items)
        except Exception as e:
            logger.error(f"Failed to sync Zotero items to SQLite database: {str(e)}")
            if self.raise_on_failure:
                raise e
            return 0

    def search_json_by_doi_sqlite(self, target_doi: str) -> List[dict]:
        """Search the SQLite database for items with the given DOI.

        Args:
            target_doi: The DOI to search for.

        Returns:
            A list of matching Zotero items.
        """
        try:
            return self.search_json_by_jsonpath(f"$.data.DOI={target_doi}")
        except Exception as e:
            logger.error(f"Failed to search SQLite database by DOI: {str(e)}")
            if self.raise_on_failure:
                raise e
            return []

    def search_json_by_url_sqlite(self, target_url: str) -> List[dict]:
        """Search the SQLite database for items with the given URL.

        Args:
            target_url: The URL to search for.

        Returns:
            A list of matching Zotero items.
        """
        try:
            return self.search_json_by_jsonpath(f"$.data.url={target_url}")
        except Exception as e:
            logger.error(f"Failed to search SQLite database by URL: {str(e)}")
            if self.raise_on_failure:
                raise e
            return []

    def search_json_by_jsonpath(self, jsonpath_expr: str) -> List[dict]:
        """Search the SQLite database for items matching a jsonpath expression.

        The jsonpath expression should be in the format "$.path=value", where path
        is the path to the property in the data object and value is the value to match.

        Examples:
            - "$.shortTitle=foo" matches items where data.shortTitle equals "foo"
            - "$.title=Example Paper" matches items where data.title equals "Example Paper"
            - "$.creators[*].lastName=Brooker" matches items where any creator has lastName "Brooker"
            - "$.creators[?(@.lastName)]==Brooker" matches items where any creator has lastName "Brooker"

        Args:
            jsonpath_expr: The jsonpath expression to search for.

        Returns:
            A list of matching Zotero items.
        """
        try:
            # Parse the jsonpath expression
            if not jsonpath_expr or "=" not in jsonpath_expr:
                logger.error(f"Invalid jsonpath expression: {jsonpath_expr}")
                return []

            # Handle special case for array queries with [?(@.field)]=='value' syntax
            if "[?(@." in jsonpath_expr and ")]==''" in jsonpath_expr or ")]==''" in jsonpath_expr or ")]=='Brooker'" in jsonpath_expr:
                # Extract the array field, property name, and value
                parts = jsonpath_expr.split("[?(@.")
                array_field = parts[0].replace("$.", "")
                property_and_value = parts[1].split(")]=='")
                property_name = property_and_value[0]
                value = property_and_value[1].replace("'", "")

                # Ensure the path starts with data.
                if not array_field.startswith("data."):
                    array_field = f"data.{array_field}"

                conn = sqlite3.connect(self.db_file)
                cursor = conn.cursor()

                # Use json_foreach to search within array elements
                cursor.execute(
                    f"""
                    SELECT item_data
                    FROM zotero_items_json
                    WHERE EXISTS (
                        SELECT 1
                        FROM json_each(json_extract(item_data, '$.{array_field}'))
                        WHERE json_extract(value, '$.{property_name}') LIKE ?
                    )
                    """,
                    (value,),
                )

                results = [json.loads(row[0]) for row in cursor.fetchall()]
                conn.close()
                return results

            # Standard path=value format
            path, value = jsonpath_expr.split("=", 1)

            # Ensure the path starts with $.data.
            if path.startswith("$."):
                # If the path starts with $. but not $.data., prepend data.
                if not path.startswith("$.data."):
                    path = path.replace("$.", "$.data.")
            else:
                # If the path doesn't start with $., prepend $.data.
                path = f"$.data.{path}"

            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()

            # Check if this is an array query (contains [*])
            if "[*]" in path:
                # Extract the array field name
                array_field = path.split("[*]")[0].split(".")[-1]
                # Extract the property to match within the array
                property_name = path.split("[*].")[-1]

                # Use json_foreach to search within array elements
                cursor.execute(
                    f"""
                    SELECT item_data
                    FROM zotero_items_json
                    WHERE EXISTS (
                        SELECT 1
                        FROM json_each(json_extract(item_data, '$.data.{array_field}'))
                        WHERE json_extract(value, '$.{property_name}') LIKE ?
                    )
                    """,
                    (value,),
                )
            else:
                # Regular non-array query
                cursor.execute(
                    """
                    SELECT item_data
                    FROM zotero_items_json
                    WHERE json_extract(item_data, ?) LIKE ?
                    """,
                    (path, value),
                )

            results = [json.loads(row[0]) for row in cursor.fetchall()]
            conn.close()
            return results
        except Exception as e:
            logger.error(f"Failed to search SQLite database by jsonpath: {str(e)}")
            if self.raise_on_failure:
                raise e
            return []


@component
class ZoteroContentResolver:
    """A resolver that uses the Zotero API to fetch academic papers by DOI.

    Uses a local SQLite database to cache Zotero items for faster querying.
    """

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

        # Initialize the database
        self.db = ZoteroDatabase(db_file=db_file, raise_on_failure=raise_on_failure)

        try:
            self.library_id = library_id.resolve_value()
            self.api_key = api_key.resolve_value()
            self.is_enabled = self.library_id is not None and self.api_key is not None

            if self.is_enabled:
                self.zotero_client = zotero.Zotero(self.library_id, library_type, self.api_key)
                # Sync Zotero data to the local database
                self.db.sync_zotero_to_json_sqlite(self.zotero_client)
            else:
                logger.info("No ZOTERO_LIBRARY_ID or ZOTERO_API_KEY provided. ZoteroContentResolver is disabled.")
        except Exception as e:
            logger.error(f"Failed to initialize Zotero client: {str(e)}")
            self.is_enabled = False

    def _find_matching_item(self, url: str) -> Optional[dict]:
        """Find a matching Zotero item for the given URL.

        Args:
            url: The URL to find a matching item for.

        Returns:
            The matching Zotero item, or None if no match is found.
        """
        matching_item = None

        # First, try to find the item by URL in the local database
        url_matches = self.db.search_json_by_url_sqlite(url)
        if url_matches:
            matching_item = url_matches[0]  # Take the first match

        # If no match by URL, try to find by DOI
        if not matching_item:
            doi = self._extract_doi(url)
            if doi:
                doi_matches = self.db.search_json_by_doi_sqlite(doi)
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

        if any(domain in url for domain in ACADEMIC_DOMAINS):
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
