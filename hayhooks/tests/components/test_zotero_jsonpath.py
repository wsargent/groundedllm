import json
import os
import sqlite3
import tempfile

import pytest

from components.zotero import ZoteroDatabase


@pytest.fixture
def zotero_db():
    # Create a temporary database file
    temp_db = tempfile.NamedTemporaryFile(delete=False)
    db_path = temp_db.name
    temp_db.close()

    # Initialize the database
    db = ZoteroDatabase(db_file=db_path)

    # Create a connection to the database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Insert some test data
    test_items = [
        {
            "key": "item1",
            "data": {
                "dateModified": "2023-01-01",
                "title": "Test Paper 1",
                "shortTitle": "TP1",
                "url": "https://example.com/paper1",
                "DOI": "10.1234/test1",
                "creators": [{"firstName": "John", "lastName": "Smith", "creatorType": "author"}, {"firstName": "Charlie", "lastName": "Brooker", "creatorType": "author"}],
            },
        },
        {
            "key": "item2",
            "data": {"dateModified": "2023-01-02", "title": "Test Paper 2", "shortTitle": "TP2", "url": "https://example.com/paper2", "DOI": "10.1234/test2", "creators": [{"firstName": "Jane", "lastName": "Doe", "creatorType": "author"}]},
        },
        {
            "key": "item3",
            "data": {
                "dateModified": "2023-01-03",
                "title": "Another Paper",
                "shortTitle": "AP",
                "url": "https://example.com/paper3",
                "DOI": "10.1234/test3",
                "creators": [{"firstName": "Alice", "lastName": "Johnson", "creatorType": "author"}, {"firstName": "Bob", "lastName": "Brooker", "creatorType": "editor"}],
            },
        },
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

    yield db

    # Cleanup
    os.unlink(db_path)


def test_search_by_short_title(zotero_db):
    # Test searching by shortTitle
    results = zotero_db.find_items_by_mongo_query({"shortTitle": "TP1"})
    assert len(results) == 1
    assert results[0]["key"] == "item1"

    # Test searching by shortTitle with another value
    results = zotero_db.find_items_by_mongo_query({"shortTitle": "TP2"})
    assert len(results) == 1
    assert results[0]["key"] == "item2"


def test_search_by_title(zotero_db):
    # Test searching by title
    results = zotero_db.find_items_by_mongo_query({"title": "Another Paper"})
    assert len(results) == 1
    assert results[0]["key"] == "item3"


def test_search_by_doi(zotero_db):
    # Test searching by DOI
    results = zotero_db.find_items_by_mongo_query({"DOI": "10.1234/test1"})
    assert len(results) == 1
    assert results[0]["key"] == "item1"


def test_search_no_results(zotero_db):
    # Test searching with no matches
    results = zotero_db.find_items_by_mongo_query({"shortTitle": "NonExistent"})
    assert len(results) == 0


def test_invalid_query(zotero_db):
    # Test with invalid query object
    results = zotero_db.find_items_by_mongo_query({})
    assert len(results) == 0


def test_search_by_creator_lastname(zotero_db):
    results = zotero_db.find_items_by_mongo_query({"creators.lastName": "Brooker"})
    assert len(results) == 2
    assert "item1" in [item["key"] for item in results]
    assert "item3" in [item["key"] for item in results]


def test_search_with_multiple_expressions(zotero_db):
    # Test searching with multiple query objects (logical AND)
    results = zotero_db.find_items_by_mongo_query([{"title": "Test Paper 1"}, {"DOI": "10.1234/test1"}])
    assert len(results) == 1
    assert results[0]["key"] == "item1"

    # Test with no matches (one condition matches, the other doesn't)
    results = zotero_db.find_items_by_mongo_query([{"title": "Test Paper 1"}, {"DOI": "10.1234/test2"}])
    assert len(results) == 0

    # Test with multiple expressions including array query
    results = zotero_db.find_items_by_mongo_query([{"creators.lastName": "Brooker"}, {"title": "Another Paper"}])
    assert len(results) == 1
    assert results[0]["key"] == "item3"
