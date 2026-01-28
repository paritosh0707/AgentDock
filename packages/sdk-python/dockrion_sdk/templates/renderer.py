"""
Dockrion Template Renderer
==========================

Provides a robust, flexible template system for generating:
- FastAPI runtime code
- Dockerfiles
- Requirements files
- Other deployment artifacts

Uses Jinja2 with custom filters and extensions for maximum flexibility.
Integrates with the dependency merger for smart version conflict resolution.
"""

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from dockrion_common.errors import BuildConflictError, DockrionError
from dockrion_common.logger import get_logger
from dockrion_schema import DockSpec
from jinja2 import (
    Environment,
    FileSystemLoader,
    StrictUndefined,
    TemplateError,
    TemplateNotFound,
    Undefined,
    select_autoescape,
)

from ..build import BuildResolution, BuildResolver
from ..dependencies import DependencyConflictError, DependencyMerger

logger = get_logger(__name__)

# ============================================================================
# Constants
# ============================================================================

DOCKRION_VERSION = "1.0.0"

# Default template directories (searched in order)
DEFAULT_TEMPLATE_DIRS = [
    # User-provided templates (highest priority)
    Path.cwd() / "templates",
    # Package templates (same directory as this renderer.py file)
    Path(__file__).parent,
]

# Template file mappings
TEMPLATE_FILES = {
    "runtime": "runtime-fastapi/main.py.j2",
    "dockerfile": "dockerfiles/Dockerfile.j2",
    "requirements": "runtime-fastapi/requirements.txt.j2",
}


# ============================================================================
# Custom Jinja2 Filters
# ============================================================================


def to_json_filter(value: Any, indent: Optional[int] = None) -> str:
    """Convert value to JSON string."""
    return json.dumps(value, indent=indent, default=str)


def to_python_filter(value: Any) -> str:
    """Convert value to Python literal representation."""
    if value is None:
        return "None"
    elif isinstance(value, bool):
        return "True" if value else "False"
    elif isinstance(value, str):
        return repr(value)
    elif isinstance(value, (list, dict)):
        return repr(value)
    else:
        return str(value)


def regex_replace_filter(value: str, pattern: str, replacement: str) -> str:
    """Apply regex replacement to string."""
    return re.sub(pattern, replacement, value)


def default_filter(value: Any, default_value: Any, boolean: bool = False) -> Any:
    """Enhanced default filter with boolean mode."""
    if boolean:
        return value if value else default_value
    return value if value is not None else default_value


def snake_case_filter(value: str) -> str:
    """Convert string to snake_case."""
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", value)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def kebab_case_filter(value: str) -> str:
    """Convert string to kebab-case."""
    return snake_case_filter(value).replace("_", "-")


# ============================================================================
# Template Context Builder
# ============================================================================


class TemplateContext:
    """
    Builds the context dictionary for template rendering.

    Extracts and transforms data from DockSpec into template-friendly format.
    Integrates with dependency merger for smart version conflict resolution.
    """

    def __init__(
        self,
        spec: DockSpec,
        project_root: Optional[Path] = None,
    ):
        """
        Initialize context builder.

        Args:
            spec: The DockSpec containing agent configuration
            project_root: Root directory of the user's project (for finding requirements.txt)
        """
        self.spec = spec
        self.project_root = project_root or Path.cwd()

    def build(self, extra_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Build complete template context.

        Args:
            extra_context: Additional context variables to include

        Returns:
            Dictionary with all template variables

        Raises:
            BuildConflictError: If build configuration has critical conflicts
        """
        # Get spec as dictionary
        # NOTE: exclude_none=False is required so that optional fields like 'handler'
        # are included with None values. Jinja2's StrictUndefined mode fails if
        # templates try to access missing dict keys (even in if checks).
        spec_dict = self.spec.model_dump(mode="python", exclude_none=False)

        # Resolve build includes/excludes using BuildResolver
        build_resolution = self._resolve_build_includes()

        # Build context with flattened access to common fields
        context = {
            # Meta information
            "dockrion_version": DOCKRION_VERSION,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "python_version": "3.12",
            # Full spec as Python literal (for embedding in runtime)
            # Use repr() instead of json.dumps() to get valid Python syntax
            "spec_python": repr(spec_dict),
            # Flattened spec sections for easy template access
            "agent": spec_dict.get("agent", {}),
            "io_schema": spec_dict.get("io_schema"),
            "arguments": spec_dict.get("arguments"),
            "policies": spec_dict.get("policies"),
            "auth": spec_dict.get("auth"),
            "observability": spec_dict.get("observability"),
            "expose": spec_dict.get("expose"),
            "metadata": spec_dict.get("metadata"),
            # Build resolution - new unified system
            "all_directories": build_resolution.directories,
            "all_files": build_resolution.files,
            "build_warnings": build_resolution.warnings,
            # Legacy compatibility - agent_directories for backward compatibility
            "agent_directories": build_resolution.directories,
            "agent_files": build_resolution.files,
            # Computed values
            "extra_dependencies": self._get_extra_dependencies(),
            # Merged dependencies (with conflict resolution)
            "merged_requirements": self._get_merged_requirements(),
            # User requirements file path (for reference)
            "user_requirements_file": self._get_user_requirements_path(),
        }

        # Log any build warnings
        for warning in build_resolution.warnings:
            logger.warning(f"Build warning: {warning}")

        # Merge extra context
        if extra_context:
            context.update(extra_context)

        return context

    def _resolve_build_includes(self) -> BuildResolution:
        """
        Resolve what files and directories to include in the build.

        Uses BuildResolver to combine:
        - Entrypoint detection
        - Explicit includes/excludes
        - Auto-detected imports

        Returns:
            BuildResolution with directories, files, and warnings

        Raises:
            BuildConflictError: If critical conflicts are detected
        """
        resolver = BuildResolver(self.spec, self.project_root)
        return resolver.resolve()

    def _get_extra_dependencies(self) -> List[str]:
        """
        Extract any extra dependencies specified in the spec.

        Supports two formats in Dockfile.yaml:
        1. arguments.dependencies: ["package1", "package2"]  # Preferred
        2. arguments.extra.dependencies: ["package1", "package2"]  # Legacy

        Example Dockfile.yaml:
            arguments:
              dependencies:
                - langchain-openai>=0.1.0
                - langchain-anthropic>=0.1.0

        Returns:
            List of pip package specifiers
        """
        deps: List[str] = []

        if not self.spec.arguments:
            return deps

        args = self.spec.arguments

        # Check for direct dependencies (preferred format)
        # arguments:
        #   dependencies:
        #     - langchain-openai>=0.1.0
        #     - langchain-anthropic>=0.1.0
        if isinstance(args, dict) and "dependencies" in args:
            arg_deps = args["dependencies"]
            if isinstance(arg_deps, list):
                deps.extend(arg_deps)

        # Check for nested extra.dependencies (legacy format)
        # arguments:
        #   extra:
        #     dependencies:
        #       - langchain-openai>=0.1.0
        if isinstance(args, dict) and "extra" in args:
            args_extra = args.get("extra", {})
            if isinstance(args_extra, dict) and "dependencies" in args_extra:
                extra_deps = args_extra["dependencies"]
                if isinstance(extra_deps, list):
                    deps.extend(extra_deps)

        return deps

    def _get_user_requirements_path(self) -> Optional[Path]:
        """
        Get the path to user's requirements file.

        Checks in order:
        1. arguments.requirements_file (user-specified)
        2. requirements.txt (default)

        Returns:
            Path to requirements file if found, None otherwise
        """
        # Check for user-specified requirements file in arguments
        if self.spec.arguments and isinstance(self.spec.arguments, dict):
            req_file = self.spec.arguments.get("requirements_file")
            if req_file:
                req_path = self.project_root / req_file
                if req_path.exists():
                    return req_path

        # Default: look for requirements.txt
        default_path = self.project_root / "requirements.txt"
        if default_path.exists():
            return default_path

        return None

    def _get_merged_requirements(self) -> List[str]:
        """
        Get merged requirements with conflict resolution.

        Merges:
        1. User's requirements.txt (if exists)
        2. Extra dependencies from Dockfile.yaml arguments
        3. Dockrion's required dependencies

        Applies smart version conflict resolution based on:
        - User version compatible → user wins
        - User version incompatible with core → error
        - User version for optional packages → user wins

        Returns:
            List of pip requirement strings

        Raises:
            DependencyConflictError: If incompatible versions detected
        """
        # Determine framework
        framework = "custom"
        if self.spec.agent and self.spec.agent.framework:
            framework = self.spec.agent.framework

        # Determine observability settings
        observability: Dict[str, bool] = {}
        if self.spec.observability:
            obs_dict = self.spec.observability.model_dump()
            if obs_dict.get("langfuse"):
                observability["langfuse"] = True
            if obs_dict.get("langsmith"):
                observability["langsmith"] = True

        # Check for safety policies with redact patterns
        has_safety_policies = False
        if self.spec.policies and self.spec.policies.safety:
            if self.spec.policies.safety.redact_patterns:
                has_safety_policies = True

        # Create merger
        merger = DependencyMerger(
            framework=framework,
            observability=observability,
            has_safety_policies=has_safety_policies,
        )

        # Get user requirements file
        user_req_file = self._get_user_requirements_path()

        # Get extra dependencies from arguments
        extra_deps = self._get_extra_dependencies()

        # Merge dependencies
        try:
            result = merger.merge(
                user_requirements_file=user_req_file,
                extra_dependencies=extra_deps,
            )

            # Log any warnings
            for warning in result.warnings:
                logger.warning(warning)

            return result.requirements
        except DependencyConflictError:
            # Re-raise to be handled by caller
            raise


# ============================================================================
# Template Renderer
# ============================================================================


class TemplateRenderer:
    """
    Main template rendering engine for Dockrion.

    Provides methods to render various templates with proper context
    and error handling.

    Example:
        >>> renderer = TemplateRenderer()
        >>> spec = load_dockspec("Dockfile.yaml")
        >>> runtime_code = renderer.render_runtime(spec)
        >>> dockerfile = renderer.render_dockerfile(spec)
    """

    def __init__(
        self, template_dirs: Optional[List[Union[str, Path]]] = None, strict_mode: bool = True
    ):
        """
        Initialize the template renderer.

        Args:
            template_dirs: Custom template directories (searched first)
            strict_mode: If True, raise errors for undefined variables
        """
        # Build template search path
        search_paths: List[str] = []

        if template_dirs:
            for td in template_dirs:
                path = Path(td)
                if path.exists():
                    search_paths.append(str(path))

        # Add default paths
        for default_dir in DEFAULT_TEMPLATE_DIRS:
            if default_dir.exists():
                search_paths.append(str(default_dir))

        if not search_paths:
            raise DockrionError(
                "No template directories found. Expected templates at:\n"
                + "\n".join(f"  - {d}" for d in DEFAULT_TEMPLATE_DIRS)
            )

        logger.debug(f"Template search paths: {search_paths}")

        # Initialize Jinja2 environment
        self.env = Environment(
            loader=FileSystemLoader(search_paths),
            autoescape=select_autoescape(["html", "xml"]),
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True,
            undefined=StrictUndefined if strict_mode else Undefined,
        )

        # Register custom filters
        self.env.filters["tojson"] = to_json_filter
        self.env.filters["to_python"] = to_python_filter
        self.env.filters["regex_replace"] = regex_replace_filter
        self.env.filters["snake_case"] = snake_case_filter
        self.env.filters["kebab_case"] = kebab_case_filter

        # Store paths for debugging
        self.template_paths = search_paths

    def render(self, template_name: str, context: Dict[str, Any]) -> str:
        """
        Render a template with given context.

        Args:
            template_name: Template file path (relative to template dirs)
            context: Variables to pass to template

        Returns:
            Rendered template as string

        Raises:
            DockrionError: If template not found or rendering fails
        """
        try:
            template = self.env.get_template(template_name)
            rendered = template.render(**context)
            return rendered

        except TemplateNotFound as e:
            raise DockrionError(
                f"Template not found: {template_name}\nSearched in: {self.template_paths}"
            ) from e
        except TemplateError as e:
            raise DockrionError(f"Template rendering error: {e}") from e

    def render_runtime(
        self,
        spec: DockSpec,
        extra_context: Optional[Dict[str, Any]] = None,
        project_root: Optional[Path] = None,
    ) -> str:
        """
        Render the FastAPI runtime code.

        Args:
            spec: Agent specification
            extra_context: Additional template variables
            project_root: Root directory of user's project

        Returns:
            Python code for the runtime
        """
        ctx_builder = TemplateContext(spec, project_root=project_root)
        context = ctx_builder.build(extra_context)

        template_file = TEMPLATE_FILES["runtime"]
        logger.info(f"Rendering runtime from template: {template_file}")

        return self.render(template_file, context)

    def render_dockerfile(
        self,
        spec: DockSpec,
        extra_context: Optional[Dict[str, Any]] = None,
        agent_path: str = ".",
        local_pypi_url: Optional[str] = None,
        project_root: Optional[Path] = None,
    ) -> str:
        """
        Render the Dockerfile.

        Args:
            spec: Agent specification
            extra_context: Additional template variables
            agent_path: Relative path from build context to agent directory
            local_pypi_url: URL of local PyPI server for framework development
            project_root: Root directory of user's project

        Returns:
            Dockerfile content
        """
        ctx_builder = TemplateContext(spec, project_root=project_root)
        context = ctx_builder.build(extra_context)

        # Add agent_path to context for Dockerfile template
        context["agent_path"] = agent_path
        # Add local PyPI URL if provided (for framework development)
        context["local_pypi_url"] = local_pypi_url

        template_file = TEMPLATE_FILES["dockerfile"]
        logger.info(f"Rendering Dockerfile from template: {template_file}")

        return self.render(template_file, context)

    def render_requirements(
        self,
        spec: DockSpec,
        extra_context: Optional[Dict[str, Any]] = None,
        project_root: Optional[Path] = None,
        use_merged: bool = True,
    ) -> str:
        """
        Render the requirements.txt file.

        Args:
            spec: Agent specification
            extra_context: Additional template variables
            project_root: Root directory of user's project
            use_merged: If True, use merged dependencies with conflict resolution

        Returns:
            Requirements file content

        Raises:
            DependencyConflictError: If use_merged=True and incompatible versions detected
        """
        ctx_builder = TemplateContext(spec, project_root=project_root)

        # Build context once - this may raise DependencyConflictError
        # which should propagate to the caller
        try:
            context = ctx_builder.build(extra_context)
        except DependencyConflictError:
            # Re-raise to be handled by caller
            raise

        # If use_merged and merged_requirements is available, generate directly
        if use_merged and context.get("merged_requirements"):
            return self._generate_merged_requirements_content(spec, context)

        # Fallback to template-based rendering (reuse the same context)
        template_file = TEMPLATE_FILES["requirements"]
        logger.info(f"Rendering requirements from template: {template_file}")

        result = self.render(template_file, context)
        return result

    def _generate_merged_requirements_content(self, spec: DockSpec, context: Dict[str, Any]) -> str:
        """
        Generate requirements.txt content from merged dependencies.

        Args:
            spec: Agent specification
            context: Template context with merged_requirements

        Returns:
            Requirements file content
        """
        lines = [
            "# ============================================================================",
            "# Dockrion Agent Runtime - Python Dependencies",
            "# ============================================================================",
            f"# Agent: {context.get('agent', {}).get('name', 'unknown')}",
            f"# Framework: {context.get('agent', {}).get('framework', 'custom')}",
            "# Generated by Dockrion SDK",
            "# ============================================================================",
            "",
        ]

        # Add all merged requirements
        merged = context.get("merged_requirements", [])
        if merged:
            lines.append("# Dependencies (merged from user and dockrion requirements)")
            lines.append("# --------------------------------------------------------")
            lines.extend(sorted(merged))
            lines.append("")

        return "\n".join(lines)

    def render_all(
        self,
        spec: DockSpec,
        extra_context: Optional[Dict[str, Any]] = None,
        project_root: Optional[Path] = None,
    ) -> Dict[str, str]:
        """
        Render all deployment templates.

        Args:
            spec: Agent specification
            extra_context: Additional template variables
            project_root: Root directory of user's project

        Returns:
            Dictionary mapping file names to rendered content:
            {
                "main.py": "...",
                "Dockerfile": "...",
                "requirements.txt": "..."
            }
        """
        return {
            "main.py": self.render_runtime(spec, extra_context, project_root=project_root),
            "Dockerfile": self.render_dockerfile(spec, extra_context, project_root=project_root),
            "requirements.txt": self.render_requirements(
                spec, extra_context, project_root=project_root
            ),
        }

    def list_templates(self) -> List[str]:
        """
        List all available templates.

        Returns:
            List of template file paths
        """
        templates: List[str] = []
        for path in self.template_paths:
            for root, _, files in os.walk(path):
                for file in files:
                    if file.endswith(".j2"):
                        rel_path = os.path.relpath(os.path.join(root, file), path)
                        if rel_path not in templates:
                            templates.append(rel_path)
        return sorted(templates)


# ============================================================================
# Convenience Functions
# ============================================================================

# Global renderer instance (lazy initialization)
_renderer: Optional[TemplateRenderer] = None


def get_renderer() -> TemplateRenderer:
    """Get or create the global template renderer."""
    global _renderer
    if _renderer is None:
        _renderer = TemplateRenderer()
    return _renderer


def render_runtime(spec: DockSpec, **kwargs: Any) -> str:
    """Convenience function to render runtime code."""
    return get_renderer().render_runtime(spec, kwargs if kwargs else None)


def render_dockerfile(spec: DockSpec, **kwargs: Any) -> str:
    """Convenience function to render Dockerfile."""
    return get_renderer().render_dockerfile(spec, kwargs if kwargs else None)


def render_requirements(spec: DockSpec, **kwargs: Any) -> str:
    """Convenience function to render requirements.txt."""
    return get_renderer().render_requirements(spec, kwargs if kwargs else None)


__all__ = [
    "TemplateRenderer",
    "TemplateContext",
    "render_runtime",
    "render_dockerfile",
    "render_requirements",
    "get_renderer",
    "DOCKRION_VERSION",
    "TEMPLATE_FILES",
    "DependencyConflictError",
    "BuildConflictError",
]
