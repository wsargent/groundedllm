import os
from typing import Any, Dict, List, Optional

from hayhooks import log as logger
from hayhooks.server.utils.base_pipeline_wrapper import BasePipelineWrapper
from haystack import Pipeline
from haystack.components.builders.prompt_builder import PromptBuilder
from haystack.components.generators.openai import OpenAIGenerator
from haystack.dataclasses.document import Document
from haystack.utils.auth import Secret

from components.google.google_mail_reader import GoogleMailReader
from resources.utils import read_resource_file

# Define a default URI for problem details
DEFAULT_PROBLEM_TYPE_URI = "urn:hayhooks:google:mail:error:"  # Consistent with GoogleMailReader


class PipelineWrapper(BasePipelineWrapper):
    """
    Pipeline wrapper for the 'search_emails' MCP tool.
    Searches Google Mail messages based on a query and other criteria,
    then filters them using an LLM based on an instruction.
    """

    def __init__(self):
        super().__init__()
        self.template = read_resource_file("search_email_prompt.md")

    def setup(self) -> None:
        logger.info("Setting up SearchEmails pipeline...")

        pipe = Pipeline()
        mail_lister = GoogleMailReader()  # OAuth handled internally
        # The prompt_builder will receive 'documents' from mail_lister
        # and 'query' from the run_api's 'instruction' input.
        prompt_builder = PromptBuilder(template=self.template, required_variables=["query", "documents"])

        model_name = os.getenv("HAYHOOKS_SEARCH_EMAIL_MODEL")
        if not model_name:
            # Fallback or raise error if critical
            logger.error("HAYHOOKS_SEARCH_EMAIL_MODEL environment variable not set.")
            raise ValueError("HAYHOOKS_SEARCH_EMAIL_MODEL environment variable not set.")

        llm = self.get_llm_generator(model_name)
        logger.info(f"Using search email model: {model_name}")

        pipe.add_component("mail_lister", mail_lister)
        pipe.add_component("prompt_builder", prompt_builder)
        pipe.add_component("llm", llm)

        pipe.connect("mail_lister.messages", "prompt_builder.documents")
        # The prompt_builder's output is 'prompt', which goes to the llm's 'prompt' input.
        pipe.connect("prompt_builder.prompt", "llm.prompt")

        self.pipeline = pipe
        logger.info("SearchEmails pipeline setup complete.")

    def get_llm_generator(self, model: str) -> OpenAIGenerator:
        return OpenAIGenerator(
            api_key=Secret.from_env_var("OPENAI_API_KEY"),
            api_base_url=os.getenv("OPENAI_API_BASE"),  # Optional: if using a custom base URL
            model=model,
        )

    def run_api(  # type: ignore # To suppress incompatible override if Base uses **kwargs
        self,
        user_id: str,
        query: Optional[str] = None,  # Gmail search query
        instruction: Optional[str] = None,  # LLM instruction
        label_ids: Optional[List[str]] = None,
        max_results: int = 25,
        page_token: Optional[str] = None,
        include_spam_trash: bool = False,
        # Removed **kwargs
    ) -> Dict[str, Any]:
        """Searches Google Mail messages and optionally filters them using an LLM.

        Parameters
        ----------
        user_id : str
            The Google user ID.
        query : Optional[str]
            Gmail search query (e.g., "from:example@example.com subject:important").
            Can be an empty string to fetch all mail (respecting other filters).
            Defaults to None.
        instruction : Optional[str]
            An instruction for the LLM to filter the retrieved emails and return a
            condensed summary of the relevant ones, e.g., "Summarize emails
            discussing the Q3 budget." If not provided, all retrieved emails
            will be returned without LLM filtering/summarization, formatted as a
            single string. Defaults to None.
        label_ids : Optional[List[str]]
            List of label IDs to filter by. Defaults to None.
        max_results : int
            Maximum number of messages to return from Gmail. Defaults to 25.
        page_token : Optional[str]
            Token for fetching the next page of Gmail results. Defaults to None.
        include_spam_trash : bool
            Whether to include messages from SPAM and TRASH in Gmail search.
            Defaults to False.

        Returns
        -------
        Dict[str, Any]
            A dictionary containing:
            - 'filtered_emails' (str): The LLM's summarized response if an
              instruction is provided, or all formatted emails if no instruction.
            - 'original_message_count' (int): The number of messages originally
              retrieved from Gmail.
            - 'next_page_token' (Optional[str]): Token for fetching the next
              page of results, if available.
            Alternatively, an RFC 7807 problem details dictionary in case of an error.
        """
        if not self.pipeline:
            logger.error("SearchEmails pipeline is not configured correctly.")
            raise RuntimeError("Pipeline not configured.")

        if not user_id:
            logger.warning("SearchEmails called without a user_id.")
            return {
                "type": f"{DEFAULT_PROBLEM_TYPE_URI}InvalidInputError",
                "title": "Invalid Input",
                "status": 400,
                "detail": "The 'user_id' parameter is required.",
                "instance": "/gmail/search/errors/missing-user-id",
            }

        logger.debug(
            f"Running search_emails with user_id='{user_id}', gmail_query='{query}', "
            f"llm_instruction='{instruction if instruction else 'None'}' "
            f"label_ids='{label_ids}', max_results={max_results}, page_token='{page_token}', "
            f"include_spam_trash={include_spam_trash}"
        )

        try:
            if not instruction:
                # No instruction provided, skip LLM filtering
                logger.info("No instruction provided, skipping LLM filtering and returning all fetched emails.")
                mail_lister_params = {
                    "user_id": user_id,
                    "query": query,
                    "label_ids": label_ids,
                    "max_results": max_results,
                    "page_token": page_token,
                    "include_spam_trash": include_spam_trash,
                }

                # Get the mail_lister component and run it directly
                mail_lister_comp = self.pipeline.get_component("mail_lister")
                if not mail_lister_comp:
                    logger.error("Mail lister component not found in pipeline during no-instruction run.")
                    return {
                        "type": f"{DEFAULT_PROBLEM_TYPE_URI}ConfigurationError",
                        "title": "Pipeline Configuration Error",
                        "status": 500,
                        "detail": "Mail lister component is missing from the pipeline.",
                        "instance": "/gmail/search/errors/missing-mail-lister-component",
                    }

                mail_lister_output = mail_lister_comp.run(**mail_lister_params)

                # Check if mail_lister itself returned an error
                if isinstance(mail_lister_output, dict) and "status" in mail_lister_output and "title" in mail_lister_output and "type" in mail_lister_output:
                    logger.warning(f"SearchEmails mail_lister component returned an RFC 7807 problem (no-instruction path): {mail_lister_output}")
                    return mail_lister_output

                messages = mail_lister_output.get("messages", [])
                next_page = mail_lister_output.get("next_page_token")

                formatted_emails_text = self._format_messages_as_string(messages)

                return {"filtered_emails": formatted_emails_text, "original_message_count": len(messages), "next_page_token": next_page}
            else:
                # Instruction provided, proceed with LLM filtering
                pipeline_input = {
                    "mail_lister": {
                        "user_id": user_id,
                        "query": query,  # Query for Gmail API
                        "label_ids": label_ids,
                        "max_results": max_results,
                        "page_token": page_token,
                        "include_spam_trash": include_spam_trash,
                    },
                    "prompt_builder": {  # 'query' for prompt_builder is the 'instruction' from run_api
                        "query": instruction
                    },
                }

                component_result = self.pipeline.run(pipeline_input)
                logger.debug(f"Raw result from SearchEmails pipeline run (with instruction): {component_result}")

                mail_lister_output = component_result.get("mail_lister", {})
                if isinstance(mail_lister_output, dict) and "status" in mail_lister_output and "title" in mail_lister_output and "type" in mail_lister_output:
                    logger.warning(f"SearchEmails mail_lister component returned an RFC 7807 problem: {mail_lister_output}")
                    return mail_lister_output

                original_messages = mail_lister_output.get("messages", [])
                next_page_token_from_lister = mail_lister_output.get("next_page_token")

                llm_output = component_result.get("llm", {})
                if "replies" in llm_output and llm_output["replies"]:
                    filtered_emails_text = llm_output["replies"][0]

                    final_response = {"filtered_emails": filtered_emails_text, "original_message_count": len(original_messages), "next_page_token": next_page_token_from_lister}
                    logger.info(f"SearchEmails pipeline successfully processed request. LLM returned filtered content. Original messages: {len(original_messages)}.")
                    return final_response
                else:
                    logger.error(f"LLM component did not return expected 'replies': {llm_output}", exc_info=True)
                    return {
                        "type": f"{DEFAULT_PROBLEM_TYPE_URI}LLMProcessingError",
                        "title": "LLM Processing Error",
                        "status": 500,
                        "detail": "The LLM component did not return the expected output structure after processing.",
                        "instance": "/gmail/search/errors/llm-output-error",
                    }
        except Exception as e:
            logger.error(f"Unexpected error in SearchEmails pipeline execution: {e}", exc_info=True)
            return {
                "type": f"{DEFAULT_PROBLEM_TYPE_URI}InternalServerError",
                "title": "Internal Server Error",
                "status": 500,
                "detail": f"An unexpected error occurred in the SearchEmails pipeline: {str(e)}",
                "instance": "/gmail/search/errors/pipeline-unexpected-error",
            }

    def _format_messages_as_string(self, messages: List[Document]) -> str:  # messages are Haystack Documents
        if not messages:
            return ""

        email_strings = []
        for doc in messages:  # Assuming doc is a Haystack Document
            meta = doc.meta if doc.meta else {}
            subject = meta.get("subject", "N/A")
            sender = meta.get("sender", "N/A")
            date = meta.get("date", "N/A")
            snippet = meta.get("snippet", "N/A")
            content = doc.content if doc.content else "N/A"

            email_strings.append(f"Subject: {subject}\nFrom: {sender}\nDate: {date}\nSnippet: {snippet}\nContent: {content}")
        return "\n---\n".join(email_strings)
