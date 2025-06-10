from haystack import Document

from components.web_search.document_extract import DocumentContentExtractor


def test_search_extraction_component():
    """Test search extraction content"""

    component = DocumentContentExtractor()
    doc = Document.from_dict({"title": "title", "content": "derp", "link": "http://example.com"})
    result = component.run(documents=[doc])
    documents = result["documents"]
    assert documents[0].content.startswith("This domain is for use")
