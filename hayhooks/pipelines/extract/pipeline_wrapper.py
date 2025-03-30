from hayhooks.server.logger import log
from hayhooks.server.utils.base_pipeline_wrapper import BasePipelineWrapper
from typing import Generator, List, Union

from haystack import Pipeline

from haystack.components.fetchers import LinkContentFetcher
from haystack.components.converters import HTMLToDocument
 
# This pipeline turns HTML into Markdown
class PipelineWrapper(BasePipelineWrapper):

    def create_pipeline(self) -> Pipeline:
        fetcher = LinkContentFetcher()

        # TODO add PDF support
        converter = HTMLToDocument()

        pipe = Pipeline()
        pipe.add_component("fetcher", fetcher)
        pipe.add_component("converter", converter)
        pipe.connect("fetcher.streams", "converter.sources")
        
        return pipe

    def create_pipeline_args(self, urls: list[str]) -> dict:    
        return {"fetcher": {"urls": urls}}

    def setup(self) -> None:    
        try:
            self.pipeline = self.create_pipeline()
        except Exception as e:
            log.error("Cannot create pipeline", e)

    def run_api(self, url: str) -> str:
        log.trace(f"Running pipeline with url: {url}")
        try:
            result = self.pipeline.run(self.create_pipeline_args([url]))
            return result["converter"]["documents"][0]
        except Exception as e:
            log.error("Cannot create pipeline", e)
            raise e         
        
    def run_chat_completion(self, model: str, messages: List[dict], body: dict) -> Union[str, Generator]:    
        return "This pipeline turns HTML into markdown and has no chat capabilities."