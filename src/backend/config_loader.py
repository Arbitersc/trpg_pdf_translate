"""
Shared Configuration Loader for TRPG PDF Translator

This module provides a unified interface for loading environment configuration
from multiple locations with support for custom environment file paths.
It's used by both backend modules and frontend CLI to ensure consistent
configuration loading.
"""

import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Global state to track which environment file was loaded
_LOADED_ENV_PATH: Optional[Path] = None


def load_environment_config(env_path: Optional[Path] = None) -> None:
    """
    Load environment variables with optional custom path.

    This function provides a unified way to load environment configuration:
    - If env_path is provided and exists, load from that path only
    - If env_path is provided but doesn't exist, fall back to standard search
    - If env_path is None, use standard search priority:
      1) Current directory .env
      2) ~/.trpg_pdf_translator/.env
      3) Project root .env

    Args:
        env_path: Optional custom path to .env file. If provided and exists,
                 only this file will be loaded (no fallbacks).

    Example:
        # Load from default locations
        load_environment_config()

        # Load from custom path
        load_environment_config(Path("/custom/path/.env"))

        # Load from known config directory
        load_environment_config(Path.home() / ".trpg_pdf_translator" / ".env")
    """
    global _LOADED_ENV_PATH

    if env_path is not None:
        # Custom path provided
        if env_path.exists():
            load_dotenv(env_path)
            _LOADED_ENV_PATH = env_path
        else:
            # Custom path doesn't exist, fall back to standard search
            _fallback_load_for_overrides(env_path)
            _LOADED_ENV_PATH = None
    else:
        # Standard location search
        _load_from_default_locations()


def _load_from_default_locations() -> None:
    """Load environment from standard locations with priority."""
    global _LOADED_ENV_PATH

    env_locations = [
        Path.cwd() / ".env",  # Current working directory
        Path.home() / ".trpg_pdf_translator" / ".env",
        Path(__file__).parent.parent.parent / ".env",  # Project root
    ]

    for path in env_locations:
        if path.exists():
            load_dotenv(path)
            _LOADED_ENV_PATH = path
            return

    # No .env found in any location, use default behavior
    load_dotenv()
    _LOADED_ENV_PATH = None


def _fallback_load_for_overrides(override_path: Path) -> None:
    """
    Load environment variables with override priority for reload scenarios.

    When a custom env_path is requested but doesn't exist, this function
    loads from default locations with override enabled.

    Args:
        override_path: The requested path that doesn't exist (for logging purposes)
    """
    import warnings

    env_locations = [
        Path.cwd() / ".env",
        Path.home() / ".trpg_pdf_translator" / ".env",
        Path(__file__).parent.parent.parent / ".env",
    ]

    for path in env_locations:
        if path.exists():
            load_dotenv(path, override=True)
            return

    warnings.warn(
        f"Requested env file not found: {override_path!s}. "
        "No .env file found in standard locations.",
        stacklevel=2
    )
    load_dotenv(override=True)


def _load_from_default_locations_with_override() -> None:
    """Load environment from standard locations with override enabled."""
    global _LOADED_ENV_PATH

    env_locations = [
        Path.cwd() / ".env",  # Current working directory
        Path.home() / ".trpg_pdf_translator" / ".env",
        Path(__file__).parent.parent.parent / ".env",  # Project root
    ]

    for path in env_locations:
        if path.exists():
            load_dotenv(path, override=True)
            _LOADED_ENV_PATH = path
            return

    # No .env found in any location, use default behavior with override
    load_dotenv(override=True)
    _LOADED_ENV_PATH = None


def get_loaded_env_path() -> Optional[Path]:
    """
    Get the path of the environment file that was most recently loaded.

    Returns:
        Path to the loaded .env file, or None if loaded from default locations
        or no .env was loaded.

    Example:
        load_environment_config()
        path = get_loaded_env_path()
        if path:
            print(f"Loaded config from: {path}")
    """
    return _LOADED_ENV_PATH


def get_env_value(key: str, default: Optional[str] = None) -> Optional[str]:
    """
    Get an environment variable value with optional default.

    This is a convenience wrapper around os.getenv() that provides
    consistent error handling and default values.

    Args:
        key: Environment variable name
        default: Default value to return if key is not found

    Returns:
        The environment variable value, or the default if not found
    """
    return os.getenv(key, default)


def reload_environment_config(env_path: Optional[Path] = None) -> None:
    """
    Reload environment configuration from the specified or default path.

    This function clears environment variables that were set from .env
    and reloads the configuration. Useful when configuration has changed.

    Args:
        env_path: Optional custom path to .env file

    Note:
        This only clears variables that were explicitly set in the .env file.
        System environment variables are preserved.
    """
    global _LOADED_ENV_PATH

    # Clear existing dotenv-loaded variables by tracking loaded keys
    # We'll store the keys that were loaded from the previous .env file
    loaded_keys = set()

    # If we previously loaded from a specific .env file, track its variables
    if _LOADED_ENV_PATH and _LOADED_ENV_PATH.exists():
        # Read the previous .env file to get variable names
        try:
            with open(_LOADED_ENV_PATH, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key = line.split('=', 1)[0].strip()
                        loaded_keys.add(key)
        except (IOError, UnicodeDecodeError):
            # If we can't read the file, we'll use a more aggressive approach
            pass

    # Clear the tracked variables from environment
    for key in loaded_keys:
        if key in os.environ:
            del os.environ[key]

    # Reset the loaded path tracking
    _LOADED_ENV_PATH = None

    # Load fresh configuration with override=True to ensure new values take effect
    if env_path is not None:
        if env_path.exists():
            load_dotenv(env_path, override=True)
            _LOADED_ENV_PATH = env_path
        else:
            # Fallback to standard search with override
            _fallback_load_for_overrides(env_path)
    else:
        # Standard location search with override
        _load_from_default_locations_with_override()


# Export public API
__all__ = [
    "load_environment_config",
    "get_loaded_env_path",
    "get_env_value",
    "reload_environment_config",
]
