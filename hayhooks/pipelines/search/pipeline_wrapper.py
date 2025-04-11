import os
from typing import Literal, Optional, List

from hayhooks.server.logger import log
from hayhooks.server.utils.base_pipeline_wrapper import BasePipelineWrapper

from haystack import Pipeline, logging, Document
from haystack.components.builders.prompt_builder import PromptBuilder
from haystack.components.generators import OpenAIGenerator
from haystack.components.joiners import DocumentJoiner
from haystack.components.routers import ConditionalRouter
from haystack.utils import Secret

from resources.utils import read_resource_file
from components.tavily_web_search import TavilyWebSearch

logger = logging.getLogger("answer")


class PipelineWrapper(BasePipelineWrapper):
    """
    A Haystack pipeline wrapper that runs a search query.

    Input:
      question (str): The user's query to search for and answer.

    Output:
      str: The generated answer based on the web search results.
    """

    def __init__(self):
        super().__init__()
        self.template = read_resource_file("search_prompt.md")

    def setup(self) -> None:
        self.pipeline = self.create_pipeline()

    def create_pipeline(self) -> Pipeline:
        search = TavilyWebSearch()
        prompt_builder = PromptBuilder(
            template=self.template, required_variables=["query"]
        )
        llm = self.create_llm()
        joiner = DocumentJoiner()

        routes = [
            {
                "condition": '{{ search_depth == "best" }}',
                "output": "{{documents}}",
                "output_name": "search_results_full_content",
                "output_type": List[Document],
            },
            {
                "condition": "{{ True }}",
                "output": "{{documents}}",
                "output_name": "search_results",
                "output_type": List[Document],
            },
        ]
        router = ConditionalRouter(routes, unsafe=True)

        pipe = Pipeline()
        pipe.add_component("search", search)
        pipe.add_component("router", router)
        pipe.add_component("joiner", joiner)
        pipe.add_component("prompt_builder", prompt_builder)
        pipe.add_component("llm", llm)

        # Best search is https://docs.tavily.com/documentation/best-practices/best-practices-extract#2-two-step-process%3A-search%2C-then-extract
        # Extracting raw content is tricky:
        # We want to keep the score and URL of existing documents the same, but replace the content.
        # We want to fetch each URL concurrently, so either AsyncPipeline or
        # https://haystack.deepset.ai/cookbook/concurrent_tasks
        # https://haystack.deepset.ai/cookbook/async_pipeline

        # When we hook up the extract pipeline this will be uncommented
        #pipe.connect("extract.documents_plus_content", "router.documents_plus_content")
        pipe.connect("search.documents", "router.documents")
        pipe.connect("router.search_results", "joiner")
        pipe.connect("router.search_results_full_content", "joiner")
        pipe.connect("joiner.documents", "prompt_builder.documents")
        pipe.connect("prompt_builder", "llm")

        return pipe

    def create_llm(self):
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
        return llm

    def run_api(self,
                question: str,
                max_results: int, 
                search_depth: Literal["basic", "advanced", "best"] = "basic",
                include_domains: Optional[list[str]] = None,
                exclude_domains: Optional[list[str]] = None) -> str:
        """
        Runs the search pipeline to answer a given question using web search results.

        This method takes a user's question, performs a web search using Tavily,
        constructs a prompt with the search results, and generates an answer
        using an LLM. It allows customization of the search parameters.

        Parameters
        ----------
        question : str
            The user's query to search for and answer.
        max_results : int
            The maximum number of search results to retrieve from Tavily.
        search_depth : Literal["basic", "advanced", "best"], optional
            The depth of the web search.
            "basic" provides standard results and is the default.
            "advanced" uses more sophisticated techniques for higher relevance at a higher cost (2 API credits vs 1).
            "best" uses "advanced" and also extracts the raw content of all search results
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
        log.trace(f"Running answer pipeline with question: {question}")

        result = self.pipeline.run(
            {"search": {
                "query": question,
                "search_depth": search_depth,
                "max_results": max_results,
                "include_domains": include_domains,
                "exclude_domains": exclude_domains
            },
            "router": {"search_depth": search_depth},
            "prompt_builder": {"query": question}}
        )

        logger.info(f"answer: answer result from pipeline {result}")

        # Assuming the LLM component is named 'llm' and returns replies
        if "llm" in result and "replies" in result["llm"] and result["llm"]["replies"]:
            reply = result["llm"]["replies"][0]
            logger.info(f"answer: reply is {reply}")
            return reply
        else:
            # Raise a proper exception instance
            raise RuntimeError("Error: Could not retrieve answer from the pipeline.")

    # The duplicated _read_resource_file method is now removed.
