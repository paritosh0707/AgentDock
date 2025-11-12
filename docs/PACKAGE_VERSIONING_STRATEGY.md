# Package Versioning Strategy

Comprehensive guide for versioning AgentDock packages and managing dependencies.

---

## Overview

AgentDock follows **Semantic Versioning (SemVer)** for all packages. This document explains how to version packages, manage dependencies, and handle upgrades.

---

## Semantic Versioning Basics

Format: `MAJOR.MINOR.PATCH` (e.g., `1.2.3`)

- **MAJOR** (1.x.x): Breaking changes, incompatible API changes
- **MINOR** (x.2.x): New features, backward-compatible
- **PATCH** (x.x.3): Bug fixes, backward-compatible

### Pre-release Versions
- `0.x.x`: Initial development, API may change
- `1.0.0`: First stable release

---

## Current Package Versions

| Package | Version | Status |
|---------|---------|--------|
| `agentdock-common` | 0.1.1 | Development |
| `agentdock-schema` | 0.1.0 | Development |
| `agentdock-adapters` | TBD | Not started |
| `agentdock-policy-engine` | TBD | Not started |
| `agentdock-telemetry` | TBD | Not started |
| `agentdock-sdk-python` | TBD | Not started |
| `agentdock-cli` | TBD | Not started |

---

## Dependency Versioning

### Common Package (Foundation)

**No internal dependencies** - Only external deps:

```toml
# packages/common-py/pyproject.toml
[project]
name = "agentdock-common"
version = "0.1.1"
dependencies = [
    "pydantic>=2.5,<3.0"  # Allow minor updates, block major
]
```

### Schema Package (Depends on Common)

**Uses compatible release operator** (`~=`) or range:

```toml
# packages/schema/pyproject.toml
[project]
name = "agentdock-schema"
version = "0.1.0"
dependencies = [
    "pydantic>=2.5,<3.0",
    "agentdock-common>=0.1.1,<0.2.0",  # Compatible with 0.1.x only
]
```

**Explanation:**
- `>=0.1.1`: Requires at least 0.1.1 (for ConfigDict support)
- `<0.2.0`: Block 0.2.x (may have breaking changes)
- Allows: `0.1.1`, `0.1.2`, `0.1.15`, etc.
- Blocks: `0.2.0`, `0.2.1`, `1.0.0`, etc.

### Alternative Notation (Equivalent)

```toml
dependencies = [
    "agentdock-common~=0.1.1",  # Same as >=0.1.1,<0.2.0
]
```

---

## Version Update Scenarios

### Scenario 1: Bug Fix in Common (Patch)

**Common: 0.1.1 → 0.1.2**

```python
# Fix bug in validate_entrypoint
def validate_entrypoint(entrypoint: str):
    # Bug fix: Handle edge case better
    ...
```

**Impact:**
- ✅ Schema automatically gets fix (within range `>=0.1.1,<0.2.0`)
- ✅ No schema code changes needed
- ✅ No version bump for schema

**Actions:**
1. Update common version: `0.1.1` → `0.1.2`
2. Push common package
3. Run `uv sync` in schema to get update
4. Verify tests pass

---

### Scenario 2: New Feature in Common (Minor, Backward-Compatible)

**Common: 0.1.2 → 0.2.0**

```python
# Add new constant
SUPPORTED_FRAMEWORKS = ["langgraph", "langchain", "crewai"]  # Added crewai

# Add new validation function
def validate_webhook_url(url: str):
    ...
```

**Impact:**
- ⚠️ Schema needs dependency update (current range blocks 0.2.0)
- ✅ No breaking changes in common
- ✅ Schema can optionally use new features

**Actions:**
1. Update common version: `0.1.2` → `0.2.0`
2. Update common CHANGELOG with new features
3. **Update schema dependency**:
   ```toml
   "agentdock-common>=0.2.0,<0.3.0"  # New range
   ```
4. Optionally add support for new framework in schema
5. Update schema version: `0.1.0` → `0.2.0` (if using new features)
6. Run tests, update docs

---

### Scenario 3: Breaking Change in Common (Major)

**Common: 0.2.0 → 1.0.0**

```python
# Breaking change: Rename constant
SUPPORTED_FRAMEWORKS = ...  # Old name
AGENT_FRAMEWORKS = ...      # New name (breaking!)

# Breaking change: Change function signature
def validate_entrypoint(entrypoint: str, strict: bool = True):  # Added param
    ...
```

**Impact:**
- ❌ Schema breaks if it uses old API
- ❌ Schema dependency blocks 1.0.0 (range: `<0.3.0`)
- 🔧 Schema needs code changes

**Actions:**
1. Update common version: `0.2.0` → `1.0.0`
2. Document breaking changes in CHANGELOG
3. **Update schema code** to use new API:
   ```python
   # Old
   from agentdock_common import SUPPORTED_FRAMEWORKS
   
   # New
   from agentdock_common import AGENT_FRAMEWORKS
   ```
4. **Update schema dependency**:
   ```toml
   "agentdock-common>=1.0.0,<2.0.0"  # New major version range
   ```
5. Update schema version: `0.2.0` → `1.0.0` (breaking change propagates)
6. Full test suite run
7. Update all docs

---

## Version Compatibility Matrix

### Current (v0.x Development Phase)

| Common Version | Schema Compatible | Notes |
|----------------|-------------------|-------|
| 0.1.0 | ❌ No | Schema needs 0.1.1+ (ConfigDict) |
| 0.1.1 | ✅ Yes | Current baseline |
| 0.1.2-0.1.x | ✅ Yes | Auto-compatible (patch updates) |
| 0.2.0 | ⚠️ Needs update | Dependency range must be updated |
| 1.0.0 | ❌ No | Would require schema v1.0.0 |

### Future (v1.x Stable Phase)

| Common Version | Schema Compatible | Notes |
|----------------|-------------------|-------|
| 1.0.0 | ✅ Yes | Stable baseline |
| 1.1.0-1.x.x | ✅ Yes | Backward-compatible features |
| 2.0.0 | ⚠️ Major update | Requires schema code changes |

---

## Upgrade Process

### For Users (Installing Packages)

#### Development Install (Editable)
```bash
# Install both packages in dev mode
cd AgentDock
pip install -e packages/common-py
pip install -e packages/schema

# Or using uv
uv pip install -e packages/common-py
uv pip install -e packages/schema
```

#### Production Install (From PyPI - Future)
```bash
# Will automatically resolve compatible versions
pip install agentdock-schema

# Explicitly pin versions
pip install agentdock-common==0.1.1 agentdock-schema==0.1.0
```

### For Developers (Upgrading Dependencies)

#### Step 1: Check Current Versions
```bash
cd packages/schema
uv pip list | grep agentdock
# agentdock-common    0.1.1
# agentdock-schema    0.1.0
```

#### Step 2: Update Common Package
```bash
cd packages/common-py
# Make changes
# Update version in pyproject.toml
# Update CHANGELOG.md
```

#### Step 3: Update Schema Dependency
```toml
# If common 0.1.1 → 0.1.2 (patch)
# No change needed, auto-compatible

# If common 0.1.x → 0.2.0 (minor)
dependencies = [
    "agentdock-common>=0.2.0,<0.3.0",  # Update range
]

# If common 0.x.x → 1.0.0 (major)
dependencies = [
    "agentdock-common>=1.0.0,<2.0.0",  # Update range + code changes
]
```

#### Step 4: Sync and Test
```bash
cd packages/schema
uv sync  # Update dependencies
uv run pytest tests/  # Verify all tests pass
```

#### Step 5: Update Schema Version (If Needed)
```toml
# If schema has new features or breaking changes
version = "0.2.0"  # or "1.0.0"
```

---

## Version Decision Tree

### When to Bump MAJOR (x.0.0)

- ✅ Removed a public API
- ✅ Changed function signature (removed/renamed params)
- ✅ Renamed constants that consumers use
- ✅ Changed error behavior (new exception types)
- ✅ Changed model field types (e.g., `str` → `int`)

**Example:**
```python
# Breaking: Renamed constant
# Old: SUPPORTED_FRAMEWORKS
# New: AGENT_FRAMEWORKS
# Version: 0.1.1 → 1.0.0
```

### When to Bump MINOR (x.y.0)

- ✅ Added new constants
- ✅ Added new functions/classes
- ✅ Added new optional fields to models
- ✅ Added new validation rules (more strict)
- ✅ Deprecated (but not removed) APIs

**Example:**
```python
# New feature: Add new framework
SUPPORTED_FRAMEWORKS = ["langgraph", "langchain", "crewai"]  # Added crewai
# Version: 0.1.1 → 0.2.0
```

### When to Bump PATCH (x.y.z)

- ✅ Bug fixes
- ✅ Performance improvements
- ✅ Documentation updates
- ✅ Internal refactoring (no API changes)
- ✅ Dependency updates (patch level)

**Example:**
```python
# Bug fix: Handle edge case
def validate_port(port: int):
    if port < 1 or port > 65535:
        raise ValidationError(f"Invalid port: {port}")  # Better message
# Version: 0.1.1 → 0.1.2
```

---

## CI/CD Considerations

### Automated Version Checking

```yaml
# .github/workflows/test.yml
- name: Check dependency compatibility
  run: |
    cd packages/schema
    uv pip check  # Verify no conflicts
```

### Lock Files (uv.lock)

```bash
# After changing dependencies, update lock file
uv lock

# Commit uv.lock to repo
git add uv.lock
git commit -m "chore: update dependency lock file"
```

### Release Workflow

```bash
# 1. Update version in pyproject.toml
# 2. Update CHANGELOG.md
# 3. Run tests
uv run pytest tests/

# 4. Commit
git add packages/*/pyproject.toml packages/*/CHANGELOG.md
git commit -m "chore: bump version to X.Y.Z"

# 5. Tag release (future, when publishing to PyPI)
git tag -a v0.1.1 -m "Release v0.1.1"
git push origin v0.1.1
```

---

## Best Practices

### 1. **Pin Internal Dependencies Conservatively**

```toml
# ✅ Good: Allow patch updates only
"agentdock-common>=0.1.1,<0.2.0"

# ⚠️ Risky: Allow any version
"agentdock-common"

# ⚠️ Too strict: Blocks bug fixes
"agentdock-common==0.1.1"
```

### 2. **Document Breaking Changes**

```markdown
# CHANGELOG.md

## [1.0.0] - Breaking Changes

### Changed
- **BREAKING**: Renamed `SUPPORTED_FRAMEWORKS` → `AGENT_FRAMEWORKS`
- **BREAKING**: `validate_entrypoint()` now requires `strict` parameter

### Migration Guide
```python
# Before
from agentdock_common import SUPPORTED_FRAMEWORKS

# After
from agentdock_common import AGENT_FRAMEWORKS
```
```

### 3. **Use Deprecation Warnings**

```python
import warnings

# Old API (deprecated but not removed)
def old_function():
    warnings.warn(
        "old_function() is deprecated, use new_function() instead",
        DeprecationWarning,
        stacklevel=2
    )
    return new_function()

# New API
def new_function():
    ...
```

### 4. **Test Matrix for Multiple Versions**

```yaml
# .github/workflows/test.yml
strategy:
  matrix:
    common-version: ['0.1.1', '0.1.2', '0.2.0']
```

---

## Monorepo vs Multi-Repo Considerations

**Current Setup: Monorepo** ✅

**Advantages:**
- Single version control
- Atomic commits across packages
- Easy local development
- Coordinated releases

**Dependency Management:**
```bash
# Development: Use local packages
pip install -e packages/common-py -e packages/schema

# Testing: Use specific versions
pip install agentdock-common==0.1.1 agentdock-schema==0.1.0
```

---

## Future: Publishing to PyPI

### Setup (One-time)

```bash
# Install build tools
pip install build twine

# Configure PyPI credentials
# Create ~/.pypirc
```

### Release Process

```bash
# 1. Build packages
cd packages/common-py
python -m build
cd ../schema
python -m build

# 2. Upload to PyPI
twine upload dist/*

# 3. Users can install
pip install agentdock-common agentdock-schema
```

---

## FAQs

### Q: Should I pin exact versions in development?

**A:** No. Use ranges (`>=0.1.1,<0.2.0`) to allow automatic patch updates.

### Q: What if a bug fix in common breaks schema?

**A:** The bug fix is actually a breaking change. Should be a major version bump.

### Q: Can I skip versions (e.g., 0.1.1 → 0.1.5)?

**A:** Yes, but document why in CHANGELOG. Usually happens when releasing multiple fixes together.

### Q: How do I handle pre-release versions?

**A:** Use suffixes: `0.1.0-alpha.1`, `0.1.0-beta.2`, `0.1.0-rc.1`

### Q: What about Python version compatibility?

**A:** Specified in `requires-python`:
```toml
requires-python = ">=3.12"  # Minimum Python version
```

---

## Summary

### Version Format
- `MAJOR.MINOR.PATCH` (SemVer)
- `0.x.x` = Development
- `1.0.0` = First stable release

### Dependency Specification
```toml
# Allow minor updates in same major version
"agentdock-common>=0.1.1,<0.2.0"
```

### Upgrade Checklist
1. ☐ Update version in pyproject.toml
2. ☐ Update CHANGELOG.md
3. ☐ Update dependent package ranges (if needed)
4. ☐ Run full test suite
5. ☐ Update documentation
6. ☐ Commit and tag release
7. ☐ Update uv.lock

---

## References

- [Semantic Versioning Spec](https://semver.org/)
- [Python Packaging Guide](https://packaging.python.org/)
- [PEP 440 - Version Identification](https://peps.python.org/pep-0440/)
- [Dependency Specifiers](https://peps.python.org/pep-0508/)

---

**Last Updated**: November 12, 2024  
**Current Versions**: common=0.1.1, schema=0.1.0

