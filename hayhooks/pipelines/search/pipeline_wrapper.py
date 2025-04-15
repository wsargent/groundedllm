import os

from hayhooks.server.utils.base_pipeline_wrapper import BasePipelineWrapper
from haystack import Pipeline, logging
from haystack.components.builders.prompt_builder import PromptBuilder
from haystack.components.generators import OpenAIGenerator
from haystack.utils import Secret

from components.content_extraction import build_search_extraction_component
from components.tavily_web_search import TavilyWebSearch
from resources.utils import read_resource_file

logger = logging.getLogger("answer")


class PipelineWrapper(BasePipelineWrapper):
    """A Haystack pipeline wrapper that runs a search query."""

    def setup(self) -> None:
        search = TavilyWebSearch()

        default_user_agent = os.getenv(
            "SEARCH_USER_AGENT",
            "SearchAgent.extract @ https://github.com/wsargent/groundedllm",
        )
        use_http2 = bool(os.getenv("SEARCH_HTTP2", "True"))
        retry_attempts = int(os.getenv("SEARCH_RETRY_ATTEMPTS", "3"))
        timeout = int(os.getenv("SEARCH_TIMEOUT", "3"))
        raise_on_failure = bool(os.getenv("SEARCH_RAISE_ON_FAILURE", "False"))
        content_extractor = build_search_extraction_component(
            raise_on_failure=raise_on_failure,
            user_agents=[default_user_agent],
            retry_attempts=retry_attempts,
            timeout=timeout,
            http2=use_http2,
        )

        template = read_resource_file("search_prompt.md")
        prompt_builder = PromptBuilder(template=template, required_variables=["query"])

        # This will typically use Gemini 2.0 Flash, as the LLM is fast, cheap, and has a huge context window.
        #
        # If you try searching directly using Letta and in Claude Sonnet 3.7, you'll get rate limited fairly quickly.
        #
        # RATE_LIMIT_EXCEEDED: Rate limited by Anthropic: Error code: 429...
        # This request would exceed the rate limit for your organization of 40,000 input tokens per minute
        # Revert to using os.getenv and Secret

        search_api_key = Secret.from_env_var("OPENAI_API_KEY")

        api_base_url = os.getenv("OPENAI_API_BASE")
        if api_base_url is None:
            raise ValueError("OPENAI_API_BASE environment variable is not set!")

        search_model = os.getenv("SEARCH_MODEL")
        if search_model is None:
            raise ValueError("SEARCH_MODEL environment variable is not set!")

        llm = OpenAIGenerator(api_key=search_api_key, api_base_url=api_base_url, model=search_model)

        pipe = Pipeline()
        pipe.add_component("search", search)
        pipe.add_component("content_extractor", content_extractor)
        pipe.add_component("prompt_builder", prompt_builder)
        pipe.add_component("llm", llm)

        # Connect components
        pipe.connect("search.documents", "content_extractor.documents")
        pipe.connect("content_extractor.documents", "prompt_builder.documents")
        # pipe.connect("search.documents", "prompt_builder.documents")
        pipe.connect("prompt_builder", "llm")

        self.pipeline = pipe

    def run_api(
        self,
        question: str,
        max_results: int = 5,
        search_depth: str = "basic",
        include_domains: str = "",
        exclude_domains: str = "",
    ) -> str:
        """Run the search pipeline to answer a given question using web search results.

        This method takes a user's question, performs a web search using Tavily,
        constructs a prompt with the search results, and generates an answer
        using an LLM. It allows customization of the search parameters.

        Parameters
        ----------
        question : str
            The user's query to search for and answer.
        max_results : int
            The maximum number of search results to retrieve from Tavily.
            Set this to 5 unless you specifically want more documents.
        search_depth : str
            The depth of the web search: "basic" or "advanced".
            Using "basic" provides standard results.
            Using "advanced" is higher relevance at a higher cost (2 API credits vs 1).
        include_domains : str
            A list of domains to specifically include in the search results.
            Use "" to ignore this argument.
        exclude_domains : str
            A list of domains to specifically exclude from the search results.
            Use "" to ignore this argument.

        Returns
        -------
        str
            The generated answer based on the web search results.

        Raises
        ------
        RuntimeError
            If the pipeline fails to retrieve an answer from the LLM.

        """
        logger.debug(f"Running answer pipeline with question: {question}")

        result = self.pipeline.run(
            {
                "search": {
                    "query": question,
                    "search_depth": search_depth,
                    "max_results": max_results,
                    "include_domains": include_domains if include_domains != "" else None,
                    "exclude_domains": exclude_domains if exclude_domains != "" else None,
                },
                "prompt_builder": {"query": question},
            }
        )

        # logger.debug(f"answer: answer result from pipeline {result}")
        if "llm" in result and "replies" in result["llm"] and result["llm"]["replies"]:
            reply = result["llm"]["replies"][0]
            logger.info(f"answer: reply is {reply}")
            return reply
        else:
            raise RuntimeError(f"Error: Could not retrieve answer from the pipeline. {result}")
