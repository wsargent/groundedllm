from typing import List, Dict, Any
from haystack import Pipeline
from components import MultiImageContentExtractor # Changed from hayhooks.components
from server.utils.base_pipeline_wrapper import BasePipelineWrapper # Changed from hayhooks.server

PIPELINE_NAME = "extract_image_data"

class PipelineWrapper(BasePipelineWrapper):
    # __init__ is removed. Pipeline initialization is moved to setup().
    # If BasePipelineWrapper had an __init__ requiring arguments,
    # a PipelineWrapper __init__ calling super().__init__(...) would be needed.
    # Assuming BasePipelineWrapper.__init__() is parameterless or not strictly needed here.

    def setup(self) -> None:
        """
        Initializes the Haystack pipeline. This method is expected to be called
        by the hayhooks framework after instantiation.
        """
        # super().setup() # Call if BasePipelineWrapper has a setup method.
        self.pipeline = self._create_pipeline()

    def _create_pipeline(self) -> Pipeline:
        """
        Helper method to create and configure the Haystack pipeline.
        """
        pipe = Pipeline()
        pipe.add_component("image_extractor", MultiImageContentExtractor())
        return pipe

    def run(self, urls: List[str], **kwargs) -> Dict[str, Any]:
        """
        This function is called by hayhooks to run your pipeline.
        It takes a list of URLs and returns a dictionary with the extracted
        base64 image data or an error.
        """
        if not hasattr(self, 'pipeline') or self.pipeline is None:
            # This check is a safeguard. Ideally, the framework ensures setup() is called.
            # Consider logging an error here as well.
            return {"error": "Pipeline is not initialized. Ensure setup() has been called."}

        if not urls or not isinstance(urls, list):
            return {"error": "Input 'urls' must be a non-empty list of strings."}

        if not all(isinstance(url, str) for url in urls):
            return {"error": "All items in 'urls' must be strings."}

        try:
            # The component name "image_extractor" must match the name given in _create_pipeline.
            result = self.pipeline.run(data={"image_extractor": {"urls": urls}})
        except Exception as e:
            # You might want to log the error. If BasePipelineWrapper provides a logger:
            # self.logger.error(f"Error running pipeline: {e}")
            return {"error": f"Pipeline execution failed: {str(e)}"}

        if "image_extractor" not in result or "images" not in result["image_extractor"]:
            return {"error": "Pipeline did not return the expected 'images' output."}

        image_contents = result["image_extractor"]["images"]

        base64_images: List[str] = []
        processing_errors: List[str] = []

        for img_content in image_contents:
            if hasattr(img_content, 'base64_image') and img_content.base64_image:
                base64_images.append(img_content.base64_image)
            else:
                url_source = "unknown_url"
                if hasattr(img_content, 'meta') and isinstance(img_content.meta, dict):
                    url_source = img_content.meta.get("url", "unknown_url")
                processing_errors.append(f"Could not extract base64 data for image from {url_source}.")

        output: Dict[str, Any] = {"base64_images": base64_images}
        if processing_errors:
            output["processing_errors"] = processing_errors

        return output
