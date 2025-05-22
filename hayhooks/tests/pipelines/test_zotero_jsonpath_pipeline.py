import json
import os
import sqlite3
import tempfile

import pytest

from components.zotero import ZoteroDatabase
from pipelines.zotero_search.pipeline_wrapper import PipelineWrapper


@pytest.fixture
def zotero_db():
    # Create a temporary database file
    temp_db = tempfile.NamedTemporaryFile(delete=False)
    db_path = temp_db.name
    temp_db.close()

    # Set environment variable for the pipeline to use
    os.environ["ZOTERO_DB_FILE"] = db_path

    # Initialize the database
    ZoteroDatabase(db_file=db_path)

    # Create a connection to the database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Insert some test data
    test_items = [
        {"key": "item1", "data": {"dateModified": "2023-01-01", "title": "Test Paper 1", "shortTitle": "TP1", "url": "https://example.com/paper1", "DOI": "10.1234/test1"}},
        {"key": "item2", "data": {"dateModified": "2023-01-02", "title": "Test Paper 2", "shortTitle": "TP2", "url": "https://example.com/paper2", "DOI": "10.1234/test2"}},
        {"key": "item3", "data": {"dateModified": "2023-01-03", "title": "Another Paper", "shortTitle": "AP", "url": "https://example.com/paper3", "DOI": "10.1234/test3"}},
    ]

    for item in test_items:
        cursor.execute(
            """
            INSERT INTO zotero_items_json 
            (item_key, date_modified, item_data)
            VALUES (?, ?, ?)
            """,
            (
                item["key"],
                item["data"]["dateModified"],
                json.dumps(item),
            ),
        )

    conn.commit()
    conn.close()

    yield db_path

    # Cleanup
    os.unlink(db_path)
    if "ZOTERO_DB_FILE" in os.environ:
        del os.environ["ZOTERO_DB_FILE"]


def test_pipeline_search_by_short_title(zotero_db):
    # Initialize the pipeline wrapper
    pipeline = PipelineWrapper()
    pipeline.setup()

    # Test searching by shortTitle
    results = pipeline.run_api("$.shortTitle=TP1")
    assert len(results) == 1
    assert results[0]["key"] == "item1"


def test_pipeline_search_by_title(zotero_db):
    # Initialize the pipeline wrapper
    pipeline = PipelineWrapper()
    pipeline.setup()

    # Test searching by title
    results = pipeline.run_api("$.title=Another Paper")
    assert len(results) == 1
    assert results[0]["key"] == "item3"


def test_pipeline_search_by_doi(zotero_db):
    # Initialize the pipeline wrapper
    pipeline = PipelineWrapper()
    pipeline.setup()

    # Test searching by DOI
    results = pipeline.run_api("$.DOI=10.1234/test1")
    assert len(results) == 1
    assert results[0]["key"] == "item1"


def test_pipeline_search_no_results(zotero_db):
    # Initialize the pipeline wrapper
    pipeline = PipelineWrapper()
    pipeline.setup()

    # Test searching with no matches
    results = pipeline.run_api("$.shortTitle=NonExistent")
    assert len(results) == 0


def test_pipeline_invalid_jsonpath(zotero_db):
    # Initialize the pipeline wrapper
    pipeline = PipelineWrapper()
    pipeline.setup()

    # Test with invalid jsonpath expression
    # This should not raise an exception but return an empty list
    results = pipeline.run_api("invalid_expression")
    assert len(results) == 0


def test_pipeline_shorthand_jsonpath(zotero_db):
    # Initialize the pipeline wrapper
    pipeline = PipelineWrapper()
    pipeline.setup()

    # Test that "shortTitle=TP2" is equivalent to "$.shortTitle=TP2"
    # as claimed in the pipeline wrapper's docstring
    results_with_dollar = pipeline.run_api("$.shortTitle=TP2")
    results_without_dollar = pipeline.run_api("shortTitle=TP2")

    # Both queries should return the same results
    assert len(results_with_dollar) == len(results_without_dollar)
    assert results_with_dollar[0]["key"] == results_without_dollar[0]["key"]
    assert results_with_dollar[0]["key"] == "item2"
