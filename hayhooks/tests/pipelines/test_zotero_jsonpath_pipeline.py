import json
import os
import sqlite3
import tempfile

import pytest

from components.zotero import ZoteroDatabase
from pipelines.search_zotero.pipeline_wrapper import PipelineWrapper


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
    json_results = pipeline.run_api({"shortTitle": "TP1"})
    results = json.loads(json_results)
    assert len(results) == 1
    assert results[0].get("key") == "item1"


def test_pipeline_search_by_title(zotero_db):
    # Initialize the pipeline wrapper
    pipeline = PipelineWrapper()
    pipeline.setup()

    # Test searching by title
    json_results = pipeline.run_api({"title": "Another Paper"})
    results = json.loads(json_results)
    assert len(results) == 1
    assert results[0]["key"] == "item3"


def test_pipeline_search_by_doi(zotero_db):
    # Initialize the pipeline wrapper
    pipeline = PipelineWrapper()
    pipeline.setup()

    # Test searching by DOI
    json_results = pipeline.run_api({"DOI": "10.1234/test1"})
    results = json.loads(json_results)
    assert len(results) == 1
    assert results[0]["key"] == "item1"


def test_pipeline_search_no_results(zotero_db):
    # Initialize the pipeline wrapper
    pipeline = PipelineWrapper()
    pipeline.setup()

    # Test searching with no matches
    json_results = pipeline.run_api({"shortTitle": "NonExistent"})
    results = json.loads(json_results)
    assert len(results) == 0


def test_pipeline_invalid_query(zotero_db):
    # Initialize the pipeline wrapper
    pipeline = PipelineWrapper()
    pipeline.setup()

    # Test with invalid query object
    # This should not raise an exception but return an empty list
    json_results = pipeline.run_api({})
    results = json.loads(json_results)
    assert len(results) == 0


def test_pipeline_multiple_query_objects(zotero_db):
    # Initialize the pipeline wrapper
    pipeline = PipelineWrapper()
    pipeline.setup()

    # Test with multiple query objects that should match one item
    json_results = pipeline.run_api([{"title": "Test Paper 1"}, {"DOI": "10.1234/test1"}])
    results1 = json.loads(json_results)
    assert len(results1) == 1
    assert results1[0]["key"] == "item1"

    # Test with multiple query objects that should not match any items
    results2 = pipeline.run_api([{"title": "Test Paper 1"}, {"DOI": "10.1234/test2"}])
    assert len(json.loads(results2)) == 0

    # Test with multiple fields in a single query object
    single_query = pipeline.run_api({"title": "Test Paper 2", "DOI": "10.1234/test2"})
    result = json.loads(single_query)
    assert len(result) == 1
    assert result[0]["key"] == "item2"
