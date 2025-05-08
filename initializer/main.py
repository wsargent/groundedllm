import requests
import os
import sys
import logging
import json

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger("main")


def provision_search_agent():
    try:
        # Set this in your docker-compose.yml
        chat_model = os.getenv("CHAT_MODEL", "letta/letta-free")
        embedding_model = os.getenv("EMBEDDING_MODEL", "letta/letta-free")
        hayhooks_payload = {
            "agent_name": "search-agent",
            "chat_model": chat_model,
            "embedding_model": embedding_model,
        }

        hayhooks_base_url = os.getenv("HAYHOOKS_BASE_URL", "http://hayhooks:1416")
        hayhooks_pipeline = "provision_search_agent"
        hayhooks_url = f"{hayhooks_base_url}/{hayhooks_pipeline}/run"

        # Call the pipeline
        response = requests.post(hayhooks_url, json=hayhooks_payload)
        response.raise_for_status()
        json_result = response.json()
        logger.debug(f"Configuration result: {json.dumps(json_result, indent=2)}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to configure via Hayhooks: {e}")
        raise RuntimeError("Failed to configure") from e


if __name__ == "__main__":
    try:
        provision_search_agent()
        logger.info("Initialization complete!")
    except Exception as e:
        logger.error(f"Initialization failed: {e}", e, exc_info=True)
        sys.exit(1)
