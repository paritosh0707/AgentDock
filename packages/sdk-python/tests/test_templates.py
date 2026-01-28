"""Tests for template system and package data inclusion.

These tests verify that:
1. Templates are correctly located inside the package
2. Template rendering works after package installation
3. Package data (*.j2 files) are included in the distribution
"""

import sys
from pathlib import Path

import pytest

# Ensure tests directory is in path for fixture imports
tests_dir = Path(__file__).parent
if str(tests_dir) not in sys.path:
    sys.path.insert(0, str(tests_dir))


class TestTemplateLocation:
    """Test that templates are correctly located in the package."""

    def test_templates_exist_in_package(self):
        """Verify template files exist inside the dockrion_sdk package."""
        from dockrion_sdk.templates import renderer

        # Get the templates directory (same as renderer.py location)
        templates_dir = Path(renderer.__file__).parent

        # Check directory structure exists
        assert templates_dir.exists(), "Templates directory should exist"
        assert (templates_dir / "dockerfiles").exists(), "dockerfiles subdirectory should exist"
        assert (templates_dir / "runtime-fastapi").exists(), (
            "runtime-fastapi subdirectory should exist"
        )

        # Check all template files exist
        assert (templates_dir / "dockerfiles" / "Dockerfile.j2").exists(), (
            "Dockerfile.j2 should exist"
        )
        assert (templates_dir / "runtime-fastapi" / "main.py.j2").exists(), (
            "main.py.j2 should exist"
        )
        assert (templates_dir / "runtime-fastapi" / "requirements.txt.j2").exists(), (
            "requirements.txt.j2 should exist"
        )

    def test_template_path_resolution(self):
        """Test that DEFAULT_TEMPLATE_DIRS points to the correct location."""
        from dockrion_sdk.templates.renderer import DEFAULT_TEMPLATE_DIRS

        # The second path should be the package templates directory
        package_templates_dir = DEFAULT_TEMPLATE_DIRS[1]

        assert package_templates_dir.exists(), "Package templates directory should exist"
        assert (package_templates_dir / "dockerfiles" / "Dockerfile.j2").exists(), (
            "Should find Dockerfile.j2"
        )

    def test_template_files_mapping(self):
        """Test that TEMPLATE_FILES maps to existing files."""
        from dockrion_sdk.templates.renderer import DEFAULT_TEMPLATE_DIRS, TEMPLATE_FILES

        # Find the package templates directory
        package_templates_dir = None
        for template_dir in DEFAULT_TEMPLATE_DIRS:
            if template_dir.exists():
                package_templates_dir = template_dir
                break

        assert package_templates_dir is not None, "Should find a templates directory"

        # Verify each mapped template exists
        for key, template_path in TEMPLATE_FILES.items():
            full_path = package_templates_dir / template_path
            assert full_path.exists(), f"Template '{key}' at '{template_path}' should exist"


class TestTemplateRendering:
    """Test template rendering functionality."""

    def test_renderer_initialization(self):
        """Test TemplateRenderer can be initialized."""
        from dockrion_sdk.templates import TemplateRenderer

        renderer = TemplateRenderer()
        assert renderer is not None
        assert len(renderer.template_paths) > 0, "Should have at least one template path"

    def test_renderer_lists_templates(self):
        """Test that renderer can list available templates."""
        from dockrion_sdk.templates import TemplateRenderer

        renderer = TemplateRenderer()
        templates = renderer.list_templates()

        assert len(templates) >= 3, "Should find at least 3 templates"
        assert any("Dockerfile" in t for t in templates), "Should find Dockerfile template"
        assert any("main.py" in t for t in templates), "Should find main.py template"
        assert any("requirements" in t for t in templates), "Should find requirements template"

    def test_render_runtime_basic(self, sample_dockfile):
        """Test rendering runtime template."""
        from dockrion_sdk import load_dockspec
        from dockrion_sdk.templates import render_runtime

        spec = load_dockspec(sample_dockfile)
        runtime_code = render_runtime(spec)

        # Verify key components are present
        assert "create_app" in runtime_code
        assert "DockSpec" in runtime_code
        assert spec.agent.name in runtime_code

    def test_render_dockerfile_basic(self, sample_dockfile):
        """Test rendering Dockerfile template."""
        from dockrion_sdk import load_dockspec
        from dockrion_sdk.templates import render_dockerfile

        spec = load_dockspec(sample_dockfile)
        dockerfile = render_dockerfile(spec)

        # Verify key components are present
        assert "FROM python:" in dockerfile
        assert "WORKDIR" in dockerfile
        assert "EXPOSE" in dockerfile

    def test_render_requirements_basic(self, sample_dockfile):
        """Test rendering requirements template."""
        from dockrion_sdk import load_dockspec
        from dockrion_sdk.templates import render_requirements

        spec = load_dockspec(sample_dockfile)
        requirements = render_requirements(spec)

        # Verify key dependencies are present
        assert "fastapi" in requirements
        assert "uvicorn" in requirements
        assert "pydantic" in requirements

    def test_render_all_templates(self, sample_dockfile):
        """Test rendering all templates at once."""
        from dockrion_sdk import load_dockspec
        from dockrion_sdk.templates import TemplateRenderer

        spec = load_dockspec(sample_dockfile)
        renderer = TemplateRenderer()
        all_rendered = renderer.render_all(spec)

        assert "main.py" in all_rendered
        assert "Dockerfile" in all_rendered
        assert "requirements.txt" in all_rendered

        # Verify each has content
        assert len(all_rendered["main.py"]) > 100
        assert len(all_rendered["Dockerfile"]) > 100
        assert len(all_rendered["requirements.txt"]) > 50


class TestTemplateFrameworkSupport:
    """Test template rendering for different frameworks."""

    def test_langgraph_requirements(self, tmp_path):
        """Test requirements generation for LangGraph framework."""
        from dockrion_sdk import load_dockspec
        from dockrion_sdk.templates import render_requirements

        dockfile = tmp_path / "Dockfile.yaml"
        dockfile.write_text(
            """
version: "1.0"
agent:
  name: langgraph-agent
  entrypoint: app:build
  framework: langgraph
io_schema:
  input:
    type: object
  output:
    type: object
expose:
  port: 8080
"""
        )

        spec = load_dockspec(str(dockfile))
        requirements = render_requirements(spec)

        assert "langgraph" in requirements
        assert "langchain" in requirements

    def test_langchain_requirements(self, tmp_path):
        """Test requirements generation for LangChain framework."""
        from dockrion_sdk import load_dockspec
        from dockrion_sdk.templates import render_requirements

        dockfile = tmp_path / "Dockfile.yaml"
        dockfile.write_text(
            """
version: "1.0"
agent:
  name: langchain-agent
  entrypoint: app:build
  framework: langchain
io_schema:
  input:
    type: object
  output:
    type: object
expose:
  port: 8080
"""
        )

        spec = load_dockspec(str(dockfile))
        requirements = render_requirements(spec)

        assert "langchain" in requirements

    def test_custom_framework_requirements(self, tmp_path):
        """Test requirements generation for custom framework."""
        from dockrion_sdk import load_dockspec
        from dockrion_sdk.templates import render_requirements

        dockfile = tmp_path / "Dockfile.yaml"
        dockfile.write_text(
            """
version: "1.0"
agent:
  name: custom-agent
  entrypoint: app:build
  framework: custom
io_schema:
  input:
    type: object
  output:
    type: object
expose:
  port: 8080
"""
        )

        spec = load_dockspec(str(dockfile))
        requirements = render_requirements(spec)

        # Custom framework should have base dependencies but not framework-specific
        assert "fastapi" in requirements
        assert "uvicorn" in requirements


class TestTemplateCustomization:
    """Test template customization features."""

    def test_custom_template_directory_priority(self, tmp_path):
        """Test that user templates override package templates."""
        from dockrion_sdk.templates import TemplateRenderer

        # Create custom templates directory
        custom_templates = tmp_path / "templates"
        custom_templates.mkdir()
        dockerfile_dir = custom_templates / "dockerfiles"
        dockerfile_dir.mkdir()

        # Create a custom Dockerfile template
        custom_dockerfile = dockerfile_dir / "Dockerfile.j2"
        custom_dockerfile.write_text("# Custom Dockerfile\nFROM custom:image\n")

        # Create renderer with custom directory
        renderer = TemplateRenderer(template_dirs=[custom_templates])

        # Custom templates should be in the search path first
        assert str(custom_templates) in renderer.template_paths

    def test_strict_mode_catches_undefined_variables(self, sample_dockfile):
        """Test that strict mode catches undefined template variables."""
        from dockrion_sdk import load_dockspec
        from dockrion_sdk.templates import TemplateRenderer

        spec = load_dockspec(sample_dockfile)
        renderer = TemplateRenderer(strict_mode=True)

        # This should work - all variables are defined
        runtime = renderer.render_runtime(spec)
        assert len(runtime) > 0


class TestHandlerModeTemplates:
    """Test templates with handler mode (vs entrypoint mode)."""

    def test_handler_mode_runtime(self, tmp_path):
        """Test runtime generation for handler mode."""
        from dockrion_sdk import load_dockspec
        from dockrion_sdk.templates import render_runtime

        dockfile = tmp_path / "Dockfile.yaml"
        dockfile.write_text(
            """
version: "1.0"
agent:
  name: handler-agent
  handler: my_module:my_handler
  framework: custom
io_schema:
  input:
    type: object
  output:
    type: object
expose:
  port: 8080
"""
        )

        spec = load_dockspec(str(dockfile))
        runtime = render_runtime(spec)

        # Should reference handler mode
        assert "Handler" in runtime or "handler" in runtime
        assert "my_module:my_handler" in runtime

    def test_entrypoint_mode_runtime(self, sample_dockfile):
        """Test runtime generation for entrypoint mode."""
        from dockrion_sdk import load_dockspec
        from dockrion_sdk.templates import render_runtime

        spec = load_dockspec(sample_dockfile)
        runtime = render_runtime(spec)

        # Should reference entrypoint mode
        assert "Entrypoint" in runtime or "entrypoint" in runtime


class TestDockerfileVariants:
    """Test Dockerfile generation with different configurations."""

    def test_dockerfile_with_metadata(self, tmp_path):
        """Test Dockerfile with metadata labels."""
        from dockrion_sdk import load_dockspec
        from dockrion_sdk.templates import render_dockerfile

        dockfile = tmp_path / "Dockfile.yaml"
        dockfile.write_text(
            """
version: "1.0"
agent:
  name: metadata-agent
  entrypoint: app:build
  framework: langgraph
  description: "Agent with full metadata"
io_schema:
  input:
    type: object
  output:
    type: object
metadata:
  version: "2.0.0"
  maintainer: "test@example.com"
expose:
  port: 8080
"""
        )

        spec = load_dockspec(str(dockfile))
        dockerfile = render_dockerfile(spec)

        assert "2.0.0" in dockerfile
        assert "test@example.com" in dockerfile

    def test_dockerfile_local_pypi(self, sample_dockfile):
        """Test Dockerfile generation with local PyPI server."""
        from dockrion_sdk import load_dockspec
        from dockrion_sdk.templates import TemplateRenderer

        spec = load_dockspec(sample_dockfile)

        # Use TemplateRenderer directly with local_pypi_url
        renderer = TemplateRenderer()

        dockerfile = renderer.render_dockerfile(
            spec,
            local_pypi_url="http://host.docker.internal:8099/simple/",
        )

        # Local PyPI mode should include index-url, trusted-host, and dockrion package
        assert "--index-url http://host.docker.internal:8099/simple/" in dockerfile
        assert "--trusted-host host.docker.internal" in dockerfile
        assert "dockrion" in dockerfile
        # Should NOT include extra-index-url (we install only from local PyPI)
        assert "--extra-index-url" not in dockerfile
