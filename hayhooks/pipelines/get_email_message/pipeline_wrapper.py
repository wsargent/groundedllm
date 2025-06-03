from typing import Any, Dict

from hayhooks import log as logger
from hayhooks.server.utils.base_pipeline_wrapper import BasePipelineWrapper
from haystack import Pipeline

from components.google.google_mail_message_getter import GoogleMailMessageGetter

# Define a default URI for problem details
DEFAULT_PROBLEM_TYPE_URI = "urn:hayhooks:google:mail:error:"  # Consistent with GoogleMailReader


class PipelineWrapper(BasePipelineWrapper):
    """
    Pipeline wrapper for the 'get_email_message' MCP tool.
    Fetches a single Google Mail message by its ID.
    """

    def setup(self) -> None:
        logger.info("Setting up GetEmailMessage pipeline...")

        pipe = Pipeline()
        mail_getter = GoogleMailMessageGetter()
        pipe.add_component("mail_getter", mail_getter)
        self.pipeline = pipe
        logger.info("GetEmailMessage pipeline setup complete.")

    def run_api(
        self,
        user_id: str,
        message_id: str,
        mail_format: str = "full",  # 'full', 'metadata', 'raw', 'minimal'
    ) -> Dict[str, Any]:
        """
        Fetches a single Google Mail message.

        Args:
            user_id: The user id.
            message_id: The ID of the email message to retrieve.
            mail_format: The format to return the message in.

        Returns:
            A dictionary containing the 'message' (haystack.dataclasses.Document) or an RFC 7807 error object.
        """
        if not self.pipeline:
            logger.error("GetEmailMessage pipeline is not configured correctly.")
            # This will be caught by Hayhooks and turned into a 500
            raise RuntimeError("Pipeline not configured.")

        logger.debug(f"Running get_email_message with user_id='{user_id}', message_id='{message_id}', format='{mail_format}'")

        try:
            # GoogleMailReader's run method expects 'action' and 'action_params'
            pipeline_input = {
                "mail_getter": {
                    "user_id": user_id,
                    "message_id": message_id,
                    "mail_format": mail_format,
                }
            }

            component_result = self.pipeline.run(pipeline_input)
            logger.debug(f"Raw result from GetEmailMessage pipeline run: {component_result}")

            mail_getter_output = component_result.get("mail_getter", {})  # This is Dict[str, Optional[Document]] or RFC error

            # The GoogleMailMessageGetter.run now returns a dictionary like:
            # {"message": Document_instance} if found,
            # {"message": None} if not found (due to ResourceNotFoundError being caught and handled inside get_message),
            # or an RFC 7807 error dictionary if other errors occurred.

            # Case 1: Successful retrieval, message is a Document or None
            if isinstance(mail_getter_output, dict) and "message" in mail_getter_output:
                retrieved_document = mail_getter_output["message"]  # This is Optional[Document]

                if retrieved_document is None:
                    # This means the getter component itself determined the resource was not found (e.g., 404 from API)
                    # and returned {"message": None} as per its updated logic.
                    logger.info(f"Message with ID '{message_id}' not found by GoogleMailMessageGetter.")
                    return {
                        "type": f"{DEFAULT_PROBLEM_TYPE_URI}ResourceNotFoundError",
                        "title": "Resource Not Found",
                        "status": 404,
                        "detail": f"Gmail message with ID '{message_id}' was not found.",
                        "instance": f"/gmail/messages/errors/notfound-{message_id}",
                    }

                # If we reach here, retrieved_document is a Haystack Document
                logger.info(f"GetEmailMessage pipeline successfully processed request for message_id: {message_id}. Returning Document.")
                # The tool's output schema expects the Document itself under the "message" key.
                # The component already returns {"message": Document_instance}, so we just pass it through.
                return mail_getter_output  # This is {"message": Document_instance}

            # Case 2: The mail_getter_output is an RFC 7807 error dictionary
            elif isinstance(mail_getter_output, dict) and "status" in mail_getter_output and "title" in mail_getter_output and "type" in mail_getter_output:
                logger.warning(f"GetEmailMessage component returned an RFC 7807 problem: {mail_getter_output}")
                return mail_getter_output  # Propagate the error

            # Case 3: Unexpected structure from the component (should not happen if component is well-behaved)
            else:
                logger.error(f"Unexpected output structure from mail_getter: {mail_getter_output}", exc_info=True)
                return {
                    "type": f"{DEFAULT_PROBLEM_TYPE_URI}InternalServerError",
                    "title": "Internal Server Error",
                    "status": 500,
                    "detail": "The mail reader component returned an unexpected response structure.",
                    "instance": "/gmail/messages/errors/unexpected-component-response",
                }
        except Exception as e:  # Catch truly unexpected errors in the pipeline wrapper itself
            logger.error(f"Unexpected error in GetEmailMessage pipeline execution: {e}", exc_info=True)
            return {
                "type": f"{DEFAULT_PROBLEM_TYPE_URI}InternalServerError",
                "title": "Internal Server Error",
                "status": 500,
                "detail": f"An unexpected error occurred in the GetEmailMessage pipeline: {str(e)}",
                "instance": "/gmail/messages/errors/pipeline-unexpected-error",
            }
