from typing import List

from haystack import Document
from haystack.components.routers import ConditionalRouter

from components.content_extraction import build_search_extraction_component


def test_conditional_router():
    """Test conditional router works."""
    routes = [
        {
            "condition": "{{streams|length > 2}}",
            "output": "{{streams}}",
            "output_name": "enough_streams",
            "output_type": List[int],
        },
        {
            "condition": "{{streams|length <= 2}}",
            "output": "{{streams}}",
            "output_name": "insufficient_streams",
            "output_type": List[int],
        },
    ]
    router = ConditionalRouter(routes)
    kwargs = {"streams": [1, 2, 3], "query": "Haystack"}
    result = router.run(**kwargs)

    assert result["enough_streams"] == [1, 2, 3]


def test_search_extraction_component():
    """Test search extraction content"""

    component = build_search_extraction_component()

    doc = Document.from_dict({"title": "title", "content": "derp", "link": "http://example.com"})
    kwargs = {"documents": [doc]}
    # This should produce an array containing the contents of example.com
    result = component.run(**kwargs)
    print(result)
    assert result["contents"][0].startswith("This domain is for use")
