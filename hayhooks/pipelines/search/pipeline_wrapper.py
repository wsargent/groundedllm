import os
from typing import List, Literal, Optional

from hayhooks.server.logger import log
from hayhooks.server.utils.base_pipeline_wrapper import BasePipelineWrapper
from haystack import Pipeline, logging
from haystack.components.builders.prompt_builder import PromptBuilder
from haystack.components.converters import HTMLToDocument
from haystack.components.fetchers import LinkContentFetcher
from haystack.components.generators import OpenAIGenerator
from haystack.components.preprocessors import DocumentCleaner
from haystack.components.routers import ConditionalRouter
from haystack.dataclasses import Document
from haystack.utils import Secret

from components.tavily_web_search import TavilyWebSearch
from resources.utils import read_resource_file

logger = logging.getLogger("search")


class PipelineWrapper(BasePipelineWrapper):
    """
    A Haystack pipeline wrapper that runs a search query.
    """

    def setup(self) -> None:
        self.template = read_resource_file("search_prompt.md")
        self.pipeline = self.create_pipeline()

    def create_pipeline(self) -> Pipeline:
        search = TavilyWebSearch()
        prompt_builder = PromptBuilder(
            template=self.template, required_variables=["query"]
        )

        # This will typically use Gemini 2.0 Flash, as the LLM is fast, cheap, and has a huge context window.
        #
        # If you try searching directly using Letta and in Claude Sonnet 3.7, you'll get rate limited fairly quickly, i.e.
        #
        # RATE_LIMIT_EXCEEDED: Rate limited by Anthropic: Error code: 429...
        # This request would exceed the rate limit for your organization of 40,000 input tokens per minute
        # Revert to using os.getenv and Secret
        llm = OpenAIGenerator(
            api_key=Secret.from_env_var("OPENAI_API_KEY"),
            api_base_url=os.getenv("OPENAI_API_BASE"),
            model=os.getenv("SEARCH_MODEL"),
        )

        # Extraction components (for the 'advanced' path)
        fetcher = LinkContentFetcher()
        converter = HTMLToDocument()
        cleaner = DocumentCleaner()

        # Define routes for the ConditionalRouter
        routes = [
            {
                # If search_depth is 'advanced', extract URLs and send them to the fetcher
                "condition": "{{ search_depth == 'advanced' }}",
                "output": "{{ documents | map(attribute='meta.url') | list }}",
                "output_name": "urls_to_fetch",
                "output_type": List[str],
            },
            {
                # If search_depth is 'basic', pass the original documents directly
                "condition": "{{ search_depth == 'basic' }}",
                "output": "{{ documents }}",
                "output_name": "basic_documents",
                "output_type": List[Document],
            },
        ]
        router = ConditionalRouter(routes=routes)

        # Build the pipeline
        pipe = Pipeline()
        pipe.add_component("search", search)
        pipe.add_component("router", router)
        pipe.add_component("fetcher", fetcher)
        pipe.add_component("converter", converter)
        pipe.add_component("cleaner", cleaner)
        pipe.add_component("prompt_builder", prompt_builder)
        pipe.add_component("llm", llm)

        # Connect components
        # Input documents and search_depth go to the router
        pipe.connect("search.documents", "router.documents")
        # Note: TavilyWebSearch doesn't output search_depth, it's an input.
        # We'll pass search_depth directly to the router in the run_api method.

        # Advanced path: router -> fetcher -> converter -> cleaner -> prompt_builder
        pipe.connect("router.urls_to_fetch", "fetcher.urls")
        pipe.connect("fetcher.streams", "converter.sources")
        pipe.connect("converter.documents", "cleaner.documents")
        pipe.connect("cleaner.documents", "prompt_builder.documents")

        # Basic path: router -> prompt_builder
        pipe.connect("router.basic_documents", "prompt_builder.documents")

        # Final connection to LLM
        pipe.connect("prompt_builder", "llm")

        return pipe

    def run_api(
        self,
        question: str,
        max_results: int,
        search_depth: Literal["basic", "advanced"] = "basic",
        include_domains: Optional[list[str]] = None,
        exclude_domains: Optional[list[str]] = None,
    ) -> str:
        """
        Runs the search pipeline to answer a given question using web search results.

        This method takes a user's question and performs a web search using Tavily.
        Based on the `search_depth` parameter, it either uses the initial search result
        snippets ("basic") or fetches and cleans the full content of the linked web pages
        ("advanced"). It then constructs a prompt with the selected documents and
        generates an answer using an LLM. Allows customization of search parameters.

        Parameters
        ----------
        question : str
            The user's query to search for and answer.
        max_results : int
            The maximum number of search results to retrieve from Tavily.
        search_depth : Literal["basic", "advanced"], optional
            Controls the search behavior. "basic" uses document snippets from the initial
            search. "advanced" does a deeper search for context, and also fetches and
            cleans the full content from result URLs, providing more context but potentially
            taking longer. Defaults to "basic".
        include_domains : Optional[list[str]], optional
            A list of domains to specifically include in the search results. Defaults to None.
        exclude_domains : Optional[list[str]], optional
            A list of domains to specifically exclude from the search results. Defaults to None.

        Returns
        -------
        str
            The generated answer based on the web search results.

        Raises
        ------
        RuntimeError
            If the pipeline fails to retrieve an answer from the LLM.
        """
        log.trace(f"Running search pipeline with question: {question}")

        result = self.pipeline.run(
            {
                "search": {
                    "query": question,
                    "search_depth": search_depth,
                    "max_results": max_results,
                    "include_domains": include_domains,
                    "exclude_domains": exclude_domains,
                },
                "router": {
                    "search_depth": search_depth
                },
                "prompt_builder": {"query": question},
            }
        )

        logger.info(f"search: search result from pipeline {result}")

        if "llm" in result and "replies" in result["llm"] and result["llm"]["replies"]:
            reply = result["llm"]["replies"][0]
            logger.info(f"search: reply is {reply}")
            return reply
        else:
            raise RuntimeError("Error: Could not retrieve answer from the pipeline.")
