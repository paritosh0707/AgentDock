"""Tests for path utilities."""

import sys

from dockrion_common.path_utils import (
    add_to_python_path,
    resolve_module_path,
    setup_module_path,
)


class TestResolveModulePath:
    """Tests for resolve_module_path function."""

    def test_module_in_base_dir(self, tmp_path):
        """Test when module exists in base directory."""
        # Create structure: tmp_path/app/
        app_dir = tmp_path / "app"
        app_dir.mkdir()
        (app_dir / "__init__.py").touch()

        result = resolve_module_path("app.service:handler", tmp_path)
        assert result == tmp_path

    def test_module_in_parent_dir(self, tmp_path):
        """Test when module exists in parent directory."""
        # Create structure: tmp_path/app/ and tmp_path/subdir/
        app_dir = tmp_path / "app"
        app_dir.mkdir()
        (app_dir / "__init__.py").touch()

        subdir = tmp_path / "subdir"
        subdir.mkdir()

        result = resolve_module_path("app.service:handler", subdir)
        assert result == tmp_path

    def test_module_two_levels_up(self, tmp_path):
        """Test when module is two levels up."""
        # Create structure: tmp_path/app/ and tmp_path/sub1/sub2/
        app_dir = tmp_path / "app"
        app_dir.mkdir()
        (app_dir / "__init__.py").touch()

        sub1 = tmp_path / "sub1"
        sub1.mkdir()
        sub2 = sub1 / "sub2"
        sub2.mkdir()

        result = resolve_module_path("app.service:handler", sub2)
        assert result == tmp_path

    def test_module_not_found_returns_base_dir(self, tmp_path):
        """Test when module is not found, returns base directory."""
        result = resolve_module_path("nonexistent.module:handler", tmp_path)
        assert result == tmp_path

    def test_nested_module_path(self, tmp_path):
        """Test with nested module path."""
        # Create structure: tmp_path/myapp/services/
        myapp_dir = tmp_path / "myapp"
        myapp_dir.mkdir()
        (myapp_dir / "__init__.py").touch()

        services_dir = myapp_dir / "services"
        services_dir.mkdir()
        (services_dir / "__init__.py").touch()

        result = resolve_module_path("myapp.services.handler:process", tmp_path)
        assert result == tmp_path

    def test_module_path_without_callable(self, tmp_path):
        """Test module path without callable part."""
        app_dir = tmp_path / "app"
        app_dir.mkdir()
        (app_dir / "__init__.py").touch()

        result = resolve_module_path("app.service", tmp_path)
        assert result == tmp_path

    def test_max_levels_limit(self, tmp_path):
        """Test that max_levels limit is respected."""
        # Create deep structure but set max_levels low
        app_dir = tmp_path / "app"
        app_dir.mkdir()

        # Create deep nested structure
        deep = tmp_path
        for i in range(10):
            deep = deep / f"level{i}"
            deep.mkdir()

        # With max_levels=2, should not find module at tmp_path
        result = resolve_module_path("app:handler", deep, max_levels=2)
        # Should return somewhere in the path, not tmp_path
        assert result != tmp_path


class TestAddToPythonPath:
    """Tests for add_to_python_path function."""

    def test_add_new_path(self, tmp_path):
        """Test adding a new path to sys.path."""
        # Ensure path is not in sys.path
        path_str = str(tmp_path.resolve())
        if path_str in sys.path:
            sys.path.remove(path_str)

        result = add_to_python_path(tmp_path)
        assert result is True
        assert path_str in sys.path

        # Cleanup
        sys.path.remove(path_str)

    def test_add_existing_path(self, tmp_path):
        """Test adding a path that's already in sys.path."""
        path_str = str(tmp_path.resolve())

        # Add it first
        if path_str not in sys.path:
            sys.path.insert(0, path_str)

        # Try to add again
        result = add_to_python_path(tmp_path)
        assert result is False

        # Cleanup
        sys.path.remove(path_str)

    def test_path_added_at_beginning(self, tmp_path):
        """Test that path is added at the beginning of sys.path."""
        path_str = str(tmp_path.resolve())
        if path_str in sys.path:
            sys.path.remove(path_str)

        original_first = sys.path[0]
        add_to_python_path(tmp_path)

        assert sys.path[0] == path_str

        # Cleanup
        sys.path.remove(path_str)


class TestSetupModulePath:
    """Tests for setup_module_path function."""

    def test_setup_module_path(self, tmp_path):
        """Test complete setup of module path."""
        # Create structure
        app_dir = tmp_path / "app"
        app_dir.mkdir()
        (app_dir / "__init__.py").touch()

        subdir = tmp_path / "subdir"
        subdir.mkdir()

        # Ensure not in sys.path
        path_str = str(tmp_path.resolve())
        if path_str in sys.path:
            sys.path.remove(path_str)

        result = setup_module_path("app.service:handler", subdir)

        assert result == tmp_path
        assert path_str in sys.path

        # Cleanup
        sys.path.remove(path_str)

    def test_setup_with_custom_max_levels(self, tmp_path):
        """Test setup with custom max_levels parameter."""
        app_dir = tmp_path / "app"
        app_dir.mkdir()

        subdir = tmp_path / "subdir"
        subdir.mkdir()

        path_str = str(tmp_path.resolve())
        if path_str in sys.path:
            sys.path.remove(path_str)

        result = setup_module_path("app:handler", subdir, max_levels=10)

        assert result == tmp_path
        assert path_str in sys.path

        # Cleanup
        sys.path.remove(path_str)


class TestRealWorldScenarios:
    """Tests for real-world usage scenarios."""

    def test_invoice_copilot_structure(self, tmp_path):
        """Test with structure similar to invoice_copilot example."""
        # Create: examples/invoice_copilot/app/service.py
        examples = tmp_path / "examples"
        examples.mkdir()

        invoice = examples / "invoice_copilot"
        invoice.mkdir()

        app = invoice / "app"
        app.mkdir()
        (app / "__init__.py").touch()
        (app / "service.py").touch()

        # Dockfile is in invoice_copilot directory
        dockfile_dir = invoice

        result = resolve_module_path("app.service:process_invoice", dockfile_dir)
        assert result == invoice

    def test_top_level_module_structure(self, tmp_path):
        """Test with top-level module structure."""
        # Create: myproject/myapp/handlers.py
        myapp = tmp_path / "myapp"
        myapp.mkdir()
        (myapp / "__init__.py").touch()
        (myapp / "handlers.py").touch()

        result = resolve_module_path("myapp.handlers:process", tmp_path)
        assert result == tmp_path
