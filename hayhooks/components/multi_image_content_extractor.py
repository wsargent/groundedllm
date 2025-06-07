from typing import List

from haystack import component
from haystack.components.fetchers.link_content import LinkContentFetcher
from haystack_experimental.components.image_converters import ImageFileToImageContent
from haystack_experimental.dataclasses import ImageContent


@component
class MultiImageContentExtractor:
    """
    Extracts image contents from a list of URLs.
    It uses LinkContentFetcher to download the content from URLs and
    ImageFileToImageContent to convert the downloaded content into ImageContent objects.
    """

    @component.output_types(images=list[ImageContent])
    def run(self, urls: List[str]):
        """
        Fetches images from the given URLs and converts them to ImageContent objects.

        :param urls: A list of URLs to fetch images from.
        :return: A dictionary containing a list of ImageContent objects under the key "images".
        """
        fetcher = LinkContentFetcher(raise_on_failure=True, retry_attempts=3, timeout=10)
        # The LinkContentFetcher returns a dictionary with a "streams" key
        # that contains a list of ByteStream objects.
        fetched_data = fetcher.run(urls=urls)
        streams = fetched_data["streams"]

        # ImageFileToImageContent expects a list of sources (ByteStream) and a list of metadata.
        # We'll pass an empty list for metadata for now, as the basic requirement
        # is to convert URLs to ImageContent.
        # Each ByteStream object in `streams` already carries its own metadata (like the URL).
        # The ImageFileToImageContent component should ideally propagate or use this existing metadata.
        converter = ImageFileToImageContent()

        # The 'meta' parameter in converter.run() is used to pass a list of dictionaries,
        # where each dictionary is used as metadata for the corresponding ImageContent object.
        # If we want to pass specific metadata for each image, we would need to construct
        # a list of dictionaries here, corresponding to each stream.
        # For now, we'll pass an empty list, which means no *additional* metadata is added
        # by this step, but the metadata from the ByteStream (like the URL) should still be there.
        # Update: Pass a list of empty dicts for meta, one for each stream, as per component requirements.
        meta_list = [{}] * len(streams)
        image_contents_result = converter.run(sources=streams, meta=meta_list)

        return {"images": image_contents_result["images"]}
