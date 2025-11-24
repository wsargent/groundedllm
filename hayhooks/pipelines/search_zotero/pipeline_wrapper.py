import json
import os
from typing import List

from hayhooks import log as logger
from hayhooks.server.utils.base_pipeline_wrapper import BasePipelineWrapper
from haystack import Pipeline

from components.zotero import ZoteroDatabase


class PipelineWrapper(BasePipelineWrapper):
    """A Haystack pipeline wrapper that searches Zotero database using MongoDB-style query objects."""

    def setup(self) -> None:
        """Set up the pipeline with a ZoteroDatabase component."""
        pipe = Pipeline()

        # Initialize the ZoteroDatabase component
        db_file = os.getenv("ZOTERO_DB_FILE")
        self.zotero_db = ZoteroDatabase(db_file=db_file)

        self.pipeline = pipe

    def run_api(self, query: List[dict]) -> str:
        """
        Search the Zotero database using one or more MongoDB-style query objects.

        Arguments
        --------
        query: List[dict]
            The MongoDB-style query object(s) to search for. Keys are field paths and values are the values to match.
            If a list of query objects is provided, they are logically ANDed together (all must match).

            Supported operators:
            - Exact match: {"field": "value"}
            - Not equals: {"field": {"$ne": "value"}}
            - Exists: {"field": {"$exists": True}}
            - Contains (case-insensitive): {"field": {"$contains": "text"}}
            - Regex (case-insensitive): {"field": {"$regex": "pattern"}}

            Examples:
            - [{"DOI": "10.3389/fnins.2012.00138"}] matches items where data.DOI equals "10.3389/fnins.2012.00138"
            - [{"url": "http://journal.frontiersin.org/article/10.3389/fnins.2012.00138/abstract"}] matches items.
            - [{"shortTitle": "foo"}] matches items where data.shortTitle equals "foo"
            - [{"title": "Example Paper"}] matches items where data.title equals "Example Paper"
            - [{"title": {"$contains": "Consciousness"}}] matches items where data.title contains "Consciousness" (case-insensitive)
            - [{"abstractNote": {"$regex": "cognitive.*therapy"}}] matches items with regex pattern (case-insensitive)
            - [{"creators.lastName": "Brooker"}] matches items where any creator has lastName "Brooker"
            - [{"title": "Example Paper"}, {"DOI": "10.1234/test"}] matches items where both conditions are true
            - {"title": "Example Paper", "DOI": "10.1234/test"} matches items where both fields match

        Return
        -------
        str
            A string with an array of JSON objects. Each item contains:
            - links.attachment.href: The Zotero API URL to the PDF file (use this with excerpt tool)
            - data.url: The original publication URL
            - data.title: The paper title
            - data.abstractNote: The abstract
            - Other metadata fields

            IMPORTANT: To ask questions about the PDF content, use the excerpt tool with the
            links.attachment.href URLs (format: https://api.zotero.org/users/{userID}/items/{itemKey}/file/view).

            Example workflow:
            1. Search with $contains: [{"title": {"$contains": "Consciousness"}}]
            2. Extract PDF URLs from results: item["links"]["attachment"]["href"]
            3. Ask questions with excerpt tool using those URLs
        """
        try:
            results = self.zotero_db.find_items_by_mongo_query(query)
            logger.info(f"Found {len(results)} results for query: {query}")
            return json.dumps(results, indent=2)
        except Exception as e:
            logger.error(f"Error searching Zotero database with query {query}: {str(e)}")
            raise RuntimeError(f"Error searching Zotero database: {str(e)}")
