import importlib.resources as pkg_resources
import logging

logger = logging.getLogger(__name__)


def read_resource_file(relative_path: str) -> str:
    """Reads content from a resource file located within the 'resources' package.

    Uses importlib.resources for reliable access to package data files,
    making it suitable for use even when the application is packaged.

    Args:
        relative_path (str): The path to the resource file relative to the 'resources' package.

    Returns:
        str: The content of the resource file as a string.

    Raises:
        RuntimeError: If the file cannot be found or read.

    """
    try:
        # Use importlib.resources to access package data files reliably
        # Assumes 'resources' is a top-level package or discoverable relative to the caller
        package_resources = pkg_resources.files("resources")
        resource_path = package_resources.joinpath(relative_path)
        logger.debug(f"Reading resource file from: {resource_path}")
        return resource_path.read_text(encoding="utf-8")
    except FileNotFoundError as e:
        # Log the error with more context if possible
        logger.error(
            f"Could not find resource file at relative path '{relative_path}' using package 'resources'. Full path attempted: {package_resources}/{relative_path}",
            exc_info=True,
        )
        raise RuntimeError(f"Could not find resource file '{relative_path}' within the 'resources' package.") from e
    except Exception as e:
        logger.error(
            f"An error occurred while reading resource file '{relative_path}' using package 'resources'. Full path attempted: {package_resources}/{relative_path}",
            exc_info=True,
        )
        raise RuntimeError(f"An error occurred while reading '{relative_path}' from the 'resources' package.") from e
