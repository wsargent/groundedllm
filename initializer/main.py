import requests
import time
import os
import sys
import logging

# Import the refactored functions/classes
from letta_setup import LettaSetup # Import the new class
from openwebui_setup import OpenWebUISetup # Import the class

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger("main")

MAX_WAIT_SECONDS = 120
SLEEP_INTERVAL = 5

def wait_for_service(url, service_name):
    """Polls a service's health/base endpoint until it's responsive."""
    start_time = time.time()
    logger.info(f"Waiting for {service_name} at {url}...")
    while time.time() - start_time < MAX_WAIT_SECONDS:
        try:
            # Use a simple GET request to a known endpoint (e.g., health or base URL)
            response = requests.get(url, timeout=3) # Adjust endpoint if needed
            # Check for a successful status code (e.g., 200-299)
            if response.status_code >= 200 and response.status_code < 300:
                logger.info(f"{service_name} is ready!")
                return True
            else:
                # Use warning for non-2xx status during polling
                logger.warning(f"{service_name} returned status {response.status_code}. Retrying...")
        except requests.exceptions.ConnectionError as e:
             # Use warning for transient connection issues during polling
            logger.warning(f"{service_name} connection failed. Retrying at {url}", e)
        except requests.exceptions.Timeout:
             # Use warning for timeouts during polling
            logger.warning(f"{service_name} request timed out. Retrying at {url}")
        except requests.exceptions.RequestException as e:
             # Use warning for other request exceptions during polling
            logger.warning(f"Error connecting to {service_name}: {e}. Retrying at {url}")

        time.sleep(SLEEP_INTERVAL)

    # Use error when the wait finally fails
    logger.error(f"Error: {service_name} did not become ready within {MAX_WAIT_SECONDS} seconds.")
    return False

def configure_and_setup_letta() -> str:
    """Gets Letta URL, waits for service, configures and executes the setup for the Letta agent."""
    letta_base_url = os.getenv("LETTA_BASE_URL")
    if letta_base_url is None:
        raise ValueError("LETTA_BASE_URL environment variable is not defined!")

    letta_health_url = f"{letta_base_url}/v1/health/"
    if not wait_for_service(letta_health_url, "Letta"):
        raise RuntimeError(f"Letta service at {letta_health_url} did not become ready.")

    logger.info("Configuring Letta agent...")
    letta_setup = LettaSetup(base_url=letta_base_url)
    agent_id = letta_setup.setup_agent() # Call the setup method
    logger.info("Letta agent setup completed successfully.")
    return agent_id
    

def configure_and_setup_openwebui(agent_id):
    """Gets OpenWebUI URL, waits for service, configures and executes the setup for the Open WebUI function."""
    openwebui_base_url = os.getenv("OPEN_WEBUI_URL")
    if openwebui_base_url is None:
        raise ValueError("OPEN_WEBUI_URL environment variable is not defined!")

    openwebui_health_url = f"{openwebui_base_url}/health"
    if not wait_for_service(openwebui_health_url, "Open WebUI"):
        raise RuntimeError(f"Open WebUI service at {openwebui_health_url} did not become ready.")

    openwebui_email = "admin@localhost"
    openwebui_password = "password" # Consider getting this from env vars in a real scenario
    letta_pipe_id = "letta_pipe"
    letta_pipe_name = "Letta Pipe"
    letta_pipe_description = "Pipe requests to Letta Agent"
    # Path relative to the WORKDIR (/app) inside the container
    letta_pipe_script_path = "open-webui/letta_pipe.py"
    # Define the payload needed for the valve update step
    letta_pipe_valve_payload = {"Agent_ID": agent_id}
    
    logger.info(f"Configuring Open WebUI function: {letta_pipe_name} (ID: {letta_pipe_id})")
    openwebui_setup = OpenWebUISetup(
        base_url=openwebui_base_url,
        email=openwebui_email,
        password=openwebui_password,
        function_id=letta_pipe_id,
            function_name=letta_pipe_name,
            function_description=letta_pipe_description,
            function_script_path=letta_pipe_script_path
        )
    openwebui_setup.setup_function(valve_payload=letta_pipe_valve_payload)
    logger.info("Open WebUI function setup completed successfully.")


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
