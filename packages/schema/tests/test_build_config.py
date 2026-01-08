"""Tests for BuildConfig and BuildIncludeConfig models."""

import pytest
from pydantic import ValidationError as PydanticValidationError

from dockrion_common.errors import ValidationError as DockrionValidationError
from dockrion_schema.dockfile_v1 import (
    BuildConfig,
    BuildIncludeConfig,
    DockSpec,
)


class TestBuildIncludeConfig:
    """Tests for BuildIncludeConfig model."""

    def test_default_values(self):
        """Test default values for BuildIncludeConfig."""
        config = BuildIncludeConfig()

        assert config.directories == []
        assert config.files == []
        assert config.patterns == []

    def test_with_directories(self):
        """Test BuildIncludeConfig with directories."""
        config = BuildIncludeConfig(directories=["utils", "models"])

        assert config.directories == ["utils", "models"]
        assert config.files == []
        assert config.patterns == []

    def test_with_files(self):
        """Test BuildIncludeConfig with files."""
        config = BuildIncludeConfig(files=["config.yaml", "constants.py"])

        assert config.files == ["config.yaml", "constants.py"]

    def test_with_patterns(self):
        """Test BuildIncludeConfig with patterns."""
        config = BuildIncludeConfig(patterns=["*.json", "data/**"])

        assert config.patterns == ["*.json", "data/**"]

    def test_with_all_fields(self):
        """Test BuildIncludeConfig with all fields."""
        config = BuildIncludeConfig(
            directories=["utils"],
            files=["config.yaml"],
            patterns=["*.json"],
        )

        assert config.directories == ["utils"]
        assert config.files == ["config.yaml"]
        assert config.patterns == ["*.json"]

    def test_empty_string_in_directories_fails(self):
        """Test that empty strings in directories are rejected."""
        with pytest.raises(DockrionValidationError) as exc_info:
            BuildIncludeConfig(directories=["utils", ""])

        assert "empty" in str(exc_info.value).lower()

    def test_empty_string_in_files_fails(self):
        """Test that empty strings in files are rejected."""
        with pytest.raises(DockrionValidationError) as exc_info:
            BuildIncludeConfig(files=["config.yaml", ""])

        assert "empty" in str(exc_info.value).lower()

    def test_empty_string_in_patterns_fails(self):
        """Test that empty strings in patterns are rejected."""
        with pytest.raises(DockrionValidationError) as exc_info:
            BuildIncludeConfig(patterns=["*.json", "   "])

        assert "empty" in str(exc_info.value).lower()

    def test_extra_fields_allowed(self):
        """Test that extra fields are allowed for extensibility."""
        config = BuildIncludeConfig(
            directories=["utils"],
            future_field="value",
        )

        assert config.directories == ["utils"]


class TestBuildConfig:
    """Tests for BuildConfig model."""

    def test_default_values(self):
        """Test default values for BuildConfig."""
        config = BuildConfig()

        assert config.include is None
        assert config.exclude == []
        assert config.auto_detect_imports is False

    def test_with_include(self):
        """Test BuildConfig with include."""
        config = BuildConfig(
            include=BuildIncludeConfig(directories=["utils"]),
        )

        assert config.include is not None
        assert config.include.directories == ["utils"]

    def test_with_exclude(self):
        """Test BuildConfig with exclude patterns."""
        config = BuildConfig(exclude=["tests/", "**/__pycache__"])

        assert config.exclude == ["tests/", "**/__pycache__"]

    def test_with_auto_detect(self):
        """Test BuildConfig with auto_detect_imports enabled."""
        config = BuildConfig(auto_detect_imports=True)

        assert config.auto_detect_imports is True

    def test_with_all_fields(self):
        """Test BuildConfig with all fields."""
        config = BuildConfig(
            include=BuildIncludeConfig(
                directories=["utils", "models"],
                files=["config.yaml"],
                patterns=["data/*.json"],
            ),
            exclude=["tests/", "*.pyc"],
            auto_detect_imports=True,
        )

        assert config.include.directories == ["utils", "models"]
        assert config.include.files == ["config.yaml"]
        assert config.include.patterns == ["data/*.json"]
        assert config.exclude == ["tests/", "*.pyc"]
        assert config.auto_detect_imports is True

    def test_empty_exclude_pattern_fails(self):
        """Test that empty exclude patterns are rejected."""
        with pytest.raises(DockrionValidationError) as exc_info:
            BuildConfig(exclude=["tests/", ""])

        assert "empty" in str(exc_info.value).lower()

    def test_extra_fields_allowed(self):
        """Test that extra fields are allowed for extensibility."""
        config = BuildConfig(
            exclude=["tests/"],
            future_option=True,
        )

        assert config.exclude == ["tests/"]


class TestDockSpecWithBuild:
    """Tests for DockSpec integration with BuildConfig."""

    def test_dockspec_without_build(self):
        """Test DockSpec without build config."""
        spec = DockSpec.model_validate({
            "version": "1.0",
            "agent": {
                "name": "test-agent",
                "entrypoint": "app:handler",
                "framework": "langgraph",
            },
            "io_schema": {
                "input": {"type": "object"},
                "output": {"type": "object"},
            },
            "expose": {"port": 8080},
        })

        assert spec.build is None

    def test_dockspec_with_build(self):
        """Test DockSpec with build config."""
        spec = DockSpec.model_validate({
            "version": "1.0",
            "agent": {
                "name": "test-agent",
                "entrypoint": "app:handler",
                "framework": "langgraph",
            },
            "io_schema": {
                "input": {"type": "object"},
                "output": {"type": "object"},
            },
            "expose": {"port": 8080},
            "build": {
                "include": {
                    "directories": ["utils", "models"],
                    "files": ["config.yaml"],
                },
                "exclude": ["tests/", "**/__pycache__"],
                "auto_detect_imports": False,
            },
        })

        assert spec.build is not None
        assert spec.build.include is not None
        assert spec.build.include.directories == ["utils", "models"]
        assert spec.build.include.files == ["config.yaml"]
        assert spec.build.exclude == ["tests/", "**/__pycache__"]
        assert spec.build.auto_detect_imports is False

    def test_dockspec_with_minimal_build(self):
        """Test DockSpec with minimal build config."""
        spec = DockSpec.model_validate({
            "version": "1.0",
            "agent": {
                "name": "test-agent",
                "entrypoint": "app:handler",
                "framework": "langgraph",
            },
            "io_schema": {
                "input": {"type": "object"},
                "output": {"type": "object"},
            },
            "expose": {"port": 8080},
            "build": {
                "auto_detect_imports": True,
            },
        })

        assert spec.build is not None
        assert spec.build.include is None
        assert spec.build.exclude == []
        assert spec.build.auto_detect_imports is True

    def test_dockspec_with_only_exclude(self):
        """Test DockSpec with only exclude patterns."""
        spec = DockSpec.model_validate({
            "version": "1.0",
            "agent": {
                "name": "test-agent",
                "entrypoint": "app:handler",
                "framework": "langgraph",
            },
            "io_schema": {
                "input": {"type": "object"},
                "output": {"type": "object"},
            },
            "expose": {"port": 8080},
            "build": {
                "exclude": ["tests/", "docs/"],
            },
        })

        assert spec.build is not None
        assert spec.build.include is None
        assert spec.build.exclude == ["tests/", "docs/"]
        assert spec.build.auto_detect_imports is False

    def test_dockspec_serialization(self):
        """Test that build config serializes correctly."""
        spec = DockSpec.model_validate({
            "version": "1.0",
            "agent": {
                "name": "test-agent",
                "entrypoint": "app:handler",
                "framework": "langgraph",
            },
            "io_schema": {
                "input": {"type": "object"},
                "output": {"type": "object"},
            },
            "expose": {"port": 8080},
            "build": {
                "include": {
                    "directories": ["utils"],
                },
                "exclude": ["tests/"],
                "auto_detect_imports": True,
            },
        })

        # Serialize and deserialize
        data = spec.model_dump()
        restored = DockSpec.model_validate(data)

        assert restored.build is not None
        assert restored.build.include.directories == ["utils"]
        assert restored.build.exclude == ["tests/"]
        assert restored.build.auto_detect_imports is True

