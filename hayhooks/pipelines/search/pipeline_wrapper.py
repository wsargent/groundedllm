import os
from typing import Literal, Optional

from hayhooks.server.logger import log
from hayhooks.server.utils.base_pipeline_wrapper import BasePipelineWrapper

from haystack import Pipeline, logging
from haystack.components.builders.prompt_builder import PromptBuilder
from haystack.components.generators import OpenAIGenerator
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

    def setup(self) -> None:
        # Removed settings instantiation
        # Use the imported utility function
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

        pipe = Pipeline()
        pipe.add_component("search", search)
        pipe.add_component("prompt_builder", prompt_builder)
        pipe.add_component("llm", llm)

        # Connect components
        pipe.connect("search.documents", "prompt_builder.documents")
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

        This method takes a user's question, performs a web search using Tavily,
        constructs a prompt with the search results, and generates an answer
        using an LLM. It allows customization of the search parameters.

        Parameters
        ----------
        question : str
            The user's query to search for and answer.
        max_results : int
            The maximum number of search results to retrieve from Tavily.
        search_depth : Literal["basic", "advanced"], optional
            The depth of the web search. "basic" provides standard results,
            while "advanced" uses more sophisticated techniques for higher relevance
            at a higher cost (2 API credits vs 1). Defaults to "basic".
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
            {
                "search": {
                    "query": question,
                    "search_depth": search_depth,
                    "max_results": max_results,
                    "include_domains": include_domains,
                    "exclude_domains": exclude_domains,
                },
                "prompt_builder": {"query": question},
            }
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
