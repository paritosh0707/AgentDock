"""
Environment Utilities for Dockrion

This module provides centralized environment variable resolution for local development.
It handles loading from multiple sources with proper priority:

Priority (lowest to highest):
1. Default values from secrets declaration
2. .env file in project root
3. env.yaml / .dockrion-env.yaml in project root
4. Shell environment variables (os.environ)
5. CLI --env-file flag (explicit override)

Usage:
    from dockrion_common.env_utils import load_env_files, resolve_secrets, validate_secrets

    # Load environment from various sources
    loaded = load_env_files(project_root, env_file="./secrets/.env.local")

    # Resolve secrets with priority
    resolved = resolve_secrets(secrets_config, loaded)

    # Validate all required secrets are present
    warnings = validate_secrets(secrets_config, resolved)
"""

import os
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional

import yaml

from .errors import MissingSecretError
from .logger import get_logger

if TYPE_CHECKING:
    from dockrion_schema import SecretsConfig

logger = get_logger(__name__)


# Standard .env file names to search for
ENV_FILE_NAMES = [".env", ".env.local"]

# YAML-based env file names
ENV_YAML_NAMES = ["env.yaml", ".dockrion-env.yaml"]


def _parse_dotenv(content: str) -> Dict[str, str]:
    """
    Parse .env file content into a dictionary.

    Handles:
    - KEY=value pairs
    - Comments (lines starting with #)
    - Empty lines
    - Quoted values (single and double quotes)
    - Values with = signs

    Args:
        content: Raw .env file content

    Returns:
        Dictionary of environment variable names to values
    """
    result = {}

    for line in content.splitlines():
        line = line.strip()

        # Skip empty lines and comments
        if not line or line.startswith("#"):
            continue

        # Skip lines without =
        if "=" not in line:
            continue

        # Split on first = only (value may contain =)
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()

        # Skip if key is empty
        if not key:
            continue

        # Remove surrounding quotes from value
        if (value.startswith('"') and value.endswith('"')) or (
            value.startswith("'") and value.endswith("'")
        ):
            value = value[1:-1]

        result[key] = value

    return result


def _load_dotenv_file(path: Path) -> Dict[str, str]:
    """
    Load a .env file and return parsed key-value pairs.

    Args:
        path: Path to .env file

    Returns:
        Dictionary of environment variables
    """
    try:
        content = path.read_text(encoding="utf-8")
        result = _parse_dotenv(content)
        logger.debug(f"Loaded {len(result)} variables from {path}")
        return result
    except Exception as e:
        logger.warning(f"Failed to load .env file {path}: {e}")
        return {}


def _load_yaml_env_file(path: Path) -> Dict[str, str]:
    """
    Load an env.yaml file and return environment variables.

    Expected format:
        secrets:
          KEY_NAME: "value"
          ANOTHER_KEY: "another_value"

    Or simple format:
        KEY_NAME: "value"
        ANOTHER_KEY: "another_value"

    Args:
        path: Path to env.yaml file

    Returns:
        Dictionary of environment variables
    """
    try:
        content = path.read_text(encoding="utf-8")
        data = yaml.safe_load(content)

        if data is None:
            return {}

        # Handle nested "secrets" key
        if isinstance(data, dict) and "secrets" in data:
            secrets = data.get("secrets", {})
            if isinstance(secrets, dict):
                # Convert all values to strings
                result = {k: str(v) for k, v in secrets.items()}
                logger.debug(f"Loaded {len(result)} variables from {path} (secrets section)")
                return result

        # Handle flat format
        if isinstance(data, dict):
            # Filter to only string-like values (skip nested dicts)
            result = {k: str(v) for k, v in data.items() if not isinstance(v, (dict, list))}
            logger.debug(f"Loaded {len(result)} variables from {path}")
            return result

        return {}
    except Exception as e:
        logger.warning(f"Failed to load env.yaml file {path}: {e}")
        return {}


def load_env_files(
    project_root: Path, env_file: Optional[str] = None, include_yaml: bool = True
) -> Dict[str, str]:
    """
    Load environment variables from .env and env.yaml files.

    Resolution order (later sources override earlier):
    1. Auto-detected .env in project_root
    2. Auto-detected env.yaml in project_root (if include_yaml=True)
    3. Explicit env_file if provided

    Args:
        project_root: Root directory to search for env files
        env_file: Optional explicit path to .env file (overrides auto-detection)
        include_yaml: Whether to also load env.yaml files (default: True)

    Returns:
        Merged dictionary of environment variables
    """
    result: Dict[str, str] = {}
    project_root = Path(project_root).resolve()

    # 1. Load auto-detected .env files
    for env_name in ENV_FILE_NAMES:
        env_path = project_root / env_name
        if env_path.exists():
            loaded = _load_dotenv_file(env_path)
            result.update(loaded)
            logger.info(f"Loaded environment from {env_path}")

    # 2. Load env.yaml files (if enabled)
    if include_yaml:
        for yaml_name in ENV_YAML_NAMES:
            yaml_path = project_root / yaml_name
            if yaml_path.exists():
                loaded = _load_yaml_env_file(yaml_path)
                result.update(loaded)
                logger.info(f"Loaded environment from {yaml_path}")

    # 3. Load explicit env_file (highest priority for file-based loading)
    if env_file:
        explicit_path = Path(env_file)
        if not explicit_path.is_absolute():
            explicit_path = project_root / explicit_path

        if explicit_path.exists():
            if explicit_path.suffix in [".yaml", ".yml"]:
                loaded = _load_yaml_env_file(explicit_path)
            else:
                loaded = _load_dotenv_file(explicit_path)
            result.update(loaded)
            logger.info(f"Loaded environment from explicit file {explicit_path}")
        else:
            logger.warning(f"Explicit env file not found: {explicit_path}")

    return result


def resolve_secrets(
    secrets_config: Optional["SecretsConfig"],
    loaded_env: Dict[str, str],
    shell_env: Optional[Dict[str, str]] = None,
) -> Dict[str, str]:
    """
    Resolve all secrets using priority chain.

    Priority (highest wins):
    1. Shell environment (os.environ or provided shell_env)
    2. loaded_env (from .env / env.yaml files)
    3. Default values from secrets declaration

    Args:
        secrets_config: SecretsConfig from Dockfile (may be None)
        loaded_env: Environment loaded from files
        shell_env: Shell environment (defaults to os.environ)

    Returns:
        Final resolved environment variables
    """
    if shell_env is None:
        shell_env = dict(os.environ)

    result: Dict[str, str] = {}

    if secrets_config is None:
        # No secrets config - just merge file env with shell env
        result.update(loaded_env)
        # Shell env has higher priority
        for key in loaded_env:
            if key in shell_env:
                result[key] = shell_env[key]
        return result

    # Process all declared secrets
    all_secrets = list(secrets_config.required) + list(secrets_config.optional)

    for secret in all_secrets:
        name = secret.name
        value = None

        # Priority chain (lowest to highest)
        # 1. Default value
        if secret.default is not None:
            value = secret.default

        # 2. Loaded from file
        if name in loaded_env:
            value = loaded_env[name]

        # 3. Shell environment (highest priority)
        if name in shell_env:
            value = shell_env[name]

        if value is not None:
            result[name] = value

    # Also include any non-declared secrets from loaded_env
    # (for backwards compatibility and convenience)
    for key, value in loaded_env.items():
        if key not in result:
            # Check shell env override
            if key in shell_env:
                result[key] = shell_env[key]
            else:
                result[key] = value

    return result


def validate_secrets(
    secrets_config: Optional["SecretsConfig"], resolved: Dict[str, str], strict: bool = True
) -> List[str]:
    """
    Validate all required secrets are present.

    Args:
        secrets_config: SecretsConfig from Dockfile (may be None)
        resolved: Resolved environment variables
        strict: If True, raise MissingSecretError for missing required secrets

    Returns:
        List of warning messages for missing optional secrets

    Raises:
        MissingSecretError: If strict=True and required secrets are missing
    """
    warnings: List[str] = []

    if secrets_config is None:
        return warnings

    # Check required secrets
    missing_required: List[str] = []
    for secret in secrets_config.required:
        if secret.name not in resolved or not resolved[secret.name]:
            missing_required.append(secret.name)

    if missing_required and strict:
        raise MissingSecretError(missing_required)
    elif missing_required:
        warnings.append(
            f"Missing required secrets (will fail at runtime): {', '.join(missing_required)}"
        )

    # Check optional secrets (just warn)
    for secret in secrets_config.optional:
        if secret.name not in resolved:
            desc = f" ({secret.description})" if secret.description else ""
            if secret.default is not None:
                warnings.append(
                    f"Optional secret '{secret.name}'{desc} not set, using default: '{secret.default}'"
                )
            else:
                warnings.append(f"Optional secret '{secret.name}'{desc} not set")

    return warnings


def inject_env(env_vars: Dict[str, str]) -> None:
    """
    Inject resolved environment variables into os.environ.

    This makes the resolved variables available to the Python process
    and any subprocesses.

    Args:
        env_vars: Dictionary of environment variables to inject
    """
    for key, value in env_vars.items():
        os.environ[key] = value

    if env_vars:
        logger.debug(f"Injected {len(env_vars)} environment variables")


def get_env_summary(
    secrets_config: Optional["SecretsConfig"], resolved: Dict[str, str]
) -> Dict[str, Any]:
    """
    Get a summary of environment variable resolution.

    Useful for debugging and CLI output.

    Args:
        secrets_config: SecretsConfig from Dockfile (may be None)
        resolved: Resolved environment variables

    Returns:
        Summary dict with counts and status
    """
    if secrets_config is None:
        return {
            "has_secrets_config": False,
            "total_resolved": len(resolved),
        }

    required_count = len(secrets_config.required)
    optional_count = len(secrets_config.optional)

    required_set = sum(
        1 for s in secrets_config.required if s.name in resolved and resolved[s.name]
    )
    optional_set = sum(1 for s in secrets_config.optional if s.name in resolved)

    return {
        "has_secrets_config": True,
        "required": {
            "declared": required_count,
            "set": required_set,
            "missing": required_count - required_set,
        },
        "optional": {
            "declared": optional_count,
            "set": optional_set,
        },
        "total_resolved": len(resolved),
    }
