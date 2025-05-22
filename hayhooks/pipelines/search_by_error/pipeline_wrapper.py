import os
from typing import List, Optional

from hayhooks import log as logger
from hayhooks.server.utils.base_pipeline_wrapper import BasePipelineWrapper
from haystack import Pipeline
from haystack.components.builders.prompt_builder import PromptBuilder
from haystack.components.generators import OpenAIGenerator
from haystack.utils import Secret

from components.stackoverflow import StackOverflowErrorSearch
from resources.utils import read_resource_file


class PipelineWrapper(BasePipelineWrapper):
    """A Haystack pipeline wrapper that searches Stack Overflow for error messages."""

    def setup(self) -> None:
        #######
        # Set up the pipeline

        pipe = Pipeline()
        error_search = StackOverflowErrorSearch()
        pipe.add_component("error_search", error_search)
        template = read_resource_file("stackoverflow_prompt.md")

        # Even using Markdown, there's a large amount of context that needs to be passed in, and most
        # of it doesn't need to be passed back to the agent, so use an LLM to summarize the results.
        prompt_builder = PromptBuilder(template=template, required_variables=["query", "documents"])
        pipe.add_component("prompt_builder", prompt_builder)

        # Reuse the excerpt model....
        model = os.getenv("HAYHOOKS_EXCERPT_MODEL")
        if model is None or model == "":
            raise ValueError("No model found in HAYHOOKS_EXCERPT_MODEL environment variable!")
        llm = self.get_extract_generator(model)
        pipe.add_component("llm", llm)

        pipe.connect("error_search.documents", "prompt_builder.documents")
        pipe.connect("prompt_builder", "llm")

        self.pipeline = pipe

    def run_api(self, error_message: str, language: Optional[str] = None, technologies: Optional[List[str]] = None, min_score: Optional[int] = None, include_comments: bool = False, limit: int = 10) -> str:
        """
        Uses Stack Overflow to search for error-related questions and returns a summary of results.

        Arguments
        --------
        error_message: str
            Error message to search for.
        language: Optional[str]
            Programming language.
        technologies: Optional[List[str]]
            Related technologies
        min_score: Optional[int]
            Minimum score threshold.
        include_comments: bool
            Include comments in results, default false
        limit: int
            Maximum number of results, default 10

        Return
        -------
        str
            A summary of the results in Markdown format.
        """

        # https://github.com/gscalzo/stackoverflow-mcp/blob/main/src/index.ts#L268
        result = self.pipeline.run(
            {"error_search": {"error_message": error_message, "language": language, "technologies": technologies, "min_score": min_score, "include_comments": include_comments, "limit": limit}, "prompt_builder": {"query": error_message}}
        )
        # logger.debug(f"run_api: result = {result}")

        # return result["prompt_builder"]["prompt"]
        if "llm" in result and "replies" in result["llm"] and result["llm"]["replies"]:
            reply = result["llm"]["replies"][0]
            logger.info(f"run_api: reply is {reply}")
            return reply
        else:
            raise RuntimeError("Error: Could not retrieve answer from the pipeline.")

    def get_extract_generator(self, model) -> OpenAIGenerator:
        return OpenAIGenerator(
            api_key=Secret.from_env_var("OPENAI_API_KEY"),
            api_base_url=os.getenv("OPENAI_API_BASE"),
            model=model,
        )
