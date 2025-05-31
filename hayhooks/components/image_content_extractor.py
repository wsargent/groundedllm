from typing import List

from haystack import component
from haystack.components.fetchers.link_content import LinkContentFetcher
from haystack_experimental.components.image_converters import ImageFileToImageContent
from haystack_experimental.dataclasses import ImageContent


@component
class ImageContentExtractor:
    """
    Extracts image contents from a list URL.
    """

    @component.output_types(images=list[ImageContent])
    def run(self, urls: List[str]):
        fetcher = LinkContentFetcher(raise_on_failure=True, retry_attempts=3, timeout=10)
        streams = fetcher.run(urls=urls)["streams"]
        converter = ImageFileToImageContent()
        metas = []
        result = converter.run(sources=streams, meta=metas)
        return {"images": result}
