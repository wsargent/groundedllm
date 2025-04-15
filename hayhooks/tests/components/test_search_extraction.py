from haystack import Document

from components.content_extraction import build_search_extraction_component


def test_search_extraction_component():
    """Test search extraction content"""

    component = build_search_extraction_component()
    doc = Document.from_dict({"title": "title", "content": "derp", "link": "http://example.com"})
    kwargs = {"documents": [doc]}
    result = component.run(**kwargs)
    contents = result["contents"]
    assert contents[0].startswith("This domain is for use")
