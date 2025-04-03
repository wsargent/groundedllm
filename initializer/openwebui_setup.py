import requests
import json
import logging
import os

logger = logging.getLogger("openwebui_setup")

class OpenWebUISetup:
    """Handles the setup and configuration of a generic Open WebUI function pipe."""

    def __init__(self, base_url, email, password, function_id, function_name, function_description, function_script_path):
        """
        Initializes the setup class with Open WebUI connection and function details.

        Args:
            base_url (str): The base URL of the Open WebUI instance.
            email (str): Email for Open WebUI signin.
            password (str): Password for Open WebUI signin.
            function_id (str): The unique ID for the function to be created/managed.
            function_name (str): The display name for the function.
            function_description (str): The description for the function.
            function_script_path (str): The file path to the Python script defining the function.
        """
        if not all([base_url, email, password, function_id, function_name, function_description, function_script_path]):
             raise ValueError("All arguments must be provided and non-empty.")

        self.base_url = base_url
        self.email = email
        self.password = password
        self.function_id = function_id
        self.function_name = function_name
        self.function_description = function_description
        self.function_script_path = function_script_path
        self.headers = None # Will be set after signin

    def _make_request(self, method, endpoint, **kwargs):
        """Internal helper method for making requests and handling errors."""
        url = f"{self.base_url}{endpoint}"
        # Ensure headers are included if available
        if self.headers and 'headers' not in kwargs:
             kwargs['headers'] = self.headers
        elif self.headers and 'headers' in kwargs:
             # Merge provided headers with instance headers, prioritizing provided ones
             kwargs['headers'] = {**self.headers, **kwargs['headers']}

        response = requests.request(method, url, **kwargs)
        response.raise_for_status() # Will raise HTTPError for bad responses (4xx or 5xx)
        return response
        
    def _signin(self):
        """Signs into Open WebUI using provided credentials and sets auth headers."""
        logger.info(f"Attempting to sign in to Open WebUI as {self.email}...")
        endpoint = "/api/v1/auths/signin"
        payload = {"email": self.email, "password": self.password}
        # Signin doesn't require auth headers initially
        response = self._make_request("post", endpoint, json=payload, headers={})
        token = response.json()["token"]
        self.headers = {
            "Authorization": f"Bearer {token}",
            "accept": "application/json"
        }
        logger.info("Successfully obtained auth token and set headers.")

    def _get_functions(self):
        """Fetches the list of existing functions from Open WebUI."""
        endpoint = "/api/v1/functions/"
        response = self._make_request("get", endpoint)
        existing_functions = response.json()
        return existing_functions

    def _create_function(self):
        """Creates the specified function in Open WebUI using instance details."""
        logger.debug(f"Creating function '{self.function_name}' (ID: {self.function_id})...")
        try:
            with open(self.function_script_path, "r") as f:
                content = f.read()
        except FileNotFoundError as e:
            raise RuntimeError(f"Could not find function script at {self.function_script_path}") from e

        endpoint = "/api/v1/functions/create"
        payload = {
            "id": self.function_id,
            "name": self.function_name,
            "content": content,
            "meta": {
                "description": self.function_description,
                "manifest": {} # Assuming empty manifest for now
            }
        }
        response = self._make_request("post", endpoint, json=payload)
        new_function = response.json()
        logger.debug(f"Successfully created function: {json.dumps(new_function, indent=2)}")

    def _update_function_valve(self, valve_payload: dict):
        """Updates the valve settings for the specified function."""
        if not isinstance(valve_payload, dict):
             raise TypeError("valve_payload must be a dictionary.")
        logger.debug(f"Updating valve for function ID {self.function_id} with payload: {json.dumps(valve_payload)}")
        endpoint = f"/api/v1/functions/id/{self.function_id}/valves/update"
        response = self._make_request("post", endpoint, json=valve_payload)
        logger.debug(f"Valve update response: {json.dumps(response.json(), indent=2)}")

    def _get_function_state(self):
        """Gets the current function state"""
        logger.debug(f"Getting function ID {self.function_id} toggle...")
        endpoint = f"/api/v1/functions/id/{self.function_id}"
        response = self._make_request("get", endpoint)
        logger.debug(f"_get_function_state response: {json.dumps(response.json(), indent=2)}")

    def _toggle_function(self):
        """Toggles the specified function state (enables it)."""
        logger.debug(f"Toggling function ID {self.function_id}...")
        endpoint = f"/api/v1/functions/id/{self.function_id}/toggle"
        response = self._make_request("post", endpoint)
        logger.debug(f"Toggle response: {json.dumps(response.json(), indent=2)}")

    def setup_function(self, valve_payload: dict):
        """
        Orchestrates the setup of the configured function in Open WebUI.

        Args:
            valve_payload (dict): The dictionary payload for the valve update request.
        """
        logger.info(f"Starting setup for function ID {self.function_id}...")
        self._signin()

        existing_functions = self._get_functions()
        function_exists = any(func.get('id') == self.function_id for func in existing_functions)

        if not function_exists:
            self._create_function()
            ### if it's already there it toggles it off?
            self._toggle_function()
        else:
            logger.info(f"Function ID {self.function_id} already exists.")

        # Set up the agent id as a valve setting
        self._update_function_valve(valve_payload)
        
        logger.info(f"Setup complete for function ID {self.function_id}.")
