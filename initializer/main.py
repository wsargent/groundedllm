import requests
import os
import sys
import logging
import json

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger("main")

def _get_hayhooks_base_url() -> str:
    """Retrieves the Hayhooks base URL from environment or uses default."""
    return os.getenv("HAYHOOKS_BASE_URL", "http://hayhooks:1416")


def _configure_service(
    hayhooks_endpoint: str,
    hayhooks_payload: dict,
    result_key: str = "result",
    default_result: str | None = None,
    service_name_for_logging: str = "Service", # Optional name for logging
) -> str:
    """Generic function to configure a service via Hayhooks."""
    hayhooks_base_url = _get_hayhooks_base_url()
    hayhooks_url = f"{hayhooks_base_url}/{hayhooks_endpoint}/run"

    try:
        response = requests.post(hayhooks_url, json=hayhooks_payload)
        response.raise_for_status()
        json_result = response.json()
        logger.debug(
            f"Configuration result for {service_name_for_logging}: {json.dumps(json_result, indent=2)}"
        )
        if default_result is not None:
            return json_result.get(result_key, default_result)
        else:
            return json_result[result_key]
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to configure {service_name_for_logging} via Hayhooks: {e}")
        raise RuntimeError(f"Failed to configure {service_name_for_logging}") from e


def configure_and_setup_letta() -> str:
    """Configures and executes the setup for the Letta agent."""
    return _configure_service(
        hayhooks_endpoint="provision_letta_agent",
        hayhooks_payload={"agent_name": "letta-agent"},
        result_key="result",
        service_name_for_logging="Letta Agent",
    )

def configure_and_setup_openwebui(agent_id: str) -> str:
    """Configures and executes the setup for the Open WebUI function."""
    # Wait for OpenWebUI service separately if needed before configuration
    return _configure_service(
        hayhooks_endpoint="provision_letta_pipe",
        hayhooks_payload={"agent_id": agent_id},
        result_key="result",
        default_result="Setup initiated", # Provide default if key might be missing
        service_name_for_logging="OpenWebUI Pipe",
    )


if __name__ == "__main__":
    try:
        # Configure and set up Letta agent
        agent_id = configure_and_setup_letta()

        # Configure and set up Open WebUI
        configure_and_setup_openwebui(agent_id)

        logger.info("Initialization complete.")
    except Exception as e:
        logger.error(f"Initialization failed: {e}", e, exc_info=True)
        sys.exit(1)
