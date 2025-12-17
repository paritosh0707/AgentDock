"""
Dockrion Template Renderer
==========================

Provides a robust, flexible template system for generating:
- FastAPI runtime code
- Dockerfiles
- Requirements files
- Other deployment artifacts

Uses Jinja2 with custom filters and extensions for maximum flexibility.
"""

import os
import json
import re
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from datetime import datetime

from jinja2 import (
    Environment,
    FileSystemLoader,
    select_autoescape,
    TemplateNotFound,
    TemplateError,
    StrictUndefined
)

from dockrion_schema import DockSpec
from dockrion_common.errors import DockrionError
from dockrion_common.logger import get_logger

logger = get_logger(__name__)

# ============================================================================
# Constants
# ============================================================================

DOCKRION_VERSION = "1.0.0"

# Default template directories (searched in order)
DEFAULT_TEMPLATE_DIRS = [
    # User-provided templates (highest priority)
    Path.cwd() / "templates",
    # Package templates
    Path(__file__).parent.parent.parent.parent / "templates",
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

def to_json_filter(value: Any, indent: int = None) -> str:
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
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', value)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


def kebab_case_filter(value: str) -> str:
    """Convert string to kebab-case."""
    return snake_case_filter(value).replace('_', '-')


# ============================================================================
# Template Context Builder
# ============================================================================

class TemplateContext:
    """
    Builds the context dictionary for template rendering.
    
    Extracts and transforms data from DockSpec into template-friendly format.
    """
    
    def __init__(self, spec: DockSpec):
        """
        Initialize context builder.
        
        Args:
            spec: The DockSpec containing agent configuration
        """
        self.spec = spec
    
    def build(self, extra_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Build complete template context.
        
        Args:
            extra_context: Additional context variables to include
            
        Returns:
            Dictionary with all template variables
        """
        # Get spec as dictionary
        spec_dict = self.spec.model_dump(mode='python', exclude_none=True)
        
        # Build context with flattened access to common fields
        context = {
            # Meta information
            "dockrion_version": DOCKRION_VERSION,
            "generated_at": datetime.utcnow().isoformat(),
            "python_version": "3.12",
            
            # Full spec as Python literal (for embedding in runtime)
            # Use repr() instead of json.dumps() to get valid Python syntax
            "spec_python": repr(spec_dict),
            
            # Flattened spec sections for easy template access
            "agent": spec_dict.get("agent", {}),
            "model": spec_dict.get("model"),
            "io_schema": spec_dict.get("io_schema"),
            "arguments": spec_dict.get("arguments"),
            "policies": spec_dict.get("policies"),
            "auth": spec_dict.get("auth"),
            "observability": spec_dict.get("observability"),
            "expose": spec_dict.get("expose"),
            "metadata": spec_dict.get("metadata"),
            
            # Computed values
            "agent_directories": self._get_agent_directories(),
            "extra_dependencies": self._get_extra_dependencies(),
        }
        
        # Merge extra context
        if extra_context:
            context.update(extra_context)
        
        return context
    
    def _get_agent_directories(self) -> List[str]:
        """
        Determine which directories contain agent code.
        
        Returns:
            List of directory paths to copy into container
        """
        directories = []
        
        # Extract from entrypoint (if using entrypoint mode)
        entrypoint = self.spec.agent.entrypoint
        if entrypoint and ":" in entrypoint:
            module_path = entrypoint.rsplit(":", 1)[0]
            # Get top-level module/package
            top_module = module_path.split(".")[0]
            if top_module and top_module not in directories:
                directories.append(top_module)
        
        # Extract from handler (if using handler mode)
        handler = self.spec.agent.handler
        if handler and ":" in handler:
            module_path = handler.rsplit(":", 1)[0]
            # Get top-level module/package
            top_module = module_path.split(".")[0]
            if top_module and top_module not in directories:
                directories.append(top_module)
        
        return directories
    
    def _get_extra_dependencies(self) -> List[str]:
        """
        Extract any extra dependencies specified in the spec.
        
        Returns:
            List of pip package specifiers
        """
        deps = []
        
        # Check for extra dependencies in model config
        if self.spec.model and hasattr(self.spec.model, 'extra'):
            extra = self.spec.model.extra
            if isinstance(extra, dict) and 'dependencies' in extra:
                deps.extend(extra['dependencies'])
        
        # Check for dependencies in arguments
        if self.spec.arguments and hasattr(self.spec.arguments, 'extra'):
            args_extra = self.spec.arguments.extra
            if isinstance(args_extra, dict) and 'dependencies' in args_extra:
                deps.extend(args_extra['dependencies'])
        
        return deps


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
        self,
        template_dirs: Optional[List[Union[str, Path]]] = None,
        strict_mode: bool = True
    ):
        """
        Initialize the template renderer.
        
        Args:
            template_dirs: Custom template directories (searched first)
            strict_mode: If True, raise errors for undefined variables
        """
        # Build template search path
        search_paths = []
        
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
                "No template directories found. Expected templates at:\n" +
                "\n".join(f"  - {d}" for d in DEFAULT_TEMPLATE_DIRS)
            )
        
        logger.debug(f"Template search paths: {search_paths}")
        
        # Initialize Jinja2 environment
        self.env = Environment(
            loader=FileSystemLoader(search_paths),
            autoescape=select_autoescape(['html', 'xml']),
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True,
            undefined=StrictUndefined if strict_mode else None
        )
        
        # Register custom filters
        self.env.filters['tojson'] = to_json_filter
        self.env.filters['to_python'] = to_python_filter
        self.env.filters['regex_replace'] = regex_replace_filter
        self.env.filters['snake_case'] = snake_case_filter
        self.env.filters['kebab_case'] = kebab_case_filter
        
        # Store paths for debugging
        self.template_paths = search_paths
    
    def render(
        self,
        template_name: str,
        context: Dict[str, Any]
    ) -> str:
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
            
        except TemplateNotFound:
            raise DockrionError(
                f"Template not found: {template_name}\n"
                f"Searched in: {self.template_paths}"
            )
        except TemplateError as e:
            raise DockrionError(f"Template rendering error: {e}")
    
    def render_runtime(
        self,
        spec: DockSpec,
        extra_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Render the FastAPI runtime code.
        
        Args:
            spec: Agent specification
            extra_context: Additional template variables
            
        Returns:
            Python code for the runtime
        """
        ctx_builder = TemplateContext(spec)
        context = ctx_builder.build(extra_context)
        
        template_file = TEMPLATE_FILES["runtime"]
        logger.info(f"Rendering runtime from template: {template_file}")
        
        return self.render(template_file, context)
    
    def render_dockerfile(
        self,
        spec: DockSpec,
        extra_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Render the Dockerfile.
        
        Args:
            spec: Agent specification
            extra_context: Additional template variables
            
        Returns:
            Dockerfile content
        """
        ctx_builder = TemplateContext(spec)
        context = ctx_builder.build(extra_context)
        
        template_file = TEMPLATE_FILES["dockerfile"]
        logger.info(f"Rendering Dockerfile from template: {template_file}")
        
        return self.render(template_file, context)
    
    def render_requirements(
        self,
        spec: DockSpec,
        extra_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Render the requirements.txt file.
        
        Args:
            spec: Agent specification
            extra_context: Additional template variables
            
        Returns:
            Requirements file content
        """
        ctx_builder = TemplateContext(spec)
        context = ctx_builder.build(extra_context)
        
        template_file = TEMPLATE_FILES["requirements"]
        logger.info(f"Rendering requirements from template: {template_file}")
        
        return self.render(template_file, context)
    
    def render_all(
        self,
        spec: DockSpec,
        extra_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, str]:
        """
        Render all deployment templates.
        
        Args:
            spec: Agent specification
            extra_context: Additional template variables
            
        Returns:
            Dictionary mapping file names to rendered content:
            {
                "main.py": "...",
                "Dockerfile": "...",
                "requirements.txt": "..."
            }
        """
        return {
            "main.py": self.render_runtime(spec, extra_context),
            "Dockerfile": self.render_dockerfile(spec, extra_context),
            "requirements.txt": self.render_requirements(spec, extra_context),
        }
    
    def list_templates(self) -> List[str]:
        """
        List all available templates.
        
        Returns:
            List of template file paths
        """
        templates = []
        for path in self.template_paths:
            for root, _, files in os.walk(path):
                for file in files:
                    if file.endswith('.j2'):
                        rel_path = os.path.relpath(
                            os.path.join(root, file),
                            path
                        )
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


def render_runtime(spec: DockSpec, **kwargs) -> str:
    """Convenience function to render runtime code."""
    return get_renderer().render_runtime(spec, kwargs if kwargs else None)


def render_dockerfile(spec: DockSpec, **kwargs) -> str:
    """Convenience function to render Dockerfile."""
    return get_renderer().render_dockerfile(spec, kwargs if kwargs else None)


def render_requirements(spec: DockSpec, **kwargs) -> str:
    """Convenience function to render requirements.txt."""
    return get_renderer().render_requirements(spec, kwargs if kwargs else None)

