.PHONY: bootstrap bootstrap-dev test test-cov test-verbose lint typecheck ci clean help build build-check pypi-local install-local

# Default target
help:
	@echo "Dockrion Development Commands"
	@echo "=============================="
	@echo ""
	@echo "Setup:"
	@echo "  make bootstrap     - Install all packages in editable mode (user mode)"
	@echo "  make bootstrap-dev - Install all packages with dev dependencies"
	@echo ""
	@echo "Testing:"
	@echo "  make test          - Run all tests"
	@echo "  make test-cov      - Run tests with coverage report"
	@echo "  make test-verbose  - Run tests with verbose output"
	@echo "  make test-fast     - Run tests excluding slow tests"
	@echo ""
	@echo "Quality:"
	@echo "  make lint          - Run linters (ruff)"
	@echo "  make typecheck     - Run type checker (mypy)"
	@echo "  make format        - Format code (ruff format)"
	@echo "  make ci            - Run all CI checks (lint, typecheck, test)"
	@echo ""
	@echo "Build & Publish:"
	@echo "  make build         - Build the dockrion package for distribution"
	@echo "  make build-check   - Build and verify package contents"
	@echo "  make publish-test  - Publish to TestPyPI (for testing)"
	@echo "  make publish       - Publish to PyPI (production)"
	@echo ""
	@echo "Local Testing:"
	@echo "  make pypi-local    - Start local PyPI server on port 8099 (run in separate terminal)"
	@echo "  make install-local - Install dockrion from local PyPI server"
	@echo ""
	@echo "Package-specific testing:"
	@echo "  make test-adapters   - Run adapters tests"
	@echo "  make test-cli        - Run CLI tests"
	@echo "  make test-common     - Run common-py tests"
	@echo "  make test-schema     - Run schema tests"
	@echo "  make test-sdk        - Run SDK tests"
	@echo "  make test-runtime    - Run runtime tests"
	@echo "  make test-policy     - Run policy-engine tests"
	@echo "  make test-telemetry  - Run telemetry tests"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean         - Remove build artifacts and cache files"

# Install all packages in editable mode (for users)
bootstrap:
	uv sync

# Install all packages with dev dependencies (for developers)
bootstrap-dev:
	uv sync --group dev --extra dev

# Install test dependencies only (for CI or quick testing)
bootstrap-test:
	uv sync --group test --extra test

# Run all tests (sequentially per package to avoid import conflicts)
test:
	@echo "=== Testing common-py ===" && uv run pytest packages/common-py/tests -q && \
	echo "=== Testing schema ===" && uv run pytest packages/schema/tests -q && \
	echo "=== Testing adapters ===" && uv run pytest packages/adapters/tests -q && \
	echo "=== Testing events ===" && uv run pytest packages/events/tests -q && \
	echo "=== Testing policy-engine ===" && uv run pytest packages/policy-engine/tests -q && \
	echo "=== Testing telemetry ===" && uv run pytest packages/telemetry/tests -q && \
	echo "=== Testing runtime ===" && uv run pytest packages/runtime/tests -q && \
	echo "=== Testing sdk-python ===" && uv run pytest packages/sdk-python/tests -q && \
	echo "=== Testing cli ===" && uv run pytest packages/cli/tests -q && \
	echo "=== All tests passed! ==="

# Run tests with coverage
test-cov:
	uv run pytest --cov=packages --cov-report=term-missing --cov-report=html

# Run tests with verbose output
test-verbose:
	uv run pytest -v --tb=long

# Run tests excluding slow tests
test-fast:
	uv run pytest -m "not slow"

# Run integration tests only
test-integration:
	uv run pytest -m "integration"

# Package-specific test targets
test-adapters:
	uv run pytest packages/adapters/tests -v

test-cli:
	uv run pytest packages/cli/tests -v

test-common:
	uv run pytest packages/common-py/tests -v

test-schema:
	uv run pytest packages/schema/tests -v

test-sdk:
	uv run pytest packages/sdk-python/tests -v

test-runtime:
	uv run pytest packages/runtime/tests -v

test-policy:
	uv run pytest packages/policy-engine/tests -v

test-telemetry:
	uv run pytest packages/telemetry/tests -v

test-events:
	uv run pytest packages/events/tests -v

# Linting (ignore common acceptable patterns)
# E501: line too long (handled by formatter)
# E402: import not at top (needed in tests for path setup)
# F401: unused import (often intentional in __init__.py)
# F841: unused variable (sometimes intentional in tests)
# B904: raise from (stylistic preference)
# B008: function call in default arg (common FastAPI pattern)
# B017: blind exception (acceptable in tests)
# B027: empty method without abstract decorator (intentional)
lint:
	uv run ruff check packages/ --ignore E501,E402,F401,F841,B904,B008,B017,B027

# Type checking
typecheck:
	@echo "=== Type checking common-py ===" && \
	uv run mypy packages/common-py --ignore-missing-imports --explicit-package-bases && \
	echo "=== Type checking schema ===" && \
	uv run mypy packages/schema --ignore-missing-imports --explicit-package-bases && \
	echo "=== Type checking adapters ===" && \
	uv run mypy packages/adapters --ignore-missing-imports --explicit-package-bases && \
	echo "=== Type checking policy-engine ===" && \
	uv run mypy packages/policy-engine/dockrion_policy --ignore-missing-imports && \
	MYPYPATH=packages/policy-engine uv run mypy packages/policy-engine/tests --ignore-missing-imports && \
	echo "=== Type checking telemetry ===" && \
	uv run mypy packages/telemetry --ignore-missing-imports --explicit-package-bases && \
	echo "=== Type checking runtime ===" && \
	uv run mypy packages/runtime --ignore-missing-imports --explicit-package-bases && \
	echo "=== Type checking sdk-python ===" && \
	uv run mypy packages/sdk-python --ignore-missing-imports --explicit-package-bases && \
	echo "=== Type checking cli ===" && \
	uv run mypy packages/cli --ignore-missing-imports --explicit-package-bases && \
	echo "=== All type checks passed! ==="

# Format code
format:
	uv run ruff format packages/

# Run all CI checks
ci: lint typecheck test
	@echo "=== All CI checks passed! ==="

# ============================================================================
# Build & Publish (only the dockrion meta-package is published)
# ============================================================================

# Build the dockrion package for distribution
build:
	@echo "Building dockrion package..."
	cd packages/dockrion && uv run python build_package.py
	@echo ""
	@echo "Built packages:"
	@ls -la dist/

# Build and verify package contents
build-check: build
	@echo ""
	@echo "Verifying package contents..."
	@uv run python -c "\
import zipfile, glob, sys; \
wheels = glob.glob('dist/dockrion-*.whl'); \
wheel = wheels[0] if wheels else sys.exit('No dockrion wheel found in dist/'); \
print(f'Checking: {wheel}'); \
files = zipfile.ZipFile(wheel).namelist(); \
expected = ['dockrion_common/', 'dockrion_schema/', 'dockrion_adapters/', \
            'dockrion_events/', 'dockrion_policy/', 'dockrion_telemetry/', \
            'dockrion_runtime/', 'dockrion_sdk/', 'dockrion_cli/']; \
missing = [p for p in expected if not any(f.startswith(p) for f in files)]; \
sys.exit(f'Missing: {missing}') if missing else print('✓ All packages included'); \
print(f'Total files: {len(files)}')"
	@echo ""
	@echo "Checking with twine..."
	uv run twine check dist/*

# Publish to TestPyPI (for testing before real publish)
publish-test: build-check
	@echo "Publishing to TestPyPI..."
	uv run twine upload --repository testpypi dist/*

# Publish to PyPI (production)
publish: build-check
	@echo "Publishing to PyPI..."
	uv run twine upload dist/*

# ============================================================================
# Local PyPI Server (for testing before publish)
# ============================================================================

# Start local PyPI server (run this in a separate terminal)
pypi-local: build
	@echo "Starting local PyPI server on http://localhost:8099"
	@echo "Install from another project with:"
	@echo "  uv pip install --index-url http://localhost:8099/simple/ --trusted-host localhost dockrion"
	@echo ""
	uv run python -m pypiserver run -p 8099 ./dist

# Install from local PyPI server (for testing in current environment)
install-local:
	uv pip install --index-url http://localhost:8099/simple/ --trusted-host localhost dockrion

# ============================================================================
# Cleanup
# ============================================================================

# Clean build artifacts
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	# Only remove build directories that are actual build artifacts, not source code
	# Remove build/ at root level and in packages/dockrion/, but exclude source code directories
	rm -rf ./build 2>/dev/null || true
	rm -rf packages/dockrion/build 2>/dev/null || true
	# Also remove build directories in .mypy_cache (type checker cache)
	find . -type d -path "*/.mypy_cache/*/build" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name ".coverage" -delete 2>/dev/null || true
	rm -rf dist/
