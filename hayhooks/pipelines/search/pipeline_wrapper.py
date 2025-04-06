import os

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

    def run_api(self, question: str) -> str:
        """
        Passes the question to an LLM Model that will search and answer the question.

        This tool is also useful for cheap summarization of a web page.

        The LLM Model is not very creative, but has a large context window, and is fast.

        Parameters
        ----------
        question: str
            The question to answer.

        Returns
        -------
        str
            The answer to the question from the LLM Model.
        """
        log.trace(f"Running answer pipeline with question: {question}")

        result = self.pipeline.run(
            {"search": {"query": question}, "prompt_builder": {"query": question}}
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
