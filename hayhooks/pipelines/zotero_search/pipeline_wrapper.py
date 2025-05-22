import os
from typing import Any, Dict, List

from hayhooks import log as logger
from hayhooks.server.utils.base_pipeline_wrapper import BasePipelineWrapper
from haystack import Pipeline

from components.zotero import ZoteroDatabase


class PipelineWrapper(BasePipelineWrapper):
    """A Haystack pipeline wrapper that searches Zotero database using jsonpath expressions."""

    def setup(self) -> None:
        """Set up the pipeline with a ZoteroDatabase component."""
        pipe = Pipeline()

        # Initialize the ZoteroDatabase component
        db_file = os.getenv("ZOTERO_DB_FILE")
        self.zotero_db = ZoteroDatabase(db_file=db_file)

        self.pipeline = pipe

    def run_api(self, jsonpath: str) -> List[Dict[str, Any]]:
        """
        Search the Zotero database using a jsonpath expression.

        Arguments
        --------
        jsonpath: str
            The jsonpath expression to search for, in the format "$.field=value" or "field=value".
            Examples:
            - "$.DOI=10.3389/fnins.2012.00138" matches items where data.DOI equals "10.3389/fnins.2012.00138"
            " "$.url=http://journal.frontiersin.org/article/10.3389/fnins.2012.00138/abstract" matches items.
            - "$.shortTitle=foo" matches items where data.shortTitle equals "foo"
            - "$.title=Example Paper" matches items where data.title equals "Example Paper"
            - "shortTitle=foo" is equivalent to "$.shortTitle=foo"

        Return
        -------
        List[Dict[str, Any]]
            A list of matching Zotero items as JSON objects.
            Use the extract tool with an item's URL to extract the full text content.
            Use the excerpt tool with several items URLs to ask an LLM a question about the items.
        """
        try:
            # Use the ZoteroDatabase's search_json_by_jsonpath method
            results = self.zotero_db.search_json_by_jsonpath(jsonpath)
            logger.info(f"Found {len(results)} results for jsonpath: {jsonpath}")
            return results
        except Exception as e:
            logger.error(f"Error searching Zotero database with jsonpath {jsonpath}: {str(e)}")
            raise RuntimeError(f"Error searching Zotero database: {str(e)}")
