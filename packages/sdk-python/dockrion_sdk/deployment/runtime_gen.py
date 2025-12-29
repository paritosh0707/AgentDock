"""
Runtime Generation Module
=========================

Provides functionality for generating and managing runtime files:
- Creating runtime directories
- Writing generated runtime files (main.py, requirements.txt)
- Cleaning up runtime directories
"""

import shutil
from pathlib import Path
from typing import Dict, Optional

from dockrion_common.logger import get_logger
from dockrion_schema import DockSpec

from ..templates import TemplateRenderer

logger = get_logger(__name__)

# Default name for the runtime directory
RUNTIME_DIR_NAME = ".dockrion_runtime"


def ensure_runtime_dir(base_path: Optional[Path] = None) -> Path:
    """
    Ensure the runtime directory exists.

    Args:
        base_path: Base directory (defaults to current working directory)

    Returns:
        Path to the runtime directory
    """
    base = base_path or Path.cwd()
    runtime_dir = base / RUNTIME_DIR_NAME
    runtime_dir.mkdir(exist_ok=True)
    return runtime_dir


def write_runtime_files(
    spec: DockSpec, runtime_dir: Path, renderer: Optional[TemplateRenderer] = None
) -> Dict[str, Path]:
    """
    Generate and write all runtime files using templates.

    Args:
        spec: Agent specification
        runtime_dir: Directory to write files to
        renderer: Optional custom template renderer

    Returns:
        Dictionary mapping file names to their paths
    """
    if renderer is None:
        renderer = TemplateRenderer()

    files: Dict[str, Path] = {}

    # Render and write main.py
    logger.info("Generating runtime code from template...")
    runtime_code = renderer.render_runtime(spec)
    main_file = runtime_dir / "main.py"
    main_file.write_text(runtime_code, encoding="utf-8")
    files["main.py"] = main_file
    logger.debug(f"Written: {main_file}")

    # Render and write requirements.txt
    logger.info("Generating requirements from template...")
    requirements = renderer.render_requirements(spec)
    req_file = runtime_dir / "requirements.txt"
    req_file.write_text(requirements, encoding="utf-8")
    files["requirements.txt"] = req_file
    logger.debug(f"Written: {req_file}")

    return files


def clean_runtime(base_path: Optional[Path] = None) -> bool:
    """
    Clean up the runtime directory.

    Args:
        base_path: Base directory (defaults to cwd)

    Returns:
        True if directory was removed, False if it didn't exist
    """
    base = base_path or Path.cwd()
    runtime_dir = base / RUNTIME_DIR_NAME

    if runtime_dir.exists():
        shutil.rmtree(runtime_dir)
        logger.info(f"Removed runtime directory: {runtime_dir}")
        return True

    return False


__all__ = [
    "ensure_runtime_dir",
    "write_runtime_files",
    "clean_runtime",
    "RUNTIME_DIR_NAME",
]
