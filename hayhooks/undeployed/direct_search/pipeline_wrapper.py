from typing import Generator, List, Union, Optional

from hayhooks.server.logger import log
from hayhooks.server.utils.base_pipeline_wrapper import BasePipelineWrapper
from haystack import Pipeline
from haystack.components.builders.prompt_builder import PromptBuilder

from tavily_web_search import TavilyWebSearch

class PipelineWrapper(BasePipelineWrapper):
    """
     This pipeline searches using Tavily, and returns the document results directly.
    """

    def create_pipeline(self) -> Pipeline:
        search = TavilyWebSearch()

        prompt_template = """
{% for doc in documents %}
### {{ doc.meta }}

#### Score

{{ doc.score }}

#### URL 

{{ doc.meta.link }}

#### Content
   
{{ doc.content }}
{% endfor %}
"""
        prompt_builder = PromptBuilder(template=prompt_template)

        pipe = Pipeline()
        pipe.add_component("search", search)
        pipe.add_component("prompt_builder", prompt_builder)

        pipe.connect("search.documents", "prompt_builder.documents")

        return pipe

    def create_pipeline_args(self, query: str, include_domains: Optional[list[str]] = None) -> dict:    
        return {"search": {"query": query, "include_domains": include_domains}}

    def setup(self) -> None:    
        try:
            self.pipeline = self.create_pipeline()
        except Exception as e:
            log.error("Cannot create pipeline", e)

    def run_api(self, query: str, include_domains: Optional[list[str]] = None) -> str:
        """
        This tool calls tavily search and returns results.

        Parameters
        ----------
        query: str
            The query for Tavily Search.
        include_domains: Optional[list[str]]
            The only domains to include in the search.

        Returns
        -------
        str
            A markdown list of document results that you can process as necessary.
        """
        log.trace(f"Running pipeline with query: {query} and include_domains {include_domains}")
        try:
            result = self.pipeline.run(self.create_pipeline_args(query, include_domains))
            prompt = result["prompt_builder"]["prompt"]
            return prompt
        except Exception as e:
            log.error("Cannot create pipeline", e)
            raise e
