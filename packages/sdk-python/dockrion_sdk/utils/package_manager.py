"""
Package Manager Module
======================

Provides utilities for working with Python package managers:
- Checking for uv availability
- Installing dependencies with uv or pip fallback
- User-friendly setup instructions
"""

import subprocess
import sys
from pathlib import Path

from dockrion_common.errors import DockrionError
from dockrion_common.logger import get_logger

logger = get_logger(__name__)


def check_uv_available() -> bool:
    """
    Check if uv package manager is available.

    Returns:
        True if uv is available, False otherwise
    """
    try:
        subprocess.check_output(["uv", "--version"], stderr=subprocess.STDOUT, text=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def print_uv_setup_instructions() -> None:
    """Print instructions for installing uv package manager."""
    print("\n" + "=" * 70)
    print("⚠️  UV Package Manager Not Found")
    print("=" * 70)
    print("\nDockrion uses 'uv' for fast, reliable package management.")
    print("\n📦 Quick Setup (recommended):")
    print("\n  On macOS/Linux:")
    print("    curl -LsSf https://astral.sh/uv/install.sh | sh")
    print("\n  On Windows:")
    print('    powershell -c "irm https://astral.sh/uv/install.ps1 | iex"')
    print("\n  Using pip:")
    print("    pip install uv")
    print("\n  Using pipx:")
    print("    pipx install uv")
    print("\n📚 Learn more: https://github.com/astral-sh/uv")
    print("\n💡 Note: Docker builds will still work (uv is installed in the container)")
    print("   but local development benefits from having uv installed.")
    print("=" * 70 + "\n")


def install_requirements(requirements_dir: Path, use_uv: bool = True) -> None:
    """
    Install dependencies from requirements.txt.

    Args:
        requirements_dir: Directory containing requirements.txt
        use_uv: Try to use uv if available (falls back to pip)

    Raises:
        DockrionError: If installation fails
    """
    uv_available = check_uv_available() if use_uv else False

    if uv_available:
        logger.info("  Using uv package manager (fast!)...")
        try:
            subprocess.check_call(
                ["uv", "pip", "install", "-r", "requirements.txt", "-q"],
                cwd=str(requirements_dir),
                stdout=subprocess.DEVNULL,
            )
        except subprocess.CalledProcessError as e:
            raise DockrionError(f"Failed to install dependencies with uv: {str(e)}")
    else:
        if use_uv:
            print_uv_setup_instructions()
        logger.info("  Using pip (consider installing uv for faster installs)...")
        try:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", "-r", "requirements.txt", "-q"],
                cwd=str(requirements_dir),
                stdout=subprocess.DEVNULL,
            )
        except subprocess.CalledProcessError as e:
            raise DockrionError(f"Failed to install dependencies with pip: {str(e)}")


__all__ = [
    "check_uv_available",
    "print_uv_setup_instructions",
    "install_requirements",
]
