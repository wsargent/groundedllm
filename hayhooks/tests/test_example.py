from typing import List

from haystack.components.routers import ConditionalRouter


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
