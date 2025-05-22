import os

from hayhooks import log as logger
from hayhooks.server.utils.base_pipeline_wrapper import BasePipelineWrapper
from haystack import Pipeline
from haystack.components.builders.prompt_builder import PromptBuilder
from haystack.components.generators import OpenAIGenerator
from haystack.utils import Secret

from components.stackoverflow import StackOverflowStackTraceAnalyzer
from resources.utils import read_resource_file


class PipelineWrapper(BasePipelineWrapper):
    """A Haystack pipeline wrapper that runs an analyze stacktrace."""

    def __init__(self):
        super().__init__()
        self.template = read_resource_file("stackoverflow_prompt.md")

    def setup(self) -> None:
        #######
        # Set up the pipeline

        pipe = Pipeline()
        stacktrace_analyzer = StackOverflowStackTraceAnalyzer()
        pipe.add_component("stacktrace_analyzer", stacktrace_analyzer)

        # Even using Markdown, there's a large amount of context that needs to be passed in, and most
        # of it doesn't need to be passed back to the agent, so use an LLM to summarize the results.
        prompt_builder = PromptBuilder(template=self.template, required_variables=["query", "documents"])
        pipe.add_component("prompt_builder", prompt_builder)

        # Reuse the excerpt model....
        model = os.getenv("HAYHOOKS_EXCERPT_MODEL")
        if model is None or model == "":
            raise ValueError("No model found in HAYHOOKS_EXCERPT_MODEL environment variable!")
        llm = self.get_extract_generator(model)
        pipe.add_component("llm", llm)

        pipe.connect("stacktrace_analyzer.documents", "prompt_builder.documents")
        pipe.connect("prompt_builder", "llm")

        self.pipeline = pipe

    def run_api(self, stack_trace: str, language: str, limit: int = 10) -> str:
        """
        Analyzes the provided stack trace in the specified programming language and formats the response as markdown.

        The analysis can optionally be constrained to a specified limit.

        :param stack_trace: The stack trace string to be analyzed during execution.
        :type stack_trace: str

        :param language: The programming language of the stack trace.
        :type language: str

        :param limit: Limit the analysis or size of the output, 10 by default.
        :type limit: int

        :return: The result of the stack trace analysis in markdown format.
        :rtype: str
        """
        logger.debug(f"Running stacktrace analyze pipeline with stack_trace: {stack_trace}")

        result = self.pipeline.run({"stacktrace_analyzer": {"stack_trace": stack_trace, "language": language, "include_comments": False, "limit": limit}, "prompt_builder": {"query": stack_trace}})
        logger.debug(f"result = {result}")

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
