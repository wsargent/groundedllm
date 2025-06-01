from typing import Dict

from hayhooks import log as logger
from hayhooks.server.utils.base_pipeline_wrapper import BasePipelineWrapper
from haystack import Pipeline

from components.google.google_oauth_component import GoogleOAuthComponent


class PipelineWrapper(BasePipelineWrapper):
    """
    Pipeline wrapper for the 'google_auth' MCP tool.
    Checks Google authentication status and provides an authorization URL if needed.
    """

    def setup(self) -> None:
        logger.info("Setting up GoogleAuth pipeline...")

        pipe = Pipeline()
        self.pipeline = pipe

        oauth_component = GoogleOAuthComponent()
        pipe.add_component("google_auth", oauth_component)

        # This pipeline wrapper doesn't run a traditional Haystack pipeline,
        # but it needs a `self.pipeline` attribute. We can assign a dummy one or None.
        # For now, let's create an empty pipeline to satisfy the base class if it expects one.
        logger.info("GoogleAuth pipeline setup complete.")

    def run_api(self, user_id: str) -> Dict:
        """
        MCP Tool: Checks Google authentication status or initiates auth.

        Args:
            user_id: The user ID for Google authentication.

        Returns:
            A dictionary.
            If authenticated: {"authenticated": True, "user_id": user_id}
            If not authenticated: {"authorization_url": "...", "state": "..."}

        Raises:
            RuntimeError: If the OAuth component is not configured.
            HTTPException: Potentially from underlying OAuth calls for errors.
        """
        result = self.pipeline.run({"google_auth": {"user_id": user_id}})
        logger.info(f"GoogleAuth pipeline result: {result}")
        return result["google_auth"]
