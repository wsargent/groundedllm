import requests
import json

import logging
from haystack import component
from haystack.utils import Secret

logger = logging.getLogger("openwebui_setup")


@component
class CreateFunction:
    """Handles the setup and configuration of a generic Open WebUI function pipe."""

    def __init__(self, base_url: str, email: str, password: Secret):
        """
        Initializes the setup class with Open WebUI connection and function details.

        Args:
            base_url (str): The base URL of the Open WebUI instance.
            email (str): Email for Open WebUI signin.
            password (str): Password for Open WebUI signin.
        """
        self.base_url = base_url
        self.email = email
        self.password = password
        self.headers = None  # Will be set after signin

    @component.output_types(function_state=dict)
    def run(
        self,
        function_id: str,
        function_name: str,
        function_description: str,
        function_content: str,
        function_manifest: dict,
        function_valve_payload: dict,
    ) -> dict:
        """
        Orchestrates the setup of the configured function in Open WebUI.

        Arguments
        ----------
        function_id: str
              The unique ID for the function to be created/managed.
        function_name: str
            The display name for the function.
        function_description: str
            The description for the function.
        function_content: str
            The content of the function
        function_manifest: dict
            The function manifest
        function_valve_payload: dict
            The dictionary payload for the valve update request.

        Returns
        -------
        dict:
              the function state
        """
        logger.info(f"Starting setup for function ID {function_id}...")
        self._signin()

        existing_functions = self._get_functions()
        function_exists = any(
            func.get("id") == function_id for func in existing_functions
        )

        if not function_exists:
            self._create_function(
                function_id=function_id,
                function_name=function_name,
                function_description=function_description,
                function_content=function_content,
                function_manifest=function_manifest,
            )
            # Only toggle the function if newly created so we don't override the user.
            self._toggle_function(function_id)
        else:
            logger.info(f"Function ID {function_id} already exists.")

        # Set up the agent id as a valve setting
        self._update_function_valve(function_id, function_valve_payload)

        logger.info(f"Setup complete for function ID {function_id}.")

        function_state = self._get_function_state(function_id=function_id)

        return function_state

    def _make_request(self, method, endpoint, **kwargs):
        """Internal helper method for making requests and handling errors."""
        url = f"{self.base_url}{endpoint}"
        # Ensure headers are included if available
        if self.headers and "headers" not in kwargs:
            kwargs["headers"] = self.headers
        elif self.headers and "headers" in kwargs:
            # Merge provided headers with instance headers, prioritizing provided ones
            kwargs["headers"] = {**self.headers, **kwargs["headers"]}

        response = requests.request(method, url, **kwargs)
        response.raise_for_status()  # Will raise HTTPError for bad responses (4xx or 5xx)
        return response

    def _signin(self):
        """Signs into Open WebUI using provided credentials and sets auth headers."""
        logger.info(f"Attempting to sign in to Open WebUI as {self.email}...")
        endpoint = "/api/v1/auths/signin"
        payload = {"email": self.email, "password": self.password.resolve_value()}
        response = self._make_request("post", endpoint, json=payload, headers={})
        token = response.json()["token"]
        self.headers = {
            "Authorization": f"Bearer {token}",
            "accept": "application/json",
        }
        logger.info("Successfully obtained auth token and set headers.")

    def _get_functions(self):
        """Fetches the list of existing functions from Open WebUI."""
        endpoint = "/api/v1/functions/"
        response = self._make_request("get", endpoint)
        existing_functions = response.json()
        return existing_functions

    def _create_function(
        self,
        function_id: str,
        function_name: str,
        function_description: str,
        function_content: str,
        function_manifest: dict = {},
    ):
        """Creates the specified function in Open WebUI using instance details."""
        logger.debug(f"Creating function '{function_name}' (ID: {function_id})...")

        endpoint = "/api/v1/functions/create"
        payload = {
            "id": function_id,
            "name": function_name,
            "content": function_content,
            "meta": {
                "description": function_description,
                "manifest": function_manifest,
            },
        }
        response = self._make_request("post", endpoint, json=payload)
        new_function = response.json()
        logger.debug(
            f"Successfully created function: {json.dumps(new_function, indent=2)}"
        )

    def _update_function_valve(self, function_id: str, valve_payload: dict):
        """Updates the valve settings for the specified function."""
        if not isinstance(valve_payload, dict):
            raise TypeError("valve_payload must be a dictionary.")
        logger.debug(
            f"Updating valve for function ID {function_id} with payload: {json.dumps(valve_payload)}"
        )
        endpoint = f"/api/v1/functions/id/{function_id}/valves/update"
        response = self._make_request("post", endpoint, json=valve_payload)
        logger.debug(f"Valve update response: {json.dumps(response.json(), indent=2)}")

    def _get_function_state(self, function_id: str) -> dict:
        """Gets the current function state"""
        logger.debug(f"Getting function ID {function_id} toggle...")
        endpoint = f"/api/v1/functions/id/{function_id}"
        response = self._make_request("get", endpoint)
        logger.debug(
            f"_get_function_state response: {json.dumps(response.json(), indent=2)}"
        )
        return response.json()

    def _toggle_function(
        self,
        function_id: str,
    ):
        """Toggles the specified function state (enables it)."""
        logger.debug(f"Toggling function ID {function_id}...")
        endpoint = f"/api/v1/functions/id/{function_id}/toggle"
        response = self._make_request("post", endpoint)
        logger.debug(f"Toggle response: {json.dumps(response.json(), indent=2)}")
