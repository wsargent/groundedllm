import os
from typing import Generator, List, Union

from haystack import Pipeline
from haystack.components.builders.prompt_builder import PromptBuilder
from haystack.components.converters import HTMLToDocument
from haystack.components.fetchers import LinkContentFetcher
from haystack.components.generators import OpenAIGenerator
from haystack.utils import Secret

from hayhooks.server.logger import log
from hayhooks.server.utils.base_pipeline_wrapper import BasePipelineWrapper
from tavily_web_search import TavilyWebSearch


class PipelineWrapper(BasePipelineWrapper):
    """
    A Haystack pipeline wrapper that performs web searches using Tavily, fetches
    content from the resulting links, converts HTML to text documents, and then
    uses an OpenAI model to generate an answer based on the fetched content and
    the user's query.

    This pipeline is designed for scenarios where retrieving full web page content
    is preferred over relying solely on search result snippets.

    Input:
      question (str): The user's query to search for and answer.

    Output:
      str: The generated answer based on the web search results.
    """

    def create_pipeline(self) -> Pipeline:
        """
        Constructs the Haystack pipeline by defining and connecting components.

        Components:
        - TavilyWebSearch: Performs the initial web search.
        - LinkContentFetcher: Fetches content from URLs found by the search.
        - HTMLToDocument: Converts fetched HTML content into Haystack Documents.
        - PromptBuilder: Creates the prompt for the language model using a template
                         and the fetched documents.
        - OpenAIGenerator: Generates the final answer using an OpenAI model.

        Returns:
            Pipeline: The constructed Haystack pipeline instance.
        """
        search = TavilyWebSearch()
        link_content = LinkContentFetcher()
        html_converter = HTMLToDocument()

        # Note: This prompt template provides detailed instructions for the LLM,
        # including specific citation guidelines based on <source_id> tags.
        template = """
### Task:
Respond to the user query using the provided context, incorporating inline citations in the format [source_id] **only when the <source_id> tag is explicitly provided** in the context.

### Guidelines:
- If you don't know the answer, clearly state that.
- If uncertain, ask the user for clarification.
- Respond in the same language as the user's query.
- If the context is unreadable or of poor quality, inform the user and provide the best possible answer.
- If the answer isn't present in the context but you possess the knowledge, explain this to the user and provide the answer using your own understanding.
- **Only include inline citations using [source_id] when a <source_id> tag is explicitly provided in the context.**
- Do not cite if the <source_id> tag is not provided in the context.
- Do not use XML tags in your response.
- Ensure citations are concise and directly related to the information provided.

### Example of Citation:
If the user asks about a specific topic and the information is found in "whitepaper.pdf" with a provided <source_id>, the response should include the citation like so:
* "According to the study, the proposed method increases efficiency by 20% [whitepaper.pdf]."
If no <source_id> is present, the response should omit the citation.

### Output:
Provide a clear and direct response to the user's query, including inline citations in the format [source_id] only when the <source_id> tag is present in the context.

<context>
{% for document in documents %}
    {{ document.content }}
{% endfor %}
</context>

<user_query>
{{query}}
</user_query>
"""

        prompt_builder = PromptBuilder(template=template)
        llm = OpenAIGenerator(
            api_key=Secret.from_env_var("OPENAI_API_KEY"),
            api_base_url=os.getenv("OPENAI_API_BASE"),
            model=os.getenv("CHAT_MODEL")
        )

        pipe = Pipeline()
        pipe.add_component("search", search)
        pipe.add_component("fetcher", link_content)
        pipe.add_component("converter", html_converter)
        pipe.add_component("prompt_builder", prompt_builder)
        pipe.add_component("llm", llm)

        # Connect components
        pipe.connect("search.links", "fetcher.urls")
        pipe.connect("fetcher.streams", "converter.sources")
        pipe.connect("converter.documents", "prompt_builder.documents")
        pipe.connect("prompt_builder.prompt", "llm.prompt")

        return pipe

    def create_pipeline_args(self, query: str) -> dict:
        return {"search": {"query": query}, "prompt_builder": {"query": query}}

    def setup(self) -> None:
        self.pipeline = self.create_pipeline()
        log.info("Answer pipeline created successfully.")

    def run_api(self, question: str) -> str:
        """
        Passes the question to an LLM model that will do a search and extract
        the full content of the web pages, and answer the question.

        Parameters
        ----------
        question: str
            The question to answer.

        Returns
        -------
        str
            The answer to the question from the agent.
        """
        log.trace(f"Running answer pipeline with question: {question}")
        if not hasattr(self, 'pipeline') or self.pipeline is None:
             log.error("Pipeline is not initialized. Call setup() first.")
             # Or handle appropriately, maybe raise a specific error
             raise RuntimeError("Pipeline not initialized during setup.")
        try:
            result = self.pipeline.run(self.create_pipeline_args(question))
            # Assuming the LLM component is named 'llm' and returns replies
            if "llm" in result and "replies" in result["llm"] and result["llm"]["replies"]:
                return result["llm"]["replies"][0]
            else:
                log.error("Unexpected result structure from pipeline: %s", result)
                return "Error: Could not retrieve answer from the pipeline."
        except Exception as e:
            log.error("Error running answer pipeline: %s", e, exc_info=True)
            raise e # Re-raise the exception after logging
